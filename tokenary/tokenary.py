from tokenary.catalog import PricingCatalog, get_default_catalog
from tokenary.errors import MissingPriceError
from tokenary.pricing import ModelPricing
from tokenary.views import CostBreakdown, UsageCostRequest


def _unit_cost(
    request: UsageCostRequest,
    pricing: ModelPricing,
    quantity: int | float,
    field: str,
    *,
    fallback: str | None = None,
    divisor: int = 1,
) -> float:
    if quantity == 0:
        return 0.0
    rate = pricing.rate(field, request.input_tokens)
    if rate is None and fallback is not None:
        rate = pricing.rate(fallback, request.input_tokens)
    if rate is None:
        raise MissingPriceError(request.model, field)
    return quantity * rate / divisor


def calculate(
    request: UsageCostRequest | None = None,
    *,
    model: str | None = None,
    catalog: PricingCatalog | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    reasoning_tokens: int = 0,
    audio_input_tokens: int = 0,
    audio_output_tokens: int = 0,
    cached_input_tokens: int = 0,
    cache_creation_input_tokens: int = 0,
    cache_creation_1h_input_tokens: int = 0,
    generated_images: int = 0,
    code_interpreter_sessions: int = 0,
    file_search_calls: int = 0,
    file_search_gb_days: float = 0.0,
    vector_store_gb_days: float = 0.0,
) -> CostBreakdown:
    """Calculate with inclusive input/output totals and disjoint token subsets."""
    if request is None:
        if model is None:
            raise ValueError("Either request or model must be provided")
        request = UsageCostRequest(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            audio_input_tokens=audio_input_tokens,
            audio_output_tokens=audio_output_tokens,
            cached_input_tokens=cached_input_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
            cache_creation_1h_input_tokens=cache_creation_1h_input_tokens,
            generated_images=generated_images,
            code_interpreter_sessions=code_interpreter_sessions,
            file_search_calls=file_search_calls,
            file_search_gb_days=file_search_gb_days,
            vector_store_gb_days=vector_store_gb_days,
        )
    else:
        keyword_usage = (
            input_tokens,
            output_tokens,
            reasoning_tokens,
            audio_input_tokens,
            audio_output_tokens,
            cached_input_tokens,
            cache_creation_input_tokens,
            cache_creation_1h_input_tokens,
            generated_images,
            code_interpreter_sessions,
            file_search_calls,
            file_search_gb_days,
            vector_store_gb_days,
        )
        if model is not None or any(keyword_usage):
            raise ValueError("Pass either a request or usage keywords, not both")

    if catalog is None:
        catalog = get_default_catalog()
    pricing = catalog.models.get(request.model)
    if pricing is None:
        raise KeyError(f"Unknown model: {request.model!r}")

    def cost(quantity: int | float, field: str, **options) -> float:
        return _unit_cost(request, pricing, quantity, field, **options)

    plain_input = (
        request.input_tokens
        - request.audio_input_tokens
        - request.cached_input_tokens
        - request.cache_creation_input_tokens
    )
    plain_output = (
        request.output_tokens - request.reasoning_tokens - request.audio_output_tokens
    )
    short_cache_writes = (
        request.cache_creation_input_tokens - request.cache_creation_1h_input_tokens
    )
    metadata = catalog.metadata
    return CostBreakdown(
        model=request.model,
        input_cost=cost(plain_input, "input_cost_per_token"),
        output_cost=cost(plain_output, "output_cost_per_token"),
        reasoning_cost=cost(
            request.reasoning_tokens,
            "output_cost_per_reasoning_token",
            fallback="output_cost_per_token",
        ),
        audio_input_cost=cost(request.audio_input_tokens, "input_cost_per_audio_token"),
        audio_output_cost=cost(
            request.audio_output_tokens, "output_cost_per_audio_token"
        ),
        cached_input_cost=cost(
            request.cached_input_tokens,
            "cache_read_input_token_cost",
            fallback="input_cost_per_token_cache_hit",
        ),
        cache_creation_cost=(
            cost(short_cache_writes, "cache_creation_input_token_cost")
            + cost(
                request.cache_creation_1h_input_tokens,
                "cache_creation_input_token_cost_above_1hr",
            )
        ),
        image_cost=cost(request.generated_images, "output_cost_per_image"),
        code_interpreter_cost=cost(
            request.code_interpreter_sessions, "code_interpreter_cost_per_session"
        ),
        file_search_call_cost=cost(
            request.file_search_calls, "file_search_cost_per_1k_calls", divisor=1000
        ),
        file_search_storage_cost=cost(
            request.file_search_gb_days, "file_search_cost_per_gb_per_day"
        ),
        vector_store_cost=cost(
            request.vector_store_gb_days, "vector_store_cost_per_gb_per_day"
        ),
        pricing_source_sha256=metadata.source_sha256 if metadata else None,
        pricing_catalog_sha256=metadata.catalog_sha256 if metadata else None,
    )
