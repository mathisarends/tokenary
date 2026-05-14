from pydantic import BaseModel, ConfigDict
from tokenary._generated import ModelName


class SearchContextCost(BaseModel):
    search_context_size_high: float | None = None
    search_context_size_low: float | None = None
    search_context_size_medium: float | None = None


class ModelPricing(BaseModel):
    model_config = ConfigDict(extra="allow")

    litellm_provider: str | None = None
    mode: str | None = None

    input_cost_per_token: float | None = None
    output_cost_per_token: float | None = None
    output_cost_per_reasoning_token: float | None = None

    input_cost_per_audio_token: float | None = None
    output_cost_per_image: float | None = None
    file_search_cost_per_1k_calls: float | None = None
    file_search_cost_per_gb_per_day: float | None = None
    vector_store_cost_per_gb_per_day: float | None = None
    code_interpreter_cost_per_session: float | None = None

    max_input_tokens: int | str | None = None
    max_output_tokens: int | str | None = None
    max_tokens: int | str | None = None

    search_context_cost_per_query: SearchContextCost | None = None


class PricingCatalog(BaseModel):
    sample_spec: ModelPricing | None = None
    models: dict[str, ModelPricing]


class UsageCostRequest(BaseModel):
    model: ModelName

    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    audio_input_tokens: int = 0

    generated_images: int = 0
    code_interpreter_sessions: int = 0
    file_search_calls: int = 0
    file_search_gb_days: float = 0.0
    vector_store_gb_days: float = 0.0


class CostBreakdown(BaseModel):
    model: str
    currency: str = "USD"

    input_cost: float = 0.0
    output_cost: float = 0.0
    reasoning_cost: float = 0.0
    audio_input_cost: float = 0.0

    image_cost: float = 0.0
    code_interpreter_cost: float = 0.0
    file_search_call_cost: float = 0.0
    file_search_storage_cost: float = 0.0
    vector_store_cost: float = 0.0

    total_cost: float = 0.0
