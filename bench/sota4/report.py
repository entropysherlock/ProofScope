"""SOTA-4 machine-readable reports (case level; nothing averaged away).

    python -m bench.sota4.report core    --dirs <engine out dir>... --out core.json
    python -m bench.sota4.report hostile --records hostile/records.json
    python -m bench.sota4.report summary --mathlib <dir> --runs shards/runs --out sota4_summary.json

`core` and `hostile` exit non-zero on any must-not violation, any certificate whose axioms are outside
propext / Classical.choice / Quot.sound, or a certificate without an axiom report. `summary` never decides
the release status; it reports each acceptance check with its evidence.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

STD = {"propext", "Classical.choice", "Quot.sound"}


def _cert_problems(row: dict) -> list[str]:
    bad = []
    for k, c in (row.get("certificates") or {}).items():
        ax = c.get("axioms") if isinstance(c, dict) else None
        if ax is None:
            bad.append(f"{k}: no axiom report")
        elif not set(ax) <= STD:
            bad.append(f"{k}: axioms {ax}")
    return bad


def core(a) -> int:
    rows, fail = [], False
    print("| suite / engine | case | verdict | expected | must-not violated | certificates (axioms) |")
    print("|---|---|---|---|---|---|")
    for d in a.dirs:
        for f in sorted(Path(d).glob("rows/*.json")):
            r = json.loads(f.read_text())
            viol = r.get("verdict") in (r.get("must_not_be") or [])
            probs = _cert_problems(r)
            fail |= viol or bool(probs)
            certs = {k: (c.get("axioms") if isinstance(c, dict) else None) for k, c in (r.get("certificates") or {}).items()}
            rows.append({"dir": d, "case": r["id"], "engine": r.get("engine"), "verdict": r.get("verdict"),
                         "direction": r.get("direction"), "expected": r.get("expected"), "exact": r.get("verdict") == r.get("expected"),
                         "must_not_violation": viol, "certificate_problems": probs, "certificates": certs,
                         "certify_status": r.get("certify_status"), "failure_class": r.get("failure_class"),
                         "regions": r.get("regions")})
            print(f"| {d} | {r['id']} | {r.get('verdict')} {r.get('direction') or ''} | {r.get('expected')} | {viol} | "
                  + ", ".join(f"{k}{'' if not v else ' ' + '+'.join(v)}" for k, v in sorted(certs.items())) + " |")
    by = {}
    for r in rows:
        s = by.setdefault(r["dir"], {"cases": 0, "exact": 0, "must_not_violations": 0, "certificate_problems": 0})
        s["cases"] += 1
        s["exact"] += r["exact"]
        s["must_not_violations"] += r["must_not_violation"]
        s["certificate_problems"] += bool(r["certificate_problems"])
    Path(a.out).write_text(json.dumps({"by_dir": by, "rows": rows}, ensure_ascii=False, indent=1))
    print("\n" + json.dumps(by, indent=1))
    return 1 if fail else 0


def hostile(a) -> int:
    recs = json.loads(Path(a.records).read_text())
    fail = False
    print("| engine | case | status | verdict | expected | must-not violated | CPU s |")
    print("|---|---|---|---|---|---|---|")
    for r in recs:
        fail |= r["must_not_violation"]
        print(f"| {r['engine']} | {r['case']} | {r['status']} | {r['verdict']} | {r['expected']} | {r['must_not_violation']} | {r['cpu_tree_s']} |")
    return 1 if fail else 0


def summary(a) -> int:
    recs = []
    for f in sorted(Path(a.mathlib).rglob("records.json")):
        recs += json.loads(f.read_text())
    out = {"mathlib_measurement": {}, "harness": {}, "checks": {}}
    for eng in ("cjcs", "cjcs4"):
        rs = [r for r in recs if r["engine"] == eng]
        if not rs:
            continue
        cpu = sorted(r["cpu_tree_s"] for r in rs)
        out["mathlib_measurement"][eng] = {
            "cases": len(rs), "statuses": {s: sum(r["status"] == s for r in rs) for s in {r["status"] for r in rs}},
            "verdicts": {v: sum(r["verdict"] == v for r in rs) for v in {str(r["verdict"]) for r in rs}},
            "must_not_violations": sum(r["must_not_violation"] for r in rs),
            "exact_vs_provisional": sum(bool(r["exact"]) for r in rs),
            "median_cpu_tree_s": statistics.median(cpu), "max_cpu_tree_s": cpu[-1],
            "median_wall_s": statistics.median(r["wall_s"] for r in rs), "max_rss_mb": max(r["max_rss_mb"] for r in rs),
            "median_environment_loads": statistics.median(r["launches"]["environment_loads"] for r in rs),
            "max_repl_loads": max(r["launches"]["repl"] for r in rs),
            "cases_detail": [{k: r[k] for k in ("case", "status", "cpu_tree_s", "wall_s", "max_rss_mb", "verdict", "expected",
                                                "must_not_violation", "certificates", "failure_class")} | {"launches": r["launches"]}
                             for r in sorted(rs, key=lambda r: r["case"])]}
    runs = Path(a.runs)
    for sysdir in sorted(p for p in runs.glob("*") if p.is_dir() and p.name != "work"):
        cls = {}
        for f in sysdir.rglob("*.r0.json"):
            r = json.loads(f.read_text())
            cls[r.get("evaluation_class")] = cls.get(r.get("evaluation_class"), 0) + 1
        out["harness"][sysdir.name] = cls
    m3, m4 = out["mathlib_measurement"].get("cjcs"), out["mathlib_measurement"].get("cjcs4")
    if m4:
        out["checks"]["median_cpu_le_10s"] = {"value": m4["median_cpu_tree_s"], "pass": m4["median_cpu_tree_s"] <= 10}
        out["checks"]["at_most_one_search_load"] = {"value": m4["max_repl_loads"], "pass": m4["max_repl_loads"] <= 1}
        out["checks"]["no_must_not_violation"] = {"value": m4["must_not_violations"], "pass": m4["must_not_violations"] == 0}
    if m3 and m4:
        out["checks"]["no_fewer_decisive_than_sota3"] = {
            "sota3": sum(v for k, v in m3["verdicts"].items() if k.startswith("CERTIFIED")),
            "sota4": sum(v for k, v in m4["verdicts"].items() if k.startswith("CERTIFIED"))}
        out["checks"]["fewer_infrastructure_failures"] = {
            "sota3": sum(v for k, v in m3["statuses"].items() if k != "OK") + m3["verdicts"].get("INCONCLUSIVE", 0) + m3["verdicts"].get("None", 0),
            "sota4": sum(v for k, v in m4["statuses"].items() if k != "OK") + m4["verdicts"].get("INCONCLUSIVE", 0) + m4["verdicts"].get("None", 0)}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("```json\n" + json.dumps({k: out[k] for k in ("harness", "checks")}, indent=1) + "\n```")
    for eng, m in out["mathlib_measurement"].items():
        print(f"\n{eng}: median CPU {m['median_cpu_tree_s']} s, max {m['max_cpu_tree_s']} s, env loads {m['median_environment_loads']}, verdicts {m['verdicts']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.sota4.report")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("core")
    c.add_argument("--dirs", nargs="+", required=True)
    c.add_argument("--out", required=True)
    h = sub.add_parser("hostile")
    h.add_argument("--records", required=True)
    s = sub.add_parser("summary")
    s.add_argument("--mathlib", required=True)
    s.add_argument("--runs", required=True)
    s.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return {"core": core, "hostile": hostile, "summary": summary}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
