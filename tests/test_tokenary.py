from __future__ import annotations

from enum import StrEnum
import importlib.util

import pytest

from tokenary.generator.catalog import (
    generate_catalog_artifacts,
    get_python_catalog_path,
    render_python_catalog,
    write_python_catalog_file,
)
from tokenary.tokenary import (
    Tokenary,
    calculate_usage_cost,
    load_catalog,
    load_embedded_catalog,
)
from tokenary.views import CostResponse, PricingCatalog, UsageCostRequest


def test_load_catalog_rejects_non_object_json(tmp_path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="not a JSON object"):
        load_catalog(path)


def test_generate_catalog_artifacts_delegates_fetch_and_write(
    monkeypatch, tmp_path
) -> None:
    output_path = tmp_path / "prices.json"
    python_path = get_python_catalog_path(tmp_path / "_generated.py")
    fake_data = {"sample_spec": {}, "m": {"mode": "chat"}}
    called = {"fetch": False, "write_json": False, "write_python": False}

    def fake_fetch(url: str):
        called["fetch"] = True
        assert url == "https://example.test/prices.json"
        return fake_data

    def fake_write_json(raw_prices, output_path):
        called["write_json"] = True
        assert raw_prices == fake_data
        assert str(output_path).endswith("prices.json")
        return output_path

    def fake_write_python(raw_prices, output_path):
        called["write_python"] = True
        assert raw_prices == fake_data
        assert output_path == python_path
        return output_path

    monkeypatch.setattr("tokenary.generator.catalog.fetch_model_prices_raw", fake_fetch)
    monkeypatch.setattr(
        "tokenary.generator.catalog.write_raw_prices_file", fake_write_json
    )
    monkeypatch.setattr(
        "tokenary.generator.catalog.write_python_catalog_file", fake_write_python
    )

    result_json, result_python = generate_catalog_artifacts(
        output_json_path=output_path,
        output_python_path=python_path,
        source_url="https://example.test/prices.json",
    )

    assert called["fetch"] is True
    assert called["write_json"] is True
    assert called["write_python"] is True
    assert result_json == output_path
    assert result_python == python_path


def test_calculate_usage_cost_all_components() -> None:
    catalog = PricingCatalog.from_raw(
        {
            "sample_spec": {},
            "test-model": {
                "input_cost_per_token": 0.001,
                "output_cost_per_token": 0.002,
                "output_cost_per_reasoning_token": 0.003,
                "input_cost_per_audio_token": 0.004,
                "output_cost_per_image": 0.5,
                "code_interpreter_cost_per_session": 2.0,
                "file_search_cost_per_1k_calls": 1.0,
                "file_search_cost_per_gb_per_day": 0.6,
                "vector_store_cost_per_gb_per_day": 0.7,
            },
        }
    )

    usage = UsageCostRequest(
        model="test-model",
        input_tokens=100,
        output_tokens=50,
        reasoning_tokens=10,
        audio_input_tokens=25,
        generated_images=2,
        code_interpreter_sessions=3,
        file_search_calls=500,
        file_search_gb_days=2.5,
        vector_store_gb_days=1.2,
    )

    breakdown = calculate_usage_cost(catalog, usage)

    assert breakdown.input_cost == pytest.approx(0.1)
    assert breakdown.output_cost == pytest.approx(0.1)
    assert breakdown.reasoning_cost == pytest.approx(0.03)
    assert breakdown.audio_input_cost == pytest.approx(0.1)
    assert breakdown.image_cost == pytest.approx(1.0)
    assert breakdown.code_interpreter_cost == pytest.approx(6.0)
    assert breakdown.file_search_call_cost == pytest.approx(0.5)
    assert breakdown.file_search_storage_cost == pytest.approx(1.5)
    assert breakdown.vector_store_cost == pytest.approx(0.84)
    assert breakdown.total_cost == pytest.approx(10.17)


def test_calculate_usage_cost_unknown_model() -> None:
    catalog = PricingCatalog.from_raw({"sample_spec": {}, "known": {"mode": "chat"}})

    with pytest.raises(KeyError, match="Unknown model"):
        calculate_usage_cost(catalog, UsageCostRequest(model="unknown"))


def test_render_python_catalog_contains_str_enum_members() -> None:
    rendered = render_python_catalog(
        {
            "sample_spec": {},
            "azure/gpt-35-turbo-0125": {"mode": "chat"},
            "1024-x-1024/dall-e-2": {"mode": "image_generation"},
        }
    )

    assert "class ModelName(StrEnum):" in rendered
    assert "AZURE_GPT_35_TURBO_0125" in rendered
    assert "MODEL_1024_X_1024_DALL_E_2" in rendered
    assert "GeneratedModelPricing.model_validate" in rendered
    assert "PRICING_AZURE_GPT_35_TURBO_0125" in rendered


def test_write_python_catalog_file_roundtrip(tmp_path) -> None:
    py_path = tmp_path / "prices.py"
    write_python_catalog_file(
        {
            "sample_spec": {},
            "azure/gpt-35-turbo-0125": {
                "mode": "chat",
                "input_cost_per_token": 0.000001,
            },
        },
        py_path,
    )

    spec = importlib.util.spec_from_file_location("generated_catalog", py_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert "azure/gpt-35-turbo-0125" in module.MODEL_PRICES_RAW
    assert module.MODEL_NAMES
    assert module.MODEL_PRICINGS_BY_NAME


def test_load_embedded_catalog_reads_generated_module(monkeypatch) -> None:
    fake_raw = {
        "sample_spec": {},
        "my-model": {
            "mode": "chat",
            "input_cost_per_token": 0.000001,
        },
    }
    monkeypatch.setattr(
        "tokenary.tokenary._generated.MODEL_PRICES_RAW", fake_raw, raising=False
    )

    catalog = load_embedded_catalog()
    assert "my-model" in catalog.models


def test_tokenary_calculate_accepts_model_enum() -> None:
    class LocalModel(StrEnum):
        TEST = "my-model"

    expected_catalog = PricingCatalog.from_raw(
        {"sample_spec": {}, "my-model": {"input_cost_per_token": 0.5}}
    )
    tokenary = Tokenary(catalog=expected_catalog)

    result = tokenary.calculate(model=LocalModel.TEST, input_tokens=2)
    assert result.total_cost == pytest.approx(1.0)


def test_tokenary_uses_embedded_catalog_by_default(monkeypatch) -> None:
    expected_catalog = PricingCatalog.from_raw(
        {"sample_spec": {}, "my-model": {"input_cost_per_token": 0.01}}
    )
    monkeypatch.setattr(
        "tokenary.tokenary.load_embedded_catalog", lambda: expected_catalog
    )

    tokenary = Tokenary()
    result = tokenary.calculate(request={"model": "my-model", "input_tokens": 3})

    assert isinstance(result, CostResponse)
    assert result.total_cost == pytest.approx(0.03)


def test_tokenary_rejects_catalog_and_catalog_path(tmp_path) -> None:
    catalog_path = tmp_path / "catalog.json"
    with pytest.raises(ValueError, match="either catalog or catalog_path"):
        Tokenary(
            catalog=PricingCatalog.from_raw({"sample_spec": {}}),
            catalog_path=catalog_path,
        )
