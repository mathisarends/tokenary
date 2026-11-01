"""Offline example: generate provider/model subsets and explicitly use their data."""

import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from tokenary import PricingCatalog, calculate


def main() -> None:
    with TemporaryDirectory(prefix="tokenary-example-") as directory:
        root = Path(directory)
        source = root / "prices.lock.json"
        source.write_text(
            json.dumps(
                {
                    "example/new-chat": {
                        "litellm_provider": "example",
                        "input_cost_per_token": 0.25,
                    },
                    "example/unused": {
                        "litellm_provider": "example",
                        "input_cost_per_token": 0.5,
                    },
                    "other/model": {
                        "litellm_provider": "other",
                        "input_cost_per_token": 1,
                    },
                }
            ),
            encoding="utf-8",
        )
        # Generating an artifact does not change the library's default catalog.
        for selection, output in (
            (["--provider", "example"], root / "provider.json"),
            (["--model", "example/new-chat"], root / "model.json"),
            (
                ["--provider", "example", "--model", "example/new-chat"],
                root / "combined.json.gz",
            ),
        ):
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tokenary.generator",
                    "--input",
                    str(source),
                    *selection,
                    "--output",
                    str(output),
                ],
                cwd=root,
                check=True,
            )
            catalog = PricingCatalog.from_file(output)
            result = calculate(
                model="example/new-chat", input_tokens=4, catalog=catalog
            )
            assert result.total_cost == 1
            print(
                f"{output.name}: {len(catalog.models)} models, "
                f"cost ${result.total_cost:.2f}"
            )


if __name__ == "__main__":
    main()
