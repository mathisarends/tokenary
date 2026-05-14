from tokenary import ModelName, calculate

# o1 charges separately for reasoning tokens
result = calculate(
    model=ModelName.O1,
    input_tokens=500,
    output_tokens=200,
    reasoning_tokens=300,
)

print(f"Total cost: ${result.total_cost:.6f}")
print(f"  Input:     ${result.input_cost:.6f}")
print(f"  Output:    ${result.output_cost:.6f}")
print(f"  Reasoning: ${result.reasoning_cost:.6f}")
