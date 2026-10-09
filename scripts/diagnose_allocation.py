#!/usr/bin/env python
"""Why does the allocation not converge? Print, per iteration, each class's area against its demand.

    python scripts/diagnose_allocation.py --cellspace data/cellspace_bdc_5k.tif [--iterations 40]

Runs the same model and scenario as scripts/run_experiment.py (same demand, cell area, tolerance),
but stops after a few iterations of the first year and prints area, demand, gap and elasticity of
each class at selected iterations. A class whose gap does not shrink is the one the model cannot
move: usually a class whose potential is zero or negative nearly everywhere, or whose demand asks
for more area than its cells can take.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import tempfile
import time

try:
    from _common import LAND_USES, MODEL_TOML, SCENARIO_TOML, cell_area_km2, class_areas_km2, load_toml, read_bands
    from make_demand import demand_table, write_csv
except ImportError:  # pragma: no cover
    from scripts._common import LAND_USES, MODEL_TOML, SCENARIO_TOML, cell_area_km2, class_areas_km2, load_toml, read_bands
    from scripts.make_demand import demand_table, write_csv

STEP = 1  # first year traced; set by --step
SHOW = {0, 1, 2, 5, 10, 20, 40, 80, 120, 160, 240, 320, 480, 640, 800, 1000}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cellspace", required=True, type=pathlib.Path)
    ap.add_argument("--iterations", type=int, default=40, help="iterations of the failing year to run (default 40)")
    ap.add_argument("--step", type=int, default=1, help="year to trace (default 1, the first year with a change)")
    a = ap.parse_args()
    global STEP
    STEP = a.step

    bands, transform, _ = read_bands(a.cellspace)
    scenario = load_toml(SCENARIO_TOML)["scenario"]
    area = cell_area_km2(transform)
    rows = demand_table(class_areas_km2(bands, transform), {"scenario": scenario})
    tmp = pathlib.Path(tempfile.mkdtemp())
    write_csv(rows, tmp / "demand.csv")

    from disslucc.components.allocation import saturation as sat

    original = sat.AllocationClueLikeSaturation.compare_to_demand
    state = {"n": 0, "t0": time.perf_counter()}

    def traced(self, step):
        areas = self._areas()
        if step >= STEP and state["n"] in SHOW:
            print(f"\n--- step {step}, evaluation {state['n']} "
                  f"({time.perf_counter() - state['t0']:.0f} s since start; sum of gaps {sum(areas) - sum(self.demand.get_current_lu_demand(i) for i in range(len(areas))):+.0f} km2) ---")
            print(f"{'class':24s}{'area km2':>14s}{'demand km2':>14s}{'gap km2':>12s}{'elasticity':>12s}{'dir':>5s}")
            for i, lu in enumerate(self.land_use_types):
                d = self.demand.get_current_lu_demand(i)
                print(f"{lu:24s}{areas[i]:14.1f}{d:14.1f}{areas[i]-d:12.1f}{self.elasticity[i]:12.4f}"
                      f"{self.demand.get_current_lu_direction(i):5d}")
        if step >= STEP:
            state["n"] += 1
            if state["n"] > a.iterations:
                raise SystemExit("stopped after the requested iterations")
        return original(self, step)

    sat.AllocationClueLikeSaturation.compare_to_demand = traced

    sys.argv = [
        "saturation", "run", "--toml", str(MODEL_TOML), "--input", str(a.cellspace),
        "--param", f"demand_csv={tmp / 'demand.csv'}", "--param", f"cell_area={area}",
        "--param", f"n_steps={int(scenario['n_steps'])}",
        "--param", f"max_difference={scenario['max_difference_km2']}",
        "--output", str(tmp / "lucc.tif"),
    ]
    from disslucc.executors.saturation import LuccSaturationExecutor
    from dissmodel.executor.cli import run_cli

    run_cli(LuccSaturationExecutor)


if __name__ == "__main__":
    main()
