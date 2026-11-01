[Documentation](README.md) · [Quick start](../README.md)

# Custom catalogs

For a custom pricing snapshot, generate a small module containing just your
selected models. Without `--input`, this command downloads the current upstream
prices once; it does not change the installed default catalog:

```bash
tokenary-generate --models gpt-4o o1 --output my_prices.py
```

Import the calculator from `tokenary` and pass the generated catalog explicitly:

```python
from tokenary import calculate
from my_prices import CATALOG, ModelName

result = calculate(
    model=ModelName.GPT_4O,
    input_tokens=1000,
    output_tokens=500,
    catalog=CATALOG,
)
print(result.total_cost)
```

The generated module contains model names and pricing data. Passing its `CATALOG`
to `tokenary.calculate` does not load the bundled full catalog or construct price
objects for unrelated models. Calculation stays in `tokenary`; generated modules
do not export a calculator or duplicate library code. Request objects and usage
adapters work with a custom catalog through the same `catalog=CATALOG` argument.
Generation works after a plain `pip install tokenary` and does not require Ruff.

## Output safety

`--output` is required for both generation and `--check`; there is no implicit
destination. Scripts that relied on the v0.2 default `model_prices.py` must add
`--output model_prices.py`. Missing/invalid arguments and `--help` are handled
before downloads, catalog reads or writes. Outputs are validated first and
replaced atomically; a failed replacement preserves an existing file and removes
its temporary file. An unsuccessful generation reports an error and nonzero exit.

## Model and provider selection

Use exact LiteLLM model IDs. An unknown ID fails generation without changing the
output. Pass `--all` explicitly if you want the entire catalog.

Select a provider through its exact `litellm_provider` metadata, or combine it
with model IDs:

```bash
tokenary-generate --provider openai --output openai_prices.json
tokenary-generate --provider openai --provider anthropic --output prices.json.gz
tokenary-generate --provider openai --model gpt-4o --model o1 --output my_prices.py
```

Repeated providers or models are combined with OR; provider and model filters
are combined with AND. Values are case-sensitive, with no prefix matching.
Unknown values and empty intersections fail before output is replaced. `--all`
cannot be combined with filters. Models without provider metadata remain
selectable by ID. The generator's `build_catalog_payload(..., providers=...,
models=...)` and render/write helpers accept the same filters; `None` means no
filter and an explicitly empty selection is an error. `sample_spec` is metadata
and is excluded from generated runtime catalogs.

## JSON catalogs

Python code generation is optional:

```bash
tokenary-generate --models gpt-4o o1 --output my_prices.json.gz
```

```python
from tokenary import PricingCatalog, calculate

catalog = PricingCatalog.from_file("my_prices.json.gz")
result = calculate(model="gpt-4o", input_tokens=1000, catalog=catalog)
print(catalog.loaded_model_count)  # 1
print(catalog.metadata.source_sha256)
```

Plain `.json` output is supported too. A selected catalog is explicit per call;
loading it never mutates the installed package or changes a global default.

## Offline example

For an entirely offline example, run `python examples/custom_catalog.py` from an
installed checkout. It writes a small local fixture, generates provider-only,
model-only and combined JSON/gzip catalogs in a temporary directory, then passes
each catalog explicitly to `calculate`. Its new model ID is independent of the
bundled snapshot. Non-selected IDs raise `KeyError` in that catalog; invalid
usage raises Pydantic `ValidationError`, and missing supported rates raise
`MissingPriceError`. Generation does not change what a default calculation uses.

## Reproducible generation and drift checks

Live generation downloads the latest catalog from
[LiteLLM](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json).
For repeatable builds, keep a JSON snapshot and generate from it:

```bash
tokenary-generate --input prices.lock.json --models gpt-4o o1 --output my_prices.py
tokenary-generate --input prices.lock.json --models gpt-4o o1 --output my_prices.py --check
```

`--check` exits with status 1 if the output is missing or has drifted, and never
rewrites it. Python checks compare syntax trees so formatting changes do not cause
false drift reports. JSON and gzip checks compare canonical JSON content so
formatting, checkout line endings and Python/zlib builds do not cause false drift.

Each output records the source identifier, the SHA-256 of the canonical full
source JSON, and a checksum of the selected prices and enum names. Input ordering
and generation time do not affect output with the same serializer/compressor.
Gzip timestamps are fixed; canonical content hashes are independent of gzip
encoding. Runtime loaders verify the selected catalog's checksum.

Regeneration preserves existing output enum names, including collisions. New
collisions receive a deterministic hash suffix instead of renumbering old names.
Subset names are resolved against the full source and the bundled name history.
Generation and runtime use `tokenary.pricing.ModelPricing` directly.
Outputs include price fields, provider, mode and the supported
[model metadata](model-metadata.md), including token limits and capabilities.
Additional upstream `supports_*` and `supported_*` fields are retained as data;
unrelated source annotations are omitted. Metadata participates in catalog
checksums and is available through `CATALOG.models["model-id"]`.
