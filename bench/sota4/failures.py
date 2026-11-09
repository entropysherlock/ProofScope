"""SOTA-4 Task H: case-level cause analysis of the SOTA-3 CJCS development records that were not evaluated.

Input: the unchanged SOTA-3 benchmark records (`runs/cjcs/t20/*.r0.json` from artifacts
`sota3-runs-cjcs-<shard>` of run 42701174017, downloaded read-only by the SOTA-4 workflow) and, if present,
their work directories. The original record and its original `evaluation_class` are copied verbatim into
the report; the cause classification is added beside them and never replaces them.

Cause classes (first that applies):
  RESOURCE_CPU_BUDGET        status TIMEOUT_CPU: the whole-tree CPU budget (tier + startup allowance) ran out
  RESOURCE_WALL              status TIMEOUT_WALL
  RESOURCE_MEMORY            status OOM
  ADAPTER_INPUT              the statement did not round-trip through the adapter (UNSUPPORTED_INPUT / NON_ELABORATING)
  ADAPTER_ENVIRONMENT        adapter step failed outside the declaration (ADAPTER_ERROR / ADAPTER_*)
  ENGINE_LAUNCH              LAUNCH_ERROR
  ENGINE_CRASH               status ERROR / KILLED with no engine row
  EXTRACTION                 engine row with reason "extraction failed"
  CERTIFICATE_INFRASTRUCTURE certify_status INFRASTRUCTURE_ERROR / PREAMBLE_ERROR
  SEARCH_INCOMPLETE          evaluated, ABSTAIN (not a failure; listed for completeness)
  UNCLASSIFIED               anything else (reported with the log tail for manual review)

For RESOURCE_* the last pipeline stage that started is reconstructed from the work directory (which Lean
inputs exist): extract, stage-1 search, certify probe, certificate compile, witness readout.

    python -m bench.sota4.failures --records <dir with *.r0.json> --out failures.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

STAGES = [("extract", "Assumptions_input.lean"), ("stage1_search", "*_s1Search.lean"), ("certify_probe", "*Probe.lean"),
          ("certificate_compile", "build/ProofScopeCert/*.olean"), ("witness_read", "Witness_read.lean")]


def last_stage(work: Path | None) -> str | None:
    if not work or not work.exists():
        return None
    seen = None
    for name, pat in STAGES:
        if any(work.rglob(pat)):
            seen = name
    return seen


def classify(rec: dict) -> str:
    st = rec.get("status")
    if st == "TIMEOUT_CPU":
        return "RESOURCE_CPU_BUDGET"
    if st == "TIMEOUT_WALL":
        return "RESOURCE_WALL"
    if st == "OOM":
        return "RESOURCE_MEMORY"
    if st in ("UNSUPPORTED_INPUT", "NON_ELABORATING"):
        return "ADAPTER_INPUT"
    if st and st.startswith("ADAPTER"):
        return "ADAPTER_ENVIRONMENT"
    if st == "LAUNCH_ERROR":
        return "ENGINE_LAUNCH"
    if rec.get("native_verdict") is None:
        return "ENGINE_CRASH"
    if rec.get("reason") == "extraction failed":
        return "EXTRACTION"
    if rec.get("certify_status") in ("INFRASTRUCTURE_ERROR", "PREAMBLE_ERROR"):
        return "CERTIFICATE_INFRASTRUCTURE"
    if rec.get("native_verdict") == "ABSTAIN":
        return "SEARCH_INCOMPLETE"
    return "UNCLASSIFIED"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.sota4.failures")
    ap.add_argument("--records", type=Path, required=True)
    ap.add_argument("--work", type=Path, default=None, help="runs/work/cjcs/t20 if available")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    files = sorted(a.records.rglob("*.r0.json"))
    rows, counts = [], {}
    for f in files:
        rec = json.loads(f.read_text())
        ev = rec.get("evaluation_class")
        if ev and ev.startswith("EVALUATED_") and ev != "EVALUATED_ABSTAIN":
            continue
        cid = rec.get("case_id") or f.name.split(".r0.json")[0]
        work = (a.work / cid / "r0") if a.work else None
        cause = classify(rec)
        run = rec.get("run") or {}
        rows.append({"case_id": cid, "original_status": rec.get("status"), "original_evaluation_class": ev,
                     "cause": cause, "last_stage_started": last_stage(work), "cpu_tree_s": run.get("cpu_tree_s"),
                     "limit_cpu_s": (rec.get("budget") or {}).get("limit_cpu_s"), "wall_s": run.get("wall_s"),
                     "max_rss_mb": run.get("max_rss_mb"), "native_verdict": rec.get("native_verdict"),
                     "reason": rec.get("reason"), "log_tail": (rec.get("log_tail") or "")[-800:],
                     "original_record": rec})
        counts[cause] = counts.get(cause, 0) + 1
    rep = {"source_records": len(files), "not_evaluated_or_abstained": len(rows), "by_cause": counts, "cases": rows}
    a.out.write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps({k: rep[k] for k in ("source_records", "not_evaluated_or_abstained", "by_cause")}, indent=1))
    for r in rows:
        print(r["case_id"], r["original_evaluation_class"], r["cause"], r["last_stage_started"], r["cpu_tree_s"], r["limit_cpu_s"])
    return 0 if files else 3


if __name__ == "__main__":
    raise SystemExit(main())
