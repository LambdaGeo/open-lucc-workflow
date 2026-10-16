# Versions and identifiers (manuscript, section 3)

| Component | Version | DOI |
|---|---|---|
| open-lucc-workflow | 1.1.0 | 10.5281/zenodo.23415814 (1.0.0: 10.5281/zenodo.23287890) |
| dissmodel | 0.6.6 | 10.5281/zenodo.23246106 (confirm version vs concept DOI) |
| disscube | 0.6.0 | 10.5281/zenodo.23365403 (0.5.0: 10.5281/zenodo.23172450) |
| disslucc | 0.5.0 | 10.5281/zenodo.23219338 |
| disslucc-benchmark | 0.2.2 | 10.5281/zenodo.23224097 (the catalog of the labs was corrected afterwards, commit 0baba4d) |
| terrame-docker | 0.4.2 | 10.5281/zenodo.23160784 |
| luccme-goldens | 1.1.0 (pinned by the benchmark; 1.2.0 is documentation only) | 10.5281/zenodo.23161342 (1.2.0: 10.5281/zenodo.23366244) |
| disscube-benchmark | 1.1.0 | 10.5281/zenodo.23366475 (the causes of the differences in section 5 of the README were completed afterwards, commit c023ed6) |
| disscube-grids | 1.0.0 | 10.5281/zenodo.23368071 |
| brmangue-dissmodel | 0.5.0 | 10.5281/zenodo.23240385 |
| brmangue-terrame | 0.1.0 | 10.5281/zenodo.23240318 |

Environment of the reported run: `reported/v1.1.0/requirements.lock` lists the exact version of every package installed in the
virtual environment (`pip freeze`), and `reported/v1.1.0/machine.txt` describes the machine. The lock file has no hashes: the
SHA-256 of the PyPI wheels is not recorded, so the pins fix versions, not files.

## Reported results (v1.1.0)
Run of `make full` on one Linux desktop (Python 3.12.3, 6 h 31 min of wall-clock time in total, from a clean start),
from the commit `57424aa8464efdb9c605aff0932060c6b93ca39b`. The tag `v1.1.0` differs from that commit only in
documentation and in the record of this run (`reported/v1.1.0/`, this file, the README); no code, parameter or
acceptance criterion changes between them. An earlier attempt was interrupted before it finished; the reported run is a
complete one.

| Grid | Cells | Input raster SHA-256 | Output SHA-256 | Time | Peak memory |
|---|---:|---|---|---:|---:|
| 10.56 km | 77,238 | `6cf3e5224c1849f31f069a535e659417817e73e9390dd8b7aca36bc424aa0ab0` | `f060cc08686e5cb7c2f265205d8e2f629aee8f9f6a9b8a06073ead3e3a926224` | 2,169.6 s | 384 MB |
| 5.28 km | 307,419 | `2285bb15fb847234ebb0e32340af5ee26190a39fc361dfa57f5468ae485f1897` | `895a11e8e3a49ea12fb288a044d42248c071f2d35259b5eabf59c24ac6f6d825` | 10,383.4 s | 794 MB |

The repeat run at 5.28 km (10,614.8 s, 794 MB) gave the same output hash, the same iterations in the 14 years and the same
class areas. Acceptance (`scripts/check_run.py`, criteria of `acceptance.toml`): demand met (largest error 999.75 km2,
tolerance 1,000 km2; at most 1,276 iterations in a year, limit 3,000), repeat identical (difference 0.0, same bytes), area per
class against the coarser grid 0.0021 of the mapped area (limit 0.005). The peak memory is that of the model run; the grid
build peaks near 1 GB (`reported/v1.1.0/grid5k.time.log`), and the whole `make full` process tree reached 1.05 GB
(`reported/v1.1.0/full.time.log`). The record is in `reported/v1.1.0/`; `make check-reported` audits it in seconds.

## Earlier run (v1.0.0, superseded)
The first run of the workflow (an earlier version of the verification model), from the commit `55c41cd`; its record is in
`reported/v1.0.0/`. Its input hashes were `79664844…` (10.56 km) and `327d4cf3…` (5.28 km); it is kept for history and is not
the result the note reports.

## Open decisions
1. ~~Land-use product and how it is obtained~~ Done: the LuccME-BR land-cover netCDF, direct download from Zenodo record 5123560 (`pipeline/grid/sources.toml`).
2. Grids of the reported runs: 5.28 km (20×20 cells per BDC_SM tile) and 10.56 km (10×10, an exact 2×2 aggregation); memory test at 5.28 km. 25 km is not tile-aligned and is kept only for the transport-cost case of E2.
3. ~~Freeze `acceptance.toml`~~ Done: frozen on 2026-10-09 (`frozen_commit`), release tag `v1.1.0` (criteria unchanged; `v1.0.0` was the first run).
4. Confirm DOIs marked above.
5. `e_connport` uses the TerraME GPM road network (`br_roads_5880`) and 14 ports (`br_ports_5880`), cost column `custo_ajus`, the same data as the disscube-benchmark connectivity case. Licence of these files: see `docs/DATA.md`.

## Before submission
- Remove `scripts/_run_with_progress.py` (provisional wrapper that prints one progress line per year). Add the equivalent `logging` record per year to disslucc (iterations, maximum error, time), release it, pin the new version here and in `requirements.txt`, and make `scripts/run_experiment.py` call `python -m disslucc.executors.saturation` again. Re-run the reported runs with the pinned version (results do not change; the record does).

- **DisSCube: `percentage` for vector sources (pending; optional before submission, otherwise after).** In DisSCube 0.5.0 and 0.6.0 the class
  operators (`percentage`, `majority`, `minority`) ignore the attributes of a vector source, so `ag_apti_B` and `ag_apti_MB` do not hold
  aptitude classes (docs/PARAMETERIZATION.md, section 8) and the verification model runs without the aptitude driver that LuccME-BR has.
  What is missing: an option to say which attribute holds the class, and a `percentage` that returns the share of the cell covered by
  the polygons of that class (the intersection of the `area` operator, restricted to the selected polygons). Proposed form:
  `operator = "percentage"`, `params = { attribute = "FERTILID2", equals = "Baixa" }` (the aptitude shapefile has text attributes, so
  `class_code` as an integer is not enough). Still needed from the author: which attribute and classes LuccME-BR uses for B and MB
  (S2 of Bezerra et al., 2022 calls them "low" and "medium low"). If implemented: release a new DisSCube, pin it in the workflow,
  restore the three `ag_apti_MB` weights (or the S2 form) in `model/parameter_weights.toml`, regenerate the parameters, and **repeat every
  reported run** (10.56 and 5.28 km, repeat), since the hashes change. If not implemented before submission, keep limitation 12 of the
  manuscript and state that the model has no aptitude driver. Workaround that stays inside the declared chain: rasterize the shapefile
  by attribute (`gdal_rasterize -a`) into a class raster declared as a source, where `percentage` already works.

## Note on DisSCube 0.6.0
The input rasters of the `v1.1.0` run were built with the released DisSCube 0.6.0 (PyPI): the `versions` entry of each
`metrics.json` in `reported/v1.1.0/` reads `disscube 0.6.0`, `disslucc 0.5.0`, `dissmodel 0.6.6`.
