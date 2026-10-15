#!/usr/bin/env python
"""Check the reported runs against acceptance.toml from their recorded metrics, without running the model.

    python scripts/check_reported.py --reported reported/v1.1.0

Uses metrics_br_5km.json, metrics_br_5km_repeat.json and metrics_br_10km.json of the folder. The demand and
resolution criteria are evaluated on the recorded numbers; the repeat is identical if the SHA-256 of its
input and output rasters equals that of the first run (identical bytes mean a difference of 0).
This audits the record; it does not show that the code reproduces it (see `make reproduce-10k`).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

try:
    from _common import ACCEPTANCE_TOML, load_toml
    from check_run import check_demand, check_resolution
except ImportError:  # pragma: no cover
    from scripts._common import ACCEPTANCE_TOML, load_toml
    from scripts.check_run import check_demand, check_resolution


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reported", required=True, type=pathlib.Path)
    ap.add_argument("--acceptance", type=pathlib.Path, default=ACCEPTANCE_TOML)
    a = ap.parse_args()
    try:
        fine, rep, coarse = (json.loads((a.reported / f"metrics_{n}.json").read_text(encoding="utf-8"))
                             for n in ("br_5km", "br_5km_repeat", "br_10km"))
    except FileNotFoundError as e:
        print("FAIL  missing reported file:", e.filename)
        return 1
    acc = load_toml(a.acceptance)
    same_in = fine["input_raster_sha256"] == rep["input_raster_sha256"]
    same_out = fine["output_sha256"] == rep["output_sha256"]
    results = {
        "demand_met (5.28 km)": check_demand(fine, acc),
        "demand_met (10.56 km)": check_demand(coarse, acc),
        "repeat_identical": {"ok": same_in and same_out, "same_input": same_in, "same_output": same_out},
        "area_vs_coarser": check_resolution(fine, coarse, acc),
    }
    for name, r in results.items():
        detail = {k: v for k, v in r.items() if k not in ("ok", "per_class", "iterations_per_step")}
        print(f"{'PASS' if r['ok'] else 'FAIL'}  {name:24s} {detail}")
    if not acc["meta"]["frozen"]:
        print("WARNING: acceptance.toml is not frozen")
    return 0 if all(r["ok"] for r in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
