from __future__ import annotations

import pytest

from tokenary.tokenary import _get_catalog
from tokenary.views import ModelPricing


@pytest.fixture(autouse=True)
def _clear_catalog_cache() -> None:
    _get_catalog.cache_clear()


def test_get_catalog_converts_generated_models_to_runtime_models(monkeypatch) -> None:
    fake_generated = {"my-model": ModelPricing(input_cost_per_token=0.5, mode="chat")}
    fake_sample = ModelPricing(mode="chat", max_tokens=1024)

    monkeypatch.setattr("tokenary.tokenary.MODEL_PRICINGS_BY_NAME", fake_generated)
    monkeypatch.setattr("tokenary.tokenary.SAMPLE_SPEC", fake_sample)

    catalog = _get_catalog()

    assert "my-model" in catalog.models
    assert catalog.models["my-model"].input_cost_per_token == pytest.approx(0.5)
    assert catalog.sample_spec is not None
    assert catalog.sample_spec.max_tokens == 1024


def test_get_catalog_is_cached_after_first_load(monkeypatch) -> None:
    fake_generated = {"cached-model": ModelPricing(input_cost_per_token=1.0)}

    monkeypatch.setattr("tokenary.tokenary.MODEL_PRICINGS_BY_NAME", fake_generated)
    monkeypatch.setattr("tokenary.tokenary.SAMPLE_SPEC", None)

    first = _get_catalog()

    monkeypatch.setattr("tokenary.tokenary.MODEL_PRICINGS_BY_NAME", {})
    second = _get_catalog()

    assert first is second
    assert "cached-model" in second.models
