"""Explicit, asynchronous price refreshes for synchronous calculations."""

import asyncio
import warnings
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic, time
from types import TracebackType
from typing import Literal, Self

import httpx2
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, JsonValue

from ._serialization import write_atomic
from .catalog import PricingCatalog
from .generator.downloader import _DEFAULT_PRICE_URL, fetch_model_prices_raw
from .generator.generator import build_catalog_payload

type RefreshError = httpx2.HTTPError | OSError | ValueError


class _Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    models: tuple[str, ...] | None
    providers: tuple[str, ...] | None
    url: HttpUrl
    cache_path: Path | None
    refresh_interval_seconds: float = Field(gt=0, allow_inf_nan=False)
    retry_interval_seconds: float = Field(gt=0, allow_inf_nan=False)
    timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    max_stale_seconds: float | None = Field(ge=0, allow_inf_nan=False)


class _CacheEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    cache_format_version: Literal[1] = 1
    url: str
    models: tuple[str, ...] | None
    providers: tuple[str, ...] | None
    fetched_at: float = Field(ge=0, allow_inf_nan=False)
    catalog: dict[str, JsonValue]


def _selection(values: Iterable[str] | None, name: str) -> tuple[str, ...] | None:
    if values is None:
        return None
    if isinstance(values, str):
        raise ValueError(f"{name} must be a collection of exact names")
    selected = tuple(values)
    if not selected or any(not isinstance(v, str) or not v for v in selected):
        raise ValueError(f"{name} must contain at least one nonempty name")
    return tuple(sorted(set(selected)))


