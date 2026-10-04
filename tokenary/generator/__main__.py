import argparse
import json
from pathlib import Path

from tokenary._serialization import write_atomic
from tokenary.catalog import get_default_catalog

from .downloader import _DEFAULT_PRICE_URL, fetch_model_prices_raw
from .generator import (
    build_catalog_payload,
    catalog_file_matches,
    read_existing_enum_names,
    render_catalog_file,
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate a compact offline catalog for selected models."
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--models", "--model", action="extend", nargs="+", help="Exact model IDs"
    )
    selection.add_argument("--all", action="store_true", help="Include every model")
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--input", type=Path, help="Pinned LiteLLM JSON snapshot")
    inputs.add_argument("--url", help="LiteLLM JSON URL (defaults to latest upstream)")
    parser.add_argument("--source", help="Source identifier recorded in metadata")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("model_prices.py"),
        help=".py/.json/.json.gz",
    )
    parser.add_argument(
        "--check", action="store_true", help="Fail on drift; never write output"
    )
    args = parser.parse_args(argv)

    try:
        if args.input:
            raw_prices = json.loads(args.input.read_text(encoding="utf-8"))
            source = args.source or args.input.as_posix()
        else:
            url = args.url or _DEFAULT_PRICE_URL
            raw_prices = fetch_model_prices_raw(url=url)
            source = args.source or url
        if not isinstance(raw_prices, dict):
            raise ValueError("Model price source must be a JSON object")

        # Preserve the bundled public names, then prefer this output's own history.
        try:
            previous_names = dict(get_default_catalog().enum_names)
        except FileNotFoundError:
            previous_names = {}
        previous_names.update(read_existing_enum_names(args.output))
        payload = build_catalog_payload(
            raw_prices,
            models=None if args.all else args.models,
            source=source,
            previous_names=previous_names,
        )
        rendered = render_catalog_file(payload, args.output)
        if args.check:
            if not catalog_file_matches(args.output, rendered):
                parser.exit(1, f"Catalog drift detected: {args.output}\n")
            print(f"Catalog is up to date: {args.output}")
        else:
            write_atomic(args.output, rendered)
            print(f"Generated {len(payload['models'])} models: {args.output}")
    except (OSError, ValueError, SyntaxError) as exc:
        parser.exit(1, f"Generation failed: {exc}\n")


if __name__ == "__main__":
    main()
