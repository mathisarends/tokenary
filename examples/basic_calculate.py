import tokenary
from tokenary import ModelName

result = tokenary.calculate(
    model=ModelName.AZURE_GPT_3_5_TURBO,
    input_tokens=1000,
    output_tokens=500,
)

print(f"Total cost: ${result.total_cost:.6f}")
print(f"  Input:  ${result.input_cost:.6f}")
print(f"  Output: ${result.output_cost:.6f}")