class LivePricingCatalog:
    """Keep a selected catalog current, using one instance per application loop.

    Construction performs no I/O. Use as an async context manager and await
    get_catalog() per request, or once per batch. Refreshes are demand-driven;
    there is no background worker. Returned snapshots retain their prices.
    An injected AsyncClient belongs to its caller and is never closed here.
    """

    def __init__(
        self,
        *,
        models: Iterable[str] | None = None,
        providers: Iterable[str] | None = None,
        refresh_interval_seconds: float = 3600,
        retry_interval_seconds: float = 60,
        timeout_seconds: float = 10,
        max_stale_seconds: float | None = None,
        cache_path: str | Path | None = None,
        url: str = _DEFAULT_PRICE_URL,
        client: httpx2.AsyncClient | None = None,
    ) -> None:
        self._settings = _Settings(
            models=_selection(models, "models"),
            providers=_selection(providers, "providers"),
            url=HttpUrl(url),
            cache_path=Path(cache_path) if cache_path is not None else None,
            refresh_interval_seconds=refresh_interval_seconds,
            retry_interval_seconds=retry_interval_seconds,
            timeout_seconds=timeout_seconds,
            max_stale_seconds=max_stale_seconds,
        )
        self._client = client
        self._owns_client = client is None
        self._lock = asyncio.Lock()
        self._closed = False
        self._catalog: PricingCatalog | None = None
        self._refreshed_at: float | None = None
        self._last_error: RefreshError | None = None
        self._retry_at = 0.0
        self._cache_checked = False
        self._attempt = 0

    async def __aenter__(self) -> Self:
        if self._closed:
            raise RuntimeError("Live pricing manager is closed")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the owned HTTP client; an injected client remains open."""
        async with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._owns_client and self._client is not None:
                await self._client.aclose()

    @property
    def last_refreshed_at(self) -> datetime | None:
        """UTC fetch time, not the provider's price-effective time."""
        if self._refreshed_at is None:
            return None
        return datetime.fromtimestamp(self._refreshed_at, UTC)

    @property
    def last_error(self) -> RefreshError | None:
        """Last refresh failure, cleared by a successful refresh."""
        return self._last_error

    @property
    def is_stale(self) -> bool:
        if self._refreshed_at is None:
            return True
        age = time() - self._refreshed_at
        return age < 0 or age >= self._settings.refresh_interval_seconds

    def _stale_allowed(self) -> bool:
        limit = self._settings.max_stale_seconds
        return (
            self._catalog is not None
            and self._refreshed_at is not None
            and limit is not None
            and 0 <= time() - self._refreshed_at <= limit
        )

    def _load_cache(self, path: Path) -> tuple[PricingCatalog, float]:
        cached = _CacheEntry.model_validate_json(path.read_bytes())
        settings = self._settings
        if (
            cached.url != str(settings.url)
            or cached.models != settings.models
            or cached.providers != settings.providers
            or cached.fetched_at > time()
        ):
            raise ValueError("Pricing cache source, selection or fetch time is invalid")
        catalog = PricingCatalog.from_dict(cached.catalog)
        if catalog.metadata is None or catalog.metadata.source != cached.url:
            raise ValueError("Pricing cache catalog source does not match")
        # A fallback must be usable as well as checksum-correct.
        for model in catalog.models:
            catalog.models[model]
        return catalog, cached.fetched_at

    def _build_snapshot(
        self, raw: dict[str, JsonValue]
    ) -> tuple[PricingCatalog, _CacheEntry]:
        settings = self._settings
        payload = build_catalog_payload(
            raw,
            models=settings.models,
            providers=settings.providers,
            source=str(settings.url),
            previous_names=(
                self._catalog.enum_names if self._catalog is not None else None
            ),
        )
        catalog = PricingCatalog.from_dict(payload)
        entry = _CacheEntry.model_validate(
            {
                "url": str(settings.url),
                "models": settings.models,
                "providers": settings.providers,
                "fetched_at": time(),
                "catalog": payload,
            }
        )
        return catalog, entry

    async def _save_cache(self, path: Path, entry: _CacheEntry) -> None:
        def save() -> None:
            write_atomic(path, entry.model_dump_json().encode())

        task = asyncio.create_task(asyncio.to_thread(save))
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            # Finish replacement before releasing the refresh lock. A cancelled
            # writer must not overwrite a newer refresh from another caller.
            try:
                await task
            except OSError:
                pass
            raise

    async def get_catalog(self, *, force_refresh: bool = False) -> PricingCatalog:
        """Get a stable snapshot; refresh asynchronously when its interval expires.

        Default failures propagate. max_stale_seconds explicitly permits a last
        valid snapshot up to that age since fetch, with a warning on failure.
        Retry backoff applies to initial and subsequent failures. force_refresh
        bypasses freshness and backoff; concurrent callers share one attempt.
        Network cancellation propagates without becoming a refresh failure.
        """
        attempt = self._attempt
        async with self._lock:
            if self._closed:
                raise RuntimeError("Live pricing manager is closed")
            if attempt != self._attempt:
                force_refresh = False
            path = self._settings.cache_path
            if not self._cache_checked:
                if path is not None:
                    try:
                        self._catalog, self._refreshed_at = await asyncio.to_thread(
                            self._load_cache, path
                        )
                    except FileNotFoundError:
                        pass
                    except (OSError, ValueError, TypeError) as exc:
                        warnings.warn(
                            f"Ignoring unusable pricing cache: {exc}", stacklevel=2
                        )
                self._cache_checked = True
            if not force_refresh:
                if self._catalog is not None and not self.is_stale:
                    return self._catalog
                if self._last_error is not None and monotonic() < self._retry_at:
                    if self._stale_allowed():
                        assert self._catalog is not None
                        return self._catalog
                    raise self._last_error

            try:
                if self._client is None:
                    self._client = await asyncio.to_thread(httpx2.AsyncClient)
                raw = await fetch_model_prices_raw(
                    url=str(self._settings.url),
                    timeout_seconds=self._settings.timeout_seconds,
                    client=self._client,
                )
                catalog, entry = await asyncio.to_thread(self._build_snapshot, raw)
                if path is not None:
                    await self._save_cache(path, entry)
            except (httpx2.HTTPError, OSError, ValueError) as exc:
                self._attempt += 1
                self._last_error = exc
                self._retry_at = monotonic() + self._settings.retry_interval_seconds
                if not self._stale_allowed():
                    raise
                warnings.warn(
                    f"Pricing refresh failed; using the last valid snapshot: {exc}",
                    stacklevel=2,
                )
                assert self._catalog is not None
                return self._catalog

            self._attempt += 1
            self._catalog = catalog
            self._refreshed_at = entry.fetched_at
            self._last_error = None
            self._retry_at = 0.0
            return catalog
