"""Stage-level trace of the frozen ProofScope v1.2 engine (or experimental CJCS) on one pair (SOTA-3).

    python -m bench.diagnose --ref '<closed prop>' --lean '<closed prop>' --out DIR [--import-baseline]

Every Lean/leanchecker process the engine starts is recorded (which stage, which file, CPU incl. its
children, wall, exit code) by wrapping `Toolchain.run` in this process only; the engine files are not
modified. `--import-baseline` also times a file that only imports the configured modules, to separate
the fixed cost of loading Mathlib from search and checking. No budget is applied: this is a measurement.
"""
from __future__ import annotations

import argparse
import json
import resource
import time
from pathlib import Path

from proofscope import adelta12 as A
from proofscope import toolchain as T

CALLS: list[dict] = []
_orig = T.Toolchain.run


def _traced(self, cmd, *args, **kw):
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.monotonic()
    res = _orig(self, cmd, *args, **kw)
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    target = next((c for c in reversed(cmd) if c.endswith(".lean")), cmd[-1])
    name = Path(target).name
    stage = ("extract" if "Assumptions_input" in name else "cjcs_stage1_search" if name.endswith("Search.lean") else "witness_read" if "Witness_read" in name else
             "certify_probe" if name.endswith("Probe.lean") else "replay" if "leanchecker" in cmd[0] else
             "certify_compile" if "ProofScopeCert" in str(cmd) or name.startswith(("AD_", "MIN_", "CJ_")) else
             "build_extractor" if "AssumptionExtract11" in name else "other")
    CALLS.append({"stage": stage, "file": name, "cpu_s": round((r1.ru_utime + r1.ru_stime) - (r0.ru_utime + r0.ru_stime), 3),
                  "wall_s": round(time.monotonic() - t0, 3), "returncode": getattr(res, "returncode", None),
                  "max_rss_mb_cumulative": round(r1.ru_maxrss / 1024, 1)})
    return res


def import_baseline(tc, work: Path) -> dict:
    f = work / "ImportOnly.lean"
    f.write_text(A.import_lines() + "\n")
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.monotonic()
    res = _orig(tc, [tc.lean, str(f)], cwd=work, timeout=600)
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {"imports": A.IMPORTS, "cpu_s": round((r1.ru_utime + r1.ru_stime) - (r0.ru_utime + r0.ru_stime), 3),
            "wall_s": round(time.monotonic() - t0, 3), "returncode": res.returncode}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.diagnose")
    ap.add_argument("--ref", required=True)
    ap.add_argument("--lean", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--import-baseline", action="store_true")
    ap.add_argument("--engine", choices=["v12", "cjcs"], default="v12")
    a = ap.parse_args(argv)
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    tc = T.Toolchain.find()
    T.Toolchain.run = _traced
    try:
        t0 = time.monotonic()
        b = A.build(tc, out / "build")
        if a.engine == "cjcs":
            from proofscope.experimental import cjcs
            row = cjcs.run_case({"id": "diag", "reference": a.ref, "lean": a.lean}, tc, out / "build", out / "work")
        else:
            row = A.run_case({"id": "diag", "reference": a.ref, "lean": a.lean}, tc, out / "build", out / "work")
        total_wall = time.monotonic() - t0
    finally:
        T.Toolchain.run = _orig
    rep = {"engine": a.engine, "verdict": row.get("verdict"), "direction": row.get("direction"), "regions": row.get("regions"), "certificates": sorted((row.get("certificates") or {}).keys()),
           "rejected": row.get("rejected"), "build_ok": b.get("ok"), "calls": CALLS,
           "lean_processes": len(CALLS), "total_cpu_s": round(sum(c["cpu_s"] for c in CALLS), 3),
           "total_wall_s": round(total_wall, 3),
           "obligations": {k: v for k, v in (row.get("extraction") or {}).items() if k in ("added", "dropped", "hyps")}}
    if a.import_baseline:
        rep["import_baseline"] = import_baseline(tc, out)
        rep["import_cost_share"] = round(rep["import_baseline"]["cpu_s"] * sum(c["stage"] != "build_extractor" for c in CALLS)
                                         / max(rep["total_cpu_s"], 1e-9), 3)
    (out / "diagnosis.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in rep.items() if k != "calls"}, indent=1, ensure_ascii=False))
    for c in CALLS:
        print(f"  {c['stage']:16s} cpu {c['cpu_s']:7.3f}  wall {c['wall_s']:7.3f}  rc {c['returncode']}  {c['file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
