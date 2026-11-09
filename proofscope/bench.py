"""Benchmark runner for theorem-level comparison (v0.9) and adversarial certificate cases.

    python3 -m proofscope.bench --split dev|heldout|all --out DIR

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
    ap.add_argument("--split", default="all", choices=["dev", "heldout", "all"])
    ap.add_argument("--out", default="proofscope-bench")
    ap.add_argument("--skip-adversarial", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    tc = Toolchain.find()
    splits = ["dev", "heldout"] if a.split == "all" else [a.split]
    rows = []
    for sp in splits:
        for f in sorted((HERE / sp).glob("*.json")):
            raw = json.loads(f.read_text())
            spec = CompareSpec.load(f)
            t0 = time.time()
            r = run_compare(spec, tc, out / "work" / sp / spec.ident)
            r["seconds"] = round(time.time() - t0, 2)
            r["fidelity_failure"] = raw["fidelity_failure"]
            r["baseline"] = baseline_label(raw)
            rows.append(r)
            mark = "ok" if r.get("correct") else f"expected {spec.expected}"
            print(f"[{sp}] {spec.id:<26} {r['classification']:<18} {mark}", flush=True)
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
