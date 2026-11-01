"""Rebuild the package's private provider resources from a pinned snapshot."""

import argparse
import gzip
import json
import re
from collections.abc import Mapping
from pathlib import Path

from tokenary._serialization import canonical_json, content_hash, write_atomic
from tokenary.catalog import BUNDLE_FORMAT_VERSION, PROVIDER_FILENAME

from .generator import build_catalog_payload, catalog_file_matches


def render_bundle(
    raw_prices: Mapping[str, object],
    *,
    source: str,
    previous_names: Mapping[str, str] | None = None,
) -> dict[str, bytes]:
    """Return a price-free index and independently checksummed provider catalogs."""
    full = build_catalog_payload(
        raw_prices, source=source, previous_names=previous_names
    )
    groups = {}
    for model, prices in full["models"].items():
        provider = prices.get("litellm_provider")
        groups.setdefault(provider, {})[model] = prices
    artifacts = {}
    model_providers = {}
    checksums = {}
    for provider, prices in groups.items():
        slug = re.sub(r"[^a-z0-9]+", "-", (provider or "unknown").lower()).strip("-")
        filename = f"{slug[:40] or 'unknown'}-{content_hash(provider)}.json.gz"
        names = {model: full["enum_names"][model] for model in prices}
        checksum = content_hash({"models": prices, "enum_names": names})
        payload = {
            "format_version": full["format_version"],
            "metadata": {**full["metadata"], "catalog_sha256": checksum},
            "models": prices,
            "enum_names": names,
        }
        artifacts[f"providers/{filename}"] = gzip.compress(
            canonical_json(payload), mtime=0
        )
        checksums[filename] = checksum
        model_providers.update({model: filename for model in prices})
    index = {
        "bundle_format_version": BUNDLE_FORMAT_VERSION,
        "metadata": full["metadata"],
        "enum_names": full["enum_names"],
        "model_providers": model_providers,
        "provider_checksums": checksums,
    }
    index["index_sha256"] = content_hash(index)
    artifacts["index.json.gz"] = gzip.compress(canonical_json(index), mtime=0)
    return artifacts


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        previous = {}
        index_path = args.output_dir / "index.json.gz"
        if index_path.exists():
            previous = json.loads(gzip.decompress(index_path.read_bytes()))[
                "enum_names"
            ]
        # Migration from the original single bundled file, retaining every alias.
        legacy_path = args.output_dir / "catalog.json.gz"
        if not previous and legacy_path.exists():
            previous = json.loads(gzip.decompress(legacy_path.read_bytes()))[
                "enum_names"
            ]
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Model price source must be a JSON object")
        artifacts = render_bundle(raw, source=args.source, previous_names=previous)
        stale = [
            path
            for path in (args.output_dir / "providers").glob("*.json.gz")
            if PROVIDER_FILENAME.fullmatch(path.name)
            and f"providers/{path.name}" not in artifacts
        ]
        if args.check:
            drift = [
                name
                for name, data in artifacts.items()
                if not catalog_file_matches(args.output_dir / name, data)
            ]
            if drift or stale:
                parser.exit(
                    1,
                    "Bundled catalog drift: "
                    f"{', '.join(drift + [p.name for p in stale])}\n",
                )
        else:
            # Validate everything first; publish the index after its provider resources.
            for name, data in artifacts.items():
                write_atomic(args.output_dir / name, data)
            for path in stale:
                path.unlink()
        print(
            f"Bundled catalog {'verified' if args.check else 'generated'}: "
            f"{len(artifacts) - 1} providers"
        )
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Bundle generation failed: {exc}\n")


if __name__ == "__main__":
    main()
