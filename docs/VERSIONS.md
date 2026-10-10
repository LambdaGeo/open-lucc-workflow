# Versions and identifiers (manuscript, section 3)

| Component | Version | DOI |
|---|---|---|
| dissmodel | 0.6.6 | 10.5281/zenodo.23246106 (confirm version vs concept DOI) |
| disscube | 0.5.0 | 10.5281/zenodo.23172450 |
| disslucc | 0.5.0 | 10.5281/zenodo.23219338 |
| disslucc-benchmark | 0.2.2 | 10.5281/zenodo.23224097 |
| terrame-docker | 0.4.2 | 10.5281/zenodo.23160784 |
| luccme-goldens | 1.1.0 | 10.5281/zenodo.23161342 (unverified) |
| brmangue-dissmodel | 0.5.0 | 10.5281/zenodo.23240385 |
| brmangue-terrame | 0.1.0 | 10.5281/zenodo.23240318 |

Wheel SHA-256: run `make lock` on the machine that produces the reported results and paste
`pip hash`/`requirements.lock` output here. (Not filled in: the hashes belong to the run that is reported.)

## Open decisions
1. Land-use product and how it is obtained (STAC vs direct download) for `pipeline/grid/sources.toml`.
2. Grids of the reported runs: 5.28 km (20×20 cells per BDC_SM tile) and 10.56 km (10×10, an exact 2×2 aggregation); memory test at 5.28 km. 25 km is not tile-aligned and is kept only for the transport-cost case of E2.
3. Freeze `acceptance.toml` (`frozen = true`, tag the commit, cite the tag) before the reported runs.
4. Confirm DOIs marked above.
4. `e_connport` uses the TerraME GPM road network (`br_roads_5880`) and 14 ports (`br_ports_5880`), cost column `custo_ajus`, the same data as the disscube-benchmark connectivity case. Licence of these files to be confirmed for Table 4a.

## Before submission
- Remove `scripts/_run_with_progress.py` (provisional wrapper that prints one progress line per year). Add the equivalent `logging` record per year to disslucc (iterations, maximum error, time), release it, pin the new version here and in `requirements.txt`, and make `scripts/run_experiment.py` call `python -m disslucc.executors.saturation` again. Re-run the reported runs with the pinned version (results do not change; the record does).

- **DisSCube: `percentage` for vector sources (pending; optional before submission, otherwise after).** In DisSCube 0.5.0 the class
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
