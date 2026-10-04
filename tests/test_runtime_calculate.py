import pytest
from pydantic import ValidationError

from tokenary import ModelName, PricingCatalog, UsageCostRequest, calculate


def test_calculate_returns_full_breakdown_for_all_cost_components() -> None:
    catalog = PricingCatalog.from_raw_prices(
        {
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
        }
    )
    result = calculate(
        model="demo-model",
        catalog=catalog,
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
    assert result.model == "demo-model"
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
    assert catalog.loaded_model_count == 1


def test_calculate_uses_output_rate_when_reasoning_rate_is_missing() -> None:
    catalog = PricingCatalog.from_raw_prices(
        {"reasoning-fallback": {"output_cost_per_token": 0.002}}
    )
    result = calculate(model="reasoning-fallback", reasoning_tokens=40, catalog=catalog)
    assert result.reasoning_cost == pytest.approx(0.08)
    assert result.total_cost == pytest.approx(0.08)


def test_calculate_accepts_usage_request_instance_and_selected_enum() -> None:
    catalog = PricingCatalog.from_raw_prices(
        {"custom-model": {"input_cost_per_token": 0.25}}
    )
    request = UsageCostRequest(model=catalog.model_enum.CUSTOM_MODEL, input_tokens=4)
    result = calculate(request, catalog=catalog)
    assert result.total_cost == pytest.approx(1.0)


def test_calculate_requires_request_or_model() -> None:
    with pytest.raises(ValueError, match="Either request or model must be provided"):
        calculate()


def test_calculate_rejects_unknown_model() -> None:
    catalog = PricingCatalog.from_raw_prices({"known-model": {}})
    with pytest.raises(KeyError, match="Unknown model"):
        calculate(model="missing-model", input_tokens=1, catalog=catalog)
    assert catalog.loaded_model_count == 0


def test_default_calculation_still_accepts_original_enum() -> None:
    result = calculate(model=ModelName.GPT_4O, input_tokens=1000, output_tokens=500)
    assert result.total_cost == pytest.approx(0.0075)


@pytest.mark.parametrize(
    "usage",
    [
        {"input_tokens": -1},
        {"generated_images": -1},
        {"file_search_gb_days": -0.5},
        {"vector_store_gb_days": float("nan")},
        {"vector_store_gb_days": float("inf")},
        {"misspelled_input_tokens": 100},
    ],
)
def test_request_rejects_invalid_usage(usage) -> None:
    with pytest.raises(ValidationError):
        UsageCostRequest(model="gpt-4o", **usage)
