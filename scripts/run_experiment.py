#!/usr/bin/env python
"""Run the verification model on one cell space and record time and peak memory.

    python scripts/run_experiment.py --cellspace data/cellspace_5k.tif --label bdc_5k

Writes runs/<label>/: demand.csv, the model output and its experiment record (written by the
dissmodel executor), and metrics.json (what scripts/check_run.py and scripts/report.py read).
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import platform
import resource
import shutil
import subprocess
import sys
import time
from importlib.metadata import version

try:
    from _common import MODEL_TOML, ROOT, SCENARIO_TOML, cell_area_km2, class_areas_km2, load_toml, read_bands, sha256_file, write_json
    from make_demand import demand_table, write_csv
except ImportError:  # pragma: no cover
    from scripts._common import (
        MODEL_TOML,
        ROOT,
        SCENARIO_TOML,
        cell_area_km2,
        class_areas_km2,
        load_toml,
        read_bands,
        sha256_file,
        write_json,
    )
    from scripts.make_demand import demand_table, write_csv

import numpy as np


def peak_rss_mb() -> float:
    """Peak resident memory of the child processes so far (Linux: KiB, macOS: bytes)."""
    peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return peak / (1024 * 1024) if platform.system() == "Darwin" else peak / 1024


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cellspace", required=True, type=pathlib.Path)
    ap.add_argument("--label", required=True)
    ap.add_argument("--runs-dir", type=pathlib.Path, default=ROOT / "runs")
    a = ap.parse_args()

    out_dir = a.runs_dir / a.label
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    bands, transform, _ = read_bands(a.cellspace)
    scenario = load_toml(SCENARIO_TOML)["scenario"]
    area_km2 = cell_area_km2(transform)
    rows = demand_table(class_areas_km2(bands, transform), {"scenario": scenario})
    write_csv(rows, out_dir / "demand.csv")

    cmd = [
        sys.executable, "-m", "disslucc.executors.saturation", "run",
        "--toml", str(MODEL_TOML),
        "--input", str(a.cellspace),
        "--param", f"demand_csv={out_dir / 'demand.csv'}",
        "--param", f"cell_area={area_km2}",
        "--param", f"n_steps={int(scenario['n_steps'])}",
        "--param", f"max_difference={scenario['max_difference_km2']}",
        "--output", str(out_dir / "lucc.tif"),
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    wall = time.perf_counter() - t0
    (out_dir / "executor.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        sys.exit(f"executor failed (see {out_dir / 'executor.log'}):\n{(proc.stdout + proc.stderr)[-1500:]}")

    records = sorted(glob.glob(str(out_dir / "*.record.json")))
    if len(records) != 1:
        sys.exit(f"expected one experiment record in {out_dir}, found {records}")
    record = json.loads(pathlib.Path(records[0]).read_text(encoding="utf-8"))
    m = record["metrics"]
    mask = np.nan_to_num(bands["mask"]) > 0

    metrics = {
        "label": a.label,
        "cellspace": str(a.cellspace),
        "cellspace_sha256": sha256_file(a.cellspace),
        "shape": list(mask.shape),
        "cells_in_mask": int(mask.sum()),
        "cell_area_km2": area_km2,
        "n_steps": int(scenario["n_steps"]),
        "max_difference_km2": float(scenario["max_difference_km2"]),
        "wall_seconds": round(wall, 3),
        "run_seconds": m.get("seconds"),
        "peak_rss_mb": round(peak_rss_mb(), 1),
        "iterations_per_step": m["iterations_per_step"],
        "max_error_per_step": m["max_error_per_step"],
        "final_areas_km2": {k.removeprefix("final_").removesuffix("_area"): v for k, v in m.items()
                            if k.startswith("final_") and k.endswith("_area")},
        "demand_last_year_km2": rows[-1],
        "record": records[0],
        "output": record["output_path"],
        "output_sha256": record["artifacts"]["output"],
        "experiment_id": record["experiment_id"],
        "versions": {p: version(p) for p in ("disscube", "disslucc", "dissmodel")},
        "python": platform.python_version(),
        "host": f"{platform.system()} {platform.machine()}",
    }
    write_json(out_dir / "metrics.json", metrics)
    print(f"{a.label}: {metrics['cells_in_mask']:,} cells, {wall:.1f} s, peak {metrics['peak_rss_mb']} MB, "
          f"max iterations {max(metrics['iterations_per_step'])}")


if __name__ == "__main__":
    main()
