# tokenary

Minimal Python library to calculate LLM API costs based on the LiteLLM model catalog.

The bundled pricing data (`tokenary/_generated.py`, `data/model_prices.generated.json`) is generated from the [LiteLLM model prices catalog](https://github.com/BerriAI/litellm). You are not dependent on a new `tokenary` release to pick up pricing updates: the generator ships as part of the installed package, so you can re-run it yourself at any time (see [Generate pricing artifacts](#generate-pricing-artifacts)) to refresh the data against the latest LiteLLM catalog.

## Installation

```bash
pip install tokenary
```

## Usage

### Functional API

```python
import tokenary
from tokenary import ModelName

result = tokenary.calculate(
    model=ModelName.AZURE_GPT_3_5_TURBO,
    input_tokens=1000,
    output_tokens=500,
)

print(result.total_cost)
print(result.model_dump())
```

### Request object

```python
from tokenary import ModelName, UsageCostRequest, calculate

request = UsageCostRequest(
    model=ModelName.AZURE_GPT_3_5_TURBO,
    input_tokens=2000,
    output_tokens=800,
    reasoning_tokens=200,
)

result = calculate(request)
print(result.model_dump())
```

### Reasoning tokens (e.g. o1)

```python
from tokenary import ModelName, calculate

result = calculate(
    model=ModelName.O1,
    input_tokens=500,
    output_tokens=200,
    reasoning_tokens=300,
)

print(f"Total: ${result.total_cost:.6f}")
print(f"  Reasoning: ${result.reasoning_cost:.6f}")
```

### All supported parameters

| Parameter                   | Type        | Description                    |
| --------------------------- | ----------- | ------------------------------ |
| `model`                     | `ModelName` | Model identifier               |
| `input_tokens`              | `int`       | Number of input tokens         |
| `output_tokens`             | `int`       | Number of output tokens        |
| `reasoning_tokens`          | `int`       | Reasoning tokens (e.g. o1)     |
| `audio_input_tokens`        | `int`       | Audio input tokens             |
| `generated_images`          | `int`       | Number of generated images     |
| `code_interpreter_sessions` | `int`       | Code interpreter sessions      |
| `file_search_calls`         | `int`       | File search API calls          |
| `file_search_gb_days`       | `float`     | File search storage (GB-days)  |
| `vector_store_gb_days`      | `float`     | Vector store storage (GB-days) |

The returned `CostBreakdown` object contains per-category costs (`input_cost`, `output_cost`, `reasoning_cost`, …) and a `total_cost`, all in USD.

## Generate pricing artifacts

All pricing data bundled with `tokenary` is generated from the LiteLLM model prices catalog, not hand-maintained. This means you can re-generate it locally at any time, e.g. to pick up upstream LiteLLM pricing changes before a new `tokenary` release ships them.

This works with a plain `pip install tokenary` too — the generator is part of the installed package, so no repo checkout is required:

```bash
python -m tokenary.generator
```

or via the `tokenary-generate` console script installed alongside the package:

```bash
tokenary-generate
```

If you're working from a repo checkout, there's also a helper script:

```bash
./scripts/generate_catalog.sh
```
