# tokenary

Small Python library for LLM API cost estimates from the LiteLLM pricing catalog.
The runtime contains a price-free model index and compressed offline provider
catalogs. It reads only the providers used and validates/caches individual models.
No network access is needed when calculating costs.

## Installation

```bash
pip install tokenary
```

## Quick start

Import `calculate` and start calculating. No generation or configuration is needed:

```python
from tokenary import calculate

result = calculate(model="gpt-4o", input_tokens=1000, output_tokens=500)
print(result.model_dump())
```

Tokenary loads its bundled model index on first use, opens only the requested
provider file, and validates only the requested models. Repeated lookups reuse
provider data and validated prices. Calculations never download prices; they
use the snapshot shipped with the installed version. You can generate a custom
catalog below when you want newer prices or a selected set of models.

`from tokenary import ModelName` also remains supported, including the existing
enum member names. This loads the name index and full enum, without provider prices.
Use string IDs
or the generated subset enum when you want to avoid that work. Generated enums
also provide static model names for IDE completion.

The bundled provider files are included in every wheel for offline compatibility.
Generating a subset avoids loading that data and limits generated code, but does
not remove the bundled files from an existing installation. Generating from a local
source reads only the separate naming history, never bundled provider prices.

### Request objects

```python
from tokenary import UsageCostRequest, calculate

request = UsageCostRequest(model="gpt-4o", input_tokens=2000, output_tokens=800)
result = calculate(request)
```

Model IDs are strings, so a generated subset or custom catalog can contain models
that were not known when your installed `tokenary` version was released.

## Optional: generate only the models you use

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

### JSON catalogs

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

## Supported usage parameters

| Parameter | Type | Meaning |
| --- | --- | --- |
| `model` | `str` / `StrEnum` | Exact model identifier |
| `input_tokens` | `int` | Total input including cache and audio subsets |
| `output_tokens` | `int` | Total output including reasoning and audio subsets |
| `reasoning_tokens` | `int` | Reasoning subset of output tokens |
| `audio_input_tokens` | `int` | Audio subset of input tokens |
| `audio_output_tokens` | `int` | Audio subset of output tokens |
| `cached_input_tokens` | `int` | Text cache-read subset of input tokens |
| `cache_creation_input_tokens` | `int` | Total text cache-write subset of input tokens |
| `cache_creation_1h_input_tokens` | `int` | One-hour subset of cache writes |
| `generated_images` | `int` | Generated images |
| `code_interpreter_sessions` | `int` | Code interpreter sessions |
| `file_search_calls` | `int` | File search calls |
| `file_search_gb_days` | `float` | File search storage in GB-days |
| `vector_store_gb_days` | `float` | Vector store storage in GB-days |

Results contain a per-category `CostBreakdown` and `total_cost` in USD. Usage must
be nonnegative and finite; unknown request fields are rejected.

Every requested nonzero category must have a supported rate. Missing rates raise
`MissingPriceError`, including a model that only has pixel prices when you request
a per-image calculation. Explicit zero prices are valid; unused categories do not
require a price. Pixel, character, duration and service-tier billing are not
implemented and must not be approximated with unrelated token or image rates.

Cache reads, five-minute writes and one-hour writes are separate from ordinary
input. Known `*_above_<N>k_tokens` tariff fields apply above their strict threshold
to the entire category, based on total input context, including cached tokens.
The highest matching threshold wins. Output rates use that same input threshold.

