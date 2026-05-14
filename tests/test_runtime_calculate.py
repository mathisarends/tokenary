from __future__ import annotations

import pytest

from tokenary import ModelName
from tokenary.tokenary import calculate
from tokenary.views import PricingCatalog, UsageCostRequest


def test_calculate_returns_full_breakdown_for_all_cost_components(monkeypatch) -> None:
    catalog = PricingCatalog.model_validate(
        {
            "sample_spec": None,
            "models": {
                "demo-model": {
                    "input_cost_per_token": 0.001,
                    "output_cost_per_token": 0.002,
                    "output_cost_per_reasoning_token": 0.003,
                    "input_cost_per_audio_token": 0.004,
                    "output_cost_per_image": 0.5,
                    "code_interpreter_cost_per_session": 2.0,
                    "file_search_cost_per_1k_calls": 1.0,
                    "file_search_cost_per_gb_per_day": 0.6,
                    "vector_store_cost_per_gb_per_day": 0.7,
                }
            },
        }
    )
    catalog.models[ModelName.GPT_4O.value] = catalog.models.pop("demo-model")
    monkeypatch.setattr("tokenary.tokenary._get_catalog", lambda: catalog)

    result = calculate(
        model=ModelName.GPT_4O.value,
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

    assert result.model == ModelName.GPT_4O.value
    assert result.input_cost == pytest.approx(0.1)
    assert result.output_cost == pytest.approx(0.1)
    assert result.reasoning_cost == pytest.approx(0.03)
    assert result.audio_input_cost == pytest.approx(0.1)
    assert result.image_cost == pytest.approx(1.0)
    assert result.code_interpreter_cost == pytest.approx(6.0)
    assert result.file_search_call_cost == pytest.approx(0.5)
    assert result.file_search_storage_cost == pytest.approx(1.5)
    assert result.vector_store_cost == pytest.approx(0.84)
    assert result.total_cost == pytest.approx(10.17)


def test_calculate_uses_output_rate_when_reasoning_rate_is_missing(monkeypatch) -> None:
    catalog = PricingCatalog.model_validate(
        {
            "sample_spec": None,
            "models": {
                "reasoning-fallback": {
                    "output_cost_per_token": 0.002,
                }
            },
        }
    )
    catalog.models[ModelName.GPT_4O.value] = catalog.models.pop("reasoning-fallback")
    monkeypatch.setattr("tokenary.tokenary._get_catalog", lambda: catalog)

    result = calculate(model=ModelName.GPT_4O.value, reasoning_tokens=40)

    assert result.reasoning_cost == pytest.approx(0.08)
    assert result.total_cost == pytest.approx(0.08)


def test_calculate_accepts_usage_request_instance(monkeypatch) -> None:
    catalog = PricingCatalog.model_validate(
        {
            "sample_spec": None,
            "models": {
                "request-model": {
                    "input_cost_per_token": 0.25,
                }
            },
        }
    )
    catalog.models[ModelName.GPT_4O.value] = catalog.models.pop("request-model")
    monkeypatch.setattr("tokenary.tokenary._get_catalog", lambda: catalog)

    request = UsageCostRequest(model=ModelName.GPT_4O, input_tokens=4)
    result = calculate(request)

    assert result.total_cost == pytest.approx(1.0)


def test_calculate_requires_request_or_model() -> None:
    with pytest.raises(ValueError, match="Either request or model must be provided"):
        calculate()


def test_calculate_rejects_unknown_model(monkeypatch) -> None:
    catalog = PricingCatalog.model_validate(
        {
            "sample_spec": None,
            "models": {
                "known-model": {
                    "input_cost_per_token": 1.0,
                }
            },
        }
    )
    catalog.models[ModelName.GPT_4O_MINI.value] = catalog.models.pop("known-model")
    monkeypatch.setattr("tokenary.tokenary._get_catalog", lambda: catalog)

    with pytest.raises(KeyError, match="Unknown model"):
        calculate(model=ModelName.GPT_4O.value, input_tokens=1)
