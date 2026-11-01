"""Demonstrate async price updates offline with a simulated upstream service."""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx2

from tokenary import LivePricingCatalog, calculate


async def demonstrate(cache_path: Path) -> None:
    source = {"example/new-model": {"input_cost_per_token": 0.25}}
    calls = 0

    async def handle(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(200, json=source)

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as client:
        async with LivePricingCatalog(
            models=["example/new-model"], cache_path=cache_path, client=client
        ) as prices:
            old = await prices.get_catalog()
            before = calculate(model="example/new-model", input_tokens=4, catalog=old)
            assert await prices.get_catalog() is old
            assert calls == 1
            source["example/new-model"]["input_cost_per_token"] = 0.5
            current = await prices.get_catalog(force_refresh=True)
            after = calculate(
                model="example/new-model", input_tokens=4, catalog=current
            )
            assert before.total_cost == 1
            assert after.total_cost == 2
            assert before.pricing_catalog_sha256 != after.pricing_catalog_sha256
            assert (
                calculate(
                    model="example/new-model", input_tokens=4, catalog=old
                ).total_cost
                == 1
            )
            print(f"Before: ${before.total_cost}; after update: ${after.total_cost}")

        async with LivePricingCatalog(
            models=["example/new-model"], cache_path=cache_path, client=client
        ) as restarted:
            cached = await restarted.get_catalog()
            assert cached.metadata == current.metadata
            assert calls == 2
            print("Restart reused the disk cache without another download.")


if __name__ == "__main__":
    with TemporaryDirectory(prefix="tokenary-live-example-") as directory:
        asyncio.run(demonstrate(Path(directory) / "prices.json"))
