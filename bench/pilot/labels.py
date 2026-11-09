"""Two-reviewer blinded labelling with adjudication for the 50-case pilot (docs/sota4/PILOT_PROTOCOL.md).

This module never creates a label. It moves labels written by people between files and refuses anything
that would weaken independence:

    packets    build one blinded packet per reviewer from a sealed case file (bench/seal.py output): case
               text only, no system output, no source labels, an independent order per reviewer
    ingest     validate a reviewer's returned label file against the schema
    agree      Cohen's kappa per track, raw agreement, and the adjudication queue (every disagreement and
               every UNSURE)
    finalize   merge the two reviewers and the adjudicator into gold labels with full provenance

Rules enforced:
  * reviewer ids must differ from each other and from the adjudicator, and none may appear in the
    conflict list (tool developers, including AI systems that wrote ProofScope code or cases);
  * every case needs both reviewers' labels for BOTH tracks; Track B is never filled from Track A;
  * a case where the reviewers agree is final only if neither said UNSURE; otherwise the adjudicator's label
    is required; an unresolved case stays UNRESOLVED and is excluded from scoring, never guessed;
  * gold is written only after `agree` has been run on the same inputs (input digests are recorded).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

TRACK_A = {"EQUIVALENT", "NOT_EQUIVALENT", "UNSURE"}       # logical, under the stated interpretation policy
TRACK_B = {"FAITHFUL", "NOT_FAITHFUL", "UNASSESSABLE", "UNSURE"}   # paper fidelity; UNASSESSABLE if no source
REQUIRED = {"case_id", "reviewer", "track_A", "track_B", "rationale", "minutes_spent"}


class LabelError(ValueError):
    pass


def _read(p: Path) -> list[dict]:
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def _digest(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def packets(cases: list[dict], reviewers: list[str], seeds: dict[str, int]) -> dict[str, list[dict]]:
    if len(set(reviewers)) != len(reviewers):
        raise LabelError("reviewer ids must be distinct")
    keep = ("case_id", "ref_header", "ref_decl", "cand_header", "cand_decl", "paper_source", "paper_claim",
            "interpretation_policy")
    out = {}
    for r in reviewers:
        rows = [{k: c[k] for k in keep if k in c} for c in cases]
        random.Random(seeds[r]).shuffle(rows)
        out[r] = rows
    return out


def validate(labels: list[dict], case_ids: set[str], reviewer: str) -> None:
    seen = set()
    for l in labels:
        miss = REQUIRED - set(l)
        if miss:
            raise LabelError(f"{l.get('case_id')}: missing fields {sorted(miss)}")
        if l["reviewer"] != reviewer:
            raise LabelError(f"{l['case_id']}: label from {l['reviewer']} in {reviewer}'s file")
        if l["track_A"] not in TRACK_A or l["track_B"] not in TRACK_B:
            raise LabelError(f"{l['case_id']}: invalid label values {l['track_A']}/{l['track_B']}")
        if not str(l["rationale"]).strip():
            raise LabelError(f"{l['case_id']}: empty rationale")
        if l["case_id"] in seen:
            raise LabelError(f"{l['case_id']}: labelled twice")
        seen.add(l["case_id"])
    if seen != case_ids:
        raise LabelError(f"label set differs from the case set: missing {sorted(case_ids - seen)}, extra {sorted(seen - case_ids)}")


def kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    cats = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return None if pe == 1 else (po - pe) / (1 - pe)


def agree(l1: list[dict], l2: list[dict]) -> dict:
    m1, m2 = {l["case_id"]: l for l in l1}, {l["case_id"]: l for l in l2}
    ids = sorted(m1)
    res = {"cases": len(ids), "tracks": {}, "adjudication_queue": []}
    for t in ("track_A", "track_B"):
        a, b = [m1[i][t] for i in ids], [m2[i][t] for i in ids]
        res["tracks"][t] = {"raw_agreement": sum(x == y for x, y in zip(a, b)) / len(ids) if ids else None,
                            "cohen_kappa": kappa(a, b)}
    for i in ids:
        why = [t for t in ("track_A", "track_B")
               if m1[i][t] != m2[i][t] or "UNSURE" in (m1[i][t], m2[i][t])]
        if why:
            res["adjudication_queue"].append({"case_id": i, "tracks": why,
                                              "reviewer_1": {t: m1[i][t] for t in why}, "reviewer_2": {t: m2[i][t] for t in why}})
    return res


def finalize(l1: list[dict], l2: list[dict], adj: list[dict], conflicts: set[str], adjudicator: str) -> list[dict]:
    r1, r2 = l1[0]["reviewer"], l2[0]["reviewer"]
    people = [r1, r2, adjudicator]
    if len(set(people)) != 3:
        raise LabelError("the two reviewers and the adjudicator must be three different people")
    bad = sorted(set(people) & conflicts)
    if bad:
        raise LabelError(f"conflicted participants: {bad}")
    m1, m2 = {l["case_id"]: l for l in l1}, {l["case_id"]: l for l in l2}
    ma = {(x["case_id"], x["track"]): x for x in adj}
    for x in adj:
        if x.get("adjudicator") != adjudicator:
            raise LabelError(f"adjudication for {x['case_id']} not by {adjudicator}")
    gold = []
    for i in sorted(m1):
        row = {"case_id": i, "reviewers": [r1, r2], "adjudicator": adjudicator}
        for t, allowed in (("track_A", TRACK_A), ("track_B", TRACK_B)):
            a, b = m1[i][t], m2[i][t]
            if a == b and a != "UNSURE":
                row[t], row[t + "_basis"] = a, "reviewers agree"
            elif (i, t) in ma:
                v = ma[(i, t)]["label"]
                if v not in allowed:
                    raise LabelError(f"{i} {t}: invalid adjudicated label {v}")
                row[t], row[t + "_basis"] = v, "adjudicated"
            else:
                row[t], row[t + "_basis"] = "UNRESOLVED", "awaiting adjudication (excluded from scoring)"
        gold.append(row)
    return gold


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.pilot.labels")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("packets"); p.add_argument("--cases", type=Path, required=True)
    p.add_argument("--reviewer", action="append", required=True); p.add_argument("--seed", type=int, action="append", required=True)
    p.add_argument("--out", type=Path, required=True)
    g = sub.add_parser("agree"); g.add_argument("--cases", type=Path, required=True)
    g.add_argument("--labels", type=Path, nargs=2, required=True); g.add_argument("--out", type=Path, required=True)
    f = sub.add_parser("finalize"); f.add_argument("--cases", type=Path, required=True)
    f.add_argument("--labels", type=Path, nargs=2, required=True); f.add_argument("--adjudication", type=Path, required=True)
    f.add_argument("--adjudicator", required=True); f.add_argument("--conflicts", type=Path, required=True)
    f.add_argument("--agreement", type=Path, required=True); f.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    cases = _read(a.cases)
    ids = {c["case_id"] for c in cases}
    if a.cmd == "packets":
        if len(a.seed) != len(a.reviewer):
            raise SystemExit("one --seed per --reviewer")
        a.out.mkdir(parents=True, exist_ok=True)
        for r, rows in packets(cases, a.reviewer, dict(zip(a.reviewer, a.seed))).items():
            (a.out / f"packet-{r}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))
        return 0
    l1, l2 = _read(a.labels[0]), _read(a.labels[1])
    validate(l1, ids, l1[0]["reviewer"]); validate(l2, ids, l2[0]["reviewer"])
    if a.cmd == "agree":
        res = agree(l1, l2)
        res["inputs"] = {str(x): _digest(x) for x in (a.cases, *a.labels)}
        a.out.write_text(json.dumps(res, indent=1))
        print(json.dumps(res["tracks"], indent=1), len(res["adjudication_queue"]), "to adjudicate")
        return 0
    ag = json.loads(a.agreement.read_text())
    if ag.get("inputs") != {str(x): _digest(x) for x in (a.cases, *a.labels)}:
        raise SystemExit("agreement report does not match these inputs: run `agree` first on the same files")
    conflicts = {l.strip() for l in a.conflicts.read_text().splitlines() if l.strip() and not l.startswith("#")}
    gold = finalize(l1, l2, _read(a.adjudication), conflicts, a.adjudicator)
    a.out.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in gold))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
