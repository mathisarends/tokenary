"""Shared pricing schema for generated catalogs and the runtime."""

import math
import re
from functools import cached_property
from typing import Self

from pydantic import BaseModel, ConfigDict, PrivateAttr, model_validator

_TOKEN_TIER = re.compile(r"^(.*)_above_(\d+)([km]?)_tokens$")


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
    model_config = ConfigDict(extra="allow", frozen=True)

    litellm_provider: str | None = None
    mode: str | None = None

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

    @model_validator(mode="before")
    @classmethod
    def validate_prices(cls, value: object) -> object:
        if isinstance(value, dict):
            for key, rate in value.items():
                if "cost" in key:
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
