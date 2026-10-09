#!/usr/bin/env python
"""Restrict the mask of a cell space to the cells where every land use and driver is defined.

DisSCube's `mask` band is the share of each cell inside the country boundary. Along the coast and
the borders some cells are partly inside the boundary but have no land-use value (the land-cover
layer does not cover them) or no road path to a port (islands). The model needs complete cells, so
those cells are taken out of the mask. Nothing is filled or invented; the original boundary share is
kept in the band `mask_boundary` and the cells that were taken out are counted in a JSON report, so
the choice is recorded and can be cited in the manuscript.

    python scripts/complete_cellspace.py data/raw_cellspace_bdc_5k.tif data/cellspace_bdc_5k.tif
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import rasterio

try:
    from _common import DRIVERS, LAND_USES, REQUIRED_BANDS, cell_area_km2, read_bands, sha256_file
except ImportError:  # pragma: no cover
    from scripts._common import DRIVERS, LAND_USES, REQUIRED_BANDS, cell_area_km2, read_bands, sha256_file


ZERO_SUM = 1e-3
SUM_TOL = 1e-3


def complete(src_path: str, out_path: str, min_coverage: float = 0.5, partial_mode: str = "renormalize") -> dict:
    if partial_mode not in ("renormalize", "others"):
        raise SystemExit("partial_mode must be renormalize or others")
    bands, transform, crs = read_bands(src_path)
    missing = [b for b in REQUIRED_BANDS if b not in bands]
    if missing:
        raise SystemExit(f"missing bands: {missing}")
    mask = np.nan_to_num(bands["mask"]) > 0
    lu_nan = {lu: mask & np.isnan(bands[lu]) for lu in LAND_USES}
    any_lu = np.any([v for v in lu_nan.values()], axis=0)
    all_lu = np.all([v for v in lu_nan.values()], axis=0)
    drv_nan = {d: mask & np.isnan(bands[d]) for d in DRIVERS}
    any_drv = np.any([v for v in drv_nan.values()], axis=0)
    # cells where every land use is defined but all are zero hold none of the modelled classes
    # (open water, for example, or a class the model does not carry): nothing to allocate there
    lu_sum = np.nansum([bands[lu] for lu in LAND_USES], axis=0)
    zero_sum = mask & ~any_lu & (lu_sum <= ZERO_SUM)
    # cells only partly covered by the land-cover layer (coast, borders): below `min_coverage` they are
    # taken out of the mask; above it the missing share is either spread over the classes present
    # ("renormalize") or put in `others` ("others"). Either way the choice is recorded in the report.
    low_cov = mask & ~any_lu & ~zero_sum & (lu_sum < min_coverage)
    partial = mask & ~any_lu & ~zero_sum & ~low_cov & (lu_sum < 1 - SUM_TOL)
    keep = mask & ~any_lu & ~any_drv & ~zero_sum & ~low_cov
    area = cell_area_km2(transform)
    report = {
        "source": pathlib.Path(src_path).name,
        "cells_in_boundary_mask": int(mask.sum()),
        "cells_kept": int(keep.sum()),
        "cells_removed": int((mask & ~keep).sum()),
        "removed_share_of_boundary_cells": float((mask & ~keep).sum() / mask.sum()),
        "removed_area_km2": float((mask & ~keep).sum() * area),
        "cells_with_no_land_use_at_all": int(all_lu.sum()),
        "cells_with_all_land_uses_zero": int(zero_sum.sum()),
        "cells_below_min_coverage": int(low_cov.sum()),
        "min_coverage": min_coverage,
        "cells_partly_covered_adjusted": int(partial.sum()),
        "partial_mode": partial_mode,
        "area_added_by_adjustment_km2": float(((1 - lu_sum)[partial]).sum() * area),
        "cells_with_some_land_use_missing": int((any_lu & ~all_lu).sum()),
        "cells_missing_by_band": {k: int(v.sum()) for k, v in {**lu_nan, **drv_nan}.items() if v.sum()},
        "cell_area_km2": area,
    }
    with rasterio.open(src_path) as src:
        profile = src.profile.copy()
        names = [src.tags(i).get("name") or src.descriptions[i - 1] or f"band{i}" for i in range(1, src.count + 1)]
        nodata = src.nodata
        data = src.read().astype("float32")
    fill = -1.0 if nodata is None else float(nodata)
    new_mask = np.where(keep, bands["mask"], 0.0).astype("float32")
    for i, n in enumerate(names):
        if n == "mask":
            data[i] = new_mask
        elif n in LAND_USES + DRIVERS:
            data[i] = np.where(keep, data[i], fill).astype("float32")
    idx = {n: i for i, n in enumerate(names)}
    for lu in LAND_USES:
        if partial_mode == "renormalize":
            data[idx[lu]] = np.where(partial, data[idx[lu]] / np.where(lu_sum > 0, lu_sum, 1.0), data[idx[lu]])
        elif lu == "others":
            data[idx[lu]] = np.where(partial, data[idx[lu]] + (1.0 - lu_sum), data[idx[lu]])
    boundary = np.where(mask, bands["mask"], 0.0).astype("float32")
    profile.update(count=len(names) + 1, dtype="float32", nodata=fill)
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        for i, n in enumerate(names, 1):
            dst.write(data[i - 1], i)
            dst.update_tags(i, name=n)
            dst.set_band_description(i, n)
        dst.write(boundary, len(names) + 1)
        dst.update_tags(len(names) + 1, name="mask_boundary")
        dst.set_band_description(len(names) + 1, "mask_boundary")
    report["output"] = pathlib.Path(out_path).name
    report["output_sha256"] = sha256_file(out_path)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--max-removed-share", type=float, default=0.02,
                    help="refuse to continue if more than this share of the boundary cells would be removed (default 0.02); "
                         "a large share means a problem in the data (for example a broken road network), not a coastline")
    ap.add_argument("--min-coverage", type=float, default=0.5,
                    help="cells whose land uses sum to less than this are removed from the mask (default 0.5)")
    ap.add_argument("--partial", choices=["renormalize", "others"], default="renormalize",
                    help="cells with a sum between min-coverage and 1: rescale the classes to sum to 1 (default) or put the rest in `others`")
    a = ap.parse_args()
    rep = complete(a.src, a.out, a.min_coverage, a.partial)
    if rep["removed_share_of_boundary_cells"] > a.max_removed_share:
        print(json.dumps({k: v for k, v in rep.items() if k.startswith(("cells", "removed"))}, indent=2))
        pathlib.Path(a.out).unlink(missing_ok=True)
        raise SystemExit(f"{rep['removed_share_of_boundary_cells']:.1%} of the cells in the boundary would be removed (limit "
                         f"{a.max_removed_share:.1%}). Look at the bands listed above before accepting this; "
                         "scripts/diagnose_network.py explains missing e_connport. Use --max-removed-share to override.")
    pathlib.Path(a.out).with_suffix(".report.json").write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "cells_missing_by_band"}, indent=2))
    if rep["cells_missing_by_band"]:
        print("cells missing by band:", rep["cells_missing_by_band"])


if __name__ == "__main__":
    main()
