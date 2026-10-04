import pytest
from pydantic import BaseModel, ValidationError

from tokenary import (
    UnsupportedUsageError,
    calculate,
    from_anthropic_usage,
    from_openai_usage,
)


@pytest.mark.parametrize(
    "usage",
    [
        {
            "input_tokens": 100,
            "output_tokens": 1186,
            "output_tokens_details": {"reasoning_tokens": 1024},
            "total_tokens": 1286,
        },
        {
            "prompt_tokens": 100,
            "completion_tokens": 1186,
            "completion_tokens_details": {"reasoning_tokens": 1024},
            "total_tokens": 1286,
        },
    ],
)
def test_both_openai_shapes_bill_reasoning_once(usage):
    request = from_openai_usage("o1", usage)
    assert request.output_tokens == 1186
    assert request.reasoning_tokens == 1024
    assert calculate(request).total_cost == pytest.approx(0.07266)


def test_openai_sdk_usage_objects_work_without_sdk_dependencies():
    class SDKUsage(BaseModel):
        prompt_tokens: int
        completion_tokens: int
        prompt_tokens_details: dict[str, int]
        completion_tokens_details: None = None

    usage = SDKUsage(
        prompt_tokens=1000,
        completion_tokens=0,
        prompt_tokens_details={"cached_tokens": 900},
    )
    request = from_openai_usage("gpt-4o", usage)
    assert request.cached_input_tokens == 900
    assert calculate(request).total_cost == pytest.approx(0.001375)


def test_anthropic_separate_counters_and_cache_ttls_are_normalized():
    request = from_anthropic_usage(
        "claude-sonnet-4-20250514",
        {
            "input_tokens": 50,
            "output_tokens": 10,
            "cache_read_input_tokens": 1000,
            "cache_creation_input_tokens": 100,
            "cache_creation": {
                "ephemeral_5m_input_tokens": 80,
                "ephemeral_1h_input_tokens": 20,
            },
        },
    )
    assert request.input_tokens == 1150
    assert request.cached_input_tokens == 1000
    assert request.cache_creation_1h_input_tokens == 20
    result = calculate(request)
    assert result.total_cost == pytest.approx(
        50 * 3e-6 + 10 * 1.5e-5 + 1000 * 3e-7 + 80 * 3.75e-6 + 20 * 6e-6
    )


def test_anthropic_cache_tokens_also_trigger_context_tariff():
    request = from_anthropic_usage(
        "claude-sonnet-4-20250514",
        {"input_tokens": 1, "output_tokens": 1, "cache_read_input_tokens": 200000},
    )
    assert request.input_tokens == 200001
    result = calculate(request)
    assert result.cached_input_cost == pytest.approx(200000 * 6e-7)
    assert result.output_cost == pytest.approx(2.25e-5)


def test_optional_null_sdk_detail_counts_are_zero():
    request = from_openai_usage(
        "gpt-4o",
        {
            "prompt_tokens": 100,
            "completion_tokens": 10,
            "prompt_tokens_details": {"cached_tokens": None, "audio_tokens": None},
            "completion_tokens_details": {
                "reasoning_tokens": None,
                "audio_tokens": None,
            },
        },
    )
    assert request.cached_input_tokens == 0
    assert request.reasoning_tokens == 0


@pytest.mark.parametrize("usage", [None, object(), 123])
def test_adapter_rejects_objects_without_structured_usage(usage):
    with pytest.raises(TypeError):
        from_openai_usage("gpt-4o", usage)


@pytest.mark.parametrize(
    "usage",
    [
        {},
        {"input_tokens": 1},
        {"input_tokens": -1, "output_tokens": 1},
        {"input_tokens": True, "output_tokens": 1},
        {"input_tokens": 1, "output_tokens": 1, "total_tokens": 100},
        {"input_tokens": 1, "output_tokens": 1, "input_tokens_details": []},
        {
            "input_tokens": 1,
            "output_tokens": 1,
            "input_tokens_details": {"cached_tokens": 2},
        },
    ],
)
def test_adapter_rejects_malformed_or_inconsistent_openai_usage(usage):
    with pytest.raises((ValueError, ValidationError)):
        from_openai_usage("gpt-4o", usage)


def test_adapter_rejects_ambiguous_audio_cache_overlap():
    with pytest.raises(UnsupportedUsageError, match="split"):
        from_openai_usage(
            "audio-model",
            {
                "prompt_tokens": 100,
                "completion_tokens": 0,
                "prompt_tokens_details": {"cached_tokens": 50, "audio_tokens": 80},
            },
        )


def test_anthropic_negative_counters_cannot_cancel_each_other():
    with pytest.raises(ValueError):
        from_anthropic_usage(
            "claude",
            {"input_tokens": 100, "output_tokens": 0, "cache_read_input_tokens": -10},
        )


def test_anthropic_ttl_counts_must_agree():
    with pytest.raises(ValueError, match="TTL"):
        from_anthropic_usage(
            "claude",
            {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_input_tokens": 100,
                "cache_creation": {"ephemeral_5m_input_tokens": 50},
            },
        )


@pytest.mark.parametrize(
    "extra",
    [{"service_tier": "priority"}, {"server_tool_use": {"web_search_requests": 1}}],
)
def test_anthropic_unsupported_billing_is_explicit(extra):
    with pytest.raises(UnsupportedUsageError):
        from_anthropic_usage("claude", {"input_tokens": 1, "output_tokens": 1, **extra})
