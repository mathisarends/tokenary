# tokenary

Calculate LLM API cost estimates in USD from LiteLLM pricing data.
Use the bundled offline snapshot, generate a catalog for selected models, or
opt into asynchronous price updates. `calculate()` is synchronous and performs
no network I/O.

## Install

Requires Python 3.13 or newer.

```bash
pip install tokenary
```

## Calculate a cost

```python
from tokenary import calculate

result = calculate(model="gpt-4o", input_tokens=1000, output_tokens=500)
print(result.total_cost)
print(result.model_dump())  # Category breakdown and pricing checksums
```

No setup or generation is needed. The default uses prices shipped with the
installed version, opens requested providers and validates models on demand.

Input and output counts are **inclusive totals**: reasoning, audio and cache
counts are subsets. A requested category without a supported rate raises
`MissingPriceError`. See [usage and billing rules](docs/usage.md).

## Choose your pricing source

| Need | Use | Guide |
| --- | --- | --- |
| Start immediately, fully offline | `calculate(...)` with bundled prices | [Usage](docs/usage.md) |
| Pin prices or select specific models | Generate a catalog and pass `catalog=CATALOG` | [Custom catalogs](docs/catalogs.md) |
| Refresh prices in a running application | `await prices.get_catalog()` on a `LivePricingCatalog` | [Live pricing](docs/live-pricing.md) |

For example, generate a small Python catalog:

```bash
tokenary-generate --models gpt-4o o1 --output my_prices.py
```

```python
from tokenary import calculate
from my_prices import CATALOG, ModelName

result = calculate(
    model=ModelName.GPT_4O,
    input_tokens=1000,
    output_tokens=500,
    catalog=CATALOG,
)
```

Without `--input`, generation downloads the current
[LiteLLM catalog](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json)
once. It does not update the installed default. JSON and gzip catalogs are
supported too.

## Find the details

- [Documentation index](docs/README.md) — guides, reference and runnable examples.
- [Usage reference](docs/usage.md) — request fields, adapters, cache and context tiers.
- [Development](docs/development.md) — setup, checks and catalog regeneration.
- [Snapshot provenance](data/README.md) — bundled source, checksum and refresh summary.
- [Migration notes](docs/migration.md) and [performance](docs/performance.md).
- [Agent instructions](AGENTS.md) — repository map, invariants and verification.

Review history and completed implementation tickets live in [tickets/](tickets/README.md).
