import math
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from .catalog import PricingCatalog
from .pricing import ModelPricing, SearchContextCost

__all__ = [
    "CostBreakdown",
    "ModelPricing",
    "PricingCatalog",
    "SearchContextCost",
    "UsageCostRequest",
]


class UsageCostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True)

    model: str = Field(min_length=1)

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    audio_input_tokens: int = Field(default=0, ge=0)
    audio_output_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    cache_creation_input_tokens: int = Field(default=0, ge=0)
    cache_creation_1h_input_tokens: int = Field(default=0, ge=0)

    generated_images: int = Field(default=0, ge=0)
    code_interpreter_sessions: int = Field(default=0, ge=0)
    file_search_calls: int = Field(default=0, ge=0)
    file_search_gb_days: float = Field(default=0.0, ge=0)
    vector_store_gb_days: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def validate_token_subsets(self) -> Self:
        input_subsets = (
            self.audio_input_tokens
            + self.cached_input_tokens
            + self.cache_creation_input_tokens
        )
        if input_subsets > self.input_tokens:
            raise ValueError("Input token categories must not exceed input_tokens")
        if self.reasoning_tokens + self.audio_output_tokens > self.output_tokens:
            raise ValueError("Output token categories must not exceed output_tokens")
        if self.cache_creation_1h_input_tokens > self.cache_creation_input_tokens:
            raise ValueError(
                "One-hour writes must not exceed cache_creation_input_tokens"
            )
        return self


class CostBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True)

    model: str
    currency: str = "USD"

    input_cost: float = 0.0
    output_cost: float = 0.0
    reasoning_cost: float = 0.0
    audio_input_cost: float = 0.0
    audio_output_cost: float = 0.0
    cached_input_cost: float = 0.0
    cache_creation_cost: float = 0.0

    image_cost: float = 0.0
    code_interpreter_cost: float = 0.0
    file_search_call_cost: float = 0.0
    file_search_storage_cost: float = 0.0
    vector_store_cost: float = 0.0

    pricing_source_sha256: str | None = None
    pricing_catalog_sha256: str | None = None

    @computed_field
    @property
    def total_cost(self) -> float:
        return math.fsum(
            getattr(self, field)
            for field in type(self).model_fields
            if field.endswith("_cost")
        )
