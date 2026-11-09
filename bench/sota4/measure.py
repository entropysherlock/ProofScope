"""Evaluation A (SOTA-4): the frozen SOTA-3 CJCS engine against the SOTA-4 one-process engine, case by case,
under the same accounting as the benchmark runner (bench/limits.py: whole-process-tree CPU, peak tree RSS).

Each case is one fresh invocation `python -m <engine module> run <spec> --out <fresh dir> --jobs 1`, exactly
the command shape of bench/adapters/proofscope.py:engine_cmd (so the extractor build is charged to every
case, for both engines, as in the benchmark).

Lean process counting does not trust the engines: a shim directory placed first on PATH wraps `lean`,
`leanchecker` and the REPL; every launch appends its argv to a log. A launch that elaborates or replays a
module counts as an environment load; `lean --version` / `--print-prefix` style queries do not.

    python -m bench.sota4.measure --engine cjcs --engine cjcs4 --specs research/cjcs/core_dev/*.json \
        --out evidence/perf --cpu-ceiling 900 --mem-mb 12000
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import sys
from pathlib import Path

from bench.limits import run_limited

REPO = Path(__file__).resolve().parents[2]
MODULES = {"cjcs": "proofscope.experimental.cjcs", "cjcs4": "proofscope.experimental.cjcs4"}
NON_LOAD = ("--version", "--print-prefix", "--print-libdir", "--githash", "--help")


def make_shims(shim: Path, log: Path) -> dict:
    shim.mkdir(parents=True, exist_ok=True)
    real = {"lean": shutil.which("lean"), "leanchecker": shutil.which("leanchecker"),
            "repl": os.environ.get("PROOFSCOPE_REPL") or shutil.which("repl")}
    for name, exe in real.items():
        if not exe:
            continue
        p = shim / name
        p.write_text(f'#!/bin/sh\nprintf "%s\\t%s\\n" "{name}" "$*" >> "{log}"\nexec "{exe}" "$@"\n')
        p.chmod(0o755)
    # keep the toolchain siblings (lake, ...) reachable for Toolchain.find()
    lean_bin = Path(real["lean"]).resolve().parent
    for f in lean_bin.iterdir():
        if not (shim / f.name).exists():
            (shim / f.name).symlink_to(f)
    return real


def count(log: Path) -> dict:
    c = {"lean_elab": 0, "leanchecker": 0, "repl": 0, "queries": 0}
    if log.exists():
        for line in log.read_text().splitlines():
            name, _, args = line.partition("\t")
            if any(a in args.split() for a in NON_LOAD):
                c["queries"] += 1
            elif name == "lean":
                c["lean_elab"] += 1
            else:
                c[name] += 1
    c["environment_loads"] = c["lean_elab"] + c["leanchecker"] + c["repl"]
    c["search_loads"] = None   # filled per engine below
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.sota4.measure")
    ap.add_argument("--engine", action="append", choices=sorted(MODULES), required=True)
    ap.add_argument("--specs", nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cpu-ceiling", type=float, default=900.0)
    ap.add_argument("--mem-mb", type=int, default=12000)
    ap.add_argument("--prebuilt", action="store_true",
                    help="build each engine's own Lean modules once, outside the per-case accounting, and copy them "
                         "into every case (variant B; both engines are treated identically). Default (variant A) is "
                         "the benchmark shape: every case builds them and is charged for it.")
    a = ap.parse_args(argv)
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    records = []
    pre = {}
    if a.prebuilt:
        from proofscope.toolchain import Toolchain
        import importlib
        for eng in a.engine:
            d = out / "_prebuilt" / eng
            if d.exists():
                shutil.rmtree(d)
            m = importlib.import_module(MODULES[eng])
            b = (m.build if hasattr(m, "build") else importlib.import_module("proofscope.adelta12").build)(Toolchain.find(), d)
            if not b["ok"]:
                raise SystemExit(f"prebuild failed for {eng}: {b}")
            pre[eng] = d
    for eng in a.engine:
        for spec in a.specs:
            sp = Path(spec).resolve()
            work = out / eng / sp.stem
            if work.exists():
                shutil.rmtree(work)
            work.mkdir(parents=True)
            if eng in pre:
                shutil.copytree(pre[eng], work / "ps_out" / "build")
            log = work / "launches.tsv"
            shim = work / "shim"
            real = make_shims(shim, log)
            env = dict(os.environ)
            env["PATH"] = f"{shim}{os.pathsep}{env.get('PATH', '')}"
            if real.get("repl"):
                env["PROOFSCOPE_REPL"] = str(shim / "repl")
            cmd = [sys.executable, "-m", MODULES[eng], "run", str(sp), "--out", str(work / "ps_out"), "--jobs", "1"]
            r = run_limited(cmd, a.cpu_ceiling, a.mem_mb, 2 * a.cpu_ceiling + 120, cwd=str(REPO), env=env, inputs=(str(sp),))
            rowp = work / "ps_out" / "rows" / f"{sp.stem}.json"
            row = json.loads(rowp.read_text()) if rowp.exists() else {}
            c = count(log)
            # build steps (extractor / search module) compile modules too; they are counted, not hidden
            c["search_loads"] = (c["repl"] if eng == "cjcs4" else None)
            spec_d = json.loads(sp.read_text())
            rec = {"engine": eng, "variant": "B_prebuilt" if a.prebuilt else "A_benchmark_shape", "case": sp.stem, "status": r.status, "cpu_tree_s": round(r.cpu_tree_s, 3),
                   "wall_s": round(r.wall_s, 3), "max_rss_mb": round(r.max_rss_mb, 1), "processes_seen": r.processes_seen,
                   "launches": c, "verdict": row.get("verdict"), "direction": row.get("direction"),
                   "expected": spec_d.get("expected"), "must_not_be": spec_d.get("must_not_be") or [],
                   "certificates": sorted((row.get("certificates") or {}).keys()),
                   "certify_status": row.get("certify_status"), "failure_class": row.get("failure_class"),
                   "reason": row.get("reason"), "stats": row.get("stats"),
                   "stderr_tail": (r.stderr or "")[-1500:] if r.status != "OK" else ""}
            rec["exact"] = rec["verdict"] == rec["expected"] if rec["expected"] else None
            rec["must_not_violation"] = rec["verdict"] in rec["must_not_be"]
            records.append(rec)
            print(json.dumps({k: rec[k] for k in ("engine", "case", "status", "cpu_tree_s", "verdict", "exact")}), flush=True)
    summ = {}
    for eng in a.engine:
        rs = [r for r in records if r["engine"] == eng]
        cpu = sorted(r["cpu_tree_s"] for r in rs)
        summ[eng] = {"cases": len(rs), "ok_runs": sum(r["status"] == "OK" for r in rs),
                     "exact": sum(bool(r["exact"]) for r in rs), "must_not_violations": sum(r["must_not_violation"] for r in rs),
                     "certified_difference": sum(r["verdict"] == "CERTIFIED_LOGICAL_DIFFERENCE" for r in rs),
                     "certified_equivalence": sum(r["verdict"] == "CERTIFIED_LOGICAL_EQUIVALENCE" for r in rs),
                     "abstain": sum(r["verdict"] == "ABSTAIN" for r in rs),
                     "inconclusive_or_none": sum(r["verdict"] in (None, "INCONCLUSIVE", "INCONSISTENT") for r in rs),
                     "median_cpu_tree_s": statistics.median(cpu) if cpu else None,
                     "max_cpu_tree_s": max(cpu) if cpu else None,
                     "median_wall_s": statistics.median(r["wall_s"] for r in rs) if rs else None,
                     "max_rss_mb": max((r["max_rss_mb"] for r in rs), default=None),
                     "median_environment_loads": statistics.median(r["launches"]["environment_loads"] for r in rs) if rs else None}
    (out / "records.json").write_text(json.dumps(records, ensure_ascii=False, indent=1))
    (out / "summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
