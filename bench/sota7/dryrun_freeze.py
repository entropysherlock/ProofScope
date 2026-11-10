"""Freeze the synthetic dry-run manifest (identical budgets for every case of a task)."""
import sys
from pathlib import Path

from bench.sota7.blind import freeze

BUDGETS = {"relation": {"cpu_s": 120, "mem_mb": 8000, "wall_s": 400}, "repair": {"cpu_s": 120, "mem_mb": 8000, "wall_s": 400}}

if __name__ == "__main__":
    out = Path(sys.argv[1])
    m = freeze(Path("bench/sota7/synthetic/public"), Path("bench/sota7/synthetic/gold.jsonl"), out,
               dataset_version="synthetic-dev-1", selection_protocol="SYNTHETIC_DEVELOPMENT (not a selection protocol)",
               review_protocol="SYNTHETIC_DEVELOPMENT (no review)", repo=Path("."),
               toolchain={"lean": "4.34.1", "mathlib": None, "repl": "193cf4bb9a22bb3fc6d25774f0fe6a70db1fd6ee"},
               budgets=BUDGETS)
    print(m["manifest_sha256"], len(m["cases"]))
