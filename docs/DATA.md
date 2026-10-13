# Data sources of the input raster

Declared in `pipeline/grid/sources.toml`, each with its SHA-256. This file records where each layer comes from, its
licence as far as it was checked, and what to cite. Dates are the access dates of the checks (13 Oct 2026).

| Variable | Layer | Origin | Licence / terms | Notes |
|---|---|---|---|---|
| `c_ucspas` | Conservation units, protection-integral group, created up to 2016 | MMA, CNUC `shp_cnuc_2024_02.zip` (dados.mma.gov.br) | CC BY (stated on the dataset page) | version 2024-02, filtered by `cria_ano` |
| `c_ucspas` | Indigenous lands, phase `Regularizada` | FUNAI, WFS layer `tis_poligonais` | "may be reproduced if the source is cited" (FUNAI page); the site footer says CC BY-ND 3.0 | live service, updated monthly: unmodified copy in the provisional data release (`data-preview`), SHA-256 pinned; use unmodified |
| `c_nusett` | Rural settlements (extractive modalities excluded by name prefix) | INCRA, Acervo Fundiário, "Assentamento Brasil" | not stated; asked of INCRA | invalid polygons after reprojection are repaired by DisSCube (branch `fix/repair-invalid-geometries`) |
| `e_urban10` | Municipal seats (points), 2016 | IBGE BC250, via the ANA catalogue (`GEOFT_CIDADE_2016`) | ANA record: "access is free"; IBGE terms: credit "Fonte: IBGE" | all 5,570 seats |
| `e_railway` | Railway sections, PNV 2016 | DNIT, via the ANA catalogue (`GEOFT_TRECHO_FERROVIARIO`) | not stated in the record | the layer has less planned network than the earlier INPE layer |
| `e_proads`, `e_uroads` | State road sections (SNV) | DNIT, via the ANA catalogue (`GEOFT_TRECHO_RODOVIARIO_ESTADUAL`) | not stated in the record | same 15,589 sections as the earlier INPE layer |
| `e_proads`, `e_uroads` | Federal roads | IBGE BC250 2015 | IBGE terms | unchanged |

The model weights that use each variable are in `model/parameter_weights.toml`.

The earlier input raster also had `e_rivers` and `e_urban100` (INPE layers: rivers and municipalities above 100 thousand inhabitants).
No weight of the verification model uses them, so they were removed from the pipeline and from the raster.
