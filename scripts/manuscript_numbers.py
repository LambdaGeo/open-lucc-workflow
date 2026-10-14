#!/usr/bin/env python
"""Numbers quoted in the manuscript, computed from one run (nothing is fitted or edited).

    python scripts/manuscript_numbers.py --label br_10km

Reads runs/<label>/metrics.json, the input raster and the output raster of the run, and writes
results/manuscript_numbers_<label>.md and .json with:

* the run (cells, iterations per year, largest error per year, time, memory, versions, hashes);
* the allocated area against the demand of the last year (Table S2 of the Supplementary Material);
* the forest loss, and the share of it that falls in cells more than half protected;
* forest gain per cell (to tell numerical noise from real gain);
* the declared weights and the coefficients derived from the input raster (model/parameters_derivation.json).

The output raster is found by name in runs/<label>/, so a run made on another machine can be read.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import rasterio

try:
    from _common import LAND_USES, ROOT, sha256_file
except ImportError:  # pragma: no cover
    from scripts._common import LAND_USES, ROOT, sha256_file

PROTECTED_SHARE = 0.5          # "more than half protected"
GAIN_THRESHOLDS = (1e-9, 1e-6, 1e-4, 1e-3, 1e-2)


def read(path: pathlib.Path):
    """Bands as float arrays and their names (tag `name`, else the band description, as in scripts/_common.py)."""
    with rasterio.open(path) as s:
        names = [s.tags(i).get("name") or s.descriptions[i - 1] or f"band{i}" for i in range(1, s.count + 1)]
        return s.read().astype(float), names


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="br_10km")
    ap.add_argument("--runs", type=pathlib.Path, default=ROOT / "runs")
    ap.add_argument("--input", type=pathlib.Path, default=None, help="input raster (default: data/<label>.tif)")
    ap.add_argument("--outdir", type=pathlib.Path, default=ROOT / "results")
    a = ap.parse_args()

    rd = a.runs / a.label
    m = json.loads((rd / "metrics.json").read_text(encoding="utf-8"))
    out_tif = rd / pathlib.Path(m["output"]).name
    in_tif = a.input or ROOT / "data" / f"{a.label}.tif"
    if sha256_file(in_tif) != m["input_raster_sha256"]:
        raise SystemExit(f"{in_tif} is not the input raster of this run (SHA-256 differs from metrics.json)")
    if sha256_file(out_tif) != m["output_sha256"]:
        raise SystemExit(f"{out_tif} does not match output_sha256 of metrics.json")

    cs, names = read(in_tif)
    lu, _ = read(out_tif)
    mask = cs[names.index("mask")] == 1
    cell = float(m["cell_area_km2"])

    # allocated area against demand, last year
    demand, final = m["demand_last_year_km2"], m["final_areas_km2"]
    table_s2 = [(c, demand[c], final[c], final[c] - demand[c]) for c in LAND_USES]

    # forest change per cell
    f0, f1 = cs[names.index("forest_vegetation")], lu[LAND_USES.index("forest_vegetation")]
    d = np.where(mask, f1 - f0, 0.0)
    loss_cell = np.where(d < 0, -d, 0.0)
    gross_loss, gain = loss_cell.sum() * cell, d[d > 0].sum() * cell
    init_area = f0[mask].sum() * cell
    prot = (cs[names.index("c_ucspas")] > PROTECTED_SHARE) & mask
    share_cells = 100 * prot.sum() / mask.sum()
    share_loss = 100 * loss_cell[prot].sum() / loss_cell[mask].sum()
    gains = {f"{t:g}": int((d > t).sum()) for t in GAIN_THRESHOLDS}

    it = m["iterations_per_step"][1:]            # step 0 is the initial state
    err = m["max_error_per_step"][1:]
    res = {
        "label": a.label, "cells": m["cells_in_mask"], "years": m["n_steps"],
        "iterations_min": min(it), "iterations_max": max(it),
        "max_error_min_km2": min(err), "max_error_max_km2": max(err),
        "tolerance_km2": m["max_difference_km2"],
        "run_seconds": m["run_seconds"], "wall_seconds": m["wall_seconds"], "peak_rss_mb": m["peak_rss_mb"],
        "versions": m["versions"], "python": m["python"],
        "input_raster_sha256": m["input_raster_sha256"], "output_sha256": m["output_sha256"],
        "table_s2": table_s2,
        "forest_initial_km2": init_area, "forest_gross_loss_km2": gross_loss,
        "forest_loss_pct_of_initial": 100 * gross_loss / init_area, "forest_gain_km2": gain,
        "cells_over_half_protected_pct": share_cells, "forest_loss_in_them_pct": share_loss,
        "forest_gain_cells_over": gains, "forest_gain_max_share_of_cell": max(float(d.max()), 0.0),
    }
    deriv = ROOT / "model" / "parameters_derivation.json"
    drivers = json.loads(deriv.read_text(encoding="utf-8")).get("classes", {}) if deriv.exists() else {}

    L = [f"# Numbers for the manuscript: {a.label}", "",
         f"Input raster SHA-256 `{m['input_raster_sha256']}`", f"Output raster SHA-256 `{m['output_sha256']}`",
         f"disscube {m['versions'].get('disscube')}, disslucc {m['versions'].get('disslucc')}, "
         f"dissmodel {m['versions'].get('dissmodel')}, Python {m['python']}", "",
         "## Run (Table 4)", "",
         f"- Cells {m['cells_in_mask']:,}; {m['n_steps']} years ({m['n_steps'] - 1} allocations)",
         f"- Iterations per year: {min(it):,} to {max(it):,}",
         f"- Largest error per year: {min(err):.1f} to {max(err):.1f} km2 (criterion {m['max_difference_km2']:,.0f})",
         f"- Time {m['run_seconds'] / 60:.1f} min; peak memory {m['peak_rss_mb'] / 1000:.2f} GB", "",
         "## Allocated area against demand, last year (Table S2)", "",
         "| Class | Demand (km2) | Allocated (km2) | Difference (km2) |", "|---|---:|---:|---:|"]
    L += [f"| {c} | {dm:,.1f} | {al:,.1f} | {df:+,.1f} |" for c, dm, al, df in table_s2]
    big = max(table_s2, key=lambda r: abs(r[3]))
    L += ["", f"Largest difference: {big[0]} {big[3]:+,.1f} km2 ({100 * abs(big[3]) / big[1]:.3f}% of its demand)", "",
          "## Forest", "",
          f"- Initial area {init_area:,.0f} km2; gross loss {gross_loss:,.0f} km2 ({100 * gross_loss / init_area:.2f}% of the initial area)",
          f"- Cells more than half protected: {share_cells:.1f}% of the cells; they hold {share_loss:.1f}% of the loss",
          f"- Gain: {gain:,.1f} km2 in total; largest {max(d.max(), 0.0):.6f} of a cell; cells with gain above "
          + ", ".join(f"{t}: {n:,}" for t, n in gains.items()), "",
          "## Declared weights and derived coefficients", ""]
    for c, v in drivers.items():
        L.append(f"- {c}: const {v.get('const')}, " + ", ".join(f"{k} {x.get('beta') if isinstance(x, dict) else x}"
                                                              for k, x in (v.get('betas') or v.get('drivers') or {}).items()))
    a.outdir.mkdir(parents=True, exist_ok=True)
    (a.outdir / f"manuscript_numbers_{a.label}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (a.outdir / f"manuscript_numbers_{a.label}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
