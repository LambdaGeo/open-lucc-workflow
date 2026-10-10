#!/usr/bin/env python
"""Synthetic input raster with the same bands as the Brazil input raster (no download).

Used by `make small` and by CI. One landscape (seeded) is generated at the finest resolution and
block-averaged for the coarser grids, so a fine run and a coarse run describe the same area and
their class totals can be compared (acceptance.toml, [resolution]).

    python scripts/synth_input.py --out data/synthetic_fine.tif
    python scripts/synth_input.py --out data/synthetic_coarse.tif --block 2
"""
from __future__ import annotations

import argparse
import pathlib

import numpy as np
from dissmodel.geo import RasterBackend
from dissmodel.io.raster import save_geotiff
from rasterio.transform import from_origin

try:  # run as a script or imported by the tests
    from _common import DRIVERS, LAND_USES
except ImportError:  # pragma: no cover
    from scripts._common import DRIVERS, LAND_USES

BDC_AEA = ("+proj=aea +lat_0=-12 +lon_0=-54 +lat_1=-2 +lat_2=-22 +x_0=5000000 +y_0=10000000 "
           "+ellps=GRS80 +units=m +no_defs")
FINE_RES_M = 5280.0                    # a BDC_SM tile (105.6 km) is exactly 20 cells
ORIGIN = (2465600.0, 7360000.0)        # lower-left corner of the Brazil bbox, on the tile grid


def _smooth(rng: np.random.Generator, n: int, passes: int = 8) -> np.ndarray:
    r = rng.random((n, n))
    for _ in range(passes):
        r = (r + np.roll(r, 1, 0) + np.roll(r, -1, 0) + np.roll(r, 1, 1) + np.roll(r, -1, 1)) / 5
    return (r - r.min()) / (r.max() - r.min())


def landscape(n: int, seed: int) -> dict[str, np.ndarray]:
    """n x n fine cells: land-use fractions (sum 1), drivers in realistic units, mask."""
    rng = np.random.default_rng(seed)
    logits = np.stack([_smooth(rng, n) * 3.0 for _ in LAND_USES])
    logits[LAND_USES.index("others")] -= 2.0          # water / bare: rare
    frac = np.exp(logits)
    frac /= frac.sum(0)
    out = {lu: frac[i] for i, lu in enumerate(LAND_USES)}
    out["c_ucspas"] = np.clip(_smooth(rng, n) * 1.4 - 0.3, 0.0, 1.0)   # protected share
    out["c_nusett"] = np.floor(_smooth(rng, n) * 4)                     # settlements per cell
    for name, scale in (("e_railway", 1.5e6), ("e_rivers", 4e5), ("e_urban10", 8e5),
                        ("e_urban100", 1.2e6), ("e_proads", 2e5), ("e_uroads", 3e5),
                        ("e_connport", 2.5e6)):                         # metres, or cost units
        out[name] = _smooth(rng, n) * scale
    out["mask"] = np.ones((n, n))
    return out


def block_mean(a: np.ndarray, k: int) -> np.ndarray:
    n = a.shape[0] // k * k
    return a[:n, :n].reshape(n // k, k, n // k, k).mean(axis=(1, 3))


def build(out: pathlib.Path, n: int = 60, block: int = 1, seed: int = 20260901) -> str:
    if n % block:
        raise SystemExit(f"--block {block} must divide the fine size {n}")
    fine = landscape(n, seed)
    bands = {k: (v if block == 1 else block_mean(v, block)) for k, v in fine.items()}
    m = n // block
    res = FINE_RES_M * block
    backend = RasterBackend(shape=(m, m))
    for name, arr in bands.items():
        backend.set(name, arr.astype("float32"))
    transform = from_origin(ORIGIN[0], ORIGIN[1] + m * res, res, res)
    spec = [(name, "float32", -1.0) for name in list(LAND_USES) + DRIVERS + ["mask"]]
    out.parent.mkdir(parents=True, exist_ok=True)
    return save_geotiff((backend, {"crs": BDC_AEA, "transform": transform}), str(out), band_spec=spec)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    ap.add_argument("--size", type=int, default=60, help="fine grid is size x size cells of 5.28 km")
    ap.add_argument("--block", type=int, default=1, help="aggregate block x block fine cells")
    ap.add_argument("--seed", type=int, default=20260901)
    a = ap.parse_args()
    sha = build(a.out, a.size, a.block, a.seed)
    print(f"{a.out}  sha256={sha}")


if __name__ == "__main__":
    main()
