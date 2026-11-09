"""Pre-registered scoring for comparing ProofScope with binary equivalence checkers (v1.1).

Registered before any competitor run. A pair is labelled by an independent reviewer as EQUIVALENT or
NOT_EQUIVALENT (plus optional direction). Mapping of ProofScope verdicts to the binary task:

    EQUIVALENT      SCHEMA_EQUIVALENT, EQUIVALENT_BY_LAWS, ASSUMPTION_EQUIVALENT, IDENTICAL
    NOT_EQUIVALENT  CLAIM_*, *_BY_ASSUMPTION, REFERENCE_NEEDS_ASSUMPTION, LEAN_CLAIM_FALSE, ASSUMPTION_INCOMPARABLE
    ABSTAIN         INCONCLUSIVE*, NO_SHARED_SYMBOLS, CONCLUSION_ONLY_CHANGE, NO_ASSUMPTION_DELTA

ABSTAIN is never counted as correct or incorrect; coverage is reported separately. False equivalence and
false difference are reported separately, never folded into one accuracy number. Direction is scored only
for systems that output one. Competitor outputs are mapped by their own documented semantics
(SemantEq: ExactMatch/DefEq/EquivalentRestricted → EQUIVALENT, LikelyTooWeak/LikelyTooStrong → NOT_EQUIVALENT,
Inconclusive/Timeout → ABSTAIN).
"""
from __future__ import annotations

import json
from pathlib import Path

PS_EQ = {"SCHEMA_EQUIVALENT", "EQUIVALENT_BY_LAWS", "ASSUMPTION_EQUIVALENT", "IDENTICAL"}
SE_EQ = {"ExactMatch", "DefEq", "EquivalentRestricted"}
SE_NE = {"LikelyTooWeak", "LikelyTooStrong"}


def proofscope_binary(v: str) -> str:
    if v in PS_EQ:
        return "EQUIVALENT"
    if v.startswith("CLAIM_") or v.endswith("_BY_ASSUMPTION") or v in {"REFERENCE_NEEDS_ASSUMPTION", "LEAN_CLAIM_FALSE",
                                                                      "ASSUMPTION_INCOMPARABLE"}:
        return "NOT_EQUIVALENT"
    return "ABSTAIN"


def semanteq_binary(v: str) -> str:
    return "EQUIVALENT" if v in SE_EQ else "NOT_EQUIVALENT" if v in SE_NE else "ABSTAIN"


def score(labels: dict[str, str], preds: dict[str, str]) -> dict:
    s = {"pairs": len(labels), "decided": 0, "abstain": 0, "correct": 0, "false_equivalence": 0, "false_difference": 0}
    for k, gold in labels.items():
        p = preds.get(k, "ABSTAIN")
        if p == "ABSTAIN":
            s["abstain"] += 1
            continue
        s["decided"] += 1
        if p == gold:
            s["correct"] += 1
        elif p == "EQUIVALENT":
            s["false_equivalence"] += 1
        else:
            s["false_difference"] += 1
    return s


def export_semanteq(specs: list[Path], out: Path) -> int:
    """SemantEq JSONL for closed-statement specs (`reference`/`lean`), with `import Mathlib` statements."""
    n = 0
    with out.open("w") as f:
        for p in specs:
            d = json.loads(p.read_text())
            if "reference" not in d:
                continue
            f.write(json.dumps({"id": d["id"], "reference": f"import Mathlib\ntheorem r : {d['reference']} := sorry",
                                "candidate": f"import Mathlib\ntheorem r : {d['lean']} := sorry"}, ensure_ascii=False) + "\n")
            n += 1
    return n