Input and output totals are inclusive. Reasoning and audio tokens are subsets,
not quantities to add again. All disjoint subsets must fit within their total.
This follows OpenAI's reported
[reasoning usage](https://developers.openai.com/api/docs/guides/reasoning).
Cost totals are computed from the breakdown rather than independently stored;
results also include the source and selected-catalog checksums.

For example, the bundled `o1` rates give $0.07266 for 100 input tokens and 1,186
total output tokens, of which 1,024 are reasoning tokens:

```python
result = calculate(
    model="o1", input_tokens=100, output_tokens=1186, reasoning_tokens=1024
)
```

If migrating from the original API, add previously separate reasoning or audio
counts to the corresponding total once; continue passing the subset fields for
the breakdown. Passing a request object with conflicting usage keywords fails.

### Provider usage adapters

Normalize a response's usage object without installing provider SDKs:

```python
from tokenary import calculate, from_openai_usage

request = from_openai_usage("o1", response.usage)
result = calculate(request)
```

`from_openai_usage` accepts dictionaries or SDK objects with `model_dump()` for
both Responses and Chat Completions usage. It preserves inclusive totals and
extracts reasoning, cache-read and audio details. An ambiguous combination of
audio and cache counters is rejected rather than guessing their overlap.

`from_anthropic_usage(model, response.usage)` adds separately reported ordinary
input, cache reads and cache writes into one inclusive total, and retains the
five-minute/one-hour write split. This follows Anthropic's
[cache token accounting](https://platform.claude.com/docs/en/build-with-claude/prompt-caching).
Unsupported server-tool charges and nonstandard service tiers are rejected.
Adapters handle token usage; other supported costs can be added by creating a
request with the corresponding explicit usage fields. Pricing uses standard
service rates; region-specific models must use their exact catalog ID.

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
Generation and runtime use `tokenary.pricing.ModelPricing` directly. The former
`tokenary.generator.schemas.GeneratedModelPricing` API has been removed; import
`ModelPricing` from `tokenary.pricing` if you used that generator schema.
Only provider, mode and price fields are included; upstream capability and context
metadata is kept in the source snapshot instead of copied into every installation.

## Development

```bash
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build --wheel
uv run python scripts/benchmark_runtime.py
```

The repository keeps its upstream snapshot at
`data/model_prices.generated.json`; that full snapshot is not included in wheels.
Rebuild the private index/provider resources from that pinned source with:

```bash
./scripts/generate_catalog.sh
./scripts/generate_catalog.sh --check
```

On Windows, the equivalent command is:

```powershell
uv run python -m tokenary.generator.bundle --input data/model_prices.generated.json --source https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json --output-dir tokenary/data
```

Update the upstream snapshot deliberately, then regenerate and review the price
diff before committing. CI checks that the pinned snapshot and bundled catalog
agree, alongside tests, lint, formatting and wheel construction. This private
bundle format replaces `tokenary/data/catalog.json.gz`; public single-file
JSON/gzip catalogs and generated Python modules keep their existing format.
An isolated wheel smoke test also runs without development tools or provider SDKs
to verify subset generation, loading, default compatibility and a runtime source
size budget. Benchmarks report local medians; they are not timing gates in CI.

## Size and performance

The provider bundle contains 123 provider files and a price-free index, totaling
190,119 compressed bytes with the pinned source. Splitting files increases the
compressed total compared with the former 75,518-byte monolithic snapshot, while
avoiding decoding unrelated provider prices. A generated module for `gpt-4o` and
`o1` from the pinned snapshot is 1,552 bytes and reads no bundled provider prices.

Historical v0.2.0 measurements, before the provider split, used isolated
wheel installs, seven fresh processes and 10,000 calls per process:

| Metric | Original 0.1.0 | 0.2 |
| --- | ---: | ---: |
| Import median | 137.6 ms | 101.8 ms |
| First calculation including total | 20.1 ms | 15.8 ms |
| Repeated keyword calculation including total | 3.2 us | 7.3 us |
| Repeated prevalidated request including total | 2.1 us | 4.9 us |

The added validation, category checks, context tiers and provenance have a cost
per call. Startup and installation size improve; steady-state billing does more
work. Use a generated subset to avoid bundled provider data,
and pass an adapter's validated request directly to `calculate`. These timings
are illustrative local measurements and vary by Python build and machine.

The provider-split comparison in [ticket 009](tickets/009-lazy-bundled-catalog.md)
records current medians, ranges, working-set deltas and exact wheel hashes.
Run `scripts/benchmark_runtime.py --runs 7` against an isolated installed wheel
to repeat it. Each run starts a fresh process after one unmeasured bytecode warmup;
each process performs 10,000 calls per repeated-call measurement. Windows working
set or Linux resident pages are reported when available. Results are local
observations; the regression tests enforce resource-loading behavior without
absolute timing limits.
