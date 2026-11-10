"""Scoring against separately held gold labels, after execution and replay are sealed.

Outcome classes (mutually exclusive, one per case; denominators always = all manifest cases):
  RESOURCE_EXHAUSTED, INFRA_ERROR, INPUT_NOT_EVALUABLE, ABSTAIN, INVALID_CERTIFICATE (a decisive claim whose
  certificate failed replay or is missing: never counted as certified), GOLD_UNRESOLVED (decisive and
  verified, but the gold is unresolved: reported apart, never scored as success or error),
  CORRECT, INCORRECT, CLOSED_ONLY_AGREEMENT (certified closed equivalence of two statements both true or both
  false while the gold relation is not EQUIVALENT: true at the closed level, not a formulation verdict),
  CLOSED_ONLY_UNCHECKED (same, gold gives no closed truth values), REPAIR_MISMATCH (verified repair that is not
  an intended one), MINIMALITY_CONFLICT (gold lists an acceptable repair cheaper than the certified minimum:
  the certificate and the gold disagree; routed to re-adjudication, counted as a decisive error until resolved).
A timeout, abstention or missing certificate is never a negative result.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from bench.sota7.blind import load_gold, load_public, verify_manifest
from bench.sota7.runner import verify_seal

NONEQ = {"REF_STRONGER", "CAND_STRONGER", "INCOMPARABLE", "NOT_EQUIVALENT"}
DECISIVE_CLAIMS = {"EQUIVALENT_CLOSED", "NOT_EQUIVALENT_CLOSED", "MINIMAL_REPAIR", "VERIFIED_REPAIR", "NO_REPAIR_IN_GRAMMAR"}
ERRORS = {"INCORRECT", "MINIMALITY_CONFLICT"}


def classify(rec: dict, rep: dict, gold: dict) -> str:
    cl = rec["claim"]["claim"]
    if cl == "RESOURCE_EXHAUSTED":
        return "RESOURCE_EXHAUSTED"
    if cl in ("INFRA_ERROR", "NO_OUTPUT", "ENGINE_INCONCLUSIVE"):
        return "INFRA_ERROR"
    if cl == "INPUT_NOT_EVALUABLE":
        return "INPUT_NOT_EVALUABLE"
    if cl == "ABSTAIN":
        return "ABSTAIN"
    if cl not in DECISIVE_CLAIMS:
        return "INFRA_ERROR"
    if rep.get("replay") != "VERIFIED":
        return "INVALID_CERTIFICATE"
    if gold["relation"] == "UNRESOLVED":
        return "GOLD_UNRESOLVED"
    rel, ct = gold["relation"], gold.get("closed_truth")
    if cl == "NOT_EQUIVALENT_CLOSED":
        if rel == "EQUIVALENT":
            return "INCORRECT"
        if ct and any(ct.get(k) not in (None, "UNKNOWN") and ct[k] != rec["claim"]["closed_truth"][k] for k in ("reference", "candidate")):
            return "INCORRECT"
        return "CORRECT"
    if cl == "EQUIVALENT_CLOSED":
        if rel == "EQUIVALENT":
            return "CORRECT"
        basis = rec["claim"].get("basis")
        if basis == "definitional":
            return "INCORRECT"
        want = {"both_true": "TRUE", "both_false": "FALSE"}.get(basis)
        if not ct or "UNKNOWN" in (ct.get("reference"), ct.get("candidate")):
            return "CLOSED_ONLY_UNCHECKED"
        return "CLOSED_ONLY_AGREEMENT" if ct["reference"] == ct["candidate"] == want else "INCORRECT"
    ir = gold["intended_repairs"]
    if cl == "NO_REPAIR_IN_GRAMMAR":
        return "CORRECT" if ir == "NONE_IN_GRAMMAR" else "INCORRECT"
    if ir == "NONE_IN_GRAMMAR":
        return "INCORRECT"
    got = [sorted(r) for r in rec["claim"]["repairs"]]
    if cl == "MINIMAL_REPAIR" and any(len(g) < rec["claim"]["minimal_cost"] for g in ir):
        return "MINIMALITY_CONFLICT"
    return "CORRECT" if any(sorted(g) in got for g in ir) else "REPAIR_MISMATCH"


def binom_cdf(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson(k: int, n: int, alpha: float = 0.05):
    if n == 0:
        return None
    def solve(f):
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) else (lo, mid)
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(lambda p: 1 - binom_cdf(k - 1, n, p) < alpha / 2)
    upper = 1.0 if k == n else solve(lambda p: binom_cdf(k, n, p) > alpha / 2)
    return [round(lower, 4), round(upper, 4)]


def pct(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    i = min(len(xs) - 1, max(0, math.ceil(q * len(xs)) - 1))
    return xs[i]


def score(manifest: Path, public: Path, gold_file: Path, run: Path, replay: Path) -> dict:
    m = verify_manifest(manifest, public, gold_file)
    seal = verify_seal(run)
    if seal["manifest_sha256"] != m["manifest_sha256"]:
        raise RuntimeError("records were produced under a different manifest")
    cases = load_public(public)
    gold = load_gold(gold_file, cases)
    recs = {json.loads(l)["case_id"]: json.loads(l) for l in (run / "records.jsonl").read_text().splitlines()}
    reps = {json.loads(l)["case_id"]: json.loads(l) for l in Path(replay).read_text().splitlines()}
    if set(recs) != set(cases):
        raise RuntimeError("records do not cover the manifest cases")
    rows = []
    for cid in sorted(cases):
        r = recs[cid]
        cls = classify(r, reps.get(cid, {}), gold[cid])
        rows.append({"case_id": cid, "task": cases[cid]["task"], "domain": cases[cid]["domain"],
                     "difficulty": cases[cid]["difficulty"], "claim": r["claim"]["claim"], "class": cls,
                     "gold_relation": gold[cid]["relation"], "labeler_class": gold[cid]["labeler_class"],
                     "replay": reps.get(cid, {}).get("replay"), "cpu_tree_s": r["cpu_tree_s"], "wall_s": r["wall_s"],
                     "max_rss_mb": r["max_rss_mb"], "status": r["status"]})
    n = len(rows)
    cnt = Counter(x["class"] for x in rows)
    decisive_scored = [x for x in rows if x["class"] in {"CORRECT", "INCORRECT", "MINIMALITY_CONFLICT", "REPAIR_MISMATCH",
                                                         "CLOSED_ONLY_AGREEMENT", "CLOSED_ONLY_UNCHECKED"}]
    errs = sum(x["class"] in ERRORS for x in decisive_scored)
    cpu = [x["cpu_tree_s"] for x in rows]
    wall = [x["wall_s"] for x in rows]
    labeler = Counter(x["labeler_class"] for x in rows)
    res = {"manifest_sha256": m["manifest_sha256"], "dataset_version": m["dataset_version"],
           "engine_commit": m["engine_commit"], "cases": n, "classes": dict(sorted(cnt.items())),
           "labeler_classes": dict(labeler),
           "independent": labeler.get("INDEPENDENT", 0) == n and n > 0,
           "decisive_scored": len(decisive_scored), "decisive_errors": errs,
           "decisive_error_rate_ci95": clopper_pearson(errs, len(decisive_scored)),
           "correct_ci95_over_all_cases": clopper_pearson(cnt.get("CORRECT", 0), n),
           "coverage": {"decisive_fraction": round(sum(x["claim"] in DECISIVE_CLAIMS for x in rows) / n, 4) if n else None,
                        "verified_certificate_fraction": round(sum(x["replay"] == "VERIFIED" for x in rows) / n, 4) if n else None,
                        "by_domain": {d: dict(Counter(x["class"] for x in rows if x["domain"] == d)) for d in sorted({x["domain"] for x in rows})},
                        "by_difficulty": {d: dict(Counter(x["class"] for x in rows if x["difficulty"] == d)) for d in sorted({x["difficulty"] for x in rows})}},
           "performance": {"median_cpu_s": pct(cpu, 0.5), "p90_cpu_s": pct(cpu, 0.9), "p95_cpu_s": pct(cpu, 0.95),
                           "max_cpu_s": max(cpu) if cpu else None, "median_wall_s": pct(wall, 0.5),
                           "peak_rss_mb": max((x["max_rss_mb"] for x in rows), default=None),
                           "timeouts": cnt.get("RESOURCE_EXHAUSTED", 0), "infra_errors": cnt.get("INFRA_ERROR", 0)},
           "rows": rows}
    if errs == 0 and decisive_scored:
        res["zero_error_note"] = (f"0 decisive errors in {len(decisive_scored)}: the 95% upper bound on the error rate is "
                                  f"{res['decisive_error_rate_ci95'][1]}, not zero")
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.sota7.scoring")
    for k in ("manifest", "public", "gold", "run", "replay", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args(argv)
    res = score(a.manifest, a.public, a.gold, a.run, a.replay)
    a.out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
