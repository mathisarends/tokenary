from typing import TYPE_CHECKING, Any

from .catalog import CatalogMetadata, PricingCatalog
from .errors import MissingPriceError, UnsupportedUsageError
from .tokenary import calculate
from .usage import from_anthropic_usage, from_openai_usage
from .views import CostBreakdown, UsageCostRequest

if TYPE_CHECKING:
    ModelName: Any

__all__ = [
    "CatalogMetadata",
    "CostBreakdown",
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
    if name == "ModelName":
        from .catalog import get_default_catalog

        model_enum = get_default_catalog().model_enum
        globals()[name] = model_enum
        return model_enum
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
