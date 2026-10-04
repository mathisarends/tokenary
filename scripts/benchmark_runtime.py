"""Measure startup and calculation costs in fresh Python processes."""

import argparse
import json
import statistics
import subprocess
import sys

_PROBE = """
import json
import time
started = time.perf_counter()
import tokenary
import_ms = (time.perf_counter() - started) * 1000
started = time.perf_counter()
tokenary.calculate(model='gpt-4o', input_tokens=1000).total_cost
first_ms = (time.perf_counter() - started) * 1000
started = time.perf_counter()
for _ in range(10000):
    tokenary.calculate(model='gpt-4o', input_tokens=1000).total_cost
repeat_us = (time.perf_counter() - started) * 1000000 / 10000
request = tokenary.UsageCostRequest(model='gpt-4o', input_tokens=1000)
started = time.perf_counter()
for _ in range(10000):
    tokenary.calculate(request).total_cost
request_us = (time.perf_counter() - started) * 1000000 / 10000
print(json.dumps({
    'import_ms': import_ms,
    'first_calculate_ms': first_ms,
    'repeated_calculate_us': repeat_us,
    'request_calculate_us': request_us,
}))
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=7)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    samples = [
        json.loads(
            subprocess.check_output([sys.executable, "-I", "-c", _PROBE], text=True)
        )
        for _ in range(args.runs)
    ]
    print(
        json.dumps(
            {
                field: round(statistics.median(sample[field] for sample in samples), 3)
                for field in samples[0]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
