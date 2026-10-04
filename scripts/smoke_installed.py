"""Verify an installed wheel in isolation, without Ruff or provider SDKs."""

import importlib.metadata
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir

import tokenary
from tokenary.catalog import get_default_catalog


def main() -> None:
    assert "site-packages" in tokenary.__file__, tokenary.__file__
    assert importlib.util.find_spec("ruff") is None
    assert importlib.util.find_spec("openai") is None
    assert importlib.util.find_spec("anthropic") is None
    assert get_default_catalog.cache_info().currsize == 0

    installed = importlib.metadata.distribution("tokenary")
    sources = [entry for entry in installed.files if entry.suffix == ".py"]
    source_bytes = sum(installed.locate_file(entry).stat().st_size for entry in sources)
    assert source_bytes < 64000, f"Runtime source budget exceeded: {source_bytes}"
    assert not any(entry.name == "_generated.py" for entry in sources)
    assert not any(
        entry.name == "model_prices.generated.json" for entry in installed.files
    )

    with TemporaryDirectory(prefix="tokenary-wheel-smoke-") as directory:
        root = Path(directory).resolve()
        assert root.parent == Path(gettempdir()).resolve()
        source = root / "source.json"
        source.write_text(
            json.dumps(
                {
                    "gpt-4o": {
                        "input_cost_per_token": 2.5e-6,
                        "cache_read_input_token_cost": 1.25e-6,
                    },
                    "unused": {"input_cost_per_token": 1},
                }
            ),
            encoding="utf-8",
        )
        output = root / "selected.py"
        args = [
            sys.executable,
            "-I",
            "-m",
            "tokenary.generator",
            "--input",
            str(source),
            "--models",
            "gpt-4o",
            "--output",
            str(output),
        ]
        subprocess.run(args, cwd=root, check=True)
        subprocess.run([*args, "--check"], cwd=root, check=True)
        spec = importlib.util.spec_from_file_location("selected_prices", output)
        selected = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(selected)
        result = selected.calculate(
            model=selected.ModelName.GPT_4O,
            input_tokens=1000,
            cached_input_tokens=900,
        )
        assert abs(result.total_cost - 0.001375) < 1e-12
        assert len(selected.ModelName) == 1
        assert selected.CATALOG.loaded_model_count == 1
        assert get_default_catalog.cache_info().currsize == 0
        subset_bytes = output.stat().st_size

    result = tokenary.calculate(model="gpt-4o", input_tokens=1000)
    assert result.total_cost == 0.0025
    assert get_default_catalog().loaded_model_count == 1
    print(f"Installed wheel verified; source={source_bytes} B, subset={subset_bytes} B")


if __name__ == "__main__":
    main()
