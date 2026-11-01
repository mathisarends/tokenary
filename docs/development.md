[Documentation](README.md) · [Quick start](../README.md)

# Development

## Setup

Use Python 3.13 or 3.14 and run commands from the repository root:

```bash
uv sync --locked
```

The [agent instructions](../AGENTS.md) provide a short repository map and the
billing invariants to preserve.

## Checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build --wheel
```

Run the [examples](README.md#runnable-examples) after catalog or public API changes.
Tests and examples use offline fixtures. CI runs tests, lint, formatting, bundle
drift checks, examples, wheel construction and an isolated installed-wheel smoke
test on Python 3.13 and 3.14. Benchmarks are not timing gates.

Historical billing assertions use `tests/fixtures/billing_prices.json` so a
retired upstream model cannot erase a regression case. Bundle integration checks
still exercise the committed current snapshot and its checksums.

## Rebuild the bundled catalog

The raw LiteLLM snapshot is `data/model_prices.generated.json`; it is not included
in wheels. The private runtime resources are `tokenary/data/index.json.gz` and
`tokenary/data/providers/*.json.gz`. Regenerate them together from the pinned
snapshot, preserving the existing index so enum naming history is retained:

```bash
./scripts/generate_catalog.sh
./scripts/generate_catalog.sh --check
```

On Windows, run the equivalent command, then repeat it with `--check`:

```powershell
uv run python -m tokenary.generator.bundle --input data/model_prices.generated.json --source https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json --output-dir tokenary/data
```

`--check` never writes files and fails on drift or stale provider resources.
Canonical JSON comparison tolerates gzip differences across Python/zlib builds.
The private bundle replaces the former `tokenary/data/catalog.json.gz`; public
single-file JSON/gzip catalogs and generated Python modules retain their format.

## Update the upstream snapshot

1. Download the current raw source using the existing async downloader:

   ```bash
   uv run python -c "import asyncio; from tokenary.generator.downloader import fetch_model_prices_raw, write_raw_prices_file; write_raw_prices_file(asyncio.run(fetch_model_prices_raw()), 'data/model_prices.generated.json')"
   ```

2. Rebuild the bundle and run its drift check using the commands above. Keep
   unsupported rates as data; do not invent billing rules to make a refresh pass.
3. Review added/removed IDs, changes to supported price fields, provider grouping,
   checksums and enum-name compatibility. Removed upstream models also disappear
   from the new bundle; preserve an older explicit catalog for historical usage.
4. Update [snapshot provenance](../data/README.md), including the canonical source
   checksum from the generated index. Review any size figures in
   [performance](performance.md).
5. Run the checks, all examples and the isolated wheel smoke test. Commit the raw
   snapshot, generated resources and documentation together.

The raw snapshot and a generated public catalog have different formats.
Do not overwrite the raw snapshot with `tokenary-generate --all` output.
For application catalogs, follow [custom catalogs](catalogs.md) instead.

## Test an installed wheel

After `uv build --wheel`, run this from a directory outside the checkout,
substituting absolute paths (forward-slash Windows paths work too):

```bash
uv run --isolated --no-project --python 3.14 --with /absolute/path/to/tokenary/dist/tokenary-0.2.0-py3-none-any.whl python -I /absolute/path/to/tokenary/scripts/smoke_installed.py
```

The isolated environment contains only runtime dependencies, without Ruff or
provider SDKs. The offline smoke test exercises both CLI entry points, selection,
all three output formats, new IDs, excluded-model failures, read/validation
caches, live pricing, default compatibility and a runtime source-size budget.

## Benchmarks

```bash
uv run python scripts/benchmark_runtime.py --runs 7
```

See [performance](performance.md) for the methodology and historical results.
