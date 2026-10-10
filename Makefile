# Reproduce the demonstration of the note, stage by stage.
#
#   make env            create .venv and install the pinned packages
#   make small          offline smoke test on a synthetic input raster (minutes; what CI runs)
#   make grids          build both cell-space grids from open data (no model run)
#   make grid-10k       build only the 10.56 km grid (~77 k cells; ~1 min)
#   make grid-5k        build only the 5.28 km grid (~307 k cells; ~3 min, peak ~1 GB RAM)
#   make run-10k        grid + model on the 10.56 km grid only (~30 min); writes runs/br_10km
#   make run-5k         grid + model on the 5.28 km grid only (~2.5 h); writes runs/br_5km
#   make full           Brazil, from open data (needs network; the model run at 5.28 km is the heavy step, memory not yet measured)
#   make verify         verify the experiment records of every run (hashes, versions)
#   make report         write results/table4.md from runs/*/metrics.json
#   make test           unit tests of the scripts
#
# Variables: PY (python), SYN_SIZE (fine synthetic grid, default 60 x 60 cells of 5.28 km),
#            SYN_BLOCK (coarse grid = SYN_BLOCK x SYN_BLOCK fine cells, default 2).
PY        ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
DISSCUBE  ?= $(if $(wildcard .venv/bin/disscube),.venv/bin/disscube,disscube)
SYN_SIZE  ?= 60
SYN_BLOCK ?= 2

.PHONY: env small grids grid-10k grid-5k run-10k run-5k full verify report test lint lock clean help

help:
	@sed -n '2,17p' Makefile

env:
	python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements-dev.txt

# ── small: synthetic, no downloads ───────────────────────────────────────────
small: data/synthetic_fine.tif data/synthetic_coarse.tif
	$(PY) scripts/check_input.py data/synthetic_fine.tif
	$(PY) scripts/check_input.py data/synthetic_coarse.tif
	$(PY) scripts/run_experiment.py --input data/synthetic_fine.tif   --label synthetic_fine
	$(PY) scripts/run_experiment.py --input data/synthetic_fine.tif   --label synthetic_fine_repeat
	$(PY) scripts/run_experiment.py --input data/synthetic_coarse.tif --label synthetic_coarse
	$(PY) scripts/check_run.py --run runs/synthetic_fine --repeat runs/synthetic_fine_repeat --coarse runs/synthetic_coarse
	$(MAKE) verify report

data/synthetic_fine.tif:
	$(PY) scripts/synth_input.py --out $@ --size $(SYN_SIZE)

data/synthetic_coarse.tif:
	$(PY) scripts/synth_input.py --out $@ --size $(SYN_SIZE) --block $(SYN_BLOCK)

# ── full: Brazil on the Brazil Data Cube grid ────────────────────────────────
# Stage 1-2: DisSCube catalogs the sources (fetched and checked by SHA-256) and derives the variables.
# Stage 3-4: the model, twice on the fine grid (determinism) and once on the coarse grid.
# acceptance.toml must be frozen (see the file) before the numbers are reported.
FINE   = br_5km
COARSE = br_10km

build/pipelines/br_%.toml: pipeline/grid/derivations.template.toml
	$(PY) scripts/render_pipeline.py --name br_$* --out $@

data/cube_br_%/.cataloged: pipeline/grid/sources.toml
	$(DISSCUBE) fetch pipeline/grid/sources.toml
	$(DISSCUBE) run pipeline/grid/sources.toml --workspace data/cube_br_$*
	touch $@

# keep the exported input raster even when the next step refuses it, so it can be inspected
.PRECIOUS: data/raw_br_%.tif

data/raw_br_%.tif: build/pipelines/br_%.toml data/cube_br_%/.cataloged
	$(DISSCUBE) run build/pipelines/br_$*.toml --workspace data/cube_br_$*
	mkdir -p data && $(DISSCUBE) export build/pipelines/br_$*.toml --workspace data/cube_br_$* --output $@

# cells without a complete set of bands (coast, borders, islands) leave the mask; see the .report.json
data/br_%.tif: data/raw_br_%.tif
	$(PY) scripts/complete_input.py $< $@
	$(PY) scripts/check_input.py $@

# build the grids only (stages 1-2 and the check), without running the model
grids: grid-10k grid-5k
grid-10k: data/br_10km.tif
grid-5k: data/br_5km.tif

# one resolution at a time (no acceptance check: that needs the three runs of `make full`)
run-10k: data/br_10km.tif
	$(PY) scripts/run_experiment.py --input $< --label br_10km
run-5k: data/br_5km.tif
	$(PY) scripts/run_experiment.py --input $< --label br_5km

full: data/$(FINE).tif data/$(COARSE).tif
	$(PY) scripts/run_experiment.py --input data/$(FINE).tif   --label $(FINE)
	$(PY) scripts/run_experiment.py --input data/$(FINE).tif   --label $(FINE)_repeat
	$(PY) scripts/run_experiment.py --input data/$(COARSE).tif --label $(COARSE)
	$(PY) scripts/check_run.py --require-frozen --run runs/$(FINE) --repeat runs/$(FINE)_repeat --coarse runs/$(COARSE)
	$(MAKE) verify report

# ── verification and report ──────────────────────────────────────────────────
verify:
	@for d in runs/*/; do test -f $$d/metrics.json && $(PY) scripts/verify_record.py $$d || true; done; \
	for d in runs/*/; do test -f $$d/metrics.json && $(PY) scripts/verify_record.py $$d >/dev/null || exit 1; done

report:
	$(PY) scripts/report.py

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check scripts tests

# pins every transitive dependency with hashes, on the machine that produced the results
lock:
	$(PY) -m pip freeze --exclude-editable > requirements.lock

clean:
	rm -rf runs/* build results data/synthetic_*.tif
