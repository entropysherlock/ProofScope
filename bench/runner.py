"""Shared benchmark runner: every eligible system, every case, one budget tier, full evidence.

    python -m bench.runner --system proofscope --cases sealed/primary.cases.jsonl --tier 20 \
        --startup-allowance 0 --mem-mb 12000 --out runs/ [--shard i/n] [--tool-dir DIR] [--repeat 1]

Per pair, the external CPU limit is `tier + startup_allowance` seconds. The startup allowance is the
tool's median CPU on the frozen calibration pair (identical statements) measured in the pilot and
written into the run manifest BEFORE the primary run (protocol amendment A1, docs/sota1/). Adapter work
(format conversion, ProofScope's meaning-preservation check) is timed and reported separately and is not
charged to the tool. Every case gets exactly one record per system and repeat, whatever happened.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import time
from pathlib import Path

from .canonical import read_jsonl, sha256_file
from .limits import run_limited

ADAPTER_CPU_S, ADAPTER_WALL_S = 300, 600


def _shard(rows, spec):
    if not spec:
        return rows
    i, n = (int(x) for x in spec.split("/"))
    return [r for k, r in enumerate(rows) if k % n == i]


def run_proofscope(case, work: Path, budget: float, mem_mb: int, lean: str) -> dict:
    from .adapters import proofscope as A
    prep = A.prepare(case, work, [lean])
    rec = {"adapter": {}}
    if "unsupported" in prep:
        rec["status"] = "UNSUPPORTED_INPUT"
        rec["adapter"]["error"] = prep["unsupported"]
        return rec
    env = A.imports_env(prep["imports"])
    printed = {}
    for side, cmd in zip(("ref", "cand"), prep["print_cmds"]):
        r = run_limited(cmd, ADAPTER_CPU_S, mem_mb, ADAPTER_WALL_S, cwd=str(work), env=env)
        rec["adapter"][f"print_{side}"] = {k: v for k, v in r.as_dict().items() if k not in ("stdout", "stderr")}
        p = A.extract_printed(r.stdout + r.stderr)
        if r.status != "OK" or p is None:
            rec["status"] = "NON_ELABORATING" if r.status in ("OK", "ERROR") else "ADAPTER_" + r.status
            rec["adapter"][f"print_{side}_log"] = (r.stdout + r.stderr)[-3000:]
            return rec
        printed[side] = p
        h, d = (case["ref_header"], case["ref_decl"]) if side == "ref" else (case["cand_header"], case["cand_decl"])
        f = work / f"{side}_check.lean"
        f.write_text(A.check_file(h, d, f"ps_{side}_decl", prep["imports"], p))
        c = run_limited([lean, str(f)], ADAPTER_CPU_S, mem_mb, ADAPTER_WALL_S, cwd=str(work), env=env)
        rec["adapter"][f"check_{side}"] = {k: v for k, v in c.as_dict().items() if k not in ("stdout", "stderr")}
        if c.status != "OK" or ": error" in (c.stdout + c.stderr):
            rec["status"] = "UNSUPPORTED_INPUT"
            rec["adapter"]["error"] = f"printed {side} statement does not round-trip: " + (c.stdout + c.stderr)[-1500:]
            return rec
    rec["printed"] = printed
    r = run_limited(A.engine_cmd(case["case_id"], printed["ref"], printed["cand"], work), budget, mem_mb,
                    3 * budget + 120, cwd=None, env=env)
    rec["run"] = {k: v for k, v in r.as_dict().items() if k not in ("stdout", "stderr")}
    rec["log_tail"] = (r.stdout + r.stderr)[-3000:]
    rec["status"] = r.status
    rec.update(A.parse_engine(case["case_id"], work))
    return rec


def run_semanteq(case, work: Path, budget: float, tier: int, mem_mb: int, tool_dir: Path) -> dict:
    from .adapters import semanteq as A
    prep = A.prepare(case, work, tool_dir, tier)
    r = run_limited(prep["cmd"], budget, mem_mb, 3 * budget + 120, cwd=prep["cwd"])
    rec = {"run": {k: v for k, v in r.as_dict().items() if k not in ("stdout", "stderr")},
           "log_tail": (r.stdout + r.stderr)[-3000:], "status": r.status}
    rec.update(A.parse(case, Path(prep["result"])))
    return rec


def run_beqplus(case, work: Path, budget: float, tier: int, mem_mb: int, tool_dir: Path, lean_version: str) -> dict:
    from .adapters import beqplus as A
    prep = A.prepare(case, work, tool_dir, lean_version, tier)
    r = run_limited(prep["cmd"], budget, mem_mb, 3 * budget + 300)
    rec = {"run": {k: v for k, v in r.as_dict().items() if k not in ("stdout", "stderr")},
           "log_tail": (r.stdout + r.stderr)[-3000:], "status": r.status}
    rec.update(A.parse(case, work / "out.json"))
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.runner")
    ap.add_argument("--system", required=True, choices=["proofscope", "semanteq", "beqplus"])
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--tier", type=int, required=True, choices=[20, 180])
    ap.add_argument("--startup-allowance", type=float, default=0.0)
    ap.add_argument("--mem-mb", type=int, default=12000)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--shard")
    ap.add_argument("--tool-dir", type=Path)
    ap.add_argument("--lean", default="lean")
    ap.add_argument("--beq-lean-version", default="v4.8.0")
    ap.add_argument("--cache-state", default="unknown", choices=["cold", "warm", "unknown"])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    cases = _shard(read_jsonl(a.cases), a.shard)
    budget = a.tier + a.startup_allowance
    base = a.out / a.system / f"t{a.tier}"
    base.mkdir(parents=True, exist_ok=True)
    manifest = {"system": a.system, "tier_cpu_s": a.tier, "startup_allowance_cpu_s": a.startup_allowance,
                "limit_cpu_s": budget, "mem_mb": a.mem_mb, "repeat": a.repeat, "shard": a.shard,
                "cases_file_sha256": sha256_file(a.cases), "cases": len(cases), "cache_state": a.cache_state,
                "host": platform.node(), "cpu": platform.processor() or platform.machine(),
                "python": platform.python_version(), "prlimit": shutil.which("prlimit"),
                "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (base / f"manifest{'-' + a.shard.replace('/', 'of') if a.shard else ''}.json").write_text(json.dumps(manifest, indent=1))
    for case in cases:
        for rep in range(a.repeat):
            work = a.out / "work" / a.system / f"t{a.tier}" / case["case_id"] / f"r{rep}"
            t0 = time.time()
            try:
                if a.system == "proofscope":
                    rec = run_proofscope(case, work, budget, a.mem_mb, a.lean)
                elif a.system == "semanteq":
                    rec = run_semanteq(case, work, budget, a.tier, a.mem_mb, a.tool_dir)
                else:
                    rec = run_beqplus(case, work, budget, a.tier, a.mem_mb, a.tool_dir, a.beq_lean_version)
            except Exception as e:  # recorded, never dropped
                rec = {"status": "RUNNER_ERROR", "error": repr(e)}
            rec.update(case_id=case["case_id"], system=a.system, tier=a.tier, repeat=rep, group=case.get("group"),
                       source=case.get("source"), wall_total_s=round(time.time() - t0, 3))
            if rec.get("status") == "OK" and rec.get("native_verdict") is None:
                rec["status"] = "ERROR_NO_OUTPUT"
            for t in ("A", "B"):
                if f"track_{t}" not in rec:
                    rec[f"track_{t}"] = {"certified": rec["status"], "native": rec["status"]}
            (base / f"{case['case_id']}.r{rep}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))
            print(case["case_id"], a.system, rec["status"], rec.get("native_verdict"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
