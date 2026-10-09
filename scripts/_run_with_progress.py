#!/usr/bin/env python
"""PROVISIONAL. The disslucc saturation executor, with one progress line per year. Used by scripts/run_experiment.py.

This file is a stop-gap and must be removed before the manuscript is submitted: the progress line belongs in disslucc
itself (a `logging` record per year with iterations, maximum error and time), after which scripts/run_experiment.py goes
back to running `python -m disslucc.executors.saturation` and only configures the log level. Until then it relies on an
internal name of disslucc 0.5.0 (`AllocationClueLikeSaturation.execute`) and will fail with an AttributeError, not
silently, if that name changes. See docs/VERSIONS.md ("Before submission").

    python scripts/_run_with_progress.py run --toml ... --input ... (the arguments of `disslucc.executors.saturation`)

It wraps the allocation of a year (`AllocationClueLikeSaturation.execute`) in memory: after each year it prints

    [progress] year 3 | 731 iterations | max error 999.3 km2 | 7.4 min (year) | 0.8 GB peak

and changes nothing else (no parameter, no result). disslucc and dissmodel are not modified.
"""
from __future__ import annotations

import platform
import resource
import sys
import time


def _peak_gb() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return (peak / (1024 * 1024) if platform.system() == "Darwin" else peak / 1024) / 1024


def main() -> None:
    from disslucc.components.allocation import saturation as sat
    from disslucc.executors.saturation import LuccSaturationExecutor
    from dissmodel.executor.cli import run_cli

    original = sat.AllocationClueLikeSaturation.execute
    t_start = time.perf_counter()

    def with_progress(self):
        t0 = time.perf_counter()
        original(self)
        year = int(self.env.now())
        if year >= 1 and self.iterations_per_step:
            print(f"[progress] year {year} | {self.iterations_per_step[-1]} iterations | "
                  f"max error {self.max_error_per_step[-1]:.1f} km2 | {(time.perf_counter() - t0) / 60:.1f} min (year) | "
                  f"{(time.perf_counter() - t_start) / 60:.1f} min total | {_peak_gb():.2f} GB peak", flush=True)

    sat.AllocationClueLikeSaturation.execute = with_progress
    sys.argv = ["saturation"] + sys.argv[1:]
    run_cli(LuccSaturationExecutor)


if __name__ == "__main__":
    main()
