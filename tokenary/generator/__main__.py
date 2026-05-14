from __future__ import annotations

import argparse
from pathlib import Path

from .catalog import (
    DEFAULT_JSON_CATALOG_FILE,
    DEFAULT_PYTHON_CATALOG_FILE,
    generate_catalog_artifacts,
)
from .downloader import DEFAULT_PRICE_URL


def cli_generate() -> None:
    parser = argparse.ArgumentParser(
        description="Generate local pricing artifacts from LiteLLM model price data."
    )
    parser.add_argument("--url", default=DEFAULT_PRICE_URL, help="Source JSON URL.")
    parser.add_argument(
        "--json-output",
        default=DEFAULT_JSON_CATALOG_FILE,
        help="Output JSON file path.",
    )
    parser.add_argument(
        "--python-output",
        default=DEFAULT_PYTHON_CATALOG_FILE,
        help="Output Python file path.",
    )
    parser.add_argument(
        "--no-json", action="store_true", help="Do not generate JSON output."
    )
    args = parser.parse_args()

    json_path, python_path = generate_catalog_artifacts(
        output_json_path=args.json_output,
        output_python_path=args.python_output,
        source_url=args.url,
        generate_json=not args.no_json,
    )

    if json_path is not None:
        print(f"Generated pricing JSON catalog: {json_path}")
    print(f"Generated pricing Python catalog: {Path(python_path)}")


def main() -> None:
    cli_generate()


if __name__ == "__main__":
    main()
