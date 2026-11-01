"""Measure startup and calculation costs in fresh Python processes."""

import argparse
import json
import platform
import statistics
import subprocess
import sys

_PROBE = """
import json
import time
import sys
def resident_bytes():
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    'peak_working', 'working', 'peak_paged', 'paged',
                    'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile')]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),
                                         ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.working
    if sys.platform.startswith('linux'):
        import os
        with open('/proc/self/statm') as stream:
            return int(stream.read().split()[1]) * os.sysconf('SC_PAGE_SIZE')
    return None
before = resident_bytes()
started = time.perf_counter()
import tokenary
import_ms = (time.perf_counter() - started) * 1000
after_import = resident_bytes()
started = time.perf_counter()
tokenary.calculate(model='gpt-4o', input_tokens=1000).total_cost
first_ms = (time.perf_counter() - started) * 1000
after_first = resident_bytes()
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
    'import_rss_delta_bytes': None if before is None else after_import - before,
    'first_rss_delta_bytes': None if before is None else after_first - after_import,
}))
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=7)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    # Warm installed bytecode once; every measured sample still uses a fresh process.
    subprocess.check_output([sys.executable, "-I", "-c", _PROBE])
    samples = [
        json.loads(
            subprocess.check_output([sys.executable, "-I", "-c", _PROBE], text=True)
        )
        for _ in range(args.runs)
    ]
    print(
        json.dumps(
            {
                "environment": {
                    "python": sys.version,
                    "platform": platform.platform(),
                    "runs": args.runs,
                    "bytecode": "enabled; one unmeasured warmup process",
                    "calls_per_sample": 10000,
                    "rss": "working set on Windows; resident pages on Linux",
                },
                "metrics": {
                    field: {
                        "median": round(statistics.median(values), 3),
                        "min": round(min(values), 3),
                        "max": round(max(values), 3),
                    }
                    for field in samples[0]
                    if (values := [sample[field] for sample in samples])
                    and all(value is not None for value in values)
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
