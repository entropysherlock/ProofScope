"""Pre-registered mapping from each tool's native verdict to the shared outcome vocabulary.

Two readings are reported side by side, never merged:

* `certified` (3-way): EQUIV / NONEQUIV only when the tool's output is backed by a machine-checked
  artefact for that claim; everything else is ABSTAIN. A failed proof search is never NONEQUIV.
* `native` (binary): the tool's own published accept/reject reading (what its paper scores), with
  abstentions folded into NONEQUIV exactly as that tool's authors do. Reported for comparability with
  published numbers only.

Infrastructure outcomes (TIMEOUT_*, OOM*, ERROR, NON_ELABORATING, UNSUPPORTED_INPUT, INCOMPATIBLE) are kept
as such in both readings and are never converted into abstentions or verdicts.

Track A = whole-statement logical equivalence; Track B = faithful statement equivalence. A tool's EQUIV
is the same claim in both tracks (gold differs); a tool's NONEQUIV is admissible in Track B when it
certifies a semantic difference that need not make the closed propositions inequivalent (ProofScope's
schema-level separations); such outputs are ABSTAIN in Track A.
"""
from __future__ import annotations

INFRA = {"TIMEOUT_CPU", "TIMEOUT_WALL", "OOM", "OOM_OR_KILLED", "ERROR", "NON_ELABORATING", "UNSUPPORTED_INPUT",
         "INCOMPATIBLE"}

# ProofScope v1.2 (adelta12; proofscope/v12.py)
PS_EQUIV = {"ASSUMPTION_EQUIVALENT", "NO_ASSUMPTION_DELTA", "IDENTICAL", "SCHEMA_EQUIVALENT", "EQUIVALENT_BY_LAWS"}
PS_SCHEMA_DIFF = {"LEAN_WEAKER_BY_ASSUMPTION", "LEAN_STRONGER_BY_ASSUMPTION", "ASSUMPTION_INCOMPARABLE",
                  "REFERENCE_NEEDS_ASSUMPTION", "LEAN_CLAIM_FALSE"}
# SemantEq (README at the pinned commit)
SE_EQUIV = {"ExactMatch", "DefEq", "EquivalentRestricted"}
SE_ONE_DIR = {"LikelyTooStrong", "LikelyTooWeak"}
SE_INFRA = {"Timeout": "TIMEOUT_WALL", "ContextMergeError": "INCOMPATIBLE", "NotAProposition": "UNSUPPORTED_INPUT",
            "MalformedInput": "UNSUPPORTED_INPUT", "InternalError": "ERROR"}


def proofscope(verdict: str, track: str) -> dict:
    if verdict in PS_EQUIV:
        c = "EQUIV"
    elif verdict in PS_SCHEMA_DIFF:
        c = "NONEQUIV" if track == "B" else "ABSTAIN"
    elif verdict == "BOTH_CLAIMS_FALSE":
        # both closed statements are refuted, so they are logically equivalent (False ↔ False); fidelity open
        c = "EQUIV" if track == "A" else "ABSTAIN"
    elif verdict.startswith("INCONCLUSIVE") and "extraction" in verdict.lower():
        c = "NON_ELABORATING"
    else:
        c = "ABSTAIN"
    native = "EQUIV" if c == "EQUIV" else "NONEQUIV"
    return {"certified": c, "native": native}


def semanteq(verdict: str, track: str) -> dict:
    if verdict in SE_INFRA:
        return {"certified": SE_INFRA[verdict], "native": SE_INFRA[verdict]}
    if verdict.endswith("CompileError") or verdict.endswith("NoStatement"):
        return {"certified": "NON_ELABORATING", "native": "NON_ELABORATING"}
    if verdict in SE_EQUIV:
        return {"certified": "EQUIV", "native": "EQUIV"}
    # one proved direction or nothing: no certificate of a difference
    return {"certified": "ABSTAIN", "native": "NONEQUIV"}


def beqplus(result: bool | None, track: str) -> dict:
    if result is None:
        return {"certified": "ERROR", "native": "ERROR"}
    return {"certified": "EQUIV" if result else "ABSTAIN", "native": "EQUIV" if result else "NONEQUIV"}
