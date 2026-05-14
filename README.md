# tokenary

Minimal Python library to calculate LLM API costs based on the LiteLLM model catalog.

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

### Multimodal / extended usage

```python
from tokenary import ModelName, calculate

result = calculate(
    model=ModelName.GPT_4O,
    input_tokens=500,
    output_tokens=200,
    generated_images=2,
    code_interpreter_sessions=1,
)

print(f"Total: ${result.total_cost:.6f}")
```

### All supported parameters

| Parameter | Type | Description |
|---|---|---|
| `model` | `ModelName` | Model identifier |
| `input_tokens` | `int` | Number of input tokens |
| `output_tokens` | `int` | Number of output tokens |
| `reasoning_tokens` | `int` | Reasoning tokens (e.g. o1) |
| `audio_input_tokens` | `int` | Audio input tokens |
| `generated_images` | `int` | Number of generated images |
| `code_interpreter_sessions` | `int` | Code interpreter sessions |
| `file_search_calls` | `int` | File search API calls |
| `file_search_gb_days` | `float` | File search storage (GB-days) |
| `vector_store_gb_days` | `float` | Vector store storage (GB-days) |

The returned `CostBreakdown` object contains per-category costs (`input_cost`, `output_cost`, `reasoning_cost`, …) and a `total_cost`, all in USD.

## Generate pricing artifacts

Re-generate the bundled pricing data from the LiteLLM catalog:

```bash
python -m tokenary.generator
```
