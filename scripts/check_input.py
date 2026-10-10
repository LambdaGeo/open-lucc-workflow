#!/usr/bin/env python
"""Sanity checks on an input raster before any model run (synthetic or built by DisSCube).

    python scripts/check_input.py data/br_5km.tif
If cells fail only because some bands are undefined along the coast or borders, run
scripts/complete_input.py, which takes those cells out of the mask and reports how many.
Exit status 1 if a required band is missing, a share is outside [0, 1], the land uses do not sum to 1
inside the mask, or a driver has NaN inside the mask.
"""
from __future__ import annotations

import sys

import numpy as np

try:
    from _common import DRIVERS, LAND_USES, REQUIRED_BANDS, cell_area_km2, read_bands
except ImportError:  # pragma: no cover
    from scripts._common import DRIVERS, LAND_USES, REQUIRED_BANDS, cell_area_km2, read_bands

SUM_TOLERANCE = 1e-3          # land uses sum to 1 inside the mask, up to float32 and coastal remainder


def sum_breakdown(total: np.ndarray) -> str:
    """How far from 1 the land-use sums are, in words: zero sums, deficits, excesses."""
    n = total.size
    zero = int((total <= SUM_TOLERANCE).sum())
    low = int(((total > SUM_TOLERANCE) & (total < 1 - SUM_TOLERANCE)).sum())
    high = int((total > 1 + SUM_TOLERANCE).sum())
    q = np.quantile(total[total > SUM_TOLERANCE], [0.01, 0.5, 0.99]) if zero < n else [float("nan")] * 3
    return (f"of {n:,} cells: sum = 0 in {zero:,}; 0 < sum < 1 in {low:,}; sum > 1 in {high:,}; "
            f"sum quantiles (1%, 50%, 99%) among the non-zero: {q[0]:.4g}, {q[1]:.4g}, {q[2]:.4g}")


def check(path: str) -> list[str]:
    bands, transform, crs = read_bands(path)
    problems = [f"missing band: {b}" for b in REQUIRED_BANDS if b not in bands]
    if problems:
        return problems
    mask = np.nan_to_num(bands["mask"]) > 0
    if not mask.any():
        return ["mask is empty"]
    for lu in LAND_USES:
        v = bands[lu][mask]
        if np.isnan(v).any():
            problems.append(f"{lu}: NaN inside the mask ({int(np.isnan(v).sum()):,} of {mask.sum():,} cells)")
        elif v.min() < -1e-6 or v.max() > 1 + 1e-6:
            problems.append(f"{lu}: values outside [0, 1] ({v.min():.4g} .. {v.max():.4g})")
    total = np.nansum([bands[lu] for lu in LAND_USES], axis=0)[mask]
    off = float(np.abs(total - 1.0).max())
    if off > SUM_TOLERANCE:
        problems.append(f"land uses do not sum to 1 inside the mask (max deviation {off:.4g})")
        problems.append("  " + sum_breakdown(total))
    for d in DRIVERS:
        if np.isnan(bands[d][mask]).any():
            problems.append(f"{d}: NaN inside the mask ({int(np.isnan(bands[d][mask]).sum()):,} of {mask.sum():,} cells)")
    print(f"{path}: {mask.sum():,} cells in the mask, cell area {cell_area_km2(transform):.3f} km2, CRS {str(crs)[:40]}...")
    return problems


if __name__ == "__main__":
    probs = check(sys.argv[1])
    for p in probs:
        print("FAIL", p)
    sys.exit(1 if probs else 0)
