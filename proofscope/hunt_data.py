"""Benchmark loaders for the defect hunt: rows {"id", "source", "lean_code", "informal"}.

PutnamBench: answers are `sorry` placeholders with the intended answer in a comment; the benchmark's own
scripts/rewrite_solutions.py substitutes them (we call it unchanged). The package compiles with
`autoImplicit false`, so rows carry that option.
FormalMATH: loaded from Hugging Face (SphereLab/FormalMATH-All); the Lean column is detected by content.
"""
from __future__ import annotations

import importlib.util
import json
import re
import tempfile
from pathlib import Path


def _docstring(text: str) -> str:
    m = re.search(r"/--(.*?)-/", text, re.S)
    return m.group(1).strip() if m else ""


def putnam_rows(repo: Path) -> list[dict]:
    lean4 = Path(repo) / "lean4"
    spec = importlib.util.spec_from_file_location("ps_putnam_rewrite", lean4 / "scripts" / "rewrite_solutions.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rows, out = [], Path(tempfile.mkdtemp(prefix="putnam_sol_"))
    for f in sorted((lean4 / "src").glob("*.lean")):
        original = f.read_text(encoding="utf8")
        try:
            mod.rewrite_solutions(f, out / f.name)
            code = (out / f.name).read_text(encoding="utf8")
            note = "answer substituted by PutnamBench's rewrite_solutions.py" if "_solution" in original else ""
        except Exception as e:                         # leave the placeholder; the hunt will skip it
            code, note = original, f"answer not substituted: {e}"
        lines = code.splitlines()
        k = sum(1 for l in lines if l.startswith("import "))
        code = "\n".join(lines[:k] + ["set_option autoImplicit false"] + lines[k:])
        rows.append({"id": f.stem, "source": "PutnamBench", "lean_code": code, "informal": _docstring(original),
                     "note": note})
    return rows


def formalmath_rows(dataset: str = "SphereLab/FormalMATH-All") -> list[dict]:
    from datasets import load_dataset                    # available in Colab; `pip install datasets` otherwise
    ds = load_dataset(dataset, split="train")
    cols = ds.column_names
    sample = ds[0]
    lean_col = next((c for c in cols if isinstance(sample[c], str) and "theorem" in sample[c] and ":=" in sample[c]), None)
    if lean_col is None:
        raise ValueError(f"no Lean column found in {cols}")
    nl_col = next((c for c in ("refined_statement", "informal_statement", "problem", "natural_language") if c in cols), None)
    id_col = next((c for c in ("theorem_names", "theorem_name", "id", "name") if c in cols), None)
    rows = []
    for i, r in enumerate(ds):
        rid = str(r[id_col]) if id_col else f"row{i}"
        rows.append({"id": f"fm_{rid}", "source": dataset, "lean_code": r[lean_col],
                     "informal": r[nl_col] if nl_col else ""})
    return rows


def write_jsonl(rows: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf8")
    return path
