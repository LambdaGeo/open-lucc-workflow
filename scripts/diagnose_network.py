#!/usr/bin/env python
"""Why does `network_cost` leave cells without a value? Look at the road graph it builds.

DisSCube joins road segments into one graph only where two endpoints have the same coordinates
(rounded to 1 mm). Roads from different layers (state roads from the SNV, federal roads from IBGE)
rarely share exact endpoints, so the graph breaks into many pieces, and a cell whose nearest road
vertex lies in a piece without a port gets no value. This script counts the pieces, says which ones
hold a port, and shows how many cells would be served if endpoints closer than a tolerance were joined.

    python scripts/diagnose_network.py --cellspace data/raw_cellspace_bdc_5k.tif

Note: the pipeline now uses the TerraME GPM road/port network (one connected network, as in the
disscube-benchmark connectivity case), so this script only applies to the older SNV+BC250 sources.

Reads the layers from the DisSCube download cache (default ~/.cache/disscube/raw) with the same
filters as pipeline/cellspace/sources.toml. Nothing is written.
"""
from __future__ import annotations

import argparse
import pathlib

import numpy as np

try:
    from _common import cell_area_km2, read_bands
except ImportError:  # pragma: no cover
    from scripts._common import cell_area_km2, read_bands

CRS_METRIC = "EPSG:5880"
LAYERS = {
    "state_paved": ("shapefiles/rodovias_estaduais_snv_poly_sirgas2000.zip",
                    "SNV_ROD_SU IN ('Pavimentada', 'Duplicada', 'Em Obra de Duplicação', 'Travessa')"),
    "state_unpaved": ("shapefiles/rodovias_estaduais_snv_poly_sirgas2000.zip",
                      "SNV_ROD_SU IN ('Implantada', 'Leito Natural', 'Em Obra de Pavimentação')"),
    "federal_paved": ("ibge/Transporte_v2015.zip!TRA_Trecho_Rodoviario_L.shp",
                      "(JURISDICAO = 'Federal' OR ADMINISTRA = 'Federal') AND REVESTIMEN IN ('Pavimentado', 'Calçado')"),
    "federal_unpaved": ("ibge/Transporte_v2015.zip!TRA_Trecho_Rodoviario_L.shp",
                        "(JURISDICAO = 'Federal' OR ADMINISTRA = 'Federal') AND REVESTIMEN IN ('Leito natural', 'Revestimento primário(solto)')"),
}
PORTS = "shapefiles/portos_antaq_poly_sirgas2000.zip"


def read_layer(cache: pathlib.Path, rel: str, where: str | None):
    import geopandas as gpd
    kw = {"where": where} if where else {}
    try:
        return gpd.read_file(f"zip://{cache / rel}", **kw).to_crs(CRS_METRIC)
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"could not read {cache / rel}: {e}") from e


def segments(gdf) -> np.ndarray:
    """Segment endpoints as an (n, 4) array: x1, y1, x2, y2."""
    out = []
    for g in gdf.geometry:
        if g is None or g.is_empty:
            continue
        for line in (g.geoms if g.geom_type.startswith("Multi") else [g]):
            c = np.asarray(line.coords)[:, :2]
            if len(c) > 1:
                out.append(np.hstack([c[:-1], c[1:]]))
    return np.vstack(out) if out else np.empty((0, 4))


def graph(seg: np.ndarray):
    """Nodes (rounded to 1 mm, as DisSCube does) and the edge list."""
    pts = np.round(np.vstack([seg[:, :2], seg[:, 2:]]), 3)
    nodes, inv = np.unique(pts, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    n = len(seg)
    return nodes, inv[:n], inv[n:]


def components(n_nodes: int, u: np.ndarray, v: np.ndarray, extra=None):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    if extra is not None:
        u, v = np.concatenate([u, extra[0]]), np.concatenate([v, extra[1]])
    g = coo_matrix((np.ones(len(u)), (u, v)), shape=(n_nodes, n_nodes))
    return connected_components(g, directed=False)


def report(label: str, nodes, u, v, ports_xy, cells_xy, tols=(0, 1, 10, 100, 500, 1000, 5000)):
    from scipy.spatial import cKDTree
    tree = cKDTree(nodes)
    print(f"\n== {label}: {len(nodes):,} nodes, {len(u):,} segments")
    pairs_cache = {}
    for tol in tols:
        extra = None
        if tol > 0:
            if tol not in pairs_cache:
                p = tree.query_pairs(tol, output_type="ndarray")
                pairs_cache[tol] = (p[:, 0], p[:, 1]) if len(p) else (np.empty(0, int), np.empty(0, int))
            extra = pairs_cache[tol]
        k, lab = components(len(nodes), u, v, extra)
        sizes = np.bincount(lab)
        _, pnode = tree.query(ports_xy)
        port_comps = set(lab[pnode].tolist())
        _, cnode = tree.query(cells_xy)
        served = np.isin(lab[cnode], list(port_comps)).mean()
        print(f"  join endpoints closer than {tol:>5} m: {k:>7,} pieces, largest has {sizes.max() / len(nodes):5.1%} of the nodes; "
              f"{len(port_comps)} of {len(ports_xy)} ports sit in {len(port_comps)} piece(s); cells served: {served:6.1%}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cellspace", required=True, help="the cell space exported by DisSCube (GeoTIFF)")
    ap.add_argument("--cache", default=str(pathlib.Path.home() / ".cache" / "disscube" / "raw"))
    a = ap.parse_args()
    cache = pathlib.Path(a.cache)

    bands, transform, crs = read_bands(a.cellspace)
    mask = np.nan_to_num(bands["mask"]) > 0
    rows, cols = np.nonzero(mask)
    xs, ys = transform * (cols + 0.5, rows + 0.5)
    from pyproj import Transformer
    cx, cy = Transformer.from_crs(crs, CRS_METRIC, always_xy=True).transform(xs, ys)
    cells_xy = np.column_stack([cx, cy])
    nan_now = np.isnan(bands["e_connport"][mask])
    print(f"cells in the mask: {mask.sum():,} ({cell_area_km2(transform):.1f} km2 each); "
          f"e_connport is NaN in {nan_now.sum():,} ({nan_now.mean():.1%})")

    ports = read_layer(cache, PORTS, None)
    ports_xy = np.array([(g.centroid.x, g.centroid.y) for g in ports.geometry if g is not None and not g.is_empty])
    print(f"ports: {len(ports_xy)}")

    segs = {k: segments(read_layer(cache, rel, where)) for k, (rel, where) in LAYERS.items()}
    for k, s in segs.items():
        print(f"  layer {k}: {len(s):,} segments")
    sets = {
        "federal (IBGE BC250)": ["federal_paved", "federal_unpaved"],
        "state (SNV)": ["state_paved", "state_unpaved"],
        "all_roads (state + federal, as in sources.toml)": list(LAYERS),
    }
    for label, ks in sets.items():
        seg = np.vstack([segs[k] for k in ks if len(segs[k])])
        nodes, u, v = graph(seg)
        report(label, nodes, u, v, ports_xy, cells_xy)


if __name__ == "__main__":
    main()
