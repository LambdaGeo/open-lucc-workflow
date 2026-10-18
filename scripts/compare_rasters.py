#!/usr/bin/env python
"""Compare two GeoTIFF files by their decoded values, band by band.

    python scripts/compare_rasters.py a.tif b.tif

Two files can have different SHA-256 and equal values: each platform's GDAL writes
the DEFLATE compression differently, and the bytes of the file change with it.
This script says whether the values, the grid and the masks are the same, which
is the question behind a DIFFERS of `make reproduce-10k` on another platform.
"""
import sys

import numpy as np
import rasterio

if len(sys.argv) != 3:
    sys.exit(__doc__)
pa, pb = sys.argv[1:3]
equal_all = True
with rasterio.open(pa) as a, rasterio.open(pb) as b:
    same_grid = (a.crs == b.crs and a.transform == b.transform and a.shape == b.shape and a.count == b.count)
    print(f"crs, transform, shape and bands equal: {same_grid} ({a.count} bands, {a.shape[0]}x{a.shape[1]}, {a.dtypes[0]}/{b.dtypes[0]})")
    if not same_grid:
        sys.exit(1)
    print("| band | arrays equal | NaN mask equal | cells that differ | max absolute difference | max relative difference |")
    print("|---|---|---|---|---|---|")
    for i in range(1, a.count + 1):
        x, y = a.read(i).astype("f8"), b.read(i).astype("f8")
        if a.nodata is not None:
            x, y = np.where(x == a.nodata, np.nan, x), np.where(y == b.nodata, np.nan, y)
        nx, ny = np.isnan(x), np.isnan(y)
        both = ~nx & ~ny
        d = np.abs(x[both] - y[both])
        xv = np.abs(x[both])
        nz = xv > 0
        rel = d[nz] / xv[nz]
        eq = bool(np.array_equal(x, y, equal_nan=True))
        equal_all &= eq
        label = a.tags(i).get("name") or a.descriptions[i - 1] or f"band{i}"
        print(f"| {label} | {eq} | {np.array_equal(nx, ny)} | {int((d > 0).sum())} | "
              f"{float(d.max()) if d.size else 0.0:.3g} | {float(rel.max()) if rel.size else 0.0:.3g} |")
print("\nAll values equal." if equal_all else "\nSome values differ; see the table for how many and by how much.")
