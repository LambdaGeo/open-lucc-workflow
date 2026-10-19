# Scripts

`make` calls most of these scripts; a reviewer does not run them by hand. A reviewer uses seven of them, through
`make check-reported` (1 command), `make reproduce-10k` (10 commands) and `make small` (11 commands); `make full` runs 20.
The packages (DisSCube, DisSLUCC) have their own commands: see "Using the packages without `make`" in the main README.

| Group | Script | What it does | Called by |
|---|---|---|---|
| 1. Reviewer path (levels 0 to 2) | `render_pipeline.py` | Writes the `[grid]` block of the DisSCube pipeline for one grid of the Brazil Data Cube | `make grid-10k`, `grid-5k` |
| | `complete_input.py` | Restricts the mask to the cells where every land use and driver is defined | `make grid-*` |
| | `check_input.py` | Sanity checks on an input raster (bands, CRS, mask) before any model run | `make grid-*`, `small` |
| | `run_experiment.py` | Runs the verification model on one input raster and records time and peak memory (`metrics.json`) | `make run-*`, `reproduce-10k`, `small`, `full` |
| | `verify_record.py` | Verifies an experiment record from a clean clone: hashes, versions and status | `make verify` and the targets above |
| | `check_expected.py` | Compares one run with the reported run of the same grid (the reviewer's quick check, prints OK or DIFFERS) | `make reproduce-10k` |
| | `check_reported.py` | Checks the reported runs against `acceptance.toml` from their recorded metrics, without running the model | `make check-reported` |
| 2. Smoke test and acceptance | `synth_input.py` | Synthetic input raster with the bands of the Brazil input raster, no download | `make small` |
| | `check_run.py` | Acceptance checks of `acceptance.toml` on one run, its repeat and a coarser run | `make small`, `full` |
| | `report.py` | Writes `results/table4.md` from `runs/*/metrics.json` and the checks | `make report` |
| 3. Numbers and figures of the note | `manuscript_numbers.py` | Numbers quoted in the note, computed from one run (nothing is fitted or edited) | `make numbers` |
| | `make_figures.py` | Driver maps and the figure of the verification run | by hand |
| 4. Parameters and demand | `make_parameters.py` | Writes `model/verification_model.toml` from `model/parameter_weights.toml` and the 10.56 km input raster | by hand (the output is in the repository) |
| | `make_demand.py` | Yearly demand per class for the scenario, from the input raster; its function is also used by `run_experiment.py` | `run_experiment.py`, by hand |
| 5. External check | `external_check.sh` | Repeats levels 0 to 2 on another computer and collects logs, machine description and package versions | by hand; no reported result uses it |
| | `compare_rasters.py` | Compares two GeoTIFF files by their decoded values, band by band | by hand; no reported result uses it |
| 6. Helpers and diagnostics of development | `_common.py` | Shared helpers: model TOML, bands of the input raster, areas | imported by other scripts |
| | `_run_with_progress.py` | Runs the DisSLUCC saturation executor with one progress line per year; provisional | `run_experiment.py` |
| | `diagnose_allocation.py` | Prints, per iteration, each class's area against its demand when the allocation does not converge | by hand |
| | `diagnose_network.py` | Looks at the road graph when `network_cost` leaves cells without a value | by hand |
| | `potential_balance.py` | Reports whether the net potential of the model is balanced and suggests a constant | by hand |

No Makefile target calls the scripts that are marked "by hand"; the diagnostics remain as a record of how problems were investigated.
