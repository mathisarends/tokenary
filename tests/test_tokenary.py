import pytest

from tokenary.tokenary import calculate_usage_cost, generate_catalog_file, load_catalog
from tokenary.views import PricingCatalog, UsageCostRequest


def test_load_catalog_rejects_non_object_json(tmp_path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="not a JSON object"):
        load_catalog(path)


def test_generate_catalog_file_delegates_fetch_and_write(monkeypatch, tmp_path) -> None:
    output_path = tmp_path / "prices.json"
    fake_data = {"sample_spec": {}, "m": {"mode": "chat"}}
    called = {"fetch": False, "write": False}

    def fake_fetch(url: str):
        called["fetch"] = True
        assert url == "https://example.test/prices.json"
        return fake_data

    def fake_write(raw_prices, output_path):
        called["write"] = True
        assert raw_prices == fake_data
        assert str(output_path).endswith("prices.json")
        return output_path

    monkeypatch.setattr("tokenary.tokenary.fetch_model_prices_raw", fake_fetch)
    monkeypatch.setattr("tokenary.tokenary.write_raw_prices_file", fake_write)

    result = generate_catalog_file(
        output_path=output_path,
        source_url="https://example.test/prices.json",
    )

    assert called["fetch"] is True
    assert called["write"] is True
    assert result == output_path


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