"""Certificate schema with explicit scope (SOTA-5, Mission D). Turns a CJCS row into a relation record that
says exactly what the kernel-checked declaration establishes and what it does not.

Interpretation theorem (informal statement; the Lean facts it relies on are cited per relation): if the
independent checker accepted a certificate of relation R for the statement strings X and Y *as elaborated by
Lean 4.34.1 under the recorded imports*, then R holds between those elaborated propositions. Nothing is
claimed about the strings' intended meaning, the source paper, or other elaborations; the adapter's
standalone round-trip check (bench/sota5/adapter2.py) is the only link from source declarations to X and Y.
"""
from __future__ import annotations

import hashlib

RELATIONS = {
    "equiv_defeq": ("DEFINITIONAL_EQUALITY", "X and Y elaborate to definitionally equal propositions (Iff.rfl).",
                    "Anything about intended meaning beyond the elaborated terms."),
    "equiv_both_true": ("CLOSED_EQUIVALENCE_BOTH_TRUE", "X ↔ Y, because X and Y are both proved.",
                        "Formulation-level equivalence. Two unrelated theorems are closed-equivalent. If X, Y are the "
                        "universal closures of formulas over a certified aligned context, open equivalence follows "
                        "(SOTA5.both_closures_true_open); no such alignment is certified."),
    "equiv_both_false": ("CLOSED_EQUIVALENCE_BOTH_FALSE", "X ↔ Y, because X and Y are both refuted.",
                         "Equivalence of the open formulas: both-false closures can hide strict strength or "
                         "incomparability (SOTA5.d22_strictly_stronger)."),
    "diff_RL": ("CLOSED_DIFFERENCE", "¬(X ↔ Y): X is refuted at the reported witness, Y is proved.",
                "Which formulation is the intended one. Open non-equivalence over an alignment follows "
                "(contrapositive of SOTA5.open_imp_closed) only if X, Y are closures over that alignment."),
    "diff_LR": ("CLOSED_DIFFERENCE", "¬(X ↔ Y): Y is refuted at the reported witness, X is proved.",
                "Which formulation is the intended one (see diff_RL)."),
}
ORDER = ["equiv_defeq", "diff_RL", "diff_LR", "equiv_both_false", "equiv_both_true"]


def describe(row: dict, toolchain: str = "Lean 4.34.1", imports: str = "") -> dict:
    certs = row.get("certificates") or {}
    rec = {"inputs": {"X": row.get("reference"), "Y": row.get("lean"),
                      "sha256": hashlib.sha256(f"{row.get('reference')}\x00{row.get('lean')}".encode()).hexdigest()},
           "environment": {"toolchain": toolchain, "imports": imports},
           "certificate_source_sha256": hashlib.sha256((row.get("certificate_source") or "").encode()).hexdigest()}
    if "equiv_defeq" in certs and ({"diff_RL", "diff_LR"} & set(certs)):
        rec.update(relation="INCONSISTENT_REPORT", establishes=None, does_not_establish="anything; investigate")
        return rec
    for k in ORDER:
        if k in certs:
            rel, est, not_est = RELATIONS[k]
            c = certs[k]
            rec.update(relation=rel, declaration=c.get("declaration"), proposition=c.get("statement"),
                       axioms=c.get("axioms"), establishes=est, does_not_establish=not_est)
            if k.startswith("diff"):
                rec["witness"] = (row.get("witnesses") or {}).get("wit_R" if k == "diff_RL" else "wit_L")
            return rec
    rec.update(relation="NOT_CERTIFIED", establishes="nothing",
               does_not_establish="non-equivalence or equivalence: a failed search, timeout or abstention is never "
                                  "a negative result", partial=sorted(certs))
    return rec
