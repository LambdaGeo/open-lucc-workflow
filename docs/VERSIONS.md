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
1. Land-use product and how it is obtained (STAC vs direct download) for `pipeline/cellspace/sources.toml`.
2. Grids of the reported runs: 5.28 km (20×20 cells per BDC_SM tile) and 10.56 km (10×10, an exact 2×2 aggregation); memory test at 5.28 km. 25 km is not tile-aligned and is kept only for the transport-cost case of E2.
3. Freeze `acceptance.toml` (`frozen = true`, tag the commit, cite the tag) before the reported runs.
4. Confirm DOIs marked above.
