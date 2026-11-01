# Bundled pricing snapshot

`model_prices.generated.json` is the raw LiteLLM source snapshot. The generator
derives the compressed runtime bundle in `tokenary/data/` from this file.
Neither calculations nor test runs download a replacement automatically.

| Property | Snapshot refreshed on 2026-11-01 |
| --- | --- |
| Source | [LiteLLM model price map](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json) |
| Models | 4,552 (excluding `sample_spec`) |
| Provider resources | 153, plus the price-free index |
| Canonical source SHA-256 | `db1c09c9ee8993e3bcbea6f62f41b0414390cef2493205d9d376e5e9159bb3ae` |
| Selected bundle SHA-256 | `34c2f9a3be61cccfa7fa9308d5ebd76b4002a1a974856d1c6a12e669864a4244` |

The source checksum hashes canonical parsed JSON, not raw file bytes. The bundle
checksum covers selected prices, model metadata and enum names. Both are recorded in
`tokenary/data/index.json.gz`; results expose the pricing checksums too.
The refresh date records retrieval, not when provider tariffs took effect.

## Refresh impact

Compared with the snapshot on `main` at `5c1a18d`:

- 2,973 → 4,552 models; 1,950 added and 371 removed upstream IDs.
- 768 retained models changed provider, mode or price fields. Other changes to
  upstream capability/context metadata were initially kept in the raw source only;
  the metadata rebuild described below includes them in the runtime bundle.
- 123 → 153 provider resources. Existing enum aliases are unchanged for every
  retained model.
- New `_ultrafast` service-tier and `_decisions` endpoint prices are retained as
  data, including context-qualified fields. Standard calculations do not select
  these rates. See [billing limits](../docs/usage.md#cache-and-context-tiers) and
  LiteLLM's [Ultrafast context-price change](https://github.com/BerriAI/litellm/pull/43764).

Removed IDs raise `KeyError` with the new bundle. Use a pinned explicit catalog
when replaying historical usage that requires an older model or tariff.

## Model metadata rebuild

The bundle now also retains model limits, capabilities, modalities, caching
requirements, reasoning settings, endpoints, regions and deprecation dates.
It was rebuilt from the same pinned source without downloading a new snapshot.
The source checksum, model IDs, enum aliases and price fields are unchanged;
the selected bundle checksum changed because it also covers retained metadata.
See [model metadata](../docs/model-metadata.md) for coverage and semantics.

## Regeneration

Follow [development: catalog regeneration](../docs/development.md#rebuild-the-bundled-catalog)
to rebuild offline or deliberately refresh the source. Commit the snapshot,
provider files and index together; never edit the compressed files by hand.
