"""Matched-task comparison with SemantEq (https://github.com/hlxr89/SemantEq).

    python3 -m proofscope.competitors.semanteq export --splits heldout_oracle --out pairs.jsonl
    python3 -m proofscope.competitors.semanteq compare --semanteq results.jsonl --proofscope bench_results.json --out cmp.json

Overlapping task: "is the formal statement equivalent to the reference statement?" asked of the closed statements
`∀ x, H_L x → C_L x` and `∀ x, H_R x → C_R x`.

Why the comparison is only partial (stated in every report):
  * SemantEq's relation is deliberately finer than logical equivalence: it rejects equivalence proofs that use a
    decision procedure (omega, decide) or an unrelated library theorem. Most arithmetic equivalences in this
    benchmark need exactly those, so "not SemantEq" is often the *intended* SemantEq answer for a logically
    equivalent pair.
  * ProofScope's EQUIVALENT is uniform equivalence of hypotheses and conclusions; its other labels (gaps, vacuity,
    strictness) have no SemantEq counterpart.
So we report agreement on the binary question, broken down by ProofScope label, not a winner.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "benchmark"


def closed(spec: dict, name: str) -> str:
    b = " ".join(f"({n} : {t})" for n, t in spec["binders"])
    side = "lean" if name == "c" else "ref"
    return (f"import Mathlib\ntheorem {name} : ∀ {b}, ({spec[side + '_hyp']}) → ({spec[side + '_concl']}) := sorry")


def export(splits: list[str], out: Path) -> int:
    n = 0
    with out.open("w") as f:
        for sp in splits:
            for p in sorted((HERE / sp).glob("*.json")):
                s = json.loads(p.read_text())
                f.write(json.dumps({"id": s["id"], "reference": closed(s, "r"), "candidate": closed(s, "c")},
                                   ensure_ascii=False) + "\n")
                n += 1
    return n


EQUIV = {"ExactMatch", "DefEq", "EquivalentRestricted"}  # SemantEq verdicts meaning "equivalent" (Driver.lean)


def compare(semanteq: Path, proofscope: Path, out: Path) -> dict:
    se = {}
    for line in semanteq.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            if "id" in r:  # SemantEq begins with a {"_meta": ...} record
                se[r["id"]] = r.get("verdict", "missing")
    rows = json.loads(proofscope.read_text())["rows"]
    table: dict = {}
    for r in rows:
        if r["id"] not in se:
            continue
        t = table.setdefault(r["classification"], {})
        t[se[r["id"]]] = t.get(se[r["id"]], 0) + 1
    both_equiv = [r["id"] for r in rows if se.get(r["id"]) in EQUIV and r["classification"] == "EQUIVALENT"]
    disagree = [{"id": r["id"], "proofscope": r["classification"], "semanteq": se[r["id"]]} for r in rows
                if r["id"] in se and (se[r["id"]] in EQUIV) != (r["classification"] == "EQUIVALENT")]
    res = {"pairs_compared": sum(sum(t.values()) for t in table.values()),
           "proofscope_label_x_semanteq_verdict": table,
           "agree_equivalent": len(both_equiv), "disagreements": disagree,
           "reading": "SemantEq judges the closed statements under a relation finer than logical equivalence; "
                      "ProofScope judges uniform equivalence of hypotheses and conclusions and certifies gaps. "
                      "Two true closed statements are logically equivalent, so disagreement is not by itself an "
                      "error of either tool; each disagreement should be read individually.",
           "note": __doc__.split("Why the comparison is only partial", 1)[1].strip()}
    res["ground_truth"] = ground_truth(se, rows)
    out.write_text(json.dumps(res, indent=2))
    return res



_DIR = {"EQUIVALENT": "equivalent", "LEAN_STRONGER": "stronger", "COVERS": "stronger"}
_SE_DIR = {"LikelyTooWeak": "weaker", "LikelyTooStrong": "stronger"}


def ground_truth(se: dict, rows: list) -> dict:
    """Score both tools against the benchmark's expected labels.

    These labels encode ProofScope's pointwise semantics, which are not SemantEq's
    restricted equivalence policy; disagreement alone is not an error.
    """
    cases = {}
    for p in HERE.glob("*/*.json"):
        case = json.loads(p.read_text())
        if isinstance(case, dict) and "expected" in case and "id" in case:
            cases[case["id"]] = case
    score: dict = {}
    disagreements = []
    for r in rows:
        i = r["id"]
        if i not in se or i not in cases:
            continue
        case = cases[i]
        truth = _DIR.get(case["expected"], "weaker")
        s = "equivalent" if se[i] in EQUIV else _SE_DIR.get(se[i])
        p = None if r["classification"] == "INCONCLUSIVE" else _DIR.get(r["classification"], "weaker")
        split = r.get("split") or case.get("split", "?")
        k = score.setdefault(split, {"pairs": 0,
            "semanteq": {"agree": 0, "disagree": 0, "abstain": 0, "false_equivalent": 0},
            "proofscope": {"agree": 0, "disagree": 0, "abstain": 0, "false_equivalent": 0}})
        k["pairs"] += 1
        for name, v in (("semanteq", s), ("proofscope", p)):
            if v is None:
                k[name]["abstain"] += 1
            elif v == truth:
                k[name]["agree"] += 1
            else:
                k[name]["disagree"] += 1
                if v == "equivalent":
                    k[name]["false_equivalent"] += 1
                if name == "semanteq":
                    disagreements.append({"id": i, "split": split, "expected": case["expected"],
                        "semanteq": se[i], "proofscope": r["classification"],
                        "lean": f"{case['lean_hyp']} → {case['lean_concl']}",
                        "reference": f"{case['ref_hyp']} → {case['ref_concl']}"})
    return {"by_split": score, "semanteq_disagreements": disagreements}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m proofscope.competitors.semanteq")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--splits", nargs="+", required=True)
    e.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--semanteq", required=True)
    c.add_argument("--proofscope", required=True)
    c.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "export":
        print(export(a.splits, Path(a.out)), "pairs written")
    else:
        print(json.dumps(compare(Path(a.semanteq), Path(a.proofscope), Path(a.out)), indent=2)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
