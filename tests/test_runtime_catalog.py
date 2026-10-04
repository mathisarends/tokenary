import json
import pickle
import subprocess
import sys

import pytest
from pydantic import ValidationError

from tokenary import ModelName, PricingCatalog, calculate
from tokenary.catalog import get_default_catalog
from tokenary.generator.generator import build_catalog_payload, render_catalog_file
from tokenary.generator.schemas import GeneratedModelPricing
from tokenary.pricing import ModelPricing


def test_catalog_only_validates_requested_models_and_reuses_them() -> None:
    catalog = PricingCatalog.from_raw_prices(
        {
            "used": {"input_cost_per_token": 0.5},
            "unused-invalid": {"input_cost_per_token": "not a price"},
            "sample_spec": {},
        }
    )
    assert len(catalog.models) == 2
    assert catalog.loaded_model_count == 0
    first = catalog.models["used"]
    assert catalog.models["used"] is first
    assert catalog.loaded_model_count == 1
    with pytest.raises(ValidationError):
        catalog.models["unused-invalid"]
    with pytest.raises(KeyError):
        catalog.models["unknown"]
    assert catalog.loaded_model_count == 1


def test_plain_import_does_not_load_catalog_or_generator() -> None:
    code = """
import sys
import tokenary
from tokenary.catalog import get_default_catalog
assert get_default_catalog.cache_info().currsize == 0
assert 'tokenary.generator.generator' not in sys.modules
assert 'tokenary._generated' not in sys.modules
tokenary.calculate(model='gpt-4o', input_tokens=1)
catalog = get_default_catalog()
assert catalog.loaded_model_count == 1
assert 'model_enum' not in catalog.__dict__
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_default_catalog_keeps_public_model_names_and_is_cached() -> None:
    assert ModelName.AZURE_GPT_3_5_TURBO.value == "azure/gpt-3.5-turbo"
    assert ModelName.COHERE_EMBED_V4_0.value == "cohere.embed-v4:0"
    assert ModelName.COHERE_EMBED_V4_0_2.value == "cohere/embed-v4.0"
    assert pickle.loads(pickle.dumps(ModelName.GPT_4O)) is ModelName.GPT_4O
    assert get_default_catalog() is get_default_catalog()


def test_generation_and_runtime_share_the_exact_pricing_schema() -> None:
    assert GeneratedModelPricing is ModelPricing


@pytest.mark.parametrize("suffix", [".json", ".json.gz"])
def test_catalog_file_roundtrip_and_checksum(tmp_path, suffix) -> None:
    payload = build_catalog_payload(
        {"my-model": {"input_cost_per_token": 0.25}}, source="pinned-source"
    )
    path = tmp_path / f"prices{suffix}"
    path.write_bytes(render_catalog_file(payload, path))
    catalog = PricingCatalog.from_file(path)
    assert catalog.metadata.source == "pinned-source"
    assert catalog.loaded_model_count == 0
    assert calculate(model="my-model", input_tokens=4, catalog=catalog).total_cost == 1

    payload["models"]["my-model"]["input_cost_per_token"] = 100
    with pytest.raises(ValueError, match="checksum"):
        PricingCatalog.from_dict(payload)


def test_catalog_rejects_unsupported_format_and_bad_model_names() -> None:
    with pytest.raises(ValueError, match="format version"):
        PricingCatalog.from_dict({"format_version": 999})
    payload = build_catalog_payload({"one": {}})
    payload["enum_names"] = {}
    with pytest.raises(ValueError, match="do not match"):
        PricingCatalog.from_dict(payload)


def test_catalog_rejects_non_object_json(tmp_path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps([]), encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        PricingCatalog.from_file(path)
