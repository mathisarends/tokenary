import asyncio
import json
from pathlib import Path

import httpx2
from pydantic import ConfigDict, JsonValue, TypeAdapter

_DEFAULT_PRICE_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"


_RAW_PRICES: TypeAdapter[dict[str, JsonValue]] = TypeAdapter(
    dict[str, JsonValue], config=ConfigDict(allow_inf_nan=False)
)


async def fetch_model_prices_raw(
    url: str = _DEFAULT_PRICE_URL,
    timeout_seconds: float = 30,
    *,
    client: httpx2.AsyncClient | None = None,
) -> dict[str, JsonValue]:
    """Fetch typed source JSON asynchronously; validate prices after selection."""
    if client is None:
        owned_client = await asyncio.to_thread(httpx2.AsyncClient)
        async with owned_client:
            return await fetch_model_prices_raw(
                url, timeout_seconds, client=owned_client
            )
    response = await client.get(
        url,
        timeout=timeout_seconds,
        headers={"User-Agent": "tokenary"},
        follow_redirects=True,
    )
    response.raise_for_status()
    return await asyncio.to_thread(_RAW_PRICES.validate_json, response.content)


def write_raw_prices_file(
    raw_prices: dict[str, object], output_path: str | Path
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw_prices, indent=2, sort_keys=True), encoding="utf-8")
    return path
