#!/usr/bin/env python
"""Render the DisSCube derivation pipeline for a grid of the Brazil Data Cube.

The derivations are those of the disscube-recipes case `luccme_br`
(commit f21523f, copied unchanged into pipeline/cellspace/); only the [grid] block changes.

    python scripts/render_pipeline.py --name bdc_5k  --out build/pipelines/bdc_5k.toml
    python scripts/render_pipeline.py --name bdc_10k --out build/pipelines/bdc_10k.toml

Grids (configs below):
  bdc_5k   5,280 m: 20 x 20 cells per BDC_SM tile (105.6 km), nested exactly.
  bdc_10k  10,560 m: 10 x 10 cells per tile, an exact 2 x 2 aggregation of bdc_5k.
"""
from __future__ import annotations

import argparse
import math
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "pipeline" / "cellspace" / "derivations.template.toml"

# Brazil bbox on the BDC_SM tile grid (as in disscube-recipes/cases/luccme_br), lower-left origin
BBOX = (2465600.0, 7360000.0, 7956800.0, 12112000.0)
GRIDS = {"bdc_5k": 5280.0, "bdc_10k": 10560.0}


def bbox_for(res: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = BBOX
    nx = math.ceil((x1 - x0) / res)
    ny = math.ceil((y1 - y0) / res)
    return (x0, y0, x0 + nx * res, y0 + ny * res)


def render(name: str) -> str:
    if name not in GRIDS:
        raise SystemExit(f"unknown grid {name!r}; known: {sorted(GRIDS)}")
    res = GRIDS[name]
    text = TEMPLATE.read_text(encoding="utf-8")
    bbox = bbox_for(res)
    text, n1 = re.subn(r'(?m)^name\s*=\s*"bdc_10k"', f'name = "{name}"', text, count=1)
    text, n2 = re.subn(r"(?m)^resolution\s*=\s*10560\.0", f"resolution = {res}", text, count=1)
    text, n3 = re.subn(r"(?m)^bbox\s*=\s*\[[^\]]*\]", "bbox = [" + ", ".join(f"{v}" for v in bbox) + "]", text, count=1)
    if (n1, n2, n3) != (1, 1, 1):
        raise SystemExit("the template's [grid] block changed; update render_pipeline.py")
    return text


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    a = ap.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(render(a.name), encoding="utf-8")
    print(f"{a.out}: grid {a.name} ({GRIDS[a.name]:.0f} m)")


if __name__ == "__main__":
    main()
