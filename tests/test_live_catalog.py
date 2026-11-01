import asyncio
import json
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx2
import pytest

from tokenary import LivePricingCatalog, calculate
from tokenary._serialization import content_hash, write_atomic

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def clock(monkeypatch):
    current = [1000.0]
    monkeypatch.setattr("tokenary.live.time", lambda: current[0])
    monkeypatch.setattr("tokenary.live.monotonic", lambda: current[0])
    return current


def raw_prices(rate=0.25):
    return {
        "new-model": {
            "litellm_provider": "fixture",
            "input_cost_per_token": rate,
            "output_cost_per_token": rate * 2,
        },
        "other-model": {"litellm_provider": "other", "input_cost_per_token": 2},
    }


@dataclass
class Remote:
    prices: dict = field(default_factory=raw_prices)
    calls: int = 0
    error: Exception | None = None
    gate: asyncio.Event | None = None
    started: asyncio.Event = field(default_factory=asyncio.Event)
    client: httpx2.AsyncClient = field(init=False)

    async def handle(self, request):
        self.calls += 1
        self.started.set()
        await asyncio.sleep(0)
        if self.gate is not None:
            await self.gate.wait()
        if self.error is not None:
            raise self.error
        assert request.headers["User-Agent"] == "tokenary"
        assert request.extensions["timeout"]["read"] == 10
        return httpx2.Response(200, json=self.prices)


@pytest.fixture
async def remote():
    remote = Remote()
    async with httpx2.AsyncClient(
        transport=httpx2.MockTransport(remote.handle)
    ) as client:
        remote.client = client
        yield remote


def test_import_and_construction_keep_default_runtime_offline():
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
import tokenary
assert 'tokenary.live' not in sys.modules
assert 'httpx2' not in sys.modules
from tokenary import LivePricingCatalog
from tokenary.catalog import get_default_catalog
from unittest.mock import patch
with patch('httpx2.AsyncClient', side_effect=AssertionError):
    prices = LivePricingCatalog(models=['new-model'])
    assert prices.is_stale and prices.last_refreshed_at is None
    assert get_default_catalog.cache_info().currsize == 0
    tokenary.calculate(model='gpt-4o', input_tokens=1)
