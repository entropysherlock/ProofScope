"""Scoring and uncertainty for the SOTA-1 benchmark (pre-registered; docs/competitor_benchmark_protocol.md).

    python -m bench.score --runs runs/ --gold gold.jsonl --tier 20 --out metrics.json [--markdown report.md]

gold.jsonl (released only after all runs are locked):
    {"case_id": ..., "gold_A": "equivalent"|"non_equivalent"|"disputed"|"unassessable",
     "gold_B": ..., "group": ..., "source": ...}

Per system, track (A logical / B faithful) and reading (certified / native):
    TP  EQUIV on gold equivalent            FP  EQUIV on gold non-equivalent
    TN  NONEQUIV on gold non-equivalent     FN  NONEQUIV on gold equivalent
    ABSTAIN, and every infrastructure outcome, kept as its own count.
Recall and error rates use ALL eligible gold cases of that class as denominator (abstentions included).
Intervals: exact Clopper-Pearson for proportions; group-clustered percentile bootstrap (2000 resamples,
fixed seed) for precision/recall; exact two-sided McNemar on paired per-case correctness, Holm-adjusted.
Disputed/unassessable cases are excluded from the primary denominator and scored both ways in a
sensitivity table. Zero observed errors are reported with their exact upper bound, never as "zero risk".
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from .canonical import read_jsonl
from .outcomes import INFRA

GOLD_OK = ("equivalent", "non_equivalent")


def _binom_cdf(k: int, n: int, p: float) -> float:
    if p <= 0:
        return 1.0
    if p >= 1:
        return 0.0 if k < n else 1.0
    s, term = 0.0, (1 - p) ** n
    for i in range(0, k + 1):
        if i > 0:
            term *= (n - i + 1) / i * p / (1 - p)
        s += term
    return min(1.0, s)


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float] | None:
    if n == 0:
        return None

    def solve(f, lo=0.0, hi=1.0):
        for _ in range(100):
            mid = (lo + hi) / 2
            if f(mid):
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(lambda p: 1 - _binom_cdf(k - 1, n, p) >= alpha / 2)
    upper = 1.0 if k == n else solve(lambda p: _binom_cdf(k, n, p) <= alpha / 2)
    return (round(lower, 4), round(upper, 4))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts b, c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * _binom_cdf(k, n, 0.5))


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = round(running, 6)
    return out


def classify(pred: str, gold: str) -> str:
    if pred in INFRA or pred.startswith(("ADAPTER_", "RUNNER_", "ERROR")):
        return "INFRA:" + pred
    if pred not in ("EQUIV", "NONEQUIV"):
        return "ABSTAIN"
    return {("EQUIV", "equivalent"): "TP", ("EQUIV", "non_equivalent"): "FP",
            ("NONEQUIV", "non_equivalent"): "TN", ("NONEQUIV", "equivalent"): "FN"}[(pred, gold)]


def metrics(cells: list[str], golds: list[str]) -> dict:
    c = defaultdict(int)
    for x in cells:
        c[x] += 1
    tp, fp, tn, fn = c["TP"], c["FP"], c["TN"], c["FN"]
    n_eq, n_ne, n = golds.count("equivalent"), golds.count("non_equivalent"), len(cells)
    dec = tp + fp + tn + fn
    infra = sum(v for k, v in c.items() if k.startswith("INFRA:"))
    r = {"eligible": n, "gold_equivalent": n_eq, "gold_non_equivalent": n_ne, "TP": tp, "FP": fp, "TN": tn, "FN": fn,
         "ABSTAIN": c["ABSTAIN"], "INFRA": infra, "infra_breakdown": {k[6:]: v for k, v in c.items() if k.startswith("INFRA:")},
         "precision_equiv": round(tp / (tp + fp), 4) if tp + fp else None, "precision_equiv_ci": clopper_pearson(tp, tp + fp),
         "recall_equiv": round(tp / n_eq, 4) if n_eq else None, "recall_equiv_ci": clopper_pearson(tp, n_eq),
         "false_equivalence_rate": round(fp / n_ne, 4) if n_ne else None, "false_equivalence_ci": clopper_pearson(fp, n_ne),
         "false_difference_rate": round(fn / n_eq, 4) if n_eq else None, "false_difference_ci": clopper_pearson(fn, n_eq),
         "precision_nonequiv": round(tn / (tn + fn), 4) if tn + fn else None, "precision_nonequiv_ci": clopper_pearson(tn, tn + fn),
         "recall_nonequiv": round(tn / n_ne, 4) if n_ne else None, "recall_nonequiv_ci": clopper_pearson(tn, n_ne),
         "decisive_coverage": round(dec / n, 4) if n else None,
         "selective_accuracy": round((tp + tn) / dec, 4) if dec else None}
    return r


def cluster_bootstrap(rows: list[tuple[str, str, str]], stat, reps: int = 2000, seed: int = 20261109):
    """rows: (group, cell, gold). Percentile 95% interval of `stat(cells, golds)` resampling groups."""
    by = defaultdict(list)
    for g, cell, gold in rows:
        by[g].append((cell, gold))
    groups = sorted(by)
    if not groups:
        return None
    rng, vals = random.Random(seed), []
    for _ in range(reps):
        cells, golds = [], []
        for g in (rng.choice(groups) for _ in groups):
            for cell, gold in by[g]:
                cells.append(cell)
                golds.append(gold)
        v = stat(cells, golds)
        if v is not None:
            vals.append(v)
    if not vals:
        return None
    vals.sort()
    return (round(vals[int(0.025 * len(vals))], 4), round(vals[min(len(vals) - 1, int(0.975 * len(vals)))], 4))


def load_runs(runs: Path, tier: int) -> dict[str, dict[str, list[dict]]]:
    out = defaultdict(lambda: defaultdict(list))
    for p in sorted(runs.glob(f"*/t{tier}/*.json")):
        if p.name.startswith("manifest"):
            continue
        r = json.loads(p.read_text())
        out[r["system"]][r["case_id"]].append(r)
    return out


def score(runs: Path, gold_path: Path, tier: int) -> dict:
    gold = {g["case_id"]: g for g in read_jsonl(gold_path)}
    sysruns = load_runs(runs, tier)
    res = {"tier_cpu_s": tier, "cases_with_gold": len(gold), "systems": {}, "paired": {}, "missing_records": {}}
    correct = defaultdict(dict)
    for system, by_case in sysruns.items():
        res["missing_records"][system] = sorted(set(gold) - set(by_case))
        res["systems"][system] = {}
        for track in ("A", "B"):
            for reading in ("certified", "native"):
                rows, cells, golds, sens = [], [], [], {"disputed_as_equivalent": [], "disputed_as_non_equivalent": []}
                for cid, g in gold.items():
                    recs = by_case.get(cid)
                    pred = recs[0][f"track_{track}"][reading] if recs else "MISSING"
                    gl = g[f"gold_{track}"]
                    if gl in GOLD_OK:
                        cell = classify(pred, gl)
                        rows.append((g.get("group", cid), cell, gl))
                        cells.append(cell)
                        golds.append(gl)
                        if reading == "certified":
                            correct[(track, system)][cid] = cell in ("TP", "TN")
                    else:
                        sens["disputed_as_equivalent"].append(classify(pred, "equivalent"))
                        sens["disputed_as_non_equivalent"].append(classify(pred, "non_equivalent"))
                m = metrics(cells, golds)
                m["precision_equiv_cluster_ci"] = cluster_bootstrap(
                    rows, lambda c, g: (c.count("TP") / (c.count("TP") + c.count("FP"))) if c.count("TP") + c.count("FP") else None)
                m["recall_equiv_cluster_ci"] = cluster_bootstrap(
                    rows, lambda c, g: (c.count("TP") / g.count("equivalent")) if g.count("equivalent") else None)
                m["disputed_sensitivity"] = {k: {x: v.count(x) for x in set(v)} for k, v in sens.items()}
                m["by_source"] = {}
                for src in sorted({gold[c].get("source") for c in gold}):
                    ids = [cid for cid in gold if gold[cid].get("source") == src and gold[cid][f"gold_{track}"] in GOLD_OK]
                    m["by_source"][src] = metrics([classify((by_case.get(cid) or [{f"track_{track}": {reading: "MISSING"}}])[0][f"track_{track}"][reading],
                                                            gold[cid][f"gold_{track}"]) for cid in ids],
                                                  [gold[cid][f"gold_{track}"] for cid in ids])
                cpu = [r["run"]["cpu_s"] for recs in by_case.values() for r in recs if r.get("run")]
                m["cpu_s_quantiles"] = _quantiles(cpu)
                res["systems"][system][f"{track}/{reading}"] = m
    for track in ("A", "B"):
        systems = sorted(s for (t, s) in correct if t == track)
        pv = {}
        for i, s1 in enumerate(systems):
            for s2 in systems[i + 1:]:
                ids = set(correct[(track, s1)]) & set(correct[(track, s2)])
                b = sum(correct[(track, s1)][k] and not correct[(track, s2)][k] for k in ids)
                c = sum(correct[(track, s2)][k] and not correct[(track, s1)][k] for k in ids)
                key = f"{s1}_vs_{s2}"
                res["paired"][f"{track}:{key}"] = {"paired_cases": len(ids), f"{s1}_only_correct": b, f"{s2}_only_correct": c,
                                                   "mcnemar_exact_p": round(mcnemar_exact(b, c), 6)}
                pv[f"{track}:{key}"] = mcnemar_exact(b, c)
        for k, v in holm(pv).items():
            res["paired"][k]["holm_p"] = v
    return res


def _quantiles(xs):
    if not xs:
        return None
    xs = sorted(xs)
    q = lambda f: xs[min(len(xs) - 1, int(f * len(xs)))]
    return {"p50": q(0.5), "p90": q(0.9), "p99": q(0.99), "max": xs[-1], "n": len(xs)}


def markdown(res: dict) -> str:
    L = [f"# Scores at {res['tier_cpu_s']} CPU-s per pair", ""]
    for system, d in res["systems"].items():
        for key, m in d.items():
            L.append(f"## {system} — track {key}")
            L.append("| eligible | TP | FP | TN | FN | abstain | infra | prec(eq) [CP 95%] | recall(eq) [CP 95%] | false-eq rate [CP 95%] | coverage |")
            L.append("|---|---|---|---|---|---|---|---|---|---|---|")
            L.append(f"| {m['eligible']} | {m['TP']} | {m['FP']} | {m['TN']} | {m['FN']} | {m['ABSTAIN']} | {m['INFRA']} | "
                     f"{m['precision_equiv']} {m['precision_equiv_ci']} | {m['recall_equiv']} {m['recall_equiv_ci']} | "
                     f"{m['false_equivalence_rate']} {m['false_equivalence_ci']} | {m['decisive_coverage']} |")
            L.append("")
    L.append("## Paired comparisons (certified reading; exact McNemar, Holm)")
    for k, v in res["paired"].items():
        L.append(f"- {k}: {v}")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.score")
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--gold", type=Path, required=True)
    ap.add_argument("--tier", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--markdown", type=Path)
    a = ap.parse_args(argv)
    res = score(a.runs, a.gold, a.tier)
    a.out.write_text(json.dumps(res, indent=1))
    if a.markdown:
        a.markdown.write_text(markdown(res))
    print(markdown(res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
