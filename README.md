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
catalog below when you want newer prices or a selected set of models, or opt into
the [asynchronous live pricing manager](#optional-automatic-price-updates).

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

## Optional: automatic price updates

Use one `LivePricingCatalog` per application worker/event loop to pick up current
LiteLLM prices without a new SDK release. Price retrieval is always asynchronous;
`calculate()` stays synchronous and never performs network I/O:

```python
from tokenary import LivePricingCatalog, calculate

async def main():
    async with LivePricingCatalog(
        models=["gpt-4o", "o1"],
        refresh_interval_seconds=3600,
        cache_path=".cache/tokenary-prices.json",
    ) as prices:
        catalog = await prices.get_catalog()
        result = calculate(model="gpt-4o", input_tokens=1000, catalog=catalog)
        print(result.total_cost)
```

In a server, keep the manager in your application lifespan and call
`await prices.get_catalog()` in request handlers. Optionally warm it at startup.
For a batch or billing run, acquire one catalog and reuse it throughout the run.
Construction performs no I/O. A fresh memory cache returns immediately; otherwise
the manager loads its optional disk cache or downloads the upstream map using
`httpx2.AsyncClient`. HTTP status and source JSON are checked; selected prices
reuse the existing Pydantic `ModelPricing` validation and catalog checksums.
JSON decoding, catalog construction and disk operations run off the event loop.

Once the refresh interval expires, the next call refreshes before returning.
Concurrent callers on one instance share an update, including concurrent forced
updates. There is no timer or background polling. Models and providers use the
generator's exact selection rules; omitting both selects all models. The full
upstream JSON is downloaded before selection; filters reduce validation and cache
size, not the upstream response size.

| Setting | Default | Behavior |
| --- | --- | --- |
| `refresh_interval_seconds` | `3600` | Refresh on access after one hour |
| `timeout_seconds` | `10` | HTTPX2 timeout for network operations |
| `retry_interval_seconds` | `60` | Back off after a failed refresh |
| `max_stale_seconds` | `None` | Strict: propagate errors when no current catalog exists |
| `cache_path` | `None` | Optional atomic disk cache, reusable after restart |
| `url` | LiteLLM upstream | Override with a compatible HTTP(S) source |
| `client` | Managed internally | Optional caller-owned `httpx2.AsyncClient` |

To keep serving estimates during an outage, explicitly set, for example,
`max_stale_seconds=86400`. After a failed refresh this allows the last valid
snapshot up to 24 hours **since its successful fetch**, with a warning. The age
limit is checked on each call, including during retry backoff. Without a valid
snapshot, or beyond that limit, errors propagate. Invalid updates and disk-write
failures leave the previous catalog and cache intact; the bundled default is
never silently substituted. Inspect `prices.is_stale`, `prices.last_refreshed_at`
and `prices.last_error` for health reporting. `last_refreshed_at` is the UTC fetch
time, not a guarantee of when a provider made its prices effective.

`await prices.get_catalog(force_refresh=True)` bypasses freshness and retry
backoff. Network cancellation propagates; it does not become a stale fallback or
a failed-attempt backoff. Once an atomic cache write starts, cancellation waits
for that write to finish before releasing the update lock.
Use `async with` or `await prices.aclose()` to release the owned client. An
injected client remains open and must be closed by its caller.

Each successful refresh replaces the manager's current snapshot. Already
returned catalogs and results retain their prices; results still carry the source
and catalog checksums. Store the amount and checksum with historical usage if
you need auditability. The latest map does not reconstruct historical tariffs.
Freshness is limited by when LiteLLM publishes a change plus the chosen interval.

The live cache is a versioned JSON envelope bound to the source URL and selection,
not a public `PricingCatalog.from_file()` artifact. Use a separate cache path for
each worker/selection. Locks and retry state are per instance; this is not a
distributed cache or cross-process download coordinator.

Run `python examples/live_catalog.py` for an offline demonstration using HTTPX2's
mock transport, including a price change, stable old snapshot and cached restart.
The generator's downloader also uses async HTTPX2. Its CLI starts an event loop
only at the command boundary; async applications should use the live manager or
await `tokenary.generator.downloader.fetch_model_prices_raw()` directly.

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

`--output` is required for both generation and `--check`; there is no implicit
destination. Scripts that relied on the v0.2 default `model_prices.py` must add
`--output model_prices.py`. Missing/invalid arguments and `--help` are handled
before downloads, catalog reads or writes. Outputs are validated first and
replaced atomically; a failed replacement preserves an existing file and removes
its temporary file. An unsuccessful generation reports an error and nonzero exit.

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

For an entirely offline example, run `python examples/custom_catalog.py` from an
installed checkout. It writes a small local fixture, generates provider-only,
model-only and combined JSON/gzip catalogs in a temporary directory, then passes
each catalog explicitly to `calculate`. Its new model ID is independent of the
bundled snapshot. Non-selected IDs raise `KeyError` in that catalog; invalid
usage raises Pydantic `ValidationError`, and missing supported rates raise
`MissingPriceError`. Generation does not change what a default calculation uses.

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

Supported threshold spellings are an integer token count, or an integer with
lowercase `k` (1,000) or `m` (1,000,000), followed by `_tokens`. At the exact
threshold the lower rate still applies. Recognizable unsupported token-tier
fields (for example `input_cost_per_token_above_200K_tokens`) raise a Pydantic
`ValidationError` during generation or the model's first pricing validation;
they are never silently priced at the base rate. Other unknown non-context price
fields remain available. Cache TTL fields such as `above_1hr` are separate from
token thresholds; `_priority`, `_batches` and `_flex` rates are retained data for
unsupported service tiers and do not change standard rates.

This interprets the selected snapshot, without imposing a surcharge on models
that have no such fields. [LiteLLM's cost-map contract](https://docs.litellm.ai/docs/proxy/model_cost_map)
distinguishes context, service-tier and cache-duration suffixes.
[Google's Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-pro)
assigns input and output rates by prompt-length band, including the boundary at
200k. [Anthropic's long-context rules](https://platform.claude.com/docs/en/about-claude/pricing#long-context-pricing)
count cache reads/writes in prompt length and apply a request's band to that
request. These sources explain the interpretation; prices and supported context
windows can change independently of the installed offline snapshot.

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
uv run python examples/custom_catalog.py
uv run python examples/live_catalog.py
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
outside the checkout. It exercises both installed CLI entries, provider/model
selection, all three output formats, new model IDs, excluded-model failures,
read/validation caches, default compatibility and a runtime source-size budget.
CI runs these checks and every example on Python 3.13 and 3.14. After building a
wheel, reproduce the smoke test from a directory outside the checkout:

```bash
uv run --isolated --no-project --python 3.14 --with /absolute/path/to/tokenary/dist/tokenary-0.2.0-py3-none-any.whl python -I /absolute/path/to/tokenary/scripts/smoke_installed.py
```

The wheel environment includes only runtime dependencies; the fixture stays
offline and needs no provider SDK or Ruff. Benchmarks are not timing gates in CI.

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
