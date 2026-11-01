from typing import TYPE_CHECKING, Any

from .catalog import CatalogMetadata, PricingCatalog
from .errors import MissingPriceError, UnsupportedUsageError
from .tokenary import calculate
from .usage import from_anthropic_usage, from_openai_usage
from .views import CostBreakdown, UsageCostRequest

if TYPE_CHECKING:
    from .live import LivePricingCatalog

    ModelName: Any

__all__ = [
    "CatalogMetadata",
    "CostBreakdown",
    "LivePricingCatalog",
    "ModelName",
    "MissingPriceError",
    "PricingCatalog",
    "UsageCostRequest",
    "UnsupportedUsageError",
    "calculate",
    "from_anthropic_usage",
    "from_openai_usage",
]


def __getattr__(name: str) -> object:
    if name == "LivePricingCatalog":
        from .live import LivePricingCatalog

        globals()[name] = LivePricingCatalog
        return LivePricingCatalog
    if name == "ModelName":
        from .catalog import get_bundled_model_enum

        model_enum = get_bundled_model_enum()
        globals()[name] = model_enum
        return model_enum
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
