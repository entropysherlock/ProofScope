"""Derived status.  Labels are computed from records, never typed in by hand."""
from __future__ import annotations

from .records import Ledger

ORDER = ["asserted", "computational", "informal", "reviewed", "machine_checked", "reproduced"]
FAITHFUL_ENOUGH = ("independently_corroborated", "formally_related")


def statement_status(ledger: Ledger, statement_id: str) -> dict:
    """Proof-evidence status of one statement: strongest active level, plus flags."""
    disputed = ledger.disputed()
    ev = [r for r in ledger.active() if r["type"] == "evidence" and r["about"] == statement_id]
    if not ev:
        return {"statement": statement_id, "level": "asserted", "records": [], "disputed": False,
                "refuted": False}
    refuted = any(r["level"] == "refuted" for r in ev)
    positive = [r for r in ev if r["level"] in ORDER]
    best = max(positive, key=lambda r: ORDER.index(r["level"]))["level"] if positive else "asserted"
    return {"statement": statement_id, "level": best, "records": [r["id"] for r in ev],
            "disputed": any(r["id"] in disputed for r in ev) or (refuted and bool(positive)),
            "refuted": refuted,
            "suspected_false": any(r["level"] == "suspected_false" for r in ev)}


def claim_status(ledger: Ledger, claim_id: str) -> dict:
    """Outcome for an informal claim.

    The claim is 'verified' only if some formal statement that is machine-checked is
    linked to it by a review at 'independently_corroborated' or better.  A kernel
    proof of a formal statement with an unreviewed link leaves the claim at
    'supported': something was proved, but not yet shown to be this claim.
    """
    active = ledger.active()
    reviews = [r for r in active if r["type"] == "review" and r["about"].get("claim") == claim_id]
    out = {"claim": claim_id, "outcome": "asserted", "because": []}
    for rv in reviews:
        st = statement_status(ledger, rv["about"]["statement"])
        if st["refuted"]:
            out["outcome"] = "refuted" if rv["faithfulness"] in FAITHFUL_ENOUGH else "undecided"
            out["because"].append(f"{rv['about']['statement']} refuted; link is {rv['faithfulness']}")
            return out
        kernel = st["level"] in ("machine_checked", "reproduced")
        if kernel and rv["faithfulness"] in FAITHFUL_ENOUGH and not st["disputed"]:
            out["outcome"] = "verified"
            out["because"] = [f"{rv['about']['statement']} is {st['level']}; link is {rv['faithfulness']}"]
            return out
        if kernel or st["level"] in ("informal", "reviewed", "computational"):
            out["outcome"] = "supported"
            out["because"].append(f"{rv['about']['statement']} is {st['level']}; "
                                  f"link is only {rv['faithfulness']}")
        if rv["faithfulness"] == "disputed":
            out["outcome"] = "undecided"
            out["because"].append("faithfulness disputed")
    return out
