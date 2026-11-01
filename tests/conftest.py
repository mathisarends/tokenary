import json
from pathlib import Path

import pytest

from tokenary import PricingCatalog


@pytest.fixture
def billing_catalog():
    """Freeze historical billing cases independently of upstream catalog refreshes."""
    # Pricing-only entries from the pre-refresh snapshot at 5c1a18d.
    path = Path(__file__).parent / "fixtures/billing_prices.json"
    return PricingCatalog.from_raw_prices(json.loads(path.read_text(encoding="utf-8")))
