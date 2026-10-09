#!/usr/bin/env python
"""Is the net potential of the verification model balanced? Report it and suggest a constant.

The allocation changes every class in a cell by potential x elasticity, and leaves a cell alone while
its land uses sum to 1 +- 0.005. If the potentials of the moving classes add up to more than zero in
most cells, every cell drifts to the upper edge of that band, the total area ends above the demand,
and the allocation cannot meet the demand class by class (a persistent positive 'sum of gaps').

    python scripts/potential_balance.py --cellspace data/cellspace_bdc_10k.tif

Prints, at the initial state: the mean potential of each class and of their sum, the share of cells
whose summed potential is above +0.005 or below -0.005, and the constant of the complementary class
(forest) that would bring the mean summed potential to zero. Nothing is written; the constant, if
used, is copied by hand into model/verification_model.toml and recorded there as a declared choice.
"""
from __future__ import annotations

import argparse
import copy
import pathlib

import numpy as np

try:
    from _common import LAND_USES, MODEL_TOML, load_toml, read_bands
except ImportError:  # pragma: no cover
    from scripts._common import LAND_USES, MODEL_TOML, load_toml, read_bands


MOVING = [lu for lu in LAND_USES if lu != "others"]  # `others` is static (allocation static = 1)


def potentials(bands, specs, valid, shift=0.0):
    from disslucc.components.potential.spatial_lag import spatial_lag_regression

    nd = np.nan_to_num(bands["others"])
    pots = {}
    for lu in LAND_USES:
        spec = specs[lu]
        # change `const` itself, not only `newconst`: the clip test of the regression uses `const`
        if lu == "forest_vegetation":
            spec.const = spec.const + shift
        newconst = spec.const
        drivers = {k: np.nan_to_num(bands[k]) for k in spec.betas}
        past = np.nan_to_num(bands[lu])
        _, pot = spatial_lag_regression(spec, past, drivers, valid, nd, newconst)
        pots[lu] = pot
    return pots


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cellspace", required=True, type=pathlib.Path)
    a = ap.parse_args()

    from disslucc.executors.saturation import _by_region, _potential_spec

    bands, _, _ = read_bands(a.cellspace)
    valid = np.nan_to_num(bands["mask"]) > 0
    model = load_toml(MODEL_TOML)["model"]
    specs = dict(zip(LAND_USES, _by_region(model["potential_data"], LAND_USES, _potential_spec)[0]))

    def net(shift):
        pots = potentials(bands, copy.deepcopy(specs), valid, shift)
        return pots, np.sum([pots[lu] for lu in MOVING], axis=0)

    pots, total = net(0.0)
    print(f"cells in the mask: {int(valid.sum()):,}")
    print(f"{'class':24s}{'mean potential':>16s}{'share pot > 0':>15s}")
    for lu in LAND_USES:
        v = pots[lu][valid]
        print(f"{lu:24s}{v.mean():16.5f}{(v > 0).mean():15.1%}")
    t = total[valid]
    print(f"\nsum of the six moving classes' potentials per cell: mean {t.mean():+.5f}, "
          f"> +0.005 in {(t > 0.005).mean():.1%} of the cells, < -0.005 in {(t < -0.005).mean():.1%}")
    lo, hi = -1.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        m = net(mid)[1][valid].mean()
        lo, hi = (lo, mid) if m > 0 else (mid, hi)
    shift = (lo + hi) / 2
    const = specs["forest_vegetation"].const
    print(f"\nforest_vegetation const now {const}; a shift of {shift:+.5f} (const = {const + shift:.5f}) "
          "brings the mean summed potential to zero")
    t2 = net(shift)[1][valid]
    print(f"with that shift: mean {t2.mean():+.2e}, > +0.005 in {(t2 > 0.005).mean():.1%}, < -0.005 in {(t2 < -0.005).mean():.1%}")


if __name__ == "__main__":
    main()
