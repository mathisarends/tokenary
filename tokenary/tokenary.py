from functools import lru_cache
from typing import overload

from tokenary._generated import MODEL_PRICINGS_BY_NAME, SAMPLE_SPEC
from tokenary.views import (
    CostBreakdown,
    ModelPricing,
    PricingCatalog,
    UsageCostRequest,
)


@lru_cache(maxsize=1)
def _get_catalog() -> PricingCatalog:
    return PricingCatalog(
        sample_spec=ModelPricing.model_validate(SAMPLE_SPEC.model_dump())
        if SAMPLE_SPEC
        else None,
        models={
            name: ModelPricing.model_validate(pricing.model_dump())
            for name, pricing in MODEL_PRICINGS_BY_NAME.items()
        },
    )


@overload
def calculate(request: UsageCostRequest) -> CostBreakdown: ...


@overload
def calculate(
    request: None = None,
    *,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    reasoning_tokens: int = 0,
    audio_input_tokens: int = 0,
    generated_images: int = 0,
    code_interpreter_sessions: int = 0,
    file_search_calls: int = 0,
    file_search_gb_days: float = 0.0,
    vector_store_gb_days: float = 0.0,
) -> CostBreakdown: ...


def calculate(
    request: UsageCostRequest | None = None,
    *,
    model: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    reasoning_tokens: int = 0,
    audio_input_tokens: int = 0,
    generated_images: int = 0,
    code_interpreter_sessions: int = 0,
    file_search_calls: int = 0,
    file_search_gb_days: float = 0.0,
    vector_store_gb_days: float = 0.0,
) -> CostBreakdown:
    if request is None:
        if model is None:
            raise ValueError("Either request or model must be provided")
        request = UsageCostRequest(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            audio_input_tokens=audio_input_tokens,
            generated_images=generated_images,
            code_interpreter_sessions=code_interpreter_sessions,
            file_search_calls=file_search_calls,
            file_search_gb_days=file_search_gb_days,
            vector_store_gb_days=vector_store_gb_days,
        )

    catalog = _get_catalog()
    pricing = catalog.models.get(request.model)
    if pricing is None:
        raise KeyError(f"Unknown model: {request.model!r}")

    input_cost = request.input_tokens * (pricing.input_cost_per_token or 0.0)
    output_cost = request.output_tokens * (pricing.output_cost_per_token or 0.0)
    reasoning_cost = request.reasoning_tokens * (
        pricing.output_cost_per_reasoning_token or 0.0
    )
    audio_input_cost = request.audio_input_tokens * (
        pricing.input_cost_per_audio_token or 0.0
    )
    image_cost = request.generated_images * (pricing.output_cost_per_image or 0.0)
    code_interpreter_cost = request.code_interpreter_sessions * (
        pricing.code_interpreter_cost_per_session or 0.0
    )
    file_search_call_cost = request.file_search_calls * (
        (pricing.file_search_cost_per_1k_calls or 0.0) / 1000.0
    )
    file_search_storage_cost = request.file_search_gb_days * (
        pricing.file_search_cost_per_gb_per_day or 0.0
    )
    vector_store_cost = request.vector_store_gb_days * (
        pricing.vector_store_cost_per_gb_per_day or 0.0
    )

    total_cost = (
        input_cost
        + output_cost
        + reasoning_cost
        + audio_input_cost
        + image_cost
        + code_interpreter_cost
        + file_search_call_cost
        + file_search_storage_cost
        + vector_store_cost
    )

    return CostBreakdown(
        model=request.model,
        input_cost=input_cost,
        output_cost=output_cost,
        reasoning_cost=reasoning_cost,
        audio_input_cost=audio_input_cost,
        image_cost=image_cost,
        code_interpreter_cost=code_interpreter_cost,
        file_search_call_cost=file_search_call_cost,
        file_search_storage_cost=file_search_storage_cost,
        vector_store_cost=vector_store_cost,
        total_cost=total_cost,
    )
