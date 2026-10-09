#!/usr/bin/env python3
"""Figures for the note: driver maps and the verification-run result.

    python scripts/make_figures.py --cellspace data/cellspace_bdc_10k.tif \
        --lucc runs/<label>/lucc_<id>.tif --outdir results/figures --tag 10k

Reads only the input raster and the model output; nothing is fitted or edited.
Every result panel is labelled "verification run, not a land-use projection".

Output band order (disslucc 0.5.0): the land uses in the order of `land_use_types`
of model/verification_model.toml, then the saturation band. The script checks that
the land-use bands sum to 1 inside the mask before plotting.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch

LU = ["forest_vegetation", "country_vegetation", "pasture_management",
      "agricultural", "mosaic_of_occupations", "forestry", "others"]
LU_LABEL = {"forest_vegetation": "Forest", "country_vegetation": "Other natural vegetation",
            "pasture_management": "Pasture", "agricultural": "Agriculture",
            "mosaic_of_occupations": "Mosaic of occupations", "forestry": "Forestry",
            "others": "Others"}
LU_COLOR = {"forest_vegetation": "#1b5e20", "country_vegetation": "#a5c26b",
            "pasture_management": "#f2c14e", "agricultural": "#b5651d",
            "mosaic_of_occupations": "#c0504d", "forestry": "#2a7f9e", "others": "#bdbdbd"}

# Transport cost to ports: the discrete grey legend chosen by the author (QGIS colour map),
# classes in the units of the band divided by 1000.
PORT_BREAKS = [0, 129, 249, 466, 797, np.inf]
PORT_GREYS = ["#fafafa", "#bdbdbd", "#808080", "#424242", "#050505"]
PORT_LABELS = ["3 - 129", "129 - 249", "249 - 466", "466 - 797", "797 - 2519"]


def read(path):
    with rasterio.open(path) as s:
        data = s.read().astype(float)
        names = list(s.descriptions)
        ext = (s.bounds.left / 1e3, s.bounds.right / 1e3, s.bounds.bottom / 1e3, s.bounds.top / 1e3)
    return data, names, ext


def style(ax, ext):
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_facecolor("white")


def masked(a, mask):
    return np.where(mask, a, np.nan)


def res_label(ext, shape):
    return f"{(ext[1] - ext[0]) / shape[2]:.2f} km"


def drivers(cs, names, ext, mask, out):
    band = {n: cs[i] for i, n in enumerate(names)}
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.4), constrained_layout=True)
    # (a) cost of transport to ports, author's discrete legend
    ax = axes[0, 0]
    port = masked(band["e_connport"] / 1e3, mask)
    cm = ListedColormap(PORT_GREYS)
    norm = BoundaryNorm(PORT_BREAKS[:-1] + [3000], cm.N)
    ax.imshow(port, cmap=cm, norm=norm, extent=ext, interpolation="nearest")
    ax.legend(handles=[Patch(fc=c, ec="#555", label=l) for c, l in zip(PORT_GREYS, PORT_LABELS)],
              title="Generalized cost", loc="lower left", fontsize=7, title_fontsize=7, frameon=False)
    ax.set_title("(a) Transport cost to ports (e_connport)", fontsize=9)
    spec = [
        ("(b) Distance to unpaved roads, km (e_uroads)", band["e_uroads"] / 1e3, "magma_r", None),
        ("(c) Distance to railways, km (e_railway)", band["e_railway"] / 1e3, "magma_r", None),
        ("(d) Protected share (c_ucspas)", band["c_ucspas"], "Greens", (0, 1)),
        ("(e) Distance to paved roads, km (e_proads)", band["e_proads"] / 1e3, "magma_r", None),
        ("(f) Distance to urban areas >10 km², km (e_urban10)", band["e_urban10"] / 1e3, "magma_r", None),
    ]
    for ax, (title, arr, cmap, lim) in zip(axes.ravel()[1:], spec):
        arr = masked(arr, mask)
        kw = {} if lim is None else dict(vmin=lim[0], vmax=lim[1])
        if lim is None:
            kw = dict(vmin=0, vmax=np.nanpercentile(arr, 98))
        im = ax.imshow(arr, cmap=cmap, extent=ext, interpolation="nearest", **kw)
        cb = fig.colorbar(im, ax=ax, shrink=0.55, pad=0.01)
        cb.ax.tick_params(labelsize=7)
        ax.set_title(title, fontsize=9)
    for ax in axes.ravel():
        style(ax, ext)
    fig.suptitle(f"Drivers of the verification model on the {res_label(ext, cs.shape)} model grid "
                 "(BDC AEA, EPSG:10857)", fontsize=10)
    fig.savefig(out, dpi=300)
    plt.close(fig)


def results(cs, names, lucc, ext, mask, out):
    init = np.stack([cs[names.index(n)] for n in LU])
    final = lucc[:len(LU)]
    s = np.nansum(final[:, mask], axis=0)
    if not np.allclose(s, 1.0, atol=1e-6):
        raise SystemExit(f"land-use bands do not sum to 1 (min {s.min():.6f}, max {s.max():.6f}); "
                         "check the band order of the output")
    cmap = ListedColormap([LU_COLOR[n] for n in LU])

    def dominant(a):
        d = np.argmax(a, axis=0).astype(float)
        return np.where(mask, d, np.nan)

    fig, axes = plt.subplots(2, 2, figsize=(9.6, 7.4), constrained_layout=True)
    for ax, arr, title in ((axes[0, 0], init, "(a) Initial state: dominant land use"),
                           (axes[0, 1], final, "(b) Final state: dominant land use")):
        ax.imshow(dominant(arr), cmap=cmap, vmin=-0.5, vmax=len(LU) - 0.5, extent=ext,
                  interpolation="nearest")
        ax.set_title(title, fontsize=9)
    axes[0, 0].legend(handles=[Patch(fc=LU_COLOR[n], label=LU_LABEL[n]) for n in LU],
                      loc="lower left", fontsize=7, frameon=False)
    # change maps: magnitude of change, sequential, 0 = no change (loss and gain are shown separately)
    forest = LU.index("forest_vegetation")
    anth = [LU.index("pasture_management"), LU.index("agricultural")]
    panels = ((axes[1, 0], init[forest] - final[forest], "Reds", "(c) Forest share lost"),
              (axes[1, 1], final[anth].sum(axis=0) - init[anth].sum(axis=0), "YlOrBr",
               "(d) Pasture + agriculture share gained"))
    for ax, d, cmap, title in panels:
        d = masked(d, mask)
        im = ax.imshow(d, cmap=cmap, vmin=0, vmax=np.nanpercentile(d, 99.8), extent=ext,
                       interpolation="nearest")
        cb = fig.colorbar(im, ax=ax, shrink=0.6, pad=0.01)
        cb.ax.tick_params(labelsize=7)
        ax.set_title(title, fontsize=9)
    for ax in axes.ravel():
        style(ax, ext)
    fig.suptitle(f"Verification run, not a land-use projection (declared parameters, {res_label(ext, cs.shape)} grid)",
                 fontsize=10)
    fig.savefig(out, dpi=300)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cellspace", required=True)
    ap.add_argument("--lucc", required=True)
    ap.add_argument("--outdir", default="results/figures")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    cs, names, ext = read(a.cellspace)
    lucc, _, _ = read(a.lucc)
    mask = cs[names.index("mask")] == 1
    sfx = f"_{a.tag}" if a.tag else ""
    drivers(cs, names, ext, mask, out / f"fig_drivers{sfx}.png")
    results(cs, names, lucc, ext, mask, out / f"fig_result{sfx}.png")
    print("wrote", out / f"fig_drivers{sfx}.png", out / f"fig_result{sfx}.png")


if __name__ == "__main__":
    main()
