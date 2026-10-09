#!/usr/bin/env python
"""Acceptance checks of acceptance.toml on one run (and, optionally, its repeat and a coarser run).

    python scripts/check_run.py --run runs/bdc_5k --repeat runs/bdc_5k_repeat --coarse runs/bdc_10k
Exit status 1 if a check fails. Writes <run>/checks.json.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

try:
    from _common import ACCEPTANCE_TOML, LAND_USES, load_toml, read_bands, write_json
except ImportError:  # pragma: no cover
    from scripts._common import ACCEPTANCE_TOML, LAND_USES, load_toml, read_bands, write_json


def _metrics(run: pathlib.Path) -> dict:
    return json.loads((run / "metrics.json").read_text(encoding="utf-8"))


def check_demand(m: dict, acc: dict) -> dict:
    tol = acc["demand"]["max_abs_error_km2"]
    errs = m["max_error_per_step"]
    final = {lu: abs(m["final_areas_km2"][lu] - m["demand_last_year_km2"][lu]) for lu in LAND_USES}
    worst_final = max(final.values())
    iters = m["iterations_per_step"]
    ok_iter = max(iters) < acc["demand"]["max_iterations_per_step"]
    ok = max(errs) <= tol and worst_final <= tol and ok_iter
    return {"ok": ok, "max_error_km2": max(errs), "worst_final_class_error_km2": worst_final,
            "tolerance_km2": tol, "max_iterations": max(iters), "iterations_per_step": iters}


def check_determinism(m: dict, r: dict, acc: dict) -> dict:
    a, _, _ = read_bands(m["output"])
    b, _, _ = read_bands(r["output"])
    diffs = [float(np.nanmax(np.abs(a[k] - b[k]))) for k in a if k in b and k != "mask"]
    worst = max(diffs) if diffs else float("nan")
    return {"ok": worst <= acc["determinism"]["max_abs_diff"], "max_abs_diff": worst,
            "bytes_identical": m["output_sha256"] == r["output_sha256"],
            "tolerance": acc["determinism"]["max_abs_diff"]}


def check_resolution(m: dict, c: dict, acc: dict) -> dict:
    total = sum(m["final_areas_km2"].values())
    diffs = {lu: abs(m["final_areas_km2"][lu] - c["final_areas_km2"][lu]) / total for lu in LAND_USES}
    worst = max(diffs.values())
    return {"ok": worst <= acc["resolution"]["max_class_area_diff_fraction"],
            "max_class_area_diff_fraction": worst, "per_class": diffs,
            "tolerance": acc["resolution"]["max_class_area_diff_fraction"]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, type=pathlib.Path)
    ap.add_argument("--repeat", type=pathlib.Path)
    ap.add_argument("--coarse", type=pathlib.Path, help="run of a coarser grid of the same area")
    ap.add_argument("--acceptance", type=pathlib.Path, default=ACCEPTANCE_TOML)
    ap.add_argument("--require-frozen", action="store_true")
    a = ap.parse_args()

    acc = load_toml(a.acceptance)
    if not acc["meta"]["frozen"]:
        msg = "acceptance.toml is not frozen (meta.frozen = false): these results are provisional"
        if a.require_frozen:
            print("FAIL", msg)
            return 1
        print("WARNING:", msg)

    m = _metrics(a.run)
    results = {"demand_met": check_demand(m, acc)}
    if a.repeat:
        results["repeat_identical"] = check_determinism(m, _metrics(a.repeat), acc)
    if a.coarse:
        results["area_vs_coarser"] = check_resolution(m, _metrics(a.coarse), acc)

    for name, r in results.items():
        detail = {k: v for k, v in r.items() if k not in ("ok", "per_class", "iterations_per_step")}
        print(f"{'PASS' if r['ok'] else 'FAIL'}  {name:18s} {detail}")
    results["all_ok"] = all(r["ok"] for r in results.values())
    results["acceptance_frozen"] = bool(acc["meta"]["frozen"])
    write_json(a.run / "checks.json", results)
    return 0 if results["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
