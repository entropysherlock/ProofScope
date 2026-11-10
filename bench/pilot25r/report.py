"""PS-25R report: one row per original case (25), from the actual artifacts only."""
import argparse
import json
from pathlib import Path

from bench.pilot25r.cases import load


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.pilot25r.report")
    ap.add_argument("--matrix", type=Path)
    ap.add_argument("--telemetry", type=Path)
    ap.add_argument("--rerun", type=Path)
    ap.add_argument("--replay", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    mx = json.loads(a.matrix.read_text()) if a.matrix and a.matrix.exists() else {}
    recs = {json.loads(l)["case_id"]: json.loads(l) for l in a.rerun.read_text().splitlines()} if a.rerun and a.rerun.exists() else {}
    reps = {json.loads(l)["case_id"]: json.loads(l) for l in a.replay.read_text().splitlines()} if a.replay and a.replay.exists() else {}
    tel = {}
    if a.telemetry and a.telemetry.exists():
        for f in a.telemetry.rglob("*.frozen.json"):
            tel.setdefault(f.name.split(".")[0], {})["frozen"] = json.loads(f.read_text())
        for f in a.telemetry.rglob("*.recovered.json"):
            tel.setdefault(f.name.split(".")[0], {})["recovered"] = json.loads(f.read_text())
    rows = []
    for d in load():
        cid = d["id"]
        r, t = recs.get(cid, {}), tel.get(cid, {})
        rows.append({"case_id": cid, "original_sha256": d["original_sha256"], "adapted": d["source_status"] == "ADAPTED_UNVERIFIED",
                     "input_class": (mx.get(cid) or {}).get("class", "NOT_ADAPTABLE" if d["source_status"] != "ADAPTED_UNVERIFIED" else None),
                     "unknown_identifiers": (mx.get(cid) or {}).get("unknown_identifiers"),
                     "rerun_status": r.get("status"), "rerun_claim": (r.get("claim") or {}).get("claim"),
                     "replay": (reps.get(cid) or {}).get("replay"), "rerun_peak_rss_mb": r.get("max_rss_mb"), "rerun_cpu_s": r.get("cpu_tree_s"),
                     "frozen_peak_vmrss_mb": (t.get("frozen") or {}).get("peak", {}).get("tree_vmrss_mb"),
                     "frozen_peak_anon_mb": (t.get("frozen") or {}).get("peak", {}).get("tree_anon_mb"),
                     "frozen_verdict": (t.get("frozen") or {}).get("verdict"),
                     "recovered_peak_vmrss_mb": (t.get("recovered") or {}).get("peak", {}).get("tree_vmrss_mb"),
                     "recovered_peak_anon_mb": (t.get("recovered") or {}).get("peak", {}).get("tree_anon_mb"),
                     "recovered_verdict": (t.get("recovered") or {}).get("verdict"),
                     "search_stage_anon_mb": ((t.get("frozen") or {}).get("stages", {}).get("SEARCH") or {}).get("peak_anon_mb")})
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "pilot25r_report.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    cols = ["case_id", "adapted", "input_class", "rerun_status", "rerun_claim", "replay", "rerun_peak_rss_mb",
            "frozen_peak_vmrss_mb", "frozen_peak_anon_mb", "search_stage_anon_mb", "recovered_peak_vmrss_mb", "frozen_verdict", "recovered_verdict"]
    md = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows]
    (a.out / "pilot25r_report.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
