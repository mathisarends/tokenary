import gzip
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tokenary._serialization import content_hash
from tokenary.catalog import PricingCatalog
from tokenary.generator.__main__ import main
from tokenary.generator.generator import (
    build_catalog_payload,
    catalog_file_matches,
    read_existing_enum_names,
    render_catalog_file,
    render_python_catalog,
)


@pytest.fixture
def raw_prices():
    return {
        "sample_spec": {},
        "gpt-4o": {
            "input_cost_per_token": 2.5e-6,
            "output_cost_per_token": 1e-5,
            "cache_read_input_token_cost": 1.25e-6,
            "future_cost_per_widget": 0.2,
            "litellm_provider": "openai",
            "max_input_tokens": 128000,
            "supports_vision": True,
        },
        "unused": {"output_cost_per_token": 1},
        "provider/model-a": {"input_cost_per_token": 0.1},
        "provider/model.a": {"input_cost_per_token": 0.2},
    }


def test_selected_output_only_contains_requested_prices_and_relevant_data(raw_prices):
    payload = build_catalog_payload(raw_prices, models=["gpt-4o"])
    assert set(payload["models"]) == {"gpt-4o"}
    assert set(payload["enum_names"]) == {"gpt-4o"}
    pricing = payload["models"]["gpt-4o"]
    assert pricing["cache_read_input_token_cost"] == 1.25e-6
    assert pricing["future_cost_per_widget"] == 0.2
    assert "max_input_tokens" not in pricing
    assert "supports_vision" not in pricing
    assert payload["metadata"]["source_sha256"] == content_hash(raw_prices)


@pytest.mark.parametrize("models", [["missing"], [], ["sample_spec"]])
def test_generator_rejects_invalid_or_empty_selection(raw_prices, models):
    with pytest.raises(ValueError):
        build_catalog_payload(raw_prices, models=models)


def test_subset_enum_names_match_full_catalog_and_survive_new_collisions(raw_prices):
    full = build_catalog_payload(raw_prices)
    subset = build_catalog_payload(raw_prices, models=["provider/model.a"])
    assert (
        subset["enum_names"]["provider/model.a"]
        == full["enum_names"]["provider/model.a"]
    )
    previous = full["enum_names"]
    raw_prices["provider/model+a"] = {}
    updated = build_catalog_payload(raw_prices, previous_names=previous)
    for name, alias in previous.items():
        assert updated["enum_names"][name] == alias
    assert updated["enum_names"]["provider/model+a"] not in previous.values()


def test_generation_is_byte_reproducible_even_if_source_order_changes(raw_prices):
    forward = build_catalog_payload(raw_prices, models=["gpt-4o", "unused"])
    reverse = build_catalog_payload(
        dict(reversed(list(raw_prices.items()))), models=["unused", "gpt-4o"]
    )
    for path in ["prices.py", "prices.json", "prices.json.gz"]:
        assert render_catalog_file(forward, path) == render_catalog_file(reverse, path)


def test_gzip_drift_check_ignores_compressor_and_header_differences(
    tmp_path, raw_prices
):
    path = tmp_path / "prices.json.gz"
    rendered = render_catalog_file(build_catalog_payload(raw_prices), path)
    other_encoding = gzip.compress(
        gzip.decompress(rendered), compresslevel=1, mtime=123
    )
    assert other_encoding != rendered
    path.write_bytes(other_encoding)
    assert catalog_file_matches(path, rendered)
    raw_prices["gpt-4o"]["input_cost_per_token"] = 100
    changed = render_catalog_file(build_catalog_payload(raw_prices), path)
    assert not catalog_file_matches(path, changed)


def test_generated_subset_uses_its_own_catalog_without_loading_default(
    tmp_path, raw_prices
):
    output = tmp_path / "selected.py"
    output.write_text(
        render_python_catalog(raw_prices, models=["gpt-4o"]), encoding="utf-8"
    )
    code = """
import importlib.util
import sys
from tokenary.catalog import get_default_catalog
spec = importlib.util.spec_from_file_location('selected', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert module.CATALOG.loaded_model_count == 0
result = module.calculate(model=module.ModelName.GPT_4O, input_tokens=1000)
assert result.total_cost == 0.0025
assert module.CATALOG.loaded_model_count == 1
assert get_default_catalog.cache_info().currsize == 0
assert len(module.ModelName) == 1
"""
    subprocess.run([sys.executable, "-c", code, str(output)], check=True)


def test_cli_generates_subset_detects_drift_and_preserves_files(
    tmp_path, raw_prices, capsys
):
    source = tmp_path / "source.json"
    source.write_text(json.dumps(raw_prices), encoding="utf-8")
    output = tmp_path / "selected.py"
    args = ["--input", str(source), "--models", "gpt-4o", "--output", str(output)]
    main(args)
    original = output.read_bytes()
    main([*args, "--check"])
    assert "up to date" in capsys.readouterr().out
    # Formatting-only changes must not be mistaken for price or API drift.
    output.write_bytes(b"# formatted by another tool\n" + original)
    main([*args, "--check"])

    raw_prices["gpt-4o"]["input_cost_per_token"] = 0.5
    source.write_text(json.dumps(raw_prices), encoding="utf-8")
    before = output.read_bytes()
    with pytest.raises(SystemExit) as exc:
        main([*args, "--check"])
    assert exc.value.code == 1
    assert output.read_bytes() == before
    assert "drift" in capsys.readouterr().err


def test_cli_failed_selection_never_overwrites_existing_output(tmp_path, raw_prices):
    source = tmp_path / "source.json"
    source.write_text(json.dumps(raw_prices), encoding="utf-8")
    output = tmp_path / "keep.py"
    output.write_text("# keep this file\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["--input", str(source), "--models", "missing", "--output", str(output)])
    assert exc.value.code == 1
    assert output.read_text(encoding="utf-8") == "# keep this file\n"


@pytest.mark.parametrize("suffix", [".json", ".json.gz"])
def test_cli_data_catalog_preserves_names_across_updates(tmp_path, suffix):
    source = tmp_path / "source.json"
    output = tmp_path / f"selected{suffix}"
    prices = {"review/model-a": {"input_cost_per_token": 1}}
    source.write_text(json.dumps(prices), encoding="utf-8")
    args = ["--input", str(source), "--all", "--output", str(output)]
    main(args)
    original = read_existing_enum_names(output)
    prices["review/model+a"] = {"input_cost_per_token": 2}
    source.write_text(json.dumps(prices), encoding="utf-8")
    main(args)
    catalog = PricingCatalog.from_file(output)
    assert catalog.enum_names["review/model-a"] == original["review/model-a"]
    main([*args, "--check"])


def test_cli_requires_explicit_model_selection():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_committed_catalog_matches_pinned_source():
    root = Path(__file__).resolve().parents[1]
    source = root / "data/model_prices.generated.json"
    output = root / "tokenary/data/catalog.json.gz"
    main(
        [
            "--input",
            str(source),
            "--source",
            "https://raw.githubusercontent.com/BerriAI/litellm/main/"
            "model_prices_and_context_window.json",
            "--all",
            "--output",
            str(output),
            "--check",
        ]
    )
