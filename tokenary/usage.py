"""Normalize provider token counters without importing provider SDKs."""

from collections.abc import Mapping

from .errors import UnsupportedUsageError
from .views import UsageCostRequest


def _as_mapping(usage: object) -> Mapping[str, object]:
    if isinstance(usage, Mapping):
        return usage
    dump = getattr(usage, "model_dump", None)
    if callable(dump):
        value = dump()
        if isinstance(value, Mapping):
            return value
    raise TypeError("Usage must be a mapping or an SDK object with model_dump()")


def _details(usage: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = usage.get(key)
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be an object or null")
    return value


def _tokens(usage: Mapping[str, object], key: str, *, required: bool = False) -> int:
    if required and key not in usage:
        raise ValueError(f"Usage is missing {key}")
    value = usage.get(key, 0)
    if value is None and not required:
        return 0
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{key} must be a nonnegative integer")
    return value


def from_openai_usage(model: str, usage: object) -> UsageCostRequest:
    """Accept Responses or Chat Completions usage, preserving inclusive totals."""
    data = _as_mapping(usage)
    if data.get("service_tier") not in (None, "default", "standard"):
        raise UnsupportedUsageError("Only standard service-tier pricing is supported")
    if "input_tokens" in data:
        input_key, output_key = "input_tokens", "output_tokens"
        input_detail_key, output_detail_key = (
            "input_tokens_details",
            "output_tokens_details",
        )
    elif "prompt_tokens" in data:
        input_key, output_key = "prompt_tokens", "completion_tokens"
        input_detail_key, output_detail_key = (
            "prompt_tokens_details",
            "completion_tokens_details",
        )
    else:
        raise ValueError("Unrecognized OpenAI usage shape")

    input_tokens = _tokens(data, input_key, required=True)
    output_tokens = _tokens(data, output_key, required=True)
    if "total_tokens" in data:
        if _tokens(data, "total_tokens") != input_tokens + output_tokens:
            raise ValueError("total_tokens does not match input and output totals")
    input_details = _details(data, input_detail_key)
    output_details = _details(data, output_detail_key)
    cached_tokens = _tokens(input_details, "cached_tokens")
    audio_tokens = _tokens(input_details, "audio_tokens")
    if cached_tokens and audio_tokens:
        raise UnsupportedUsageError(
            "Mixed audio/cache usage needs a text/audio cache split; "
            "this adapter cannot infer that split"
        )
    return UsageCostRequest(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_tokens,
        audio_input_tokens=audio_tokens,
        audio_output_tokens=_tokens(output_details, "audio_tokens"),
        reasoning_tokens=_tokens(output_details, "reasoning_tokens"),
    )


def from_anthropic_usage(model: str, usage: object) -> UsageCostRequest:
    """Anthropic reports ordinary input separately from cache reads and writes."""
    data = _as_mapping(usage)
    if data.get("service_tier") not in (None, "standard"):
        raise UnsupportedUsageError("Only standard service-tier pricing is supported")
    server_tools = _details(data, "server_tool_use")
    if any(server_tools.values()):
        raise UnsupportedUsageError(
            "Server tool billing is not supported by this adapter"
        )
    input_tokens = _tokens(data, "input_tokens", required=True)
    output_tokens = _tokens(data, "output_tokens", required=True)
    cached = _tokens(data, "cache_read_input_tokens")
    writes = _tokens(data, "cache_creation_input_tokens")
    creation = _details(data, "cache_creation")
    hour_writes = _tokens(creation, "ephemeral_1h_input_tokens")
    if "ephemeral_5m_input_tokens" in creation:
        if _tokens(creation, "ephemeral_5m_input_tokens") + hour_writes != writes:
            raise ValueError("Cache TTL token details do not match total cache writes")
    return UsageCostRequest(
        model=model,
        input_tokens=input_tokens + cached + writes,
        output_tokens=output_tokens,
        cached_input_tokens=cached,
        cache_creation_input_tokens=writes,
        cache_creation_1h_input_tokens=hour_writes,
    )
