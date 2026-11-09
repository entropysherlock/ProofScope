"""Benchmark runner for theorem-level comparison (v0.9) and adversarial certificate cases.

    python3 -m proofscope.bench --split all|<split> [<split> ...] [--jobs N] --out DIR

Splits are the subdirectories of proofscope/benchmark/ that contain case files.

Metrics
  exact      engine label == annotated label
  detection  "flagged" = APPLICABILITY_GAP, CONCLUSION_GAP or VACUOUS (the formal statement does not establish the
             reference claim); INCONCLUSIVE is an abstention. Precision, recall, false-positive rate and coverage
             against the annotated `fidelity_failure`, with Wilson 95% intervals.
  baseline   a naive syntactic baseline that flags a failure whenever the formal and reference texts differ.
  adversarial certificate cases (proofscope/benchmark/adversarial_certificates.json): every one must be rejected.

Competitor systems (SemantEq, FormalRx(-CC), LeanTrail) were not run: they solve different tasks or need models
and data not available here, so no comparison is reported for them.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import math
import sys
import time
from pathlib import Path

from .certify import certify
from .compare import CompareSpec, run_compare
from .toolchain import Toolchain

HERE = Path(__file__).resolve().parent / "benchmark"
FLAG = {"APPLICABILITY_GAP", "CONCLUSION_GAP", "VACUOUS"}


def wilson(k: int, n: int) -> list | None:
    if n == 0:
        return None
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def detection(rows: list[dict], key: str) -> dict:
    tp = fp = fn = tn = ab = 0
    for r in rows:
        truth = r["fidelity_failure"]
        lab = r[key]
        if lab == "INCONCLUSIVE":
            ab += 1
            fn += truth
            continue
        f = lab in FLAG
        tp += f and truth
        fp += f and not truth
        fn += (not f) and truth
        tn += (not f) and (not truth)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "abstain": ab,
            "precision": round(tp / (tp + fp), 3) if tp + fp else None,
            "recall": round(tp / (tp + fn), 3) if tp + fn else None, "recall_ci95": wilson(tp, tp + fn),
            "false_positive_rate": round(fp / (fp + tn), 3) if fp + tn else None,
            "coverage": round(1 - ab / len(rows), 3) if rows else None}


def baseline_label(d: dict) -> str:
    norm = lambda s: " ".join(s.split())  # noqa: E731
    same = norm(d["lean_hyp"]) == norm(d["ref_hyp"]) and norm(d["lean_concl"]) == norm(d["ref_concl"])
    return "EQUIVALENT" if same else "CONCLUSION_GAP"


def _one(args):
    f, out = args
    raw = json.loads(Path(f).read_text())
    spec = CompareSpec.load(f)
    tc = Toolchain.find()
    t0 = time.time()
    r = run_compare(spec, tc, Path(out) / "work" / raw.get("split", "x") / spec.ident)
    r["seconds"] = round(time.time() - t0, 2)
    r["fidelity_failure"] = raw["fidelity_failure"]
    r["baseline"] = baseline_label(raw)
    r["label_source"] = raw.get("label_source", "hand-annotated")
    r["oracle_facts"] = raw.get("oracle_facts")
    return r


def by_family(rows: list[dict]) -> dict:
    fams: dict = {}
    for r in rows:
        f = fams.setdefault(r["family"] or "?", {"cases": 0, "exact": 0, "inconclusive": 0, "flag_tp": 0, "flag_fp": 0, "flag_fn": 0})
        f["cases"] += 1
        f["exact"] += bool(r.get("correct"))
        f["inconclusive"] += r["classification"] == "INCONCLUSIVE"
        flagged = r["classification"] in FLAG
        f["flag_tp"] += flagged and r["fidelity_failure"]
        f["flag_fp"] += flagged and not r["fidelity_failure"]
        f["flag_fn"] += (not flagged) and r["fidelity_failure"]
    return fams


def oracle_disagreements(rows: list[dict]) -> list[dict]:
    """A Lean certificate that contradicts a fact the finite oracle established (an existential witness the
    oracle found, or a universal the oracle refuted) means the oracle's Lean-semantics model or the engine is
    wrong. Universals the oracle only checked on a finite grid cannot contradict a certificate."""
    bad = []
    for r in rows:
        o = r.get("oracle_facts")
        if not o:
            continue
        c = set(r["certificates"])
        for ex, univ in (("app_gap", "hyp_cover"), ("concl_gap", "concl_cover"), ("strict_hyp", "hyp_back"),
                         ("strict_concl", "concl_back"), ("inhabited", "vacuous")):
            if o.get(ex) and univ in c:
                bad.append({"id": r["id"], "oracle_witness_for": ex, "engine_certified": univ})
            if not o.get(ex) and ex in c:
                bad.append({"id": r["id"], "engine_certified": ex, "oracle_found_no_witness_on_grid": True})
    return bad


def run_adversarial(tc: Toolchain, work: Path) -> list[dict]:
    cases = json.loads((HERE / "adversarial_certificates.json").read_text())
    out = []
    for c in cases:
        t0 = time.time()
        r = certify(c["ident"], c.get("header", ""), {"cert": (c["statement"], c["tactics"])}, tc, work / c["ident"])
        accepted = "cert" in r["certificates"]
        out.append({"id": c["ident"], "attack": c["attack"], "expected": c["expected"],
                    "result": "ACCEPTED" if accepted else "REJECTED",
                    "reason": r["rejected"].get("cert", r["status"]),
                    "correct": (accepted and c["expected"] == "ACCEPTED") or (not accepted and c["expected"] == "REJECTED"),
                    "seconds": round(time.time() - t0, 2)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m proofscope.bench")
    ap.add_argument("--split", nargs="+", default=["all"])
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--out", default="proofscope-bench")
    ap.add_argument("--skip-adversarial", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    tc = Toolchain.find()
    found = sorted(d.name for d in HERE.iterdir() if d.is_dir() and any(d.glob("*.json")))
    splits = found if a.split == ["all"] else a.split
    files = [(str(f), str(out)) for sp in splits for f in sorted((HERE / sp).glob("*.json"))]
    rows = []
    with cf.ProcessPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        for r in ex.map(_one, files):
            rows.append(r)
            mark = "ok" if r.get("correct") else f"expected {r['expected']}"
            print(f"[{r['split']}] {r['id']:<34} {r['classification']:<18} {mark}", flush=True)
    report = {"toolchain": tc.version(), "splits": {}}
    for sp in splits:
        rs = [r for r in rows if r["split"] == sp]
        if not rs:
            continue
        ex = sum(1 for r in rs if r.get("correct"))
        report["splits"][sp] = {
            "cases": len(rs), "exact_label_accuracy": f"{ex}/{len(rs)}", "exact_ci95": wilson(ex, len(rs)),
            "engine_detection": detection(rs, "classification"), "baseline_detection": detection(rs, "baseline"),
            "certificates": sum(len(r["certificates"]) for r in rs),
            "inconsistent_runs": sum(1 for r in rs if r["classification"] == "INCONSISTENT"),
            "median_seconds": sorted(r["seconds"] for r in rs)[len(rs) // 2],
            "p90_seconds": sorted(r["seconds"] for r in rs)[min(len(rs) - 1, int(0.9 * len(rs)))],
            "inconclusive_rate": round(sum(r["classification"] == "INCONCLUSIVE" for r in rs) / len(rs), 3),
            "by_family": by_family(rs),
            "oracle_disagreements": oracle_disagreements(rs),
            "label_sources": sorted({r["label_source"] for r in rs}),
            "misses": [{"id": r["id"], "expected": r["expected"], "got": r["classification"]} for r in rs if not r.get("correct")],
        }
    if not a.skip_adversarial:
        adv = run_adversarial(tc, out / "work" / "adversarial")
        report["adversarial_certificates"] = {"cases": len(adv), "correct": sum(r["correct"] for r in adv),
                                              "false_acceptances": [r for r in adv if r["result"] == "ACCEPTED" and r["expected"] == "REJECTED"],
                                              "rows": adv}
    report["competitors"] = ("not run: SemantEq, FormalRx and FormalRx-CC address statement equivalence or "
                             "NL-to-Lean diagnosis on other datasets and require models/data not available here; "
                             "LeanTrail was not located. No competitor numbers are reported.")
    (out / "bench_results.json").write_text(json.dumps({"report": report, "rows": rows}, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False)[:6000])
    bad = any(s["inconsistent_runs"] for s in report["splits"].values()) or \
        bool(report.get("adversarial_certificates", {}).get("false_acceptances"))
    print("\nVERDICT\n - " + ("A soundness problem was observed (inconsistent certificates or a false acceptance)."
                              if bad else "No soundness violation observed: no contradictory certificates and no "
                              "adversarial certificate accepted. Accuracy figures are on project-authored cases."))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
