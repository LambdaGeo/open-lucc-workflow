import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from _common import LAND_USES, sha256_file  # noqa: E402
from make_demand import demand_table  # noqa: E402
from render_pipeline import bbox_for, render  # noqa: E402
from synth_input import block_mean, landscape  # noqa: E402

SCENARIO = {"scenario": {"n_steps": 5, "forest_loss_pct_per_year": 0.5,
                         "gain_shares": {"pasture_management": 0.5, "agricultural": 0.5}}}


def test_demand_conserves_total():
    initial = {lu: 100.0 for lu in LAND_USES}
    rows = demand_table(initial, SCENARIO)
    assert len(rows) == 5
    assert rows[0] == initial
    totals = {round(sum(r.values()), 6) for r in rows}
    assert totals == {round(sum(initial.values()), 6)}
    assert rows[-1]["forest_vegetation"] < initial["forest_vegetation"]


def test_demand_rejects_bad_shares():
    bad = {"scenario": {**SCENARIO["scenario"], "gain_shares": {"agricultural": 0.4}}}
    with pytest.raises(ValueError):
        demand_table({lu: 1.0 for lu in LAND_USES}, bad)


def test_landscape_is_seeded_and_block_mean_conserves():
    a, b = landscape(12, 1), landscape(12, 1)
    for k in a:
        assert np.array_equal(a[k], b[k])
    x = np.arange(144, dtype=float).reshape(12, 12)
    assert block_mean(x, 3).shape == (4, 4)
    assert block_mean(x, 3).mean() == pytest.approx(x.mean())


def test_sha256(tmp_path):
    f = tmp_path / "a"
    f.write_bytes(b"abc")
    assert sha256_file(f).startswith("ba7816bf")


def test_bbox_on_tile_grid():
    x0, y0, x1, y1 = bbox_for(5280.0)
    assert (x1 - x0) % 5280.0 == 0 and (y1 - y0) % 5280.0 == 0


def test_render_sets_grid():
    assert "br_5km" in render("br_5km")


def test_complete_input_removes_incomplete_cells(tmp_path):
    import rasterio
    from complete_input import complete
    from synth_input import build

    src = tmp_path / "s.tif"
    build(src, n=12)
    with rasterio.open(src) as s:
        profile = s.profile
        data = s.read()
        names = [s.tags(i).get("name") or s.descriptions[i - 1] for i in range(1, s.count + 1)]
    for k in range(7):
        data[k, :1, :] = profile["nodata"]
    with rasterio.open(tmp_path / "raw.tif", "w", **profile) as o:
        for i, n in enumerate(names, 1):
            o.write(data[i - 1], i)
            o.update_tags(i, name=n)
    rep = complete(str(tmp_path / "raw.tif"), str(tmp_path / "out.tif"))
    assert rep["cells_removed"] == 12 and rep["cells_kept"] == 132
    assert rep["cells_with_no_land_use_at_all"] == 12


def test_complete_input_refuses_a_large_removal(tmp_path):
    import subprocess

    import rasterio
    from synth_input import build

    src = tmp_path / "s.tif"
    build(src, n=12)
    with rasterio.open(src) as s:
        profile = s.profile
        data = s.read()
        names = [s.tags(i).get("name") or s.descriptions[i - 1] for i in range(1, s.count + 1)]
    k = names.index("e_connport")
    data[k, :6, :] = profile["nodata"]
    with rasterio.open(tmp_path / "raw.tif", "w", **profile) as o:
        for i, n in enumerate(names, 1):
            o.write(data[i - 1], i)
            o.update_tags(i, name=n)
    script = str(pathlib.Path(__file__).resolve().parents[1] / "scripts" / "complete_input.py")
    r = subprocess.run([sys.executable, script, str(tmp_path / "raw.tif"), str(tmp_path / "out.tif")], capture_output=True, text=True)
    assert r.returncode != 0 and "would be removed" in r.stderr
    assert not (tmp_path / "out.tif").exists()


def test_complete_input_removes_zero_sum_cells(tmp_path):
    import rasterio
    from complete_input import complete
    from synth_input import build

    src = tmp_path / "s.tif"
    build(src, n=12)
    with rasterio.open(src) as s:
        profile = s.profile
        data = s.read()
        names = [s.tags(i).get("name") or s.descriptions[i - 1] for i in range(1, s.count + 1)]
    for k in range(7):
        data[k, 0, :3] = 0.0
    with rasterio.open(tmp_path / "raw.tif", "w", **profile) as o:
        for i, n in enumerate(names, 1):
            o.write(data[i - 1], i)
            o.update_tags(i, name=n)
    rep = complete(str(tmp_path / "raw.tif"), str(tmp_path / "out.tif"))
    assert rep["cells_with_all_land_uses_zero"] == 3 and rep["cells_removed"] == 3


def test_complete_input_partial_coverage(tmp_path):
    import numpy as np
    import rasterio
    from complete_input import complete
    from _common import LAND_USES, read_bands
    from synth_input import build

    src = tmp_path / "s.tif"
    build(src, n=12)
    with rasterio.open(src) as s:
        profile = s.profile
        data = s.read()
        names = [s.tags(i).get("name") or s.descriptions[i - 1] for i in range(1, s.count + 1)]
    for lu in LAND_USES:
        k = names.index(lu)
        data[k, 0, :2] *= 0.2   # sum 0.2: below coverage
        data[k, 1, :3] *= 0.8   # sum 0.8: partly covered
    with rasterio.open(tmp_path / "raw.tif", "w", **profile) as o:
        for i, n in enumerate(names, 1):
            o.write(data[i - 1], i)
            o.update_tags(i, name=n)
    for mode in ("renormalize", "others"):
        rep = complete(str(tmp_path / "raw.tif"), str(tmp_path / f"{mode}.tif"), 0.5, mode)
        assert rep["cells_below_min_coverage"] == 2 and rep["cells_partly_covered_adjusted"] == 3
        b, _, _ = read_bands(str(tmp_path / f"{mode}.tif"))
        m = np.nan_to_num(b["mask"]) > 0
        assert abs(np.nansum([b[l] for l in LAND_USES], axis=0)[m] - 1).max() < 1e-4
