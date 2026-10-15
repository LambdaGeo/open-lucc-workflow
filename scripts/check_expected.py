#!/usr/bin/env python
"""Compare one run with the reported run of the same grid (the reviewer's quick check).

    python scripts/check_expected.py --label br_10km --run runs/br_10km --reported reported/v1.1.0

Reads runs/<label>/metrics.json and <reported>/metrics_<label>.json. Prints one of

    OK      identical:   same input raster and same output raster (SHA-256), same iterations
    OK      equivalent:  same input raster, output differs in bytes but every class area agrees within --rel-tol
                         and the iterations are the same (expected only across operating systems or libraries)
    DIFFERS              the input raster differs (the sources changed) or the output does not agree

Exit status 0 for the two OK cases, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def load(p: pathlib.Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def compare(run: dict, ref: dict, rel_tol: float) -> tuple[str, list[str]]:
    notes: list[str] = []
    if run["input_raster_sha256"] != ref["input_raster_sha256"]:
        notes.append(f"input raster differs: {run['input_raster_sha256'][:12]}... "
                     f"instead of {ref['input_raster_sha256'][:12]}... (the sources or DisSCube changed)")
        return "DIFFERS", notes
    same_iter = run["iterations_per_step"] == ref["iterations_per_step"]
    if run["output_sha256"] == ref["output_sha256"] and same_iter:
        return "identical", notes
    total = sum(ref["final_areas_km2"].values())
    worst = max(abs(run["final_areas_km2"][k] - ref["final_areas_km2"][k]) for k in ref["final_areas_km2"])
    notes.append(f"output bytes differ ({run['output_sha256'][:12]}... instead of {ref['output_sha256'][:12]}...); "
                 f"largest class-area difference {worst:.6g} km2 ({worst / total:.3g} of the mapped area)")
    if not same_iter:
        notes.append("the iterations per year differ from the reported run")
    if same_iter and worst / total <= rel_tol:
        return "equivalent", notes
    return "DIFFERS", notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True)
    ap.add_argument("--run", required=True, type=pathlib.Path)
    ap.add_argument("--reported", required=True, type=pathlib.Path)
    ap.add_argument("--rel-tol", type=float, default=1e-6)
    a = ap.parse_args()
    ref_file = a.reported / f"metrics_{a.label}.json"
    if not ref_file.exists():
        print(f"FAIL  no reported metrics at {ref_file}")
        return 1
    run, ref = load(a.run / "metrics.json"), load(ref_file)
    status, notes = compare(run, ref, a.rel_tol)
    versions = {p: (run["versions"].get(p), ref["versions"].get(p)) for p in ref.get("versions", {})}
    for p, (got, want) in versions.items():
        if got != want:
            notes.append(f"{p} {got} instead of the reported {want}")
    if status == "identical":
        print(f"OK  {a.label}: identical to the reported run (input and output SHA-256, iterations)")
    elif status == "equivalent":
        print(f"OK  {a.label}: numerically equivalent to the reported run (not byte for byte)")
    else:
        print(f"DIFFERS  {a.label}: does not reproduce the reported run")
    for n in notes:
        print("   ", n)
    return 0 if status in ("identical", "equivalent") else 1


if __name__ == "__main__":
    sys.exit(main())
