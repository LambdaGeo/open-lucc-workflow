#!/usr/bin/env python
"""Verify an experiment record from a clean clone: hashes, versions and status.

    python scripts/verify_record.py runs/bdc_5k
This is the 'done' criterion of the demonstration: another person can confirm that the files they
hold are the ones the record describes, and that the installed packages are the pinned ones.
Exit status 1 on any mismatch.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from importlib.metadata import version

try:
    from _common import ROOT, sha256_file
except ImportError:  # pragma: no cover
    from scripts._common import ROOT, sha256_file


def pins() -> dict[str, str]:
    out = {}
    for line in (ROOT / "requirements.txt").read_text().splitlines():
        m = re.match(r"^([A-Za-z0-9_.-]+)==([^\s#]+)", line.strip())
        if m:
            out[m[1].lower()] = m[2]
    return out


def verify(run: pathlib.Path) -> list[str]:
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    record = json.loads(pathlib.Path(metrics["record"]).read_text(encoding="utf-8"))
    problems = []
    if record.get("status") != "completed":
        problems.append(f"status is {record.get('status')!r}, not 'completed'")
    cellspace = pathlib.Path(metrics["cellspace"])
    if not cellspace.exists():
        problems.append(f"input cell space not found: {cellspace}")
    elif sha256_file(cellspace) != record["source"]["checksum"]:
        problems.append("input checksum differs from the record")
    output = pathlib.Path(record["output_path"])
    if not output.exists():
        problems.append(f"output not found: {output}")
    elif sha256_file(output) != record["artifacts"]["output"]:
        problems.append("output checksum differs from the record")
    for pkg, pinned in pins().items():
        installed = version(pkg)
        if installed != pinned:
            problems.append(f"{pkg}: installed {installed}, pinned {pinned}")
    if record.get("model_commit") != f"disslucc=={version('disslucc')}":
        problems.append(f"record model_commit {record.get('model_commit')!r} is not disslucc=={version('disslucc')}")
    if record.get("code_version") != version("dissmodel"):
        problems.append(f"record code_version {record.get('code_version')!r} is not dissmodel {version('dissmodel')}")
    return problems


if __name__ == "__main__":
    probs = verify(pathlib.Path(sys.argv[1]))
    for p in probs:
        print("FAIL", p)
    print("record verified" if not probs else f"{len(probs)} problem(s)")
    sys.exit(1 if probs else 0)
