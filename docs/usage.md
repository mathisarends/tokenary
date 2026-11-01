[Documentation](README.md) · [Quick start](../README.md)

# Usage and billing reference

`calculate()` returns a `CostBreakdown` in USD. It accepts either usage keywords
or a validated request, plus an optional `catalog=` argument. See
[custom catalogs](catalogs.md) and [live pricing](live-pricing.md) to choose prices.

## Request objects

```python
from tokenary import UsageCostRequest, calculate

request = UsageCostRequest(model="gpt-4o", input_tokens=2000, output_tokens=800)
result = calculate(request)
```

Model IDs are strings, so a generated subset or custom catalog can contain models
that were not known when your installed `tokenary` version was released.

## Usage parameters

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

## Missing and unsupported prices

Every requested nonzero category must have a supported rate. Missing rates raise
`MissingPriceError`, including a model that only has pixel prices when you request
a per-image calculation. Explicit zero prices are valid; unused categories do not
require a price. Pixel, character, duration and service-tier billing are not
implemented and must not be approximated with unrelated token or image rates.

## Cache and context tiers

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
token thresholds; `_priority`, `_batches`, `_flex` and `_ultrafast` service-tier rates, and
`_decisions` endpoint rates, are retained as data and do not change standard rates.
Only five-minute and one-hour text cache writes can be requested explicitly;
other TTL prices, including `above_12hr`, remain data only.

This interprets the selected snapshot, without imposing a surcharge on models
that have no such fields. [LiteLLM's cost-map contract](https://docs.litellm.ai/docs/proxy/model_cost_map)
distinguishes context, service-tier and cache-duration suffixes.
[Google's Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-pro)
assigns input and output rates by prompt-length band, including the boundary at
200k. [Anthropic's long-context rules](https://platform.claude.com/docs/en/about-claude/pricing#long-context-pricing)
count cache reads/writes in prompt length and apply a request's band to that
request. These sources explain the interpretation; prices and supported context
windows can change independently of the installed offline snapshot.

## Inclusive token totals

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

See the [migration notes](migration.md) for the original API. Passing a request
object with conflicting usage keywords fails.

## Provider usage adapters

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

## Errors

| Error | Meaning |
| --- | --- |
| `KeyError` | The exact model ID is absent from the selected catalog |
| Pydantic `ValidationError` | Invalid usage, invalid prices or unsupported context-tier spelling |
| `MissingPriceError` | A requested nonzero category has no supported price |
| `UnsupportedUsageError` | A usage adapter cannot safely interpret the reported usage |
| `ValueError` | Conflicting request arguments or an invalid catalog artifact |

See [live pricing failure handling](live-pricing.md#refresh-failures-and-stale-data)
for network and disk errors during refresh.
