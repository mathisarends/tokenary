# tokenary

Minimal Python library to:

- download the LiteLLM model price catalog
- generate a local JSON file with the current model prices
- calculate structured usage/session costs per model

## Generate catalog file

After installation you can run:

```bash
tokenary-generate -o data/model_prices.generated.json
```

Optional custom URL:

```bash
tokenary-generate --url https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json -o data/model_prices.generated.json
```

## Python usage

```python
from tokenary import load_catalog, UsageCostRequest, calculate_usage_cost

catalog = load_catalog("data/model_prices.generated.json")

request = UsageCostRequest(
	model="amazon.nova-lite-v1:0",
	input_tokens=1000,
	output_tokens=500,
	code_interpreter_sessions=1,
)

cost = calculate_usage_cost(catalog, request)
print(cost.model_dump())
```
