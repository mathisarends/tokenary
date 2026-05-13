from tokenary.views import PricingCatalog


def test_pricing_catalog_from_raw_parses_models_and_sample_spec() -> None:
    raw = {
        "sample_spec": {
            "max_tokens": "legacy value",
            "litellm_provider": "openai",
        },
        "gpt-test": {
            "litellm_provider": "openai",
            "mode": "chat",
            "input_cost_per_token": 0.001,
        },
        "invalid": "skip me",
    }

    catalog = PricingCatalog.from_raw(raw)

    assert catalog.sample_spec is not None
    assert catalog.sample_spec.max_tokens == "legacy value"
    assert "gpt-test" in catalog.models
    assert "invalid" not in catalog.models


def test_pricing_catalog_keeps_extra_model_fields() -> None:
    raw = {
        "sample_spec": {},
        "model-with-extra": {
            "litellm_provider": "vendor",
            "mode": "chat",
            "custom_price_field": 42,
        },
    }

    catalog = PricingCatalog.from_raw(raw)
    model = catalog.models["model-with-extra"]

    assert getattr(model, "custom_price_field") == 42