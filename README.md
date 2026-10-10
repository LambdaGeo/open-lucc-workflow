# open-lucc-workflow

Companion repository of the Technical Note (Big Earth Data): an end-to-end, open and traceable
land-use-change workflow in Python (TerraME/LuccME-style), from open data to the allocated maps.
It replaces the earlier two-repository plan (disscube-recipes + luccmebr-reconstruction).

**Purpose.** This repository does not aim to reproduce LuccME-BR. It demonstrates a *process*: how a
land-use-change experiment goes from open data to allocated maps in a way that, once built, anyone
can rerun and check (pinned versions, hashed sources, fixed acceptance criteria, experiment records).
The reproducibility is of the workflow, not of a published model's results.
The approach is open on all three sides: open data (public, hashed sources), open source (every
component and script is public and versioned) and open science (criteria fixed in advance, records
anyone can verify).

> The model here is a **verification model** with declared, synthetic coefficients, used only to
> exercise the workflow. Its maps are not land-use projections and not LuccME-BR outputs.

## Stages
1. **Input raster** — `disscube` catalogs open sources (SHA-256 checked) and derives the named bands
   (`pipeline/grid/`), on the Brazil Data Cube grid (5.28 km and 10.56 km).
2. **Check** — `scripts/check_input.py` validates bands, CRS and mask.
3. **Model** — `disslucc` saturation executor with `model/verification_model.toml` and
   `model/scenario.toml`; demand is derived from the input raster (`scripts/make_demand.py`).
4. **Verify** — `scripts/check_run.py` against `acceptance.toml` (demand met, identical repeat run,
   class areas agree across resolutions); `scripts/verify_record.py` checks the experiment record
   (hashes, pinned versions). `make report` writes `results/table4.md`.

## Use
```
make env            # .venv with pinned packages
make small          # offline, synthetic input raster (~1 min); what CI runs
make grids          # only the two grids (10.56 and 5.28 km) from open data; no model run
make grid-10k       # or one at a time: data/br_10km.tif (~1 min)
make grid-5k        # data/br_5km.tif (~3 min, peak ~1 GB RAM)
make run-10k        # grid + model at 10.56 km only (runs/br_10km)
make run-5k         # grid + model at 5.28 km only (runs/br_5km)
make full           # grids + model runs + checks + report (network; the 5.28 km model run is the heavy step)
make test lint
```
`make full` refuses to report unless `acceptance.toml` is frozen. Open decisions and pinned
versions/DOIs: `docs/VERSIONS.md`.

## Status
`make small` is tested. `make full` (real sources, IBGE downloads) has **not** been run yet.
