# Documentation

Start with the [README quick start](../README.md#calculate-a-cost).
Choose one guide for the task at hand:

| Task | Read |
| --- | --- |
| Calculate costs and understand the breakdown | [Usage and billing reference](usage.md) |
| Normalize provider response usage | [Usage adapters](usage.md#provider-usage-adapters) |
| Generate a selected Python, JSON or gzip catalog | [Custom catalogs](catalogs.md) |
| Pin a source and detect generated-file drift | [Reproducible generation](catalogs.md#reproducible-generation-and-drift-checks) |
| Refresh prices asynchronously in an application | [Live pricing](live-pricing.md) |
| Set up a checkout, run checks or rebuild bundled prices | [Development](development.md) |
| Inspect the bundled source and refresh impact | [Snapshot provenance](../data/README.md) |
| Upgrade from the original API | [Migration notes](migration.md) |
| Understand resource loading and repeat benchmarks | [Size and performance](performance.md) |
| Change this repository as an agent | [AGENTS.md](../AGENTS.md) |

## Runnable examples

After [development setup](development.md#setup), run any example with
`uv run python examples/<name>.py` from the repository root.

| Example | Demonstrates |
| --- | --- |
| [basic_calculate.py](../examples/basic_calculate.py) | Bundled prices and a category breakdown |
| [request_object.py](../examples/request_object.py) | A validated `UsageCostRequest` |
| [multimodal_cost.py](../examples/multimodal_cost.py) | Inclusive output and a separate reasoning breakdown |
| [custom_catalog.py](../examples/custom_catalog.py) | Local generation, exact filters and explicit catalogs |
| [live_catalog.py](../examples/live_catalog.py) | Async refresh and disk-cache reuse with a mock transport |

All examples run offline. The [review tickets](../tickets/README.md) record
historical implementation work; the guides above describe the current API.
