"""Conservative *schematic* relation-strength diagnostics (not concrete theorem strictness).

Only reads benchmark JSON specs. No elaborated declaration binding, paper fidelity
validation or claim of general-purpose SemantEq-style proof-term restrictions.
See lean/ProofScope/Strength.lean for the generic Nat proofs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

BENCH = Path(__file__).resolve().parent / "benchmark"
CERT = {
    ("≤", "<"): ("LEAN_WEAKER_BOUND_SCHEMA", ["ProofScope.Strength.lt_implies_le",
                                              "ProofScope.Strength.le_not_implies_lt"]),
    ("<", "≤"): ("LEAN_STRONGER_BOUND_SCHEMA", ["ProofScope.Strength.lt_implies_le",
                                               "ProofScope.Strength.le_not_implies_lt"]),
    ("≥", ">"): ("LEAN_WEAKER_BOUND_SCHEMA", ["ProofScope.Strength.gt_implies_ge",
                                              "ProofScope.Strength.ge_not_implies_gt"]),
    (">", "≥"): ("LEAN_STRONGER_BOUND_SCHEMA", ["ProofScope.Strength.gt_implies_ge",
                                               "ProofScope.Strength.ge_not_implies_gt"]),
}


def norm(s):
    return re.sub(r"\s+", "", s)


def bound(s):
    depth = 0
    found = []
    for i, ch in enumerate(s):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth < 0:
                return None
        elif depth == 0 and ch in "≤<≥>":
            found.append((i, ch))
    if depth or len(found) != 1:
        return None
    i, op = found[0]
    a, b = s[:i].strip(), s[i+1:].strip()
    return (a, op, b) if a and b else None


def inspect(spec):
    fields = ("binders", "lean_hyp", "lean_concl", "ref_hyp", "ref_concl")
    raw = json.dumps({k: spec.get(k) for k in fields}, sort_keys=True,
                     ensure_ascii=False, separators=(",", ":"))
    out = {
        "id": spec.get("id"), "spec_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "axis": "CLAIM_FORM", "trust": "SPECIFICATION_ONLY_UNREVIEWED",
        "status": "NOT_ANALYZED", "lean_certificates": [], "certificate_scope": "none",
    }
    bs = spec.get("binders", [])
    if not bs or any(len(x) != 2 or x[1].strip() != "Nat" for x in bs):
        out["reason"] = "Only Nat binder specifications supported"
        return out
    if norm(spec.get("lean_hyp", "")) != norm(spec.get("ref_hyp", "")):
        out["reason"] = "Hypotheses differ; conclusion relation cannot be isolated"
        return out
    l, r = bound(spec.get("lean_concl", "")), bound(spec.get("ref_concl", ""))
    if l is None or r is None:
        out["reason"] = "Conclusions are not single top-level Nat comparisons"
        return out
    a, op, b = l
    ar, opr, br = r
    if norm(a) != norm(ar) or norm(b) != norm(br):
        out["status"] = "BOUND_EXPRESSION_CHANGED"
        out["reason"] = "Operand changed; no mathematical strength relation inferred"
    elif op == opr:
        out["status"] = "SAME_BOUND_FORM"
        out["reason"] = "Same surface comparison; no semantic identity asserted"
    elif (op, opr) in CERT:
        out["status"], out["lean_certificates"] = CERT[(op, opr)]
        out["certificate_scope"] = "abstract Nat comparison; NOT concrete theorem strictness"
        out["reason"] = ("Strict relation implies weak relation for arbitrary operands; "
                         "reverse generic rule fails. No claim of strictness for these concrete theorems.")
    else:
        out["status"] = "RELATION_CHANGED_UNCERTIFIED"
        out["reason"] = "Relation changed; no strength proof for this pattern"
    return out


def run(splits, output):
    rows = []
    for split in splits:
        paths = sorted((BENCH / split).glob("*.json"))
        if not paths:
            raise ValueError("missing or empty split: " + split)
        for path in paths:
            result = inspect(json.loads(path.read_text()))
            result["split"] = split
            rows.append(result)
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    result = {
        "version": "v0.7-schematic-alpha", "cases": len(rows),
        "by_status": counts, "rows": rows,
        "limitations": ["no elaborated declaration binding", "no concrete theorem strictness certificate",
                        "no paper fidelity confirmation", "no external benchmark"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", nargs="+", default=["dev", "heldout_oracle"])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    result = run(a.splits, a.out)
    print(json.dumps({"cases": result["cases"], "by_status": result["by_status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
