"""Shared helpers: reading the model TOML, cell-space bands, areas."""
from __future__ import annotations

import hashlib
import json
import pathlib

import numpy as np
import rasterio
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL_TOML = ROOT / "model" / "verification_model.toml"
SCENARIO_TOML = ROOT / "model" / "scenario.toml"
ACCEPTANCE_TOML = ROOT / "acceptance.toml"

LAND_USES = [
    "forest_vegetation", "country_vegetation", "pasture_management",
    "agricultural", "mosaic_of_occupations", "forestry", "others",
]
DRIVERS = [
    "c_ucspas", "c_nusett", "e_railway", "e_rivers",
    "e_urban10", "e_urban100", "e_proads", "e_uroads", "e_connport",
]
REQUIRED_BANDS = LAND_USES + DRIVERS + ["mask"]


def load_toml(path: pathlib.Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def sha256_file(path: str | pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_bands(path: str | pathlib.Path) -> tuple[dict[str, np.ndarray], rasterio.Affine, object]:
    """Named bands of a GeoTIFF as float64 arrays, plus transform and CRS."""
    with rasterio.open(path) as src:
        names = [src.tags(i).get("name") or src.descriptions[i - 1] or f"band{i}"
                 for i in range(1, src.count + 1)]
        data = src.read().astype("float64")
        nodata = src.nodata
        bands = {}
        for n, a in zip(names, data):
            if nodata is not None:
                a = np.where(a == nodata, np.nan, a)
            bands[n] = a
        return bands, src.transform, src.crs


def cell_area_km2(transform: rasterio.Affine) -> float:
    """Area of one cell in km2; the BDC grid is equal-area, so every cell has the same area."""
    return abs(transform.a * transform.e) / 1e6


def class_areas_km2(bands: dict[str, np.ndarray], transform: rasterio.Affine) -> dict[str, float]:
    mask = np.nan_to_num(bands["mask"]) > 0
    area = cell_area_km2(transform)
    return {lu: float(np.nansum(bands[lu][mask]) * area) for lu in LAND_USES}


def write_json(path: str | pathlib.Path, obj: dict) -> None:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
