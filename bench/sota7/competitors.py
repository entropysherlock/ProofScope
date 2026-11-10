"""Competitor capability matrix and availability probe (no benchmark claims).

Only capabilities a system claims are compared; an installation failure is recorded as NOT_INSTALLED,
never as a mathematical failure. Matched tasks must use identical budgets (manifest budgets).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
from pathlib import Path

CAPS = ["structural_match", "closed_equivalence", "closed_non_equivalence", "open_relation", "source_fidelity",
        "assumption_explanation", "repair_generation", "certified_repair_minimality"]
MATRIX = {
    "ProofScope SOTA-6 (cjcs4 + repair)": {"closed_equivalence": "kernel", "closed_non_equivalence": "kernel",
        "source_fidelity": "adapter v2 check + source-link theorems", "assumption_explanation": "kernel (finite fragments)",
        "repair_generation": "kernel (declared grammar)", "certified_repair_minimality": "kernel (declared grammar)"},
    "BEq+ (LeanInteract, Poiroux et al., EMNLP 2025)": {"closed_equivalence": "kernel (bidirectional proof)", "structural_match": "yes"},
    "SemantEq": {"structural_match": "yes (normalization)"},
    "FormalRx / FormalRx-CC (ICML 2026)": {"source_fidelity": "LLM diagnosis (FormalRx); Lean-checked separating witness (CC)",
        "closed_non_equivalence": "Lean-checked witness (CC)", "repair_generation": "LLM correction (not certified)"},
    "BPF (Faithfulness Gap, 2026)": {"source_fidelity": "probe-based NL fingerprinting (statistical)"},
}


def probe() -> dict:
    st = {}
    st["BEq+ (LeanInteract, Poiroux et al., EMNLP 2025)"] = "AVAILABLE" if importlib.util.find_spec("lean_interact") else "NOT_INSTALLED"
    st["SemantEq"] = "AVAILABLE" if os.environ.get("SEMANTEQ_DIR") and Path(os.environ["SEMANTEQ_DIR"]).exists() else "NOT_INSTALLED"
    st["ProofScope SOTA-6 (cjcs4 + repair)"] = "AVAILABLE" if shutil.which("lean") else "NOT_INSTALLED"
    st["FormalRx / FormalRx-CC (ICML 2026)"] = "NOT_INTEGRATED"
    st["BPF (Faithfulness Gap, 2026)"] = "NOT_INTEGRATED"
    return st


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.sota7.competitors")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    st = probe()
    out = {"capabilities": CAPS, "matrix": {k: {c: v.get(c, "unsupported") for c in CAPS} for k, v in MATRIX.items()},
           "availability": st, "benchmark_runs": "NOT RUN (no independent dataset; smoke = availability probe only)"}
    a.out.write_text(json.dumps(out, indent=1))
    print(json.dumps(st, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
