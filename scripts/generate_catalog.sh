#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

uv run tokenary-generate \
  --input data/model_prices.generated.json \
  --source https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json \
  --all \
  --output tokenary/data/catalog.json.gz "$@"
