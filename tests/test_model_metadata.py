import importlib.util

import pytest
from pydantic import ValidationError

from tokenary import PricingCatalog, calculate
from tokenary.generator.generator import build_catalog_payload, render_catalog_file
from tokenary.pricing import ModelPricing


@pytest.fixture
def model_data():
    return {
        "input_cost_per_token": 0.25,
        "output_cost_per_token": 0.5,
        "max_input_tokens": 128000,
        "max_output_tokens": 4096,
        "max_tokens": 4096,
        "supports_function_calling": True,
        "supports_parallel_function_calling": False,
        "supports_response_schema": True,
        "supports_vision": True,
        "supports_audio_output": False,
        "supports_prompt_caching": True,
        "prompt_cache_min_tokens": 1024.0,
        "supports_reasoning": True,
        "thinking_always_on": False,
        "reasoning_effort_levels": ["low", "high"],
        "default_reasoning_effort": "low",
        "reasoning_modes": ["standard"],
        "reasoning_contexts": ["current_turn"],
        "supported_modalities": ["text", "image"],
        "supported_output_modalities": ["text"],
        "supported_endpoints": ["/v1/responses"],
        "supported_regions": ["eu-west-1"],
        "deprecation_date": "2027-01-01",
        "supports_future_feature": False,
        "supported_future_formats": ["new-format"],
    }


@pytest.mark.parametrize("suffix", [".py", ".json", ".json.gz"])
def test_metadata_survives_selected_catalog_formats(tmp_path, model_data, suffix):
    raw = {"own-model": model_data, "excluded": {"max_input_tokens": -1}}
    payload = build_catalog_payload(raw, models=["own-model"])
    assert payload["models"]["own-model"] == model_data
    output = tmp_path / f"prices{suffix}"
    output.write_bytes(render_catalog_file(payload, output))
    if suffix == ".py":
        spec = importlib.util.spec_from_file_location("metadata_prices", output)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        catalog = module.CATALOG
    else:
        catalog = PricingCatalog.from_file(output)
    assert catalog.loaded_model_count == 0
    info = catalog.models["own-model"]
    assert info.model_dump(mode="json", exclude_unset=True) == model_data
    assert info.supports_parallel_function_calling is False
    assert info.supports_audio_input is None
    assert info.supported_modalities == ("text", "image")
    assert info.prompt_cache_min_tokens == 1024
    assert catalog.loaded_model_count == 1
    assert set(catalog.models) == {"own-model"}


def test_old_catalog_metadata_is_unknown_without_inventing_limits():
    payload = build_catalog_payload({"legacy": {"max_tokens": 2048}})
    info = PricingCatalog.from_dict(payload).models["legacy"]
    assert info.max_tokens == 2048
    assert info.max_input_tokens is None
    assert info.max_output_tokens is None
    assert info.supports_function_calling is None
    assert info.supports_prompt_caching is None
    assert info.prompt_cache_min_tokens is None
    assert info.supported_modalities is None
    assert info.supported_endpoints is None
    assert info.reasoning_effort_levels is None
    assert info.deprecation_date is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_input_tokens", -1),
        ("max_output_tokens", 1.5),
        ("max_tokens", True),
        ("max_input_tokens", "128000"),
        ("max_output_tokens", float("inf")),
        ("prompt_cache_min_tokens", float("nan")),
        ("prompt_cache_min_tokens", False),
        ("supports_vision", "false"),
        ("supports_function_calling", 1),
        ("supported_modalities", "text"),
        ("supported_endpoints", [123]),
    ],
)
def test_invalid_known_metadata_fails_generation_and_lazy_runtime(field, value):
    raw = {"invalid": {field: value}, "valid": {"max_input_tokens": 0}}
    catalog = PricingCatalog.from_raw_prices(raw)
    assert catalog.loaded_model_count == 0
    assert catalog.models["valid"].max_input_tokens == 0
    with pytest.raises(ValidationError):
        catalog.models["invalid"]
    assert catalog.loaded_model_count == 1
    with pytest.raises(ValidationError):
        build_catalog_payload(raw)


def test_null_and_empty_metadata_are_distinct():
    info = ModelPricing(
        max_input_tokens=None,
        max_output_tokens=0,
        supports_vision=False,
        supports_reasoning=None,
        supported_modalities=[],
        reasoning_effort_levels=None,
    )
    assert info.max_input_tokens is None
    assert info.max_output_tokens == 0
    assert info.supports_vision is False
    assert info.supports_reasoning is None
    assert info.supported_modalities == ()
    assert info.reasoning_effort_levels is None


def test_metadata_changes_are_checksummed_and_do_not_change_billing(model_data):
    model_data.update(
        max_input_tokens=1,
        max_output_tokens=0,
        supports_reasoning=False,
        supports_prompt_caching=False,
        deprecation_date="2000-01-01",
        output_cost_per_reasoning_token=0.125,
        cache_read_input_token_cost=0.125,
    )
    first = build_catalog_payload({"own-model": model_data})
    catalog = PricingCatalog.from_dict(first)
    result = calculate(
        model="own-model",
        input_tokens=4,
        output_tokens=2,
        cached_input_tokens=2,
        reasoning_tokens=1,
        catalog=catalog,
    )
    assert result.total_cost == 1.375
    model_data["max_input_tokens"] = 1000
    second = build_catalog_payload({"own-model": model_data})
    assert first["metadata"]["source_sha256"] != second["metadata"]["source_sha256"]
    assert first["metadata"]["catalog_sha256"] != second["metadata"]["catalog_sha256"]
    assert catalog.models["own-model"].max_input_tokens == 1
    first["models"]["own-model"]["max_input_tokens"] = 1000
    with pytest.raises(ValueError, match="checksum"):
        PricingCatalog.from_dict(first)
