"""Generate the SYNTHETIC_DEVELOPMENT dry-run fixtures (bench/sota7/synthetic/). These cases and labels were
written by the engine developer. They test the harness and are never evidence of accuracy or independence.

    python -m bench.sota7.make_synthetic --out bench/sota7/synthetic
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SALT = "proofscope-sota7-synthetic-v1"
PROV = {"source": "ProofScope developer (synthetic development fixture)", "url": "", "retrieved": "2026-11-09",
        "license": "same as repository", "upstream_revision": "26eee2bd36b29c895c3f783f33b97a48e4e816a8"}
ENV = {"lean": "4.34.1", "mathlib": None, "imports": []}


def cid(name):
    return "c" + hashlib.sha256(f"{SALT}:{name}".encode()).hexdigest()[:12]


def rel(name, dom, diff, R, F, relation, truth, why):
    pub = {"schema": "proofscope-eval/1", "case_id": cid(name), "task": "relation", "domain": dom, "difficulty": diff,
           "provenance": PROV, "environment": ENV, "reference": {"text": R, "lean": R}, "candidate": {"text": F, "lean": F}}
    gold = {"schema": "proofscope-eval/1", "case_id": cid(name), "dev_name": name, "relation": relation,
            "closed_truth": truth, "evidence": why, "reviewers": ["engine-developer"], "rationales": [why],
            "adjudication": "SYNTHETIC_DEVELOPMENT" if relation != "UNRESOLVED" else "UNRESOLVED",
            "labeler_class": "SYNTHETIC_DEVELOPMENT"}
    if relation == "UNRESOLVED":
        gold["adjudication"] = "UNRESOLVED"
    return pub, gold


def rep(name, dom, diff, spec_file, intended, why, edits=None):
    s = json.loads((REPO / "research/sota6/repair" / spec_file).read_text())
    if edits is not None:
        s["edits"] = edits
    pub = {"schema": "proofscope-eval/1", "case_id": cid(name), "task": "repair", "domain": dom, "difficulty": diff,
           "provenance": PROV, "environment": ENV,
           "reference": {"text": s["reference_source"], "lean": s["reference_source"]},
           "candidate": {"text": s["candidate_source"], "lean": s["candidate_source"]},
           "repair": {k: s[k] for k in ("context", "reference", "candidate", "edits", "pool")}}
    gold = {"schema": "proofscope-eval/1", "case_id": cid(name), "dev_name": name, "relation": "REF_STRONGER",
            "intended_repairs": intended, "evidence": why, "reviewers": ["engine-developer"], "rationales": [why],
            "adjudication": "SYNTHETIC_DEVELOPMENT", "labeler_class": "SYNTHETIC_DEVELOPMENT"}
    return pub, gold


CASES = [
    rel("cast_target", "number theory", "easy", "∀ (n : Nat), (↑(n - 1) : Int) = (↑n : Int) - 1",
        "∀ (n : Nat), 1 ≤ n → (↑(n - 1) : Int) = (↑n : Int) - 1", "REF_STRONGER",
        {"reference": "FALSE", "candidate": "TRUE"}, "reference false at n = 0; candidate adds 1 ≤ n"),
    rel("unrelated_true", "arithmetic", "easy", "2 + 2 = 4", "∀ (n : Nat), n + 0 = n", "NOT_EQUIVALENT",
        {"reference": "TRUE", "candidate": "TRUE"}, "unrelated statements, both true"),
    rel("quantifier_swap", "order", "easy", "∀ (x : Nat), ∃ (y : Nat), y > x", "∃ (y : Nat), ∀ (x : Nat), y > x",
        "CAND_STRONGER", {"reference": "TRUE", "candidate": "FALSE"}, "∃∀ implies ∀∃; the candidate is false"),
    rel("division_nonzero", "arithmetic", "easy", "∀ (n : Nat), n / n = 1", "∀ (n : Nat), n ≠ 0 → n / n = 1",
        "REF_STRONGER", {"reference": "FALSE", "candidate": "TRUE"}, "n / 0 = 0 in Lean"),
    rel("rename", "arithmetic", "easy", "∀ (n : Nat), n + 0 = n", "∀ (m : Nat), m = m + 0", "EQUIVALENT",
        {"reference": "TRUE", "candidate": "TRUE"}, "renamed and symmetric"),
    rel("open_pair", "number theory", "hard",
        "∀ (n : Nat), n > 1 → ∃ (p : Nat), p > n ∧ p < 2 * n ∧ ∀ (d : Nat), d ∣ p → d = 1 ∨ d = p",
        "∀ (n : Nat), n > 2 → ∃ (p : Nat), p > n ∧ p < 2 * n ∧ ∀ (d : Nat), d ∣ p → d = 1 ∨ d = p",
        "UNRESOLVED", None, "left unresolved on purpose (tests the UNRESOLVED path)"),
    rep("repair_nonzero", "arithmetic", "easy", "r1_division_nonzero.json", [[0], [1]], "add n ≠ 0 or 0 < n"),
    rep("repair_sign", "order", "medium", "r2_square_order.json", [[0]], "add 0 ≤ a"),
    rep("repair_disjunct", "algebra", "medium", "r3_conclusion_disjunct.json", [[1]], "restore x = -1"),
    rep("repair_none", "algebra", "medium", "r3_conclusion_disjunct.json", "NONE_IN_GRAMMAR",
        "the grammar cannot restore the conclusion", edits=[{"add_hyp": "0 ≤ x"}]),
    rep("planted_label_error", "arithmetic", "easy", "r1_division_nonzero.json", [[2]],
        "PLANTED WRONG LABEL (2 ≤ n) to test that a mismatch is reported, not hidden"),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.sota7.make_synthetic")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    (a.out / "public").mkdir(parents=True, exist_ok=True)
    golds = []
    for pub, gold in CASES:
        (a.out / "public" / f"{pub['case_id']}.json").write_text(json.dumps(pub, ensure_ascii=False, indent=1) + "\n")
        golds.append(gold)
    (a.out / "gold.jsonl").write_text("".join(json.dumps(g, ensure_ascii=False) + "\n" for g in golds))
    print(len(golds), "synthetic cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
