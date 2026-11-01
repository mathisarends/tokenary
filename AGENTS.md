# Working on tokenary

Tokenary is a Python 3.13+ library for LLM API cost estimates. Start with
[README.md](README.md) and use the [documentation index](docs/README.md) to read
only the relevant guide. Documentation is in English; `tickets/` records completed
reviews and historical evidence, not the current backlog.

## Repository map

| Path | Responsibility |
| --- | --- |
| `tokenary/tokenary.py`, `tokenary/views.py` | Synchronous calculation, requests and results |
| `tokenary/pricing.py`, `tokenary/usage.py` | Rate validation, context tiers and usage adapters |
| `tokenary/catalog.py` | Lazy offline catalogs, enum names and checksums |
| `tokenary/live.py` | Opt-in async refresh, cache and failure policy |
| `tokenary/generator/` | Raw-source download, selection, public outputs and private bundle |
| `data/model_prices.generated.json` | Pinned raw upstream snapshot |
| `tokenary/data/` | Generated index and compressed provider resources |
| `tests/`, `examples/`, `scripts/` | Offline tests, runnable workflows and installed-wheel checks |

## Contracts to preserve

- Keep calculation in `tokenary.calculate(..., catalog=...)`. Generated modules
  export `CATALOG` and `ModelName`; they do not duplicate runtime code.
- Input/output tokens are inclusive totals. Reasoning, audio and cache counts are
  subsets. Disjoint subsets must fit within their total.
- Nonzero usage without a supported rate raises `MissingPriceError`. An explicit
  zero rate is valid. Do not approximate unsupported billing categories.
- Context thresholds are strict (`input_tokens > threshold`) and use total input,
  including cache. Service-tier and endpoint fields remain data only.
- `calculate()` performs no network I/O. Live refresh is explicit and asynchronous.
  A failed refresh must not silently substitute bundled prices.
- Preserve enum aliases for retained IDs, lazy provider loading, per-model
  validation and source/catalog checksums.
- Do not hand-edit `tokenary/data/`. Follow
  [catalog regeneration](docs/development.md#rebuild-the-bundled-catalog) and update
  [snapshot provenance](data/README.md) with source refreshes.

## Verification and delivery

Run `uv sync --locked`, then the checks documented in
[development](docs/development.md#checks):

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build --wheel
```

After catalog or public API changes, also run the bundle drift check, all examples
and the [isolated wheel smoke test](docs/development.md#test-an-installed-wheel).
Use offline fixtures for tests and inspect resource reads when checking loading
behavior; `sys.modules` cannot show JSON reads. Report checks actually performed.

Use a `codex/` branch from current `origin/main` and preserve unrelated local
changes, using a separate worktree when needed. Keep a PR focused and do not merge
it unless the user requests a merge. Update the relevant guide when behavior changes.
