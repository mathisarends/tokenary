import pytest
from pydantic import ValidationError

from tokenary import PricingCatalog, calculate
from tokenary.generator.generator import build_catalog_payload
from tokenary.pricing import ModelPricing


@pytest.mark.parametrize(
    "field",
    [
        "input_cost_per_token_above_200K_tokens",
        "input_cost_per_token_above_0.2m_tokens",
        "output_cost_per_token_above_many_tokens",
        "cache_read_input_token_cost_above_200k_Tokens",
        "cache_creation_input_token_cost_above_1hr_above_200K_tokens",
        "input_cost_per_token_above_200k_tokens_typo",
    ],
)
def test_unsupported_context_field_fails_instead_of_using_base_rate(field):
    data = {"input_cost_per_token": 1, field: 2}
    with pytest.raises(ValidationError, match="Unsupported token-context tier") as exc:
        ModelPricing.model_validate(data)
    assert field in str(exc.value)
    with pytest.raises(ValidationError):
        build_catalog_payload({"custom": data})
    with pytest.raises(ValidationError):
        calculate(
            model="custom",
            input_tokens=200001,
            catalog=PricingCatalog.from_raw_prices({"custom": data}),
        )


@pytest.mark.parametrize(
    "scale,threshold", [("", 200), ("k", 200000), ("m", 200000000)]
)
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_numeric_tiers_have_strict_thresholds_and_preserve_zero(
    scale, threshold, offset
):
    data = {
        "input_cost_per_token": 1,
        "output_cost_per_token": 2,
        f"input_cost_per_token_above_200{scale}_tokens": 0,
        f"output_cost_per_token_above_200{scale}_tokens": 3,
    }
    tokens = threshold + offset
    result = calculate(
        model="tier",
        input_tokens=tokens,
        output_tokens=4,
        catalog=PricingCatalog.from_raw_prices({"tier": data}),
    )
    assert result.input_cost == (0 if offset > 0 else tokens)
    assert result.output_cost == (12 if offset > 0 else 8)


def test_ttl_service_tiers_and_unrelated_future_prices_are_distinct():
    data = {
        "input_cost_per_token": 1,
        "input_cost_per_token_above_200k_tokens_priority": 99,
        "cache_creation_input_token_cost_above_1hr": 2,
        "cache_creation_input_token_cost_above_1hr_above_200k_tokens": 3,
        "future_cost_per_widget": 4,
        "input_cost_per_video_per_second_above_15s_interval": 5,
    }
    prices = ModelPricing.model_validate(data)
    assert prices.rate("input_cost_per_token", 200001) == 1
    assert prices.rate("cache_creation_input_token_cost_above_1hr", 200000) == 2
    assert prices.rate("cache_creation_input_token_cost_above_1hr", 200001) == 3
    assert prices.model_dump()["future_cost_per_widget"] == 4
