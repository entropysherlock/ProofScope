"""SOTA-5 reports (case level).

    python -m bench.sota5.report hostile --rows DIR/rows --specs research/cjcs/sota5_hostile
    python -m bench.sota5.report summary --mathlib DIR --out sota5_summary.json

`hostile` exits non-zero on a must-not violation or a relation record different from the expected one
when the verdict is decisive. `summary` reports, never enforces.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from proofscope.experimental.relations import describe


def hostile(a) -> int:
    bad = 0
    print("| case | verdict | relation | expected relation | must-not violated |\n|---|---|---|---|---|")
    for f in sorted(Path(a.specs).glob("*.json")):
        spec = json.loads(f.read_text())
        rp = Path(a.rows) / f.name
        row = json.loads(rp.read_text()) if rp.exists() else {"verdict": None}
        rel = describe(row)["relation"] if rp.exists() else None
        viol = row.get("verdict") in spec["must_not_be"]
        wrong_rel = row.get("verdict", "").startswith("CERTIFIED") and rel != spec.get("expected_relation") if row.get("verdict") else False
        bad += viol or wrong_rel
        print(f"| {spec['id']} | {row.get('verdict')} | {rel} | {spec.get('expected_relation')} | {viol} |")
    return 1 if bad else 0


def summary(a) -> int:
    recs, audit = [], []
    for f in Path(a.mathlib).rglob("records.json"):
        recs += json.loads(f.read_text())
    for f in Path(a.mathlib).rglob("_adapter_audit.log"):
        audit += json.loads(f.read_text())
    cpu = sorted(r["cpu_tree_s"] for r in recs)
    out = {
        "adapter_audit": {
            "cases": len(audit),
            "input_not_evaluable_v2": sorted(r["case_id"] for r in audit if r["status"] != "OK"),
            "v1_print_fails_frozen_check": sorted(r["case_id"] for r in audit
                                                  if any(s.get("v1", {}).get("v1_check") is False for s in r["sides"].values())),
            "v1_unchecked_strings_differ": sorted(r["case_id"] for r in audit if r["v1_unchecked_would_differ"]),
            "v1_check_passes_but_standalone_fails": sorted(
                r["case_id"] for r in audit if any(s.get("v1", {}).get("v1_check") and not s["v1"].get("v2_standalone_check")
                                                   for s in r["sides"].values()))},
        "measurement": {
            "cases": len(recs), "statuses": {s: sum(r["status"] == s for r in recs) for s in {r["status"] for r in recs}},
            "verdicts": {v: sum(str(r["verdict"]) == v for r in recs) for v in {str(r["verdict"]) for r in recs}},
            "must_not_violations": sorted(r["case"] for r in recs if r["must_not_violation"]),
            "median_cpu_tree_s": statistics.median(cpu) if cpu else None, "max_cpu_tree_s": cpu[-1] if cpu else None,
            "median_environment_loads": statistics.median(r["launches"]["environment_loads"] for r in recs) if recs else None,
            "cases_detail": sorted(({k: r[k] for k in ("case", "status", "cpu_tree_s", "wall_s", "max_rss_mb", "verdict",
                                                      "expected", "must_not_violation", "certificates", "failure_class")}
                                    for r in recs), key=lambda x: x["case"])},
        "sota4_reference": {"cases": 27, "must_not_violations": 1, "median_cpu_tree_s": 28.36,
                            "note": "SOTA-4 extended measurement used bench/sota4/specs.py, which skipped the adapter check"},
    }
    m = out["measurement"]
    out["checks"] = {
        "no_must_not_violation": {"value": m["must_not_violations"], "pass": not m["must_not_violations"]},
        "median_cpu_le_10s": {"value": m["median_cpu_tree_s"], "pass": (m["median_cpu_tree_s"] or 1e9) <= 10},
        "coverage_note": "cases dropped as INPUT_NOT_EVALUABLE are reported, never scored as correct",
    }
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("```json\n" + json.dumps({k: out[k] for k in ("adapter_audit", "checks")}, ensure_ascii=False, indent=1) + "\n```")
    print(json.dumps({k: m[k] for k in ("cases", "statuses", "verdicts", "must_not_violations", "median_cpu_tree_s")}, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.sota5.report")
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hostile"); h.add_argument("--rows", required=True); h.add_argument("--specs", required=True)
    s = sub.add_parser("summary"); s.add_argument("--mathlib", required=True); s.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return {"hostile": hostile, "summary": summary}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
