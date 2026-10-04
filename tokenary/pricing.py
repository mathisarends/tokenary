"""Shared pricing schema for generated catalogs and the runtime."""

from pydantic import BaseModel, ConfigDict


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

    input_cost_per_audio_token: float | None = None
    output_cost_per_image: float | None = None
    file_search_cost_per_1k_calls: float | None = None
    file_search_cost_per_gb_per_day: float | None = None
    vector_store_cost_per_gb_per_day: float | None = None
    code_interpreter_cost_per_session: float | None = None

    search_context_cost_per_query: SearchContextCost | None = None
