import gzip
import json
import subprocess
import sys

import pytest

from tokenary import calculate
from tokenary import catalog as catalog_module
from tokenary.catalog import PricingCatalog
from tokenary.generator.bundle import render_bundle


def test_bundle_is_reproducible_and_provider_filenames_cannot_collide():
    prices = {
        "one": {"litellm_provider": "a/b", "input_cost_per_token": 1},
        "two": {"litellm_provider": "a.b", "input_cost_per_token": 2},
        "three": {"input_cost_per_token": 3},
        "four": {"litellm_provider": "unknown", "input_cost_per_token": 4},
    }
    first = render_bundle(prices, source="fixture")
    assert first == render_bundle(
        dict(reversed(list(prices.items()))), source="fixture"
    )
    assert len(first) == 5  # Four distinct providers and the price-free index.
    assert all(".." not in name and "\\" not in name for name in first)


def test_bundle_provider_prices_and_checksums_roundtrip(tmp_path, monkeypatch):
    prices = {
        "no-provider": {"input_cost_per_token": 0.25},
        "another": {"litellm_provider": "test", "input_cost_per_token": 0.5},
    }
    artifacts = render_bundle(prices, source="fixture")
    for name, data in artifacts.items():
        target = tmp_path / "data" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    index = json.loads(gzip.decompress(artifacts["index.json.gz"]))
    assert "models" not in index
    monkeypatch.setattr(catalog_module, "files", lambda package: tmp_path)
    mapping = catalog_module._ProviderPricings(index)
    assert set(mapping) == set(prices)
    for name, data in prices.items():
        assert mapping[name].input_cost_per_token == data["input_cost_per_token"]
    filename = index["model_providers"]["no-provider"]
    index["provider_checksums"][filename] = "incorrect"
    with pytest.raises(ValueError, match="checksum mismatch"):
        catalog_module._ProviderPricings(index)["no-provider"]
    # Standalone JSON/gzip catalogs retain their public format and provenance.
    catalog = PricingCatalog.from_file(tmp_path / "data/providers" / filename)
    assert (
        calculate(model="no-provider", input_tokens=4, catalog=catalog).total_cost == 1
    )


def test_fresh_process_observes_resource_reads_and_model_validation(tmp_path):
    # JSON resource loading is invisible to sys.modules; observe actual reads.
    code = r"""
import json
from pathlib import Path
reads = []
original = Path.read_bytes
def read(path):
    index_names = {'index.json.gz', 'catalog.json.gz'}
    if path.parent.name == 'providers' or path.name in index_names:
        reads.append(path.as_posix())
    return original(path)
Path.read_bytes = read

import tokenary
import tokenary.pricing
import tokenary.generator.generator
from tokenary import get_default_catalog
from tokenary.pricing import ModelPricing
validations = []
validate = ModelPricing.model_validate
def counted(value, *args, **kwargs):
    validations.append(value)
    return validate(value, *args, **kwargs)
ModelPricing.model_validate = counted
assert reads == []

from tokenary import ModelName
assert ModelName.GPT_4O == 'gpt-4o'
assert len(reads) == 1 and reads[0].endswith('index.json.gz')
assert get_default_catalog.cache_info().currsize == 0
assert validations == []

info = get_default_catalog().models['gpt-4o']
assert info.max_input_tokens > 0
assert info.supports_function_calling is True
assert len(reads) == 2 and '/providers/' in reads[-1]
assert len(validations) == 1
first = reads[-1]
tokenary.calculate(model='gpt-4o', input_tokens=1)
tokenary.calculate(model='gpt-4o', input_tokens=2)
assert len(reads) == 2 and len(validations) == 1
tokenary.calculate(model='o1', input_tokens=1)
assert len(reads) == 2 and len(validations) == 2
tokenary.calculate(model='claude-sonnet-4-6', input_tokens=1)
assert len(reads) == 3 and reads[-1] != first
assert len(validations) == 3
assert get_default_catalog().model_enum is ModelName
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_custom_catalog_and_local_generation_never_read_bundled_prices(tmp_path):
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"brand-new": {"input_cost_per_token": 0.5}}))
    code = r"""
import sys
from pathlib import Path
original = Path.read_bytes
def read(path):
    assert path.parent.name != 'providers', path
    assert path.name != 'catalog.json.gz', path
    return original(path)
Path.read_bytes = read
from tokenary import PricingCatalog, calculate
from tokenary.catalog import get_default_catalog
from tokenary.generator.__main__ import main
catalog = PricingCatalog.from_raw_prices({'own': {'input_cost_per_token': 1}})
assert calculate(model='own', input_tokens=2, catalog=catalog).total_cost == 2
main(['--input', sys.argv[1], '--all', '--output', sys.argv[2]])
selected = PricingCatalog.from_file(sys.argv[2])
assert calculate(model='brand-new', input_tokens=2, catalog=selected).total_cost == 1
assert get_default_catalog.cache_info().currsize == 0
"""
    subprocess.run(
        [sys.executable, "-c", code, str(source), str(tmp_path / "own.json")],
        check=True,
    )
