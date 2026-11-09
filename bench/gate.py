"""Availability gates (SOTA-2, amendment A8). Fail closed: a system is available for blind benchmarking
only if it produced a valid mathematical evaluation, within the budget, of BOTH equivalent calibration
fixtures. The gate does not require any particular verdict (no tool is asked to make an unsupported
claim); the non-equivalent fixture is reported separately and never gates.

    python -m bench.gate --runs DIR --cases bench/fixtures/availability.cases.jsonl --tier 20 --out availability.json

Exit status 1 if any system fails its gate; every record is still written to the report.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .canonical import read_jsonl

GATE_CASES = ("avail-calibration-identical", "avail-equivalent-rename")
EVALUATED = ("EVALUATED_POSITIVE_KERNEL", "EVALUATED_POSITIVE_STRUCTURAL", "EVALUATED_NEGATIVE_LOGICAL",
             "EVALUATED_NEGATIVE_FIDELITY", "EVALUATED_ABSTAIN")
SYSTEMS = ("proofscope", "semanteq", "beqplus")
EXPERIMENTAL = ("cjcs",)


def system_report(recs: dict[str, dict], cases: list[str], manifests: list[dict]) -> dict:
    rows = {}
    for cid in cases:
        r = recs.get(cid)
        if r is None:
            rows[cid] = {"evaluation_class": "MISSING_RECORD"}
            continue
        run = r.get("run") or {}
        rows[cid] = {"status": r.get("status"), "evaluation_class": r.get("evaluation_class"),
                     "native_verdict": r.get("native_verdict"), "certificate_kind": r.get("certificate_kind"),
                     "certified_A": r["track_A"]["certified"], "certified_B": r["track_B"]["certified"],
                     "cpu_tree_s": run.get("cpu_tree_s"), "cpu_overshoot_s": run.get("cpu_overshoot_s"),
                     "wall_s": run.get("wall_s"), "max_rss_mb": run.get("max_rss_mb"),
                     "processes_seen": run.get("processes_seen"), "budget": r.get("budget"),
                     "note": (r.get("adapter", {}).get("error") or r.get("error") or
                              (r.get("log_tail") or "")[-300:] if r.get("status") != "OK" else None)}
    present = [x for x in rows.values() if x["evaluation_class"] != "MISSING_RECORD"]
    gate = {cid: rows.get(cid, {}).get("evaluation_class") in EVALUATED and bool((rows.get(cid, {}).get("budget") or {}).get("compliant"))
            for cid in GATE_CASES if cid in cases}
    return {
        "infrastructure_ready": bool(present),
        "native_initialized": any(x["evaluation_class"] in EVALUATED for x in present),
        "valid_mathematical_evaluations": sum(x["evaluation_class"] in EVALUATED for x in present),
        "certified_positive_kernel": sum(x["evaluation_class"] == "EVALUATED_POSITIVE_KERNEL" for x in present),
        "positive_structural_only": sum(x["evaluation_class"] == "EVALUATED_POSITIVE_STRUCTURAL" for x in present),
        "certified_negative": sum(x["evaluation_class"] in ("EVALUATED_NEGATIVE_LOGICAL", "EVALUATED_NEGATIVE_FIDELITY") for x in present),
        "abstentions": sum(x["evaluation_class"] == "EVALUATED_ABSTAIN" for x in present),
        "resource_exhausted": sum(x["evaluation_class"] == "RESOURCE_EXHAUSTED" for x in present),
        "not_evaluated": sum(x["evaluation_class"] in ("NOT_EVALUATED_INFRA", "INPUT_NOT_EVALUABLE", "MISSING_RECORD")
                             for x in rows.values()),
        "startup_allowance_cpu_s": sorted({m.get("startup_allowance_cpu_s") for m in manifests}, key=str),
        "calibration_runs_cpu_s": [run.get("cpu_tree_s") for m in manifests for run in
                                   [(x.get("run") or {}) for x in ((m.get("calibration") or {}).get("runs") or [])]],
        "gate_cases": gate,
        "gate_pass": bool(gate) and all(gate.values()),
        "cases": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.gate")
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--tier", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--markdown", type=Path)
    a = ap.parse_args(argv)
    cases = [c["case_id"] for c in read_jsonl(a.cases)]
    rep = {"tier_cpu_s": a.tier, "systems": {}}
    present = {p.parent.parent.name for p in a.runs.glob(f"**/t{a.tier}/*.json")}
    for s in SYSTEMS + tuple(x for x in EXPERIMENTAL if x in present):
        recs, mans = {}, []
        for p in a.runs.glob(f"**/{s}/t{a.tier}/*.json"):
            d = json.loads(p.read_text())
            if p.name.startswith("manifest"):
                mans.append(d)
            elif p.name.endswith(".r0.json"):
                recs[d["case_id"]] = d
        rep["systems"][s] = system_report(recs, cases, mans)
    rep["all_gates_pass"] = all(v["gate_pass"] for k, v in rep["systems"].items() if k in SYSTEMS)
    a.out.write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    md = [f"## SOTA-1 availability gates (tier {a.tier} CPU-s, whole process tree)", ""]
    for s, v in rep["systems"].items():
        md.append(f"### {s}: gate {'PASS' if v['gate_pass'] else 'FAIL'}; startup allowance {v['startup_allowance_cpu_s']} "
                  f"(calibration CPU {v['calibration_runs_cpu_s']})")
        md.append("| case | status | class | native verdict | cert. kind | A / B | tree CPU s | overshoot | wall s | peak RSS MB | procs | compliant | note |")
        md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for cid, r in v["cases"].items():
            b = r.get("budget") or {}
            note = (r.get("note") or "").replace("|", "/").replace("\n", " ")[:160]
            md.append(f"| {cid} | {r.get('status')} | {r['evaluation_class']} | {r.get('native_verdict')} | {r.get('certificate_kind')} | "
                      f"{r.get('certified_A')} / {r.get('certified_B')} | {r.get('cpu_tree_s')} | {r.get('cpu_overshoot_s')} | "
                      f"{r.get('wall_s')} | {r.get('max_rss_mb')} | {r.get('processes_seen')} | {b.get('compliant')} | {note} |")
        md.append("")
    md.append(f"**All gates pass: {rep['all_gates_pass']}**. Outcome classes only; no accuracy without released gold.")
    text = "\n".join(md) + "\n"
    if a.markdown:
        a.markdown.write_text(text)
    print(text)
    return 0 if rep["all_gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
