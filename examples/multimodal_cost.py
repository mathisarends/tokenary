from tokenary import ModelName, calculate

# Output totals include reasoning tokens; the breakdown separates their cost.
result = calculate(
    model=ModelName.O1,
    input_tokens=500,
    output_tokens=500,
    reasoning_tokens=300,
)

print(f"Total cost: ${result.total_cost:.6f}")
print(f"  Input:     ${result.input_cost:.6f}")
print(f"  Output:    ${result.output_cost:.6f}")
print(f"  Reasoning: ${result.reasoning_cost:.6f}")
