from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen

DEFAULT_PRICE_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"


def fetch_model_prices_raw(
    url: str = DEFAULT_PRICE_URL, timeout_seconds: int = 30
) -> dict[str, object]:
    request = Request(url=url, headers={"User-Agent": "tokenary/0.1.0"})
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read().decode("utf-8")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Downloaded model price payload is not a JSON object")
    return data


def write_raw_prices_file(
    raw_prices: dict[str, object], output_path: str | Path
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw_prices, indent=2, sort_keys=True), encoding="utf-8")
    return path
