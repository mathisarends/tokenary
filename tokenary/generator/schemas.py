from pydantic import BaseModel, ConfigDict


class GeneratedModelPricing(BaseModel):
    model_config = ConfigDict(extra="allow")

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

    max_input_tokens: int | str | None = None
    max_output_tokens: int | str | None = None
    max_tokens: int | str | None = None

    deprecation_date: str | None = None

    supported_endpoints: list[str] | None = None
    supported_modalities: list[str] | None = None
    supported_output_modalities: list[str] | None = None

    supports_function_calling: bool | None = None
    supports_native_streaming: bool | None = None
    supports_parallel_function_calling: bool | None = None
    supports_pdf_input: bool | None = None
    supports_prompt_caching: bool | None = None
    supports_reasoning: bool | None = None
    supports_response_schema: bool | None = None
    supports_system_messages: bool | None = None
    supports_tool_choice: bool | None = None
    supports_vision: bool | None = None
