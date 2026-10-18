#!/usr/bin/env bash
# Independent check of Open LUCC workflow, levels 0, 1 and 2. Linux, WSL2 or macOS.
# Usage, in an empty folder:  bash external_check.sh
# It takes 40 to 90 minutes, almost all of it in level 2. At the end it writes
# open-lucc-check.tar.gz (logs, machine description, package versions, metrics),
# which can be sent to the authors. It does not read or send anything else.
set -u
BASE="$(pwd)"; OUT="$BASE/check"
rm -rf "$OUT" open-lucc-workflow; mkdir -p "$OUT"

# Python 3.11 or newer
PY=""
for c in python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info>=(3,11) else 1)'; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "Python 3.11 or newer is needed (Ubuntu 24.04 has 3.12; on a Mac: brew install python@3.12)."; exit 1
fi
echo "Using $($PY --version)"

git clone https://github.com/LambdaGeo/open-lucc-workflow.git || exit 1
cd open-lucc-workflow || exit 1

{
  echo "commit: $(git rev-parse HEAD)"; echo "date: $(date -Iseconds 2>/dev/null || date)"
  echo "system: $(uname -a)"
  command -v lsb_release >/dev/null && lsb_release -a 2>/dev/null
  command -v sw_vers >/dev/null && sw_vers
  $PY --version
  if [ "$(uname)" = "Darwin" ]; then
    sysctl -n machdep.cpu.brand_string; echo "cpus: $(sysctl -n hw.ncpu)"; echo "memory (GB): $(( $(sysctl -n hw.memsize) / 1073741824 ))"
  else
    grep -m1 'Model name' <(lscpu); echo "nproc: $(nproc)"; free -g
    grep -qi microsoft /proc/version 2>/dev/null && echo "WSL2: yes" || echo "WSL2: no"
  fi
} > "$OUT/machine.txt" 2>&1

make env PYTHON="$PY" 2>&1 | tee "$OUT/env.log"
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "make env failed; see $OUT/env.log"; }
.venv/bin/python -m pip freeze > "$OUT/freeze.txt"
.venv/bin/python - > "$OUT/libs.txt" <<'PYEOF'
import platform, rasterio, shapely, pyproj, numpy
print("platform", platform.platform(), platform.machine())
print("python", platform.python_version())
print("numpy", numpy.__version__)
print("rasterio", rasterio.__version__, "GDAL", rasterio.__gdal_version__)
print("shapely", shapely.__version__, "GEOS", shapely.geos_version_string)
print("pyproj", pyproj.__version__, "PROJ", pyproj.proj_version_str)
PYEOF

( time make check-reported ) 2>&1 | tee "$OUT/level0.log"
( time make small )          2>&1 | tee "$OUT/level1.log"
( time make reproduce-10k )  2>&1 | tee "$OUT/level2.log"

mkdir -p "$OUT/runs"
for d in runs/*/; do n=$(basename "$d"); mkdir -p "$OUT/runs/$n"; cp "$d"metrics.json "$OUT/runs/$n/" 2>/dev/null; done
# the two 10.56 km rasters, so that values can be compared across computers (scripts/compare_rasters.py)
mkdir -p "$OUT/rasters"; cp data/br_10km.tif "$OUT/rasters/" 2>/dev/null
cp runs/br_10km/*.tif "$OUT/rasters/" 2>/dev/null
{ grep -hE "PASS|FAIL|identical|equivalent|differs|DIFFERS|OK|real" "$OUT"/level*.log; } > "$OUT/summary.txt"
cd "$BASE" && tar czf open-lucc-check.tar.gz check
echo; echo "Done. File to send: $BASE/open-lucc-check.tar.gz"
