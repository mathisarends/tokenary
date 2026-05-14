from tokenary import ModelName, calculate

result = calculate(
    model=ModelName.GPT_4O,
    input_tokens=500,
    output_tokens=200,
    generated_images=2,
    code_interpreter_sessions=1,
)

print(f"Total cost: ${result.total_cost:.6f}")
print(f"  Text:             ${result.input_cost + result.output_cost:.6f}")
print(f"  Images:           ${result.image_cost:.6f}")
print(f"  Code interpreter: ${result.code_interpreter_cost:.6f}")
