# Reproduce the demonstration of the note, stage by stage.
#
#   make env            create .venv and install the pinned packages
#   make small          offline smoke test on a synthetic cell space (minutes; what CI runs)
#   make full           Brazil, from open data (needs network, ~6 GB RAM for the 5.28 km grid)
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

.PHONY: env small full verify report test lint lock clean help

help:
	@sed -n '2,12p' Makefile

env:
	python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements-dev.txt

# ── small: synthetic, no downloads ───────────────────────────────────────────
small: data/synthetic_fine.tif data/synthetic_coarse.tif
	$(PY) scripts/check_cellspace.py data/synthetic_fine.tif
	$(PY) scripts/check_cellspace.py data/synthetic_coarse.tif
	$(PY) scripts/run_experiment.py --cellspace data/synthetic_fine.tif   --label synthetic_fine
	$(PY) scripts/run_experiment.py --cellspace data/synthetic_fine.tif   --label synthetic_fine_repeat
	$(PY) scripts/run_experiment.py --cellspace data/synthetic_coarse.tif --label synthetic_coarse
	$(PY) scripts/check_run.py --run runs/synthetic_fine --repeat runs/synthetic_fine_repeat --coarse runs/synthetic_coarse
	$(MAKE) verify report

data/synthetic_fine.tif:
	$(PY) scripts/synth_cellspace.py --out $@ --size $(SYN_SIZE)

data/synthetic_coarse.tif:
	$(PY) scripts/synth_cellspace.py --out $@ --size $(SYN_SIZE) --block $(SYN_BLOCK)

# ── full: Brazil on the Brazil Data Cube grid ────────────────────────────────
# Stage 1-2: DisSCube catalogs the sources (fetched and checked by SHA-256) and derives the variables.
# Stage 3-4: the model, twice on the fine grid (determinism) and once on the coarse grid.
# acceptance.toml must be frozen (see the file) before the numbers are reported.
FINE   = bdc_5k
COARSE = bdc_10k

build/pipelines/%.toml: pipeline/cellspace/derivations.template.toml
	$(PY) scripts/render_pipeline.py --name $* --out $@

data/cube_%/.cataloged: pipeline/cellspace/sources.toml
	$(DISSCUBE) fetch pipeline/cellspace/sources.toml
	$(DISSCUBE) run pipeline/cellspace/sources.toml --workspace data/cube_$*
	touch $@

# keep the exported cell space even when the next step refuses it, so it can be inspected
.PRECIOUS: data/raw_cellspace_%.tif

data/raw_cellspace_%.tif: build/pipelines/%.toml data/cube_%/.cataloged
	$(DISSCUBE) run build/pipelines/$*.toml --workspace data/cube_$*
	mkdir -p data && $(DISSCUBE) export build/pipelines/$*.toml --workspace data/cube_$* --output $@

# cells without a complete set of bands (coast, borders, islands) leave the mask; see the .report.json
data/cellspace_%.tif: data/raw_cellspace_%.tif
	$(PY) scripts/complete_cellspace.py $< $@
	$(PY) scripts/check_cellspace.py $@

full: data/cellspace_$(FINE).tif data/cellspace_$(COARSE).tif
	$(PY) scripts/run_experiment.py --cellspace data/cellspace_$(FINE).tif   --label $(FINE)
	$(PY) scripts/run_experiment.py --cellspace data/cellspace_$(FINE).tif   --label $(FINE)_repeat
	$(PY) scripts/run_experiment.py --cellspace data/cellspace_$(COARSE).tif --label $(COARSE)
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
