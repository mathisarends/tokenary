import pytest
from pydantic import ValidationError

from tokenary import MissingPriceError, PricingCatalog, UsageCostRequest, calculate
from tokenary.pricing import ModelPricing


def test_pixel_priced_image_request_fails_instead_of_looking_free():
    with pytest.raises(MissingPriceError) as exc:
        calculate(model="1024-x-1024/dall-e-2", generated_images=1)
    assert exc.value.price_field == "output_cost_per_image"
    assert exc.value.model == "1024-x-1024/dall-e-2"


def test_missing_price_is_only_required_for_nonzero_usage():
    catalog = PricingCatalog.from_raw_prices({"empty": {}})
    assert calculate(model="empty", catalog=catalog).total_cost == 0
    with pytest.raises(MissingPriceError, match="input_cost_per_token"):
        calculate(model="empty", input_tokens=1, catalog=catalog)


def test_explicit_zero_reasoning_price_is_not_replaced_by_output_rate():
    catalog = PricingCatalog.from_raw_prices(
        {"free-reasoning": {"output_cost_per_reasoning_token": 0.0}}
    )
    result = calculate(
        model="free-reasoning", output_tokens=40, reasoning_tokens=40, catalog=catalog
    )
    assert result.reasoning_cost == 0
    assert result.total_cost == 0


def test_openai_inclusive_output_totals_do_not_double_charge_reasoning():
    result = calculate(
        model="o1", input_tokens=100, output_tokens=1186, reasoning_tokens=1024
    )
    assert result.output_cost == pytest.approx(162 * 6e-5)
    assert result.reasoning_cost == pytest.approx(1024 * 6e-5)
    assert result.total_cost == pytest.approx(0.07266)


def test_openai_cached_tokens_are_subtracted_from_plain_input():
    result = calculate(model="gpt-4o", input_tokens=1000, cached_input_tokens=900)
    assert result.input_cost == pytest.approx(0.00025)
    assert result.cached_input_cost == pytest.approx(0.001125)
    assert result.total_cost == pytest.approx(0.001375)


@pytest.mark.parametrize("tokens, rate", [(200000, 3e-6), (200001, 6e-6)])
def test_context_boundary_changes_the_rate_for_the_whole_request(tokens, rate):
    result = calculate(
        model="claude-sonnet-4-20250514", input_tokens=tokens, output_tokens=1000
    )
    output_rate = 1.5e-5 if tokens == 200000 else 2.25e-5
    assert result.input_cost == pytest.approx(tokens * rate)
    assert result.output_cost == pytest.approx(1000 * output_rate)


def test_long_context_regression_from_review():
    result = calculate(
        model="claude-sonnet-4-20250514", input_tokens=250000, output_tokens=1000
    )
    assert result.total_cost == pytest.approx(1.5225)


def test_cache_reads_and_mixed_ttl_writes_use_total_context_size():
    catalog = PricingCatalog.from_raw_prices(
        {
            "cached": {
                "input_cost_per_token": 3e-6,
                "input_cost_per_token_above_200k_tokens": 6e-6,
                "cache_read_input_token_cost": 3e-7,
                "cache_read_input_token_cost_above_200k_tokens": 6e-7,
                "cache_creation_input_token_cost": 3.75e-6,
                "cache_creation_input_token_cost_above_200k_tokens": 7.5e-6,
                "cache_creation_input_token_cost_above_1hr": 6e-6,
                "cache_creation_input_token_cost_above_1hr_above_200k_tokens": 12e-6,
            }
        }
    )
    result = calculate(
        model="cached",
        catalog=catalog,
        input_tokens=250000,
        cached_input_tokens=100000,
        cache_creation_input_tokens=100000,
        cache_creation_1h_input_tokens=20000,
    )
    assert result.input_cost == pytest.approx(0.3)
    assert result.cached_input_cost == pytest.approx(0.06)
    assert result.cache_creation_cost == pytest.approx(0.84)
    assert result.total_cost == pytest.approx(1.2)


def test_highest_reached_tier_wins_and_output_length_does_not_trigger_it():
    catalog = PricingCatalog.from_raw_prices(
        {
            "tiers": {
                "input_cost_per_token": 1,
                "input_cost_per_token_above_128k_tokens": 2,
                "input_cost_per_token_above_256k_tokens": 3,
                "output_cost_per_token": 4,
                "output_cost_per_token_above_128k_tokens": 5,
            }
        }
    )
    assert calculate(
        model="tiers", input_tokens=300000, catalog=catalog
    ).input_cost == (900000)
    result = calculate(
        model="tiers", input_tokens=1, output_tokens=300000, catalog=catalog
    )
    assert result.output_cost == 1200000


def test_legacy_cache_hit_rate_is_supported():
    catalog = PricingCatalog.from_raw_prices(
        {"legacy-cache": {"input_cost_per_token_cache_hit": 0.01}}
    )
    result = calculate(
        model="legacy-cache", input_tokens=10, cached_input_tokens=10, catalog=catalog
    )
    assert result.total_cost == 0.1


@pytest.mark.parametrize(
    "usage",
    [
        {"input_tokens": 10, "cached_input_tokens": 11},
        {"input_tokens": 10, "cached_input_tokens": 5, "audio_input_tokens": 6},
        {"output_tokens": 10, "reasoning_tokens": 11},
        {"output_tokens": 10, "reasoning_tokens": 5, "audio_output_tokens": 6},
        {"cache_creation_1h_input_tokens": 1},
    ],
)
def test_inconsistent_token_subsets_are_rejected(usage):
    with pytest.raises(ValidationError):
        UsageCostRequest(model="gpt-4o", **usage)


@pytest.mark.parametrize("rate", [-1, float("nan"), float("inf"), True, "0.5"])
def test_known_and_future_price_fields_reject_invalid_rates(rate):
    for field in ["input_cost_per_token", "future_cost_per_widget"]:
        with pytest.raises(ValidationError):
            ModelPricing.model_validate({field: rate})


def test_request_and_conflicting_keyword_usage_are_rejected():
    request = UsageCostRequest(model="gpt-4o", input_tokens=100)
    with pytest.raises(ValueError, match="not both"):
        calculate(request, input_tokens=200)


def test_breakdown_total_and_catalog_provenance_are_serialized():
    result = calculate(model="gpt-4o", input_tokens=1000, output_tokens=500)
    dumped = result.model_dump()
    components = [value for name, value in dumped.items() if name.endswith("_cost")]
    assert result.total_cost == pytest.approx(sum(components) - result.total_cost)
    assert dumped["total_cost"] == result.total_cost
    assert len(dumped["pricing_source_sha256"]) == 64
    assert len(dumped["pricing_catalog_sha256"]) == 64
    changed = result.model_copy(update={"input_cost": 1.0})
    assert changed.total_cost == pytest.approx(1.0 + result.output_cost)
