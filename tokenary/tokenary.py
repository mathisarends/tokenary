from __future__ import annotations

import json
from pathlib import Path

from . import _generated
from .views import CostBreakdown, CostResponse, PricingCatalog, UsageCostRequest


def load_catalog(path: str | Path) -> PricingCatalog:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Catalog file is not a JSON object")
    return PricingCatalog.from_raw(raw)


def load_embedded_catalog() -> PricingCatalog:
    raw = getattr(_generated, "MODEL_PRICES_RAW", None)
    if not isinstance(raw, dict) or not raw:
        raise ValueError(
            "No generated pricing data found in tokenary/_generated.py. "
            "Run `python -m tokenary.generator` or `python -m cdpify.generator`."
        )
    return PricingCatalog.from_raw(raw)


def calculate_usage_cost(
    catalog: PricingCatalog, usage: UsageCostRequest
) -> CostBreakdown:
    pricing = catalog.models.get(usage.model)
    if pricing is None:
        raise KeyError(f"Unknown model: {usage.model}")

    input_cost = usage.input_tokens * (pricing.input_cost_per_token or 0.0)
    output_cost = usage.output_tokens * (pricing.output_cost_per_token or 0.0)
    reasoning_cost = usage.reasoning_tokens * (
        pricing.output_cost_per_reasoning_token or 0.0
    )
    audio_input_cost = usage.audio_input_tokens * (
        pricing.input_cost_per_audio_token or 0.0
    )

    image_cost = usage.generated_images * (pricing.output_cost_per_image or 0.0)
    code_interpreter_cost = usage.code_interpreter_sessions * (
        pricing.code_interpreter_cost_per_session or 0.0
    )
    file_search_call_cost = usage.file_search_calls * (
        (pricing.file_search_cost_per_1k_calls or 0.0) / 1000.0
    )
    file_search_storage_cost = usage.file_search_gb_days * (
        pricing.file_search_cost_per_gb_per_day or 0.0
    )
    vector_store_cost = usage.vector_store_gb_days * (
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
        model=usage.model,
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


class Tokenary:
    def __init__(
        self,
        catalog: PricingCatalog | None = None,
        catalog_path: str | Path | None = None,
    ):
        if catalog is not None and catalog_path is not None:
            raise ValueError("Pass either catalog or catalog_path, not both")

        if catalog is not None:
            self.catalog = catalog
        elif catalog_path is not None:
            self.catalog = load_catalog(catalog_path)
        else:
            self.catalog = load_embedded_catalog()

    def calculate(
        self, request: UsageCostRequest | dict | None = None, **kwargs
    ) -> CostResponse:
        if isinstance(request, UsageCostRequest):
            usage = request
        else:
            payload: dict[str, object] = {}
            if isinstance(request, dict):
                payload.update(request)
            payload.update(kwargs)
            if "model" in payload and payload["model"] is not None:
                payload["model"] = str(payload["model"])
            usage = UsageCostRequest(**payload)

        breakdown = calculate_usage_cost(self.catalog, usage)
        return CostResponse(**breakdown.model_dump())
