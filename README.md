# tokenary

Small Python library for LLM API cost estimates from the LiteLLM pricing catalog.
The runtime contains a compact, compressed offline catalog instead of thousands
of generated pricing constructors. It validates and caches only the models used.
No network access is needed when calculating costs.

## Installation

```bash
pip install tokenary
```

## Generate only the models you use

Generate a small module containing just your selected models:

```bash
tokenary-generate --models gpt-4o o1 --output my_prices.py
```

Then use that module's enum and calculator:

```python
from my_prices import ModelName, calculate

result = calculate(
    model=ModelName.GPT_4O,
    input_tokens=1000,
    output_tokens=500,
)
print(result.total_cost)
```

The generated module has its own catalog. Calculating with it does not load the
bundled full catalog or construct price objects for unrelated models. It imports
the shared calculation engine from `tokenary`; it does not duplicate library code.
Generation works after a plain `pip install tokenary` and does not require Ruff.

Use exact LiteLLM model IDs. An unknown ID fails generation without changing the
output. Pass `--all` explicitly if you want the entire catalog.

## Default API

The default API still works with the bundled catalog:

```python
from tokenary import calculate

result = calculate(model="gpt-4o", input_tokens=1000, output_tokens=500)
print(result.model_dump())
```

`from tokenary import ModelName` also remains supported, including the existing
enum member names. This explicitly loads the full model-name enum. Use string IDs
or the generated subset enum when you want to avoid that work. Generated enums
also provide static model names for IDE completion.

The bundled data file is included in every wheel for offline compatibility.
Generating a subset avoids loading that data and limits generated code, but does
not remove the bundled data file from an existing installation.

### Request objects

```python
from tokenary import UsageCostRequest
from my_prices import calculate

request = UsageCostRequest(model="gpt-4o", input_tokens=2000, output_tokens=800)
result = calculate(request)
```

Model IDs are strings, so a generated subset or custom catalog can contain models
that were not known when your installed `tokenary` version was released.

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

### Supported usage parameters

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
false drift reports. JSON and gzip output are checked byte for byte.

Each output records the source identifier, the SHA-256 of the canonical full
source JSON, and a checksum of the selected prices and enum names. Input ordering
and generation time do not affect output. Gzip timestamps are fixed. Runtime
loaders verify the selected catalog's checksum.

Regeneration preserves existing output enum names, including collisions. New
collisions receive a deterministic hash suffix instead of renumbering old names.
Subset names are resolved against the full source and the bundled name history.
All generation and runtime validation share one pricing schema. Only provider,
mode and price fields are included; upstream capability and context metadata is
kept in the source snapshot instead of copied into every installation.

## Development

```bash
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build --wheel
```

The repository keeps its upstream snapshot at
`data/model_prices.generated.json`; that full snapshot is not included in wheels.
Rebuild the bundled compressed catalog from that pinned source with:

```bash
./scripts/generate_catalog.sh
./scripts/generate_catalog.sh --check
```

On Windows, the equivalent command is:

```powershell
uv run tokenary-generate --input data/model_prices.generated.json --source https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json --all --output tokenary/data/catalog.json.gz
```

Update the upstream snapshot deliberately, then regenerate and review the price
diff before committing. CI checks that the pinned snapshot and bundled catalog
agree, alongside tests, lint, formatting and wheel construction.
