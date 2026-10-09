#!/usr/bin/env python
"""Yearly demand (km2 per class) for the verification scenario, from the cell space itself.

The demand starts at the areas of the input cell space and changes by the declared scenario
(model/scenario.toml). Because it is derived from the cell space in km2, the same scenario applies
to any grid of the same area.

    python scripts/make_demand.py --cellspace data/cellspace_5k.tif --out runs/x/demand.csv
"""
from __future__ import annotations

import argparse
import pathlib

try:
    from _common import LAND_USES, SCENARIO_TOML, class_areas_km2, load_toml, read_bands
except ImportError:  # pragma: no cover
    from scripts._common import LAND_USES, SCENARIO_TOML, class_areas_km2, load_toml, read_bands


def demand_table(initial: dict[str, float], scenario: dict) -> list[dict[str, float]]:
    s = scenario["scenario"]
    loss = initial["forest_vegetation"] * s["forest_loss_pct_per_year"] / 100.0
    shares = s["gain_shares"]
    if abs(sum(shares.values()) - 1.0) > 1e-9:
        raise ValueError("gain_shares must sum to 1")
    rows = []
    for t in range(int(s["n_steps"])):
        row = dict(initial)
        row["forest_vegetation"] = initial["forest_vegetation"] - loss * t
        for lu, share in shares.items():
            row[lu] = initial[lu] + loss * share * t
        rows.append(row)
    return rows


def write_csv(rows: list[dict[str, float]], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(LAND_USES)] + [",".join(f"{r[lu]:.6f}" for lu in LAND_USES) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cellspace", required=True, type=pathlib.Path)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    a = ap.parse_args()
    bands, transform, _ = read_bands(a.cellspace)
    rows = demand_table(class_areas_km2(bands, transform), load_toml(SCENARIO_TOML))
    write_csv(rows, a.out)
    print(f"{a.out}: {len(rows)} years, total {sum(rows[0].values()):.1f} km2")


if __name__ == "__main__":
    main()
