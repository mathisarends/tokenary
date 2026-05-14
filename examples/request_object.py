from tokenary import ModelName, UsageCostRequest, calculate

request = UsageCostRequest(
    model=ModelName.AZURE_GPT_3_5_TURBO,
    input_tokens=2000,
    output_tokens=800,
    reasoning_tokens=200,
)

result = calculate(request)

print(result.model_dump())