""",
        ],
        check=True,
    )


async def test_refresh_interval_preserves_previous_snapshots(remote, clock):
    async with LivePricingCatalog(
        models=["new-model"], refresh_interval_seconds=60, client=remote.client
    ) as live:
        old = await live.get_catalog()
        result = calculate(model="new-model", input_tokens=4, catalog=old)
        assert result.total_cost == 1
        assert set(old.models) == {"new-model"}
        assert live.last_refreshed_at == datetime.fromtimestamp(1000, UTC)
        assert not live.is_stale
        clock[0] += 59
        assert await live.get_catalog() is old
        assert remote.calls == 1
        remote.prices = raw_prices(0.5)
        clock[0] += 1
        assert live.is_stale
        new = await live.get_catalog()
        updated = calculate(model="new-model", input_tokens=4, catalog=new)
        assert updated.total_cost == 2
        assert updated.pricing_catalog_sha256 != result.pricing_catalog_sha256
        assert calculate(model="new-model", input_tokens=4, catalog=old).total_cost == 1
        assert result.total_cost == 1
        assert remote.calls == 2


async def test_provider_and_model_filters_and_forced_refresh(remote):
    async with LivePricingCatalog(
        providers=["fixture"], models=["new-model"], client=remote.client
    ) as live:
        first = await live.get_catalog()
        assert set(first.models) == {"new-model"}
        assert await live.get_catalog(force_refresh=True) is not first
        assert remote.calls == 2


async def test_stale_fallback_backoff_and_recovery(remote, clock):
    async with LivePricingCatalog(
        models=["new-model"],
        refresh_interval_seconds=10,
        max_stale_seconds=100,
        client=remote.client,
    ) as live:
        old = await live.get_catalog()
        clock[0] += 10
        remote.error = httpx2.ConnectError("offline")
        with pytest.warns(UserWarning, match="using the last valid snapshot"):
            assert await live.get_catalog() is old
        assert live.is_stale
        assert live.last_error is remote.error
        assert live.last_refreshed_at == datetime.fromtimestamp(1000, UTC)
        clock[0] += 59
        assert await live.get_catalog() is old
        assert remote.calls == 2
        remote.error = None
        remote.prices = raw_prices(0.5)
        clock[0] += 1
        assert await live.get_catalog() is not old
        assert live.last_error is None
        assert not live.is_stale


async def test_stale_age_limit_is_enforced_during_backoff(remote, clock):
    async with LivePricingCatalog(
        models=["new-model"],
        refresh_interval_seconds=10,
        max_stale_seconds=20,
        client=remote.client,
    ) as live:
        await live.get_catalog()
        clock[0] += 10
        remote.error = httpx2.ReadTimeout("offline")
        with pytest.warns(UserWarning):
            await live.get_catalog()
        clock[0] += 11
        with pytest.raises(httpx2.ReadTimeout):
            await live.get_catalog()
        assert remote.calls == 2


@pytest.mark.parametrize("max_stale", [None, 86400])
async def test_initial_failure_raises_and_is_throttled(remote, max_stale):
    remote.error = httpx2.ConnectError("offline")
    async with LivePricingCatalog(
        models=["new-model"], max_stale_seconds=max_stale, client=remote.client
    ) as live:
        for _ in range(2):
            with pytest.raises(httpx2.ConnectError):
                await live.get_catalog()
        assert remote.calls == 1
        assert live.is_stale
        remote.error = None
        assert (await live.get_catalog(force_refresh=True)).models["new-model"]
        assert remote.calls == 2


async def test_default_strict_mode_rejects_expired_prices(remote, clock):
    async with LivePricingCatalog(
        models=["new-model"], refresh_interval_seconds=10, client=remote.client
    ) as live:
        await live.get_catalog()
        clock[0] += 10
        remote.error = httpx2.ConnectError("offline")
        for _ in range(2):
            with pytest.raises(httpx2.ConnectError):
                await live.get_catalog()
        assert remote.calls == 2


async def test_restart_retains_original_fetch_time(tmp_path, remote, clock):
    config = dict(
        models=["new-model"],
        cache_path=tmp_path / "cache.json",
        client=remote.client,
        max_stale_seconds=86400,
    )
    async with LivePricingCatalog(**config) as first:
        original = await first.get_catalog()
    clock[0] += 3599
    async with LivePricingCatalog(**config) as restarted:
        cached = await restarted.get_catalog()
        assert cached.metadata == original.metadata
        assert restarted.last_refreshed_at == first.last_refreshed_at
        assert remote.calls == 1
        clock[0] += 1
        remote.error = httpx2.ConnectError("offline")
        with pytest.warns(UserWarning, match="last valid snapshot"):
            assert await restarted.get_catalog() is cached
        assert restarted.is_stale
        assert remote.calls == 2


@pytest.mark.parametrize("bad_update", ["negative", "missing", "write-failure"])
async def test_failed_update_preserves_disk_and_memory(
    tmp_path, monkeypatch, remote, clock, bad_update
):
    cache = tmp_path / "cache.json"
    async with LivePricingCatalog(
        models=["new-model"],
        cache_path=cache,
        max_stale_seconds=86400,
        client=remote.client,
    ) as live:
        old = await live.get_catalog()
        before = cache.read_bytes()
        if bad_update == "negative":
            remote.prices = raw_prices(-1)
        elif bad_update == "missing":
            remote.prices = {}
        else:

            def fail(*args):
                raise PermissionError("read-only cache")

            monkeypatch.setattr("tokenary._serialization.os.replace", fail)
        with pytest.warns(UserWarning, match="last valid snapshot"):
            assert await live.get_catalog(force_refresh=True) is old
        assert cache.read_bytes() == before
        assert list(tmp_path.iterdir()) == [cache]
        assert live.last_refreshed_at == datetime.fromtimestamp(1000, UTC)


@pytest.mark.parametrize(
    "corruption", ["json", "checksum", "selection", "source", "future", "invalid-rate"]
)
async def test_bad_or_unrelated_cache_is_ignored(tmp_path, remote, clock, corruption):
    cache = tmp_path / "cache.json"
    config = dict(models=["new-model"], cache_path=cache, client=remote.client)
    async with LivePricingCatalog(**config) as live:
        await live.get_catalog()
    cached = json.loads(cache.read_bytes())
    if corruption == "checksum":
        cached["catalog"]["models"]["new-model"]["input_cost_per_token"] = 99
    elif corruption == "selection":
        cached["models"] = ["other-model"]
    elif corruption == "source":
        cached["url"] = "https://example.test/other.json"
    elif corruption == "future":
        cached["fetched_at"] = clock[0] + 1
    elif corruption == "invalid-rate":
        cached["catalog"]["models"]["new-model"]["input_cost_per_token"] = -1
        cached["catalog"]["metadata"]["catalog_sha256"] = content_hash(
            {k: cached["catalog"][k] for k in ("models", "enum_names")}
        )
    cache.write_text("broken" if corruption == "json" else json.dumps(cached))
    remote.prices = raw_prices(0.5)
    async with LivePricingCatalog(**config) as restarted:
        with pytest.warns(UserWarning, match="Ignoring unusable pricing cache"):
            catalog = await restarted.get_catalog()
        assert (
            calculate(model="new-model", input_tokens=4, catalog=catalog).total_cost
            == 2
        )
        assert remote.calls == 2


@pytest.mark.parametrize(
    "kwargs",
    [
        {"refresh_interval_seconds": 0},
        {"refresh_interval_seconds": float("nan")},
        {"retry_interval_seconds": float("inf")},
        {"timeout_seconds": -1},
        {"timeout_seconds": True},
        {"max_stale_seconds": -1},
        {"models": "new-model"},
        {"models": []},
        {"providers": [None]},
        {"url": "file:///prices.json"},
    ],
)
def test_invalid_configuration_fails_before_io(kwargs):
    with pytest.raises(ValueError):
        LivePricingCatalog(**kwargs)


@pytest.mark.parametrize("force", [True, False])
async def test_concurrent_callers_share_one_attempt(remote, force):
    async with LivePricingCatalog(models=["new-model"], client=remote.client) as live:
        catalogs = await asyncio.gather(
            *(live.get_catalog(force_refresh=force) for _ in range(20))
        )
        assert all(catalog is catalogs[0] for catalog in catalogs)
        assert remote.calls == 1


async def test_network_wait_does_not_block_event_loop_and_cancellation_propagates(
    remote,
):
    async with LivePricingCatalog(models=["new-model"], client=remote.client) as live:
        old = await live.get_catalog()
        remote.gate = asyncio.Event()
        remote.started.clear()
        task = asyncio.create_task(live.get_catalog(force_refresh=True))
        await asyncio.wait_for(remote.started.wait(), timeout=5)
        heartbeat = asyncio.Event()
        asyncio.get_running_loop().call_soon(heartbeat.set)
        await asyncio.wait_for(heartbeat.wait(), timeout=5)
        assert not task.done()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert live.last_error is None
        assert await live.get_catalog() is old
        remote.gate.set()
        await live.get_catalog(force_refresh=True)


async def test_disk_cache_and_validation_run_outside_event_loop(
    tmp_path, monkeypatch, remote
):
    main_thread = threading.get_ident()
    cache = tmp_path / "cache.json"
    build = LivePricingCatalog._build_snapshot
    load = LivePricingCatalog._load_cache
    observed = set()

    def observed_build(self, raw):
        assert threading.get_ident() != main_thread
        observed.add("build")
        return build(self, raw)

    def observed_load(self, path):
        assert threading.get_ident() != main_thread
        observed.add("load")
        return load(self, path)

    def observed_save(path, content):
        assert threading.get_ident() != main_thread
        observed.add("save")
        return write_atomic(path, content)

    monkeypatch.setattr(LivePricingCatalog, "_build_snapshot", observed_build)
    monkeypatch.setattr(LivePricingCatalog, "_load_cache", observed_load)
    monkeypatch.setattr("tokenary.live.write_atomic", observed_save)
    for _ in range(2):
        async with LivePricingCatalog(
            models=["new-model"], cache_path=cache, client=remote.client
        ) as live:
            await live.get_catalog()
    assert observed == {"build", "load", "save"}
    assert remote.calls == 1


async def test_client_ownership_and_closed_manager(monkeypatch, remote):
    owned = remote.client
    monkeypatch.setattr("tokenary.live.httpx2.AsyncClient", lambda: owned)
    async with LivePricingCatalog(models=["new-model"]) as live:
        await live.get_catalog()
    assert owned.is_closed
    await live.aclose()
    with pytest.raises(RuntimeError, match="closed"):
        await live.get_catalog()


async def test_injected_client_is_not_closed(remote):
    async with LivePricingCatalog(client=remote.client) as live:
        await live.get_catalog()
    assert not remote.client.is_closed


async def test_owned_client_with_real_local_http(tmp_path, monkeypatch):
    source = raw_prices()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            data = json.dumps(source).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        async with LivePricingCatalog(
            models=["new-model"],
            url=f"http://127.0.0.1:{server.server_port}/prices.json",
            cache_path=tmp_path / "live.json",
        ) as prices:
            old = await prices.get_catalog()
            source["new-model"]["input_cost_per_token"] = 0.5
            current = await prices.get_catalog(force_refresh=True)
            assert (
                calculate(model="new-model", input_tokens=4, catalog=old).total_cost
                == 1
            )
            result = calculate(model="new-model", input_tokens=4, catalog=current)
            assert result.total_cost == 2
            assert prices.last_error is None
        assert prices._client.is_closed
    finally:
        await asyncio.to_thread(server.shutdown)
        server.server_close()
        worker.join(timeout=5)


async def test_concurrent_failure_does_not_repeat_download(remote):
    remote.error = httpx2.ConnectError("offline")
    async with LivePricingCatalog(client=remote.client) as live:
        results = await asyncio.gather(
            *(live.get_catalog() for _ in range(20)), return_exceptions=True
        )
        assert all(isinstance(error, httpx2.ConnectError) for error in results)
        assert remote.calls == 1


async def test_cancelled_cache_writer_finishes_before_next_refresh(
    tmp_path, monkeypatch, remote
):
    cache = tmp_path / "cache.json"
    started = threading.Event()
    release = threading.Event()

    def delayed_write(path, content):
        started.set()
        assert release.wait(timeout=5)
        return write_atomic(path, content)

    async with LivePricingCatalog(
        models=["new-model"], cache_path=cache, client=remote.client
    ) as live:
        await live.get_catalog()
        monkeypatch.setattr("tokenary.live.write_atomic", delayed_write)
        remote.prices = raw_prices(0.5)
        cancelled = asyncio.create_task(live.get_catalog(force_refresh=True))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            cancelled.cancel()
            remote.prices = raw_prices(0.75)
            next_refresh = asyncio.create_task(live.get_catalog(force_refresh=True))
            await asyncio.sleep(0)
            assert not next_refresh.done()
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await cancelled
        latest = await next_refresh
        assert latest.models["new-model"].input_cost_per_token == 0.75
        assert (
            json.loads(cache.read_bytes())["catalog"]["metadata"]["catalog_sha256"]
            == latest.metadata.catalog_sha256
        )
