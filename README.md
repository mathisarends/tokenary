# tokenary

Minimal Python library to:

- generate typed pricing data from the LiteLLM model catalog
- expose a user-facing API for usage/session cost calculation

## Generate pricing artifacts

Run the generator module (tokenary):

```bash
uv run python -m tokenary.generator
```

By default this writes:

- `data/model_prices.generated.json`
- `tokenary/_generated.py`

The generated Python module contains:

- `ModelName` as `StrEnum`
- one `GeneratedModelPricing(...)` object per model
- lookup mappings like `MODEL_PRICINGS` and `MODEL_PRICINGS_BY_NAME`

Custom outputs:

```bash
uv run python -m tokenary.generator --json-output data/model_prices.generated.json --python-output tokenary/_generated.py
```

## Python usage

```python
from tokenary import ModelName, Tokenary

tokenary = Tokenary()

result = tokenary.calculate(
    model=ModelName.AZURE_GPT_3_5_TURBO,
    input_tokens=1000,
    output_tokens=500,
)

print(result.model_dump())
```

Functional API (without keeping class state):

```python
from tokenary import ModelName, calculate

result = calculate(
    model=ModelName.AZURE_GPT_3_5_TURBO,
    input_tokens=1000,
    output_tokens=500,
)

print(result.total_cost)
```
