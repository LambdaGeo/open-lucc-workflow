import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from _common import LAND_USES, sha256_file  # noqa: E402
from make_demand import demand_table  # noqa: E402
from render_pipeline import bbox_for, render  # noqa: E402
from synth_cellspace import block_mean, landscape  # noqa: E402

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
    assert "bdc_5k" in render("bdc_5k")
