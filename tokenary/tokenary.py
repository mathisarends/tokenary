import argparse
import json
from pathlib import Path

from .downloader import DEFAULT_PRICE_URL, fetch_model_prices_raw, write_raw_prices_file
from .views import CostBreakdown, PricingCatalog, UsageCostRequest

DEFAULT_GENERATED_FILE = "model_prices.generated.json"


def generate_catalog_file(
	output_path: str | Path = DEFAULT_GENERATED_FILE,
	source_url: str = DEFAULT_PRICE_URL,
) -> Path:
	raw = fetch_model_prices_raw(url=source_url)
	return write_raw_prices_file(raw_prices=raw, output_path=output_path)


def load_catalog(path: str | Path) -> PricingCatalog:
	raw = json.loads(Path(path).read_text(encoding="utf-8"))
	if not isinstance(raw, dict):
		raise ValueError("Catalog file is not a JSON object")
	return PricingCatalog.from_raw(raw)


def calculate_usage_cost(catalog: PricingCatalog, usage: UsageCostRequest) -> CostBreakdown:
	pricing = catalog.models.get(usage.model)
	if pricing is None:
		raise KeyError(f"Unknown model: {usage.model}")

	input_cost = usage.input_tokens * (pricing.input_cost_per_token or 0.0)
	output_cost = usage.output_tokens * (pricing.output_cost_per_token or 0.0)
	reasoning_cost = usage.reasoning_tokens * (pricing.output_cost_per_reasoning_token or 0.0)
	audio_input_cost = usage.audio_input_tokens * (pricing.input_cost_per_audio_token or 0.0)

	image_cost = usage.generated_images * (pricing.output_cost_per_image or 0.0)
	code_interpreter_cost = usage.code_interpreter_sessions * (pricing.code_interpreter_cost_per_session or 0.0)
	file_search_call_cost = usage.file_search_calls * ((pricing.file_search_cost_per_1k_calls or 0.0) / 1000.0)
	file_search_storage_cost = usage.file_search_gb_days * (pricing.file_search_cost_per_gb_per_day or 0.0)
	vector_store_cost = usage.vector_store_gb_days * (pricing.vector_store_cost_per_gb_per_day or 0.0)

	total_cost = (
		input_cost
		+ output_cost
		+ reasoning_cost
		+ audio_input_cost
		+ image_cost
		+ code_interpreter_cost
		+ file_search_call_cost
		+ file_search_storage_cost
		+ vector_store_cost
	)

	return CostBreakdown(
		model=usage.model,
		input_cost=input_cost,
		output_cost=output_cost,
		reasoning_cost=reasoning_cost,
		audio_input_cost=audio_input_cost,
		image_cost=image_cost,
		code_interpreter_cost=code_interpreter_cost,
		file_search_call_cost=file_search_call_cost,
		file_search_storage_cost=file_search_storage_cost,
		vector_store_cost=vector_store_cost,
		total_cost=total_cost,
	)


def cli_generate() -> None:
	parser = argparse.ArgumentParser(description="Generate a local model price catalog file from LiteLLM pricing data.")
	parser.add_argument("-o", "--output", default=DEFAULT_GENERATED_FILE, help="Output file path.")
	parser.add_argument("--url", default=DEFAULT_PRICE_URL, help="Source JSON URL.")
	args = parser.parse_args()

	target = generate_catalog_file(output_path=args.output, source_url=args.url)
	print(f"Generated pricing catalog: {target}")


def main() -> None:
	cli_generate()


if __name__ == "__main__":
	main()
