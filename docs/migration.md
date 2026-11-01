[Documentation](README.md) · [Quick start](../README.md)

# Migration notes

## Inclusive token totals

Since 0.2, input and output counts are inclusive totals. Add previously separate
reasoning or audio counts to the corresponding total once, then keep passing
the subset fields for the breakdown:

```python
from tokenary import calculate

result = calculate(
    model="o1",
    input_tokens=100,
    output_tokens=162 + 1024,  # Ordinary output plus reasoning
    reasoning_tokens=1024,
)
```

Use [provider usage adapters](usage.md#provider-usage-adapters) when starting from
an API response. Do not add reasoning or audio again to a provider's already
inclusive total.

## Explicit generator output

`--output` is required for generation and `--check`. Scripts relying on the old
implicit `model_prices.py` destination must add `--output model_prices.py`.

## Generated catalogs and schemas

Generated Python modules export `CATALOG` and `ModelName`. Import `calculate` from
`tokenary` and pass `catalog=CATALOG`; generated modules do not export a calculator.
See [custom catalogs](catalogs.md).

The former `tokenary.generator.schemas.GeneratedModelPricing` API was removed.
Import `ModelPricing` from `tokenary.pricing` instead.

`from tokenary import ModelName` remains supported for names present in the bundled
snapshot. String IDs and generated subset enums also work with explicit catalogs
containing models newer than the installed package.
