#!/usr/bin/env python
"""Write results/table4.md (manuscript Table 4) from runs/*/metrics.json and checks.json.

    python scripts/report.py
One row per run that has a '<label>_repeat' pair or a coarser partner recorded in checks.json.
"""
from __future__ import annotations

import json
import pathlib

try:
    from _common import ROOT
except ImportError:  # pragma: no cover
    from scripts._common import ROOT


def _load(p: pathlib.Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def fmt_iter(it: list[int]) -> str:
    return " ".join(str(i) for i in it)


def main() -> None:
    runs = ROOT / "runs"
    rows = []
    for d in sorted(runs.glob("*/")):
        if d.name.endswith("_repeat") or not (d / "metrics.json").exists():
            continue
        m, c = _load(d / "metrics.json"), _load(d / "checks.json")
        demand = c.get("demand_met", {})
        rep = c.get("repeat_identical")
        res = c.get("area_vs_coarser")
        rows.append(
            "| {label} | {cells:,} | {dm} | {it} | {rp} | {rs} | {t} | {mem} |".format(
                label=m["label"], cells=m["cells_in_mask"],
                dm=("yes" if demand.get("ok") else "NO") + f" (max {demand.get('max_error_km2', float('nan')):.2f} km²)" if demand else "n/a",
                it=fmt_iter(m["iterations_per_step"]),
                rp=("yes" if rep["ok"] else "NO") + (", bytes" if rep["bytes_identical"] else f", max Δ {rep['max_abs_diff']:.2g}") if rep else "n/a",
                rs=f"{res['max_class_area_diff_fraction']:.4f} of area" if res else "n/a",
                t=f"{m['wall_seconds']:.1f} s", mem=f"{m['peak_rss_mb']:.0f} MB",
            )
        )
    head = ("| Grid | Cells | Demand met | Iterations per year | Repeat run identical | Area per class vs coarser grid "
            "| Time | Peak memory |\n|---|---:|---|---|---|---|---:|---:|")
    out = ROOT / "results" / "table4.md"
    out.parent.mkdir(exist_ok=True)
    # the checks file is written next to the fine-grid run only; look for it in every run folder
    flags = [_load(c).get("acceptance_frozen") for c in sorted(runs.glob("*/checks.json"))] if runs.exists() else []
    frozen = bool(flags) and all(flags)
    note = "" if frozen else "\n\n> Provisional: `acceptance.toml` is not frozen.\n"
    out.write_text(head + "\n" + "\n".join(rows) + "\n" + note, encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
