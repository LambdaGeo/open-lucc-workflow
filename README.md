# open-lucc-workflow

<p align="center">
  <img src="docs/graphical_abstract.png" width="525"
       alt="Four stages of the workflow: references regenerated from TerraME and LuccME in a Docker image; the DisSCube spatial benchmark against TerraME Fill; the disslucc dynamic benchmark against LuccME runs; and the make full run over Brazil on the 10.56 and 5.28 km grids, a Python-only run that is not compared with TerraME.">
</p>

*Overview. Stages 1 to 3 are the references and the two benchmarks, each of which can be repeated on your own machine
(the references in a container, the benchmarks with `pip` and `make`); stage 4, `make full`, runs the workflow over Brazil
on top of the components they verify. The maps in stage 4 are a verification run, not a land-use projection.*

Companion repository of the Technical Note (Big Earth Data): an end-to-end, open and traceable
land-use-change workflow in Python (TerraME/LuccME-style), from open data to the allocated maps.
The results cited by the note are those of the tag `v1.0.0`.

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

## Windows
The workflow is developed and tested on Linux. On Windows, use **WSL2** (Ubuntu), which gives the same
environment, and keep the repository inside the Linux file system (`~/`), not under `/mnt/c`:
```
wsl --install -d Ubuntu     # PowerShell as administrator; restart when asked
# then, in the Ubuntu terminal:
sudo apt update && sudo apt install -y make git python3-venv
git clone https://github.com/LambdaGeo/open-lucc-workflow && cd open-lucc-workflow
make env && make small
```
For `make full` give WSL2 enough memory (the 5.28 km model run is the heavy step): create
`%UserProfile%\.wslconfig` with `[wsl2]` and `memory=8GB`, then run `wsl --shutdown`.

Native Windows (PowerShell or cmd) is **not supported**: the `Makefile` calls POSIX shell commands and the
virtual environment is looked up in `.venv/bin`. The repository sets `eol=lf` in `.gitattributes`, so a
checkout on Windows does not change the line endings, and with them the SHA-256, of the declared files.
Outputs were compared byte for byte only between Linux machines; on another operating system, compare
within the numerical tolerance of `acceptance.toml`.

## Status
`make small` and `make full` have been run (Linux, Python 3.12.3). The results of `v1.0.0`, with the hashes of the input
rasters and of the outputs, are in `docs/VERSIONS.md`.
