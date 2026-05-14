import logging
import subprocess

from .downloader import fetch_model_prices_raw, write_raw_prices_file
from .generator import write_python_catalog_file

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

_JSON_OUTPUT = "data/model_prices.generated.json"
_PYTHON_OUTPUT = "tokenary/_generated.py"


def main() -> None:
    logger.info("Tokenary Price Generator\n")

    raw_prices = fetch_model_prices_raw()
    logger.info(f"✓ Downloaded {len(raw_prices)} models")

    write_raw_prices_file(raw_prices, _JSON_OUTPUT)
    logger.info(f"✓ Saved JSON: {_JSON_OUTPUT}")

    python_path = write_python_catalog_file(raw_prices, _PYTHON_OUTPUT)
    logger.info(f"✓ Generated Python: {_PYTHON_OUTPUT}")

    subprocess.run(["ruff", "check", "--fix", str(python_path)])
    subprocess.run(["ruff", "format", str(python_path)], check=True)
    logger.info(f"✓ Linted: {_PYTHON_OUTPUT}")

    logger.info("\n✅ Generation complete!")


if __name__ == "__main__":
    main()
