[Documentation](README.md) · [Quick start](../README.md)

# Model limits and capabilities

Each catalog entry exposes prices and optional LiteLLM model metadata through
the same `ModelPricing` object. Inspect the bundled offline catalog with the
public `get_default_catalog()` function:

```python
from tokenary import get_default_catalog

catalog = get_default_catalog()
model = catalog.models["gpt-4o"]
print(model.max_input_tokens)
print(model.max_output_tokens)
print(model.supports_function_calling)
print(model.supports_prompt_caching)
print(model.prompt_cache_min_tokens)
```

Importing the function performs no resource reads or network I/O. Calling it
opens the name/provider index; looking up a model opens only its provider resource
and validates that model. Repeated lookups reuse the validated object. The
full `ModelName` enum is not constructed by these calls.

## Available metadata

| Fields | Meaning |
| --- | --- |
| `max_input_tokens`, `max_output_tokens` | Upstream input and output limits |
| `max_tokens` | Legacy LiteLLM limit, retained with its original meaning |
| `supports_function_calling`, `supports_parallel_function_calling`, `supports_tool_choice` | Tool calling capabilities |
| `supports_response_schema`, `supports_native_structured_output` | Structured output capabilities |
| `supports_system_messages`, `supports_assistant_prefill`, `supports_native_streaming` | Message and streaming capabilities |
| `supported_modalities`, `supported_output_modalities` | Supported input and output modalities |
| `supports_vision`, `supports_audio_input`, `supports_audio_output`, `supports_video_input`, `supports_pdf_input` | Media input/output capabilities |
| `supports_reasoning`, `supports_adaptive_thinking`, `thinking_always_on` | Reasoning and thinking capabilities |
| `reasoning_effort_levels`, `default_reasoning_effort`, `reasoning_modes`, `reasoning_contexts` | Available reasoning settings and the upstream default |
| `supports_prompt_caching`, `prompt_cache_min_tokens` | Prompt caching support and minimum token count |
| `supports_web_search`, `supports_url_context`, `supports_computer_use` | Additional model capabilities |
| `supported_endpoints`, `supported_regions` | API routes and regions listed upstream |
| `deprecation_date` | Upstream deprecation date, retained as a string |
| `litellm_provider`, `mode` | Provider identifier and model type, such as chat or embedding |

Missing or explicit `null` values are `None`. This means **unknown**, including
when an older catalog lacks metadata. An explicit `False`, zero or empty
collection remains distinct from `None`. Do not infer an unsupported capability
from missing metadata, or infer a modality list from another capability flag.

Known capability flags accept booleans, and known token counts accept
nonnegative integers (including integral upstream floats such as `1024.0`).
Strings, booleans used as counts, fractions and nonfinite counts fail validation.
Collection fields above are exposed as tuples; `model.model_dump(mode="json")`
serializes them as JSON arrays. Reasoning settings and date strings are retained
without restricting them to a fixed list of provider-specific values.

Additional upstream `supports_*` and `supported_*` fields are retained as data
even when Tokenary has no typed field for them. Inspect them with
`model.model_extra` or include them in `model.model_dump()`. They are not
interpreted or validated as known capabilities.

## Limits describe the source snapshot

Metadata comes from the same pinned LiteLLM snapshot as the prices, rather than
probing a provider or a running proxy. Coverage varies by model and provider.
See [LiteLLM's metadata specification](https://docs.litellm.ai/docs/provider_registration/add_model_pricing).

Input and output limits are copied independently. Tokenary does not add them to
derive a combined context window or infer either limit from legacy `max_tokens`:
LiteLLM documents that legacy field as potentially referring to input or output.

Metadata is informational. `calculate()` continues to price the supplied usage
even if it exceeds a listed limit or uses a capability marked `False`. It does
not reject deprecated models, choose API endpoints, select reasoning settings,
or enforce cache minimums. Supported billing rates and inclusive usage rules
still determine the calculation; see [usage and billing](usage.md).

## Custom catalogs and live refresh

Generated Python, JSON and gzip catalogs retain these fields. Access a generated
module through `CATALOG.models["model-id"]`, or inspect `catalog.models` after
loading a JSON/gzip catalog. Existing catalogs remain readable; regenerate them
from a source containing metadata to populate previously missing fields.

`LivePricingCatalog` refreshes metadata together with prices. Inspect
`(await prices.get_catalog()).models["model-id"]`; the same metadata survives
disk-cache reuse, while previously returned catalog snapshots keep their values.
See [custom catalogs](catalogs.md) and [live pricing](live-pricing.md).

Selected-catalog checksums cover retained metadata as well as prices and enum
names. A capability-only change therefore changes the catalog checksum, even
when the estimated cost stays the same. The source checksum continues to cover
the full raw source.
