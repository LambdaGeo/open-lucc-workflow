#!/usr/bin/env python
"""Sanity checks on a cell space before any model run (synthetic or built by DisSCube).

    python scripts/check_cellspace.py data/cellspace_5k.tif
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
            problems.append(f"{lu}: NaN inside the mask")
        elif v.min() < -1e-6 or v.max() > 1 + 1e-6:
            problems.append(f"{lu}: values outside [0, 1] ({v.min():.4g} .. {v.max():.4g})")
    total = np.nansum([bands[lu] for lu in LAND_USES], axis=0)[mask]
    off = float(np.abs(total - 1.0).max())
    if off > SUM_TOLERANCE:
        problems.append(f"land uses do not sum to 1 inside the mask (max deviation {off:.4g})")
    for d in DRIVERS:
        if np.isnan(bands[d][mask]).any():
            problems.append(f"{d}: NaN inside the mask")
    print(f"{path}: {mask.sum():,} cells in the mask, cell area {cell_area_km2(transform):.3f} km2, CRS {str(crs)[:40]}...")
    return problems


if __name__ == "__main__":
    probs = check(sys.argv[1])
    for p in probs:
        print("FAIL", p)
    sys.exit(1 if probs else 0)
