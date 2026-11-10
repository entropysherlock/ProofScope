"""SOTA-7 summary and readiness report from actual run outputs.

    python -m bench.sota7.report --scores S.json --checks evidence/ --out summary/
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.sota7.report")
    ap.add_argument("--scores", type=Path, required=True)
    ap.add_argument("--competitors", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    s = json.loads(a.scores.read_text())
    c = json.loads(a.competitors.read_text())
    a.out.mkdir(parents=True, exist_ok=True)
    summ = {"infrastructure": "dry run executed on SYNTHETIC_DEVELOPMENT fixtures",
            "independent_evaluation": "NOT RUN" if not s["independent"] else "RUN",
            "dry_run": {k: v for k, v in s.items() if k != "rows"}, "competitors": c["availability"]}
    (a.out / "sota7_summary.json").write_text(json.dumps(summ, indent=1))
    md = ["# SOTA-7 evaluation readiness", "",
          f"* Independent evaluation: **{summ['independent_evaluation']}**",
          f"* Dry run: {s['cases']} synthetic development cases (labels written by the engine developer; not evidence of accuracy)",
          f"* Outcome classes: {s['classes']}",
          f"* Decisive scored: {s['decisive_scored']}, decisive errors: {s['decisive_errors']}, 95% CI {s['decisive_error_rate_ci95']}",
          f"* Median / p95 / max CPU (s): {s['performance']['median_cpu_s']} / {s['performance']['p95_cpu_s']} / {s['performance']['max_cpu_s']}",
          f"* Competitors: {c['availability']} — {c['benchmark_runs']}", "",
          "| case | task | claim | class | gold | replay | CPU s |", "|---|---|---|---|---|---|---|"]
    md += [f"| {r['case_id']} | {r['task']} | {r['claim']} | {r['class']} | {r['gold_relation']} | {r['replay']} | {r['cpu_tree_s']} |" for r in s["rows"]]
    (a.out / "evaluation_readiness.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
