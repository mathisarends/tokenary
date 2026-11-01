[Documentation](README.md) · [Quick start](../README.md)

# Size and performance

The refreshed snapshot contains 4,552 models in 153 provider files and a
price-free index, totaling 328,661 compressed bytes with model metadata in this
build (282,935 bytes before metadata). A generated module for `gpt-4o` and `o1`
is 2,901 bytes. Compressed sizes vary with the
Python/zlib build; canonical checksums remain stable.
See [snapshot provenance](../data/README.md).

## Loading behavior

The runtime opens only the requested provider files and validates/caches
individual models. A generated subset reads no bundled provider prices.
Importing `ModelName` loads the name index and full enum, without provider prices.
Use string IDs or a generated subset enum to avoid constructing the full enum.

Every wheel still includes the bundled provider files for offline use. Generating
a subset reduces loading and generated code, not the installed bundle size.
Generation from a local source reads naming history without provider prices.

## Historical measurements

Historical v0.2.0 measurements, before the provider split, used isolated
wheel installs, seven fresh processes and 10,000 calls per process:

| Metric | Original 0.1.0 | 0.2 |
| --- | ---: | ---: |
| Import median | 137.6 ms | 101.8 ms |
| First calculation including total | 20.1 ms | 15.8 ms |
| Repeated keyword calculation including total | 3.2 us | 7.3 us |
| Repeated prevalidated request including total | 2.1 us | 4.9 us |

The added validation, category checks, context tiers and provenance have a cost
per call. Startup and installation size improve; steady-state billing does more
work. Use a generated subset to avoid bundled provider data,
and pass an adapter's validated request directly to `calculate`. These timings
are illustrative local measurements and vary by Python build and machine.

The provider-split comparison in [ticket 009](../tickets/009-lazy-bundled-catalog.md)
records historical medians, ranges, working-set deltas and exact wheel hashes.

## Repeating a benchmark

Run `scripts/benchmark_runtime.py --runs 7` against an isolated installed wheel
to repeat it. Each run starts a fresh process after one unmeasured bytecode warmup;
each process performs 10,000 calls per repeated-call measurement. Windows working
set or Linux resident pages are reported when available. Results are local
observations; the regression tests enforce resource-loading behavior without
absolute timing limits.
