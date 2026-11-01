[Documentation](README.md) · [Quick start](../README.md)

# Live pricing

Use one `LivePricingCatalog` per application worker/event loop to pick up current
LiteLLM prices without a new SDK release. Price retrieval is always asynchronous;
`calculate()` stays synchronous and never performs network I/O:

```python
from tokenary import LivePricingCatalog, calculate

async def main():
    async with LivePricingCatalog(
        models=["gpt-4o", "o1"],
        refresh_interval_seconds=3600,
        cache_path=".cache/tokenary-prices.json",
    ) as prices:
        catalog = await prices.get_catalog()
        result = calculate(model="gpt-4o", input_tokens=1000, catalog=catalog)
        print(result.total_cost)
```

## Application lifecycle

Refreshes also update [model metadata](model-metadata.md). Inspect
`catalog.models["gpt-4o"]` for limits and capabilities from that same snapshot.

In a server, keep the manager in your application lifespan and call
`await prices.get_catalog()` in request handlers. Optionally warm it at startup.
For a batch or billing run, acquire one catalog and reuse it throughout the run.
Construction performs no I/O. A fresh memory cache returns immediately; otherwise
the manager loads its optional disk cache or downloads the upstream map using
`httpx2.AsyncClient`. HTTP status and source JSON are checked; selected prices
reuse the existing Pydantic `ModelPricing` validation and catalog checksums.
JSON decoding, catalog construction and disk operations run off the event loop.

Once the refresh interval expires, the next call refreshes before returning.
Concurrent callers on one instance share an update, including concurrent forced
updates. There is no timer or background polling. Models and providers use the
generator's exact selection rules; omitting both selects all models. The full
upstream JSON is downloaded before selection; filters reduce validation and cache
size, not the upstream response size.

## Settings

| Setting | Default | Behavior |
| --- | --- | --- |
| `refresh_interval_seconds` | `3600` | Refresh on access after one hour |
| `timeout_seconds` | `10` | HTTPX2 timeout for network operations |
| `retry_interval_seconds` | `60` | Back off after a failed refresh |
| `max_stale_seconds` | `None` | Strict: propagate errors when no current catalog exists |
| `cache_path` | `None` | Optional atomic disk cache, reusable after restart |
| `url` | LiteLLM upstream | Override with a compatible HTTP(S) source |
| `client` | Managed internally | Optional caller-owned `httpx2.AsyncClient` |

## Refresh failures and stale data

To keep serving estimates during an outage, explicitly set, for example,
`max_stale_seconds=86400`. After a failed refresh this allows the last valid
snapshot up to 24 hours **since its successful fetch**, with a warning. The age
limit is checked on each call, including during retry backoff. Without a valid
snapshot, or beyond that limit, errors propagate. Invalid updates and disk-write
failures leave the previous catalog and cache intact; the bundled default is
never silently substituted. Inspect `prices.is_stale`, `prices.last_refreshed_at`
and `prices.last_error` for health reporting. `last_refreshed_at` is the UTC fetch
time, not a guarantee of when a provider made its prices effective.

## Forced updates and cancellation

`await prices.get_catalog(force_refresh=True)` bypasses freshness and retry
backoff. Network cancellation propagates; it does not become a stale fallback or
a failed-attempt backoff. Once an atomic cache write starts, cancellation waits
for that write to finish before releasing the update lock.
Use `async with` or `await prices.aclose()` to release the owned client. An
injected client remains open and must be closed by its caller.

## Snapshot history and disk cache

Each successful refresh replaces the manager's current snapshot. Already
returned catalogs and results retain their prices; results still carry the source
and catalog checksums. Store the amount and checksum with historical usage if
you need auditability. The latest map does not reconstruct historical tariffs.
Freshness is limited by when LiteLLM publishes a change plus the chosen interval.

The live cache is a versioned JSON envelope bound to the source URL and selection,
not a public `PricingCatalog.from_file()` artifact. Use a separate cache path for
each worker/selection. Locks and retry state are per instance; this is not a
distributed cache or cross-process download coordinator.

## Offline example

Run `python examples/live_catalog.py` for an offline demonstration using HTTPX2's
mock transport, including a price change, stable old snapshot and cached restart.
The generator's downloader also uses async HTTPX2. Its CLI starts an event loop
only at the command boundary; async applications should use the live manager or
await `tokenary.generator.downloader.fetch_model_prices_raw()` directly.
