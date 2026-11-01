"""Shared pricing schema for generated catalogs and the runtime."""

import math
import re
from functools import cached_property
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    StrictBool,
    field_validator,
    model_validator,
)

_TokenLimit = Annotated[int, Field(ge=0)]

_TOKEN_TIER = re.compile(r"^(.*)_above_(\d+)([km]?)_tokens$")
_SPECIALIZED_TOKEN_TIER = re.compile(
    r"^.*_above_\d+[km]?_tokens_(?:priority|batches|flex|ultrafast|decisions)$"
)
_CONTEXT_TIER_MARKER = re.compile(r"_above_.*_tokens", re.IGNORECASE)


def _validate_rate(value: object) -> None:
    if value is None:
        return
    if isinstance(value, dict):
        for nested in value.values():
            _validate_rate(nested)
        return
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError("Prices must be finite nonnegative numbers or null")


class SearchContextCost(BaseModel):
    search_context_size_high: float | None = None
    search_context_size_low: float | None = None
    search_context_size_medium: float | None = None


class ModelPricing(BaseModel):
    """Rates and optional upstream model metadata; limits are informational."""

    model_config = ConfigDict(extra="allow", frozen=True)

    litellm_provider: str | None = None
    mode: str | None = None

    max_input_tokens: _TokenLimit | None = None
    max_output_tokens: _TokenLimit | None = None
    # LiteLLM's legacy field has model-dependent meaning; never infer other limits.
    max_tokens: _TokenLimit | None = None
    prompt_cache_min_tokens: _TokenLimit | None = None

    supported_modalities: tuple[str, ...] | None = None
    supported_output_modalities: tuple[str, ...] | None = None
    supported_endpoints: tuple[str, ...] | None = None
    supported_regions: tuple[str, ...] | None = None
    deprecation_date: str | None = None

    supports_function_calling: StrictBool | None = None
    supports_parallel_function_calling: StrictBool | None = None
    supports_tool_choice: StrictBool | None = None
    supports_response_schema: StrictBool | None = None
    supports_native_structured_output: StrictBool | None = None
    supports_system_messages: StrictBool | None = None
    supports_assistant_prefill: StrictBool | None = None
    supports_native_streaming: StrictBool | None = None
    supports_prompt_caching: StrictBool | None = None
    supports_vision: StrictBool | None = None
    supports_audio_input: StrictBool | None = None
    supports_audio_output: StrictBool | None = None
    supports_video_input: StrictBool | None = None
    supports_pdf_input: StrictBool | None = None
    supports_web_search: StrictBool | None = None
    supports_url_context: StrictBool | None = None
    supports_computer_use: StrictBool | None = None
    supports_reasoning: StrictBool | None = None
    supports_adaptive_thinking: StrictBool | None = None
    thinking_always_on: StrictBool | None = None
    reasoning_effort_levels: tuple[str, ...] | None = None
    default_reasoning_effort: str | None = None
    reasoning_modes: tuple[str, ...] | None = None
    reasoning_contexts: tuple[str, ...] | None = None

    input_cost_per_token: float | None = None
    output_cost_per_token: float | None = None
    output_cost_per_reasoning_token: float | None = None
    cache_read_input_token_cost: float | None = None
    input_cost_per_token_cache_hit: float | None = None
    cache_creation_input_token_cost: float | None = None
    cache_creation_input_token_cost_above_1hr: float | None = None

    input_cost_per_audio_token: float | None = None
    output_cost_per_audio_token: float | None = None
    output_cost_per_image: float | None = None
    file_search_cost_per_1k_calls: float | None = None
    file_search_cost_per_gb_per_day: float | None = None
    vector_store_cost_per_gb_per_day: float | None = None
    code_interpreter_cost_per_session: float | None = None

    search_context_cost_per_query: SearchContextCost | None = None

    _rates: dict[str, float] = PrivateAttr(default_factory=dict)
    _tiers: dict[str, list[tuple[int, float]]] = PrivateAttr(default_factory=dict)

    @field_validator(
        "max_input_tokens",
        "max_output_tokens",
        "max_tokens",
        "prompt_cache_min_tokens",
        mode="before",
    )
    @classmethod
    def validate_token_limit(cls, value: object) -> object:
        # Upstream sometimes represents integer counts as integral floats.
        # Pydantic rejects fractions/nonfinite values; exclude bools and strings too.
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float))
        ):
            raise ValueError("Token limits must be nonnegative integer counts or null")
        return value

    @model_validator(mode="before")
    @classmethod
    def validate_prices(cls, value: object) -> object:
        if isinstance(value, dict):
            for key, rate in value.items():
                if "cost" in key:
                    if (
                        _CONTEXT_TIER_MARKER.search(key)
                        and not _TOKEN_TIER.fullmatch(key)
                        # Service-tier and endpoint prices are retained as data;
                        # they do not override standard calculation rates.
                        and not _SPECIALIZED_TOKEN_TIER.fullmatch(key)
                    ):
                        raise ValueError(
                            f"Unsupported token-context tier field {key!r}; "
                            "expected *_above_<integer>[k|m]_tokens "
                            "with lowercase units"
                        )
                    _validate_rate(rate)
        return value

    @model_validator(mode="after")
    def index_rates(self) -> Self:
        for field, value in self.model_dump().items():
            if "cost" not in field or not isinstance(value, (int, float)):
                continue
            self._rates[field] = float(value)
            match = _TOKEN_TIER.fullmatch(field)
            if match:
                base, amount, scale = match.groups()
                threshold = int(amount) * {"": 1, "k": 1000, "m": 1000000}[scale]
                self._tiers.setdefault(base, []).append((threshold, float(value)))
        for tiers in self._tiers.values():
            tiers.sort(reverse=True)
        return self

    @cached_property
    def _rate_index(
        self,
    ) -> tuple[dict[str, float], dict[str, list[tuple[int, float]]]]:
        return self._rates, self._tiers

    def rate(self, field: str, input_tokens: int) -> float | None:
        """Long-context tariffs apply to the whole category above the threshold."""
        rates, tiers = self._rate_index
        for threshold, rate in tiers.get(field, ()):
            if input_tokens > threshold:
                return rate
        return rates.get(field)
