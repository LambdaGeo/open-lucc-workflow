# Data sources of the input raster

Declared in `pipeline/grid/sources.toml`, each with its SHA-256. This file records where each layer comes from, its
licence as far as it was checked, and what to cite. Dates are the access dates of the checks (13 Oct 2026; the IBGE download page, 15 Oct 2026). Nothing here is legal advice.

| Variable | Layer | Origin | Licence / terms | Notes |
|---|---|---|---|---|
| land cover (7 classes, 2000) | LuccME-BR land cover, netCDF | Zenodo record 5123560 (Bezerra et al., 2021), version v1.0.0 | CC BY 4.0 (stated on the record) | the original file; a later version (v2, 10.5281/zenodo.10611737) is not used |
| `c_ucspas` | Conservation units, protection-integral group, created up to 2016 | MMA, CNUC `shp_cnuc_2024_02.zip` (dados.mma.gov.br) | CC BY (stated on the dataset page) | version 2024-02, filtered by `cria_ano`; unmodified copy in the provisional data release (`data-preview`), SHA-256 pinned |
| `c_ucspas` | Indigenous lands, phase `Regularizada` | FUNAI, WFS layer `tis_poligonais` | "may be reproduced if the source is cited" (FUNAI page); the site footer says CC BY-ND 3.0 | live service, updated monthly: unmodified copy in the provisional data release (`data-preview`), SHA-256 pinned; use unmodified |
| `c_nusett` | Rural settlements (extractive modalities excluded by name prefix) | INCRA, Acervo Fundiário, "Assentamento Brasil" | not stated; asked of INCRA, no reply yet | unmodified copy in the provisional data release (`data-preview`), SHA-256 pinned, to be withdrawn on the agency's request; invalid polygons after reprojection are repaired by DisSCube (branch `fix/repair-invalid-geometries`) |
| `e_cities` | Municipal seats (points), 2016 | IBGE BC250, via the ANA catalogue (`GEOFT_CIDADE_2016`) | ANA record: "access is free"; no IBGE licence or terms of use found | all 5,570 seats; downloaded directly from the original address, not redistributed |
| `e_railway` | Railway sections, PNV 2016 | DNIT, via the ANA catalogue (`GEOFT_TRECHO_FERROVIARIO`) | not stated in the record | the layer has less planned network than the earlier INPE layer |
| `e_proads`, `e_uroads` | State road sections (SNV) | DNIT, via the ANA catalogue (`GEOFT_TRECHO_RODOVIARIO_ESTADUAL`) | not stated in the record | same 15,589 sections as the earlier INPE layer |
| `e_proads`, `e_uroads` | Federal roads | IBGE BC250 2015 | no licence or terms of use found on the IBGE download page (read 15 Oct 2026) | downloaded directly from the original address, not redistributed |
| country border (mask) | Brazil outline, `BR_Pais_2025` | IBGE, territorial meshes | no licence or terms of use found on the IBGE download page (read 15 Oct 2026) | downloaded directly from the original address, not redistributed |
| `e_connport` | Road network (`custo_ajus` cost per segment) and 14 ports | TerraME/gpm, commit `3aa0e91498f37d1b55adbe54d5d0fda3137f251f` | LGPL-3 declared in `description.lua`; the licence file holds the GPL-3 text (inconsistent upstream) | downloaded directly from the repository, not redistributed |

The model weights that use each variable are in `model/parameter_weights.toml`.

`e_cities` is the distance to the nearest municipal seat. It replaces the `e_urban10` of earlier versions of this repository, a name that came from a layer of urban centres of a size class, which this layer is not. The earlier input raster also had `e_rivers` and `e_urban100`; they were dropped because no weight of the verification model uses them.
No weight of the verification model uses them, so they were removed from the pipeline and from the raster.
