#!/usr/bin/env python3
"""Replace the land-use bands of a cell space with MapBiomas, one BDC tile at a time.

DisSCube 0.5.0 reads the whole window of a MapBiomas source into memory (as float32). Over Brazil at 30 m
that is about 9 billion pixels, which does not fit. This script runs DisSCube on one BDC_SM tile (105.6 km)
at a time, only on the tiles that hold cells of the mask, sums the share of each MapBiomas code into the seven
classes of the verification model (model/mapbiomas_crosswalk.toml) and writes a cell space with the same bands
as the base one. The drivers and the mask are kept from the base cell space. Time and peak memory of every
tile are recorded, because the cost of the ingestion is part of what the manuscript reports (section 5.4.3).

    python scripts/build_mapbiomas_cellspace.py --base data/raw_cellspace_bdc_5k.tif \
        --out data/raw_cellspace_bdc_5k_mapbiomas.tif --workdir data/mapbiomas_5k
    # then, as for the main cell space:
    python scripts/complete_cellspace.py data/raw_cellspace_bdc_5k_mapbiomas.tif data/cellspace_bdc_5k_mapbiomas.tif

Use --tiles to try a few tiles (indices "col,row;col,row", row counted from the top), --url for a local MapBiomas GeoTIFF (tests).
Only the land-use bands change; the model parameters must be generated again from the 10.56 km version of this
cell space (scripts/make_parameters.py --cellspace ... --out model/verification_model_mapbiomas.toml).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import pathlib
import resource
import shutil
import subprocess
import sys
import time

import numpy as np
import rasterio
import tomllib

TILE_M = 105600.0                     # BDC_SM tile side
LU = ["forest_vegetation", "country_vegetation", "pasture_management", "agricultural",
      "mosaic_of_occupations", "forestry", "others"]
ROOT = pathlib.Path(__file__).resolve().parent.parent


def peak_mb() -> float:
    return resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024.0


def tile_toml(path: pathlib.Path, crs: str, res: float, bbox, codes: list[int], cw: dict, url: str | None) -> None:
    src = cw["source"]
    lines = ["schema = 1", 'name = "MapBiomas, one BDC tile"', "", "[grid]", 'name = "tile"', f'crs = "{crs}"',
             f"resolution = {res}", "bbox = [" + ", ".join(repr(float(v)) for v in bbox) + "]", "",
             "[[source]]", 'id = "mb"', 'type = "mapbiomas"', f"year = {src['year']}",
             f"collection = {src['collection']}", f"resolution = {src['resolution']}"]
    if url:
        lines.append(f'url = "{url}"')
    for c in codes:
        lines += ["", "[[derive]]", f'target = "c{c}"', 'source = "mb"', 'operator = "percentage"', f"class_code = {c}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, type=pathlib.Path, help="cell space with the drivers and the mask (raw, before complete_cellspace)")
    ap.add_argument("--out", required=True, type=pathlib.Path)
    ap.add_argument("--workdir", required=True, type=pathlib.Path)
    ap.add_argument("--crosswalk", type=pathlib.Path, default=ROOT / "model" / "mapbiomas_crosswalk.toml")
    ap.add_argument("--tiles", default=None, help='only these tiles, "col,row;col,row" (indices: column, row counted from the top of the grid)')
    ap.add_argument("--url", default=None, help="local or remote MapBiomas GeoTIFF instead of the published one")
    ap.add_argument("--jobs", type=int, default=1,
                    help="tiles run at the same time (each uses about 0.5 GB and mostly waits for the network)")
    ap.add_argument("--resume", action="store_true", help="keep the tiles already finished in --workdir (tile.tif present)")
    a = ap.parse_args()

    cw = tomllib.loads(a.crosswalk.read_text(encoding="utf-8"))
    cls = cw["classes"]
    if set(cls) != set(LU):
        sys.exit(f"the crosswalk must define exactly {LU}")
    all_codes = [c for k in LU for c in cls[k]]
    if len(all_codes) != len(set(all_codes)):
        sys.exit("a MapBiomas code is listed in more than one class")

    with rasterio.open(a.base) as s:
        profile, names = s.profile, list(s.descriptions)
        arrays = s.read()
        tr, crs = s.transform, s.crs
    res = tr.a
    ny, nx = arrays.shape[1:]
    per_tile = round(TILE_M / res)
    if abs(per_tile * res - TILE_M) > 1e-6:
        sys.exit(f"the resolution {res} m does not divide the BDC tile of {TILE_M} m")
    mask = np.nan_to_num(arrays[names.index("mask")]) > 0
    left, top = tr.c, tr.f
    tile_ids = sorted({(int(j // per_tile), int(i // per_tile)) for i, j in zip(*np.nonzero(mask))})  # (col, row-from-top)
    if a.tiles:
        want = {tuple(int(v) for v in t.split(",")) for t in a.tiles.split(";")}
        tile_ids = [t for t in tile_ids if t in want]
    print(f"{len(tile_ids)} tiles with cells in the mask (of {-(-nx // per_tile) * -(-ny // per_tile)})", flush=True)

    a.workdir.mkdir(parents=True, exist_ok=True)
    out = {k: np.full((ny, nx), np.nan, dtype="float32") for k in LU}
    proj = crs.to_proj4()
    t_all = time.perf_counter()

    def bounds_of(tc, tr_):
        r0, c0 = tr_ * per_tile, tc * per_tile
        r1, c1 = min(r0 + per_tile, ny), min(c0 + per_tile, nx)
        return r0, r1, c0, c1, (left + c0 * res, top - r1 * res, left + c1 * res, top - r0 * res)

    def run_tile(tid):
        tc, tr_ = tid
        r0, r1, c0, c1, bbox = bounds_of(tc, tr_)
        wd = a.workdir / f"tile_{tc}_{tr_}"
        toml_path, tif = wd / "tile.toml", wd / "tile.tif"
        if a.resume and tif.exists():
            return tid, 0.0, True, ""
        if wd.exists():
            shutil.rmtree(wd)
        wd.mkdir()
        tile_toml(toml_path, proj, res, bbox, all_codes, cw, a.url)
        t0 = time.perf_counter()
        p = subprocess.run(["disscube", "run", str(toml_path), "--workspace", str(wd / "ws"), "--output", str(tif)],
                           capture_output=True, text=True)
        return tid, time.perf_counter() - t0, False, (p.stdout + p.stderr)[-1500:] if p.returncode else ""

    def read_tile(tid):
        tc, tr_ = tid
        r0, r1, c0, c1, _ = bounds_of(tc, tr_)
        with rasterio.open(a.workdir / f"tile_{tc}_{tr_}" / "tile.tif") as t:
            tn = list(t.descriptions)
            pct = {c: t.read(tn.index(f"c{c}_{cw['source']['year']}") + 1).astype("float64") for c in all_codes}
        h, w = r1 - r0, c1 - c0
        for c in pct:
            if pct[c].shape != (h, w):
                sys.exit(f"tile {tc},{tr_}: unexpected shape {pct[c].shape}, expected {(h, w)}")
        scale = 100.0 if max(np.nanmax(v) if np.isfinite(v).any() else 0 for v in pct.values()) > 1.5 else 1.0
        seen = np.zeros((h, w), dtype=bool)
        for v in pct.values():
            seen |= np.isfinite(v)
        listed = {k: sum(np.nan_to_num(pct[c]) for c in cls[k]) / scale for k in LU}
        listed["others"] = np.clip(1.0 - sum(listed[k] for k in LU if k != "others"), 0.0, 1.0)  # also every unlisted code
        for k in LU:
            out[k][r0:r1, c0:c1] = np.where(seen, np.clip(listed[k], 0.0, 1.0), np.nan)
        return int(mask[r0:r1, c0:c1].sum())

    report = []
    with cf.ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        for n, (tid, dt, skipped, err) in enumerate(ex.map(run_tile, tile_ids), 1):
            if err:
                sys.exit(f"disscube failed on tile {tid[0]},{tid[1]}:\n{err}")
            cells = read_tile(tid)
            report.append({"tile": list(tid), "cells": cells, "seconds": round(dt, 2), "resumed": skipped})
            print(f"[{n}/{len(tile_ids)}] tile {tid[0]},{tid[1]}: {'kept' if skipped else f'{dt:.1f} s'}, "
                  f"peak {peak_mb():.0f} MB", flush=True)

    # same bands as the base cell space; only the land-use bands change
    for k in LU:
        arrays[names.index(k)] = out[k]
    profile.update(count=arrays.shape[0], dtype="float32")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(a.out, "w", **profile) as d:
        d.write(arrays.astype("float32"))
        d.descriptions = tuple(names)
    cell_km2 = res * res / 1e6
    base_land = {}
    with rasterio.open(a.base) as s:
        b = s.read()
    for k in LU:
        base_land[k] = float(np.nansum(np.where(mask, b[names.index(k)], 0)) * cell_km2)
    new_land = {k: float(np.nansum(np.where(mask, out[k], 0)) * cell_km2) for k in LU}
    summary = {
        "base": str(a.base), "out": str(a.out), "year": cw["source"]["year"], "collection": cw["source"]["collection"],
        "crosswalk": str(a.crosswalk), "tiles": len(tile_ids), "wall_seconds": round(time.perf_counter() - t_all, 1),
        "peak_rss_mb": round(peak_mb(), 1), "class_area_km2_base": base_land, "class_area_km2_mapbiomas": new_land,
        "jobs": a.jobs, "cells_in_mask_of_the_tiles_run": int(sum(r["cells"] for r in report)),
        "cells_of_mask_without_mapbiomas": int((mask & np.isnan(out["forest_vegetation"])).sum()),
        "note": "cells_of_mask_without_mapbiomas counts the cells of the base mask not filled; it is meaningful for a run over all tiles only",
        "per_tile": report,
    }
    (a.workdir / "build_report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_tile"}, indent=2))


if __name__ == "__main__":
    main()
