"""Inspect bundled model metadata offline without building the full model enum."""

from tokenary import get_default_catalog

catalog = get_default_catalog()
model = catalog.models["gpt-4o"]

print(f"Input limit: {model.max_input_tokens}")
print(f"Output limit: {model.max_output_tokens}")
print(f"Tool calling: {model.supports_function_calling}")
print(f"Structured output: {model.supports_response_schema}")
print(f"Vision: {model.supports_vision}")
print(f"Prompt caching: {model.supports_prompt_caching}")
print(f"Cache minimum (None means unknown): {model.prompt_cache_min_tokens}")
print(f"Reasoning levels: {model.reasoning_effort_levels}")
print(f"Endpoints: {model.supported_endpoints}")
print(f"Deprecation date: {model.deprecation_date}")
assert catalog.loaded_model_count == 1
