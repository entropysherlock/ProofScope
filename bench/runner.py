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
import re
import platform
import shutil
import time
from pathlib import Path

from .canonical import read_jsonl, sha256_file
from .limits import POLL_S, run_limited

ADAPTER_CPU_S, ADAPTER_WALL_S = 300, 600
WALL_FACTOR = 4                 # wall cap = WALL_FACTOR x CPU limit + slack; reported as TIMEOUT_WALL, never as CPU
MEASURE_CEILING_S = 900          # calibration measurement ceiling (availability only; never a scored budget)
CALIBRATION_ID = "avail-calibration-identical"
ENFORCEMENT_TOLERANCE_S = 0.5    # preregistered limiter precision (SOTA-3 amendment A9)
REPO = Path(__file__).resolve().parents[1]


def _shard(rows, spec):
    if not spec:
        return rows
    i, n = (int(x) for x in spec.split("/"))
    return [r for k, r in enumerate(rows) if k % n == i]


def _strip(r) -> dict:
    return {k: v for k, v in r.as_dict().items() if k not in ("stdout", "stderr")}


def _decl_lines(text: str, name: str) -> tuple[int, int]:
    """1-based line range of the renamed declaration inside a generated file."""
    lines = text.splitlines()
    start = next((i + 1 for i, l in enumerate(lines) if f"theorem {name}" in l), 0)
    end = next((i + 1 for i in range(start, len(lines)) if lines[i].strip() == "end"), len(lines))
    return start, end


def _error_lines(log: str, path: Path) -> list[int]:
    return [int(m.group(1)) for m in re.finditer(re.escape(path.name) + r":(\d+):\d+: error", log)]


def run_proofscope(case, work: Path, budget: float, mem_mb: int, lean: str, engine: str = "proofscope.v12") -> dict:
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
        f = Path(cmd[-1])
        r = run_limited(cmd, ADAPTER_CPU_S, mem_mb, ADAPTER_WALL_S, cwd=str(work), env=env, inputs=(str(f),))
        rec["adapter"][f"print_{side}"] = _strip(r)
        log = r.stdout + r.stderr
        p = A.extract_printed(log)
        if r.status != "OK" or p is None:
            rec["adapter"][f"print_{side}_log"] = log[-3000:]
            lo, hi = _decl_lines(f.read_text(), f"ps_{side}_decl")
            errs = _error_lines(log, f)
            if r.status in ("OK", "ERROR") and errs and all(lo <= e <= hi for e in errs):
                rec["status"] = "NON_ELABORATING"      # Lean rejects the source declaration itself
            elif r.status in ("OK", "ERROR"):
                rec["status"] = "ADAPTER_ERROR"        # failure outside the declaration (adapter or environment)
            else:
                rec["status"] = "ADAPTER_" + r.status  # LAUNCH_ERROR, TIMEOUT_*, OOM in the adapter step
            return rec
        printed[side] = p
        h, d = (case["ref_header"], case["ref_decl"]) if side == "ref" else (case["cand_header"], case["cand_decl"])
        cf = work / f"{side}_check.lean"
        cf.write_text(A.check_file(h, d, f"ps_{side}_decl", prep["imports"], p))
        c = run_limited([lean, str(cf)], ADAPTER_CPU_S, mem_mb, ADAPTER_WALL_S, cwd=str(work), env=env, inputs=(str(cf),))
        rec["adapter"][f"check_{side}"] = _strip(c)
        if c.status != "OK" or ": error" in (c.stdout + c.stderr):
            rec["status"] = "UNSUPPORTED_INPUT" if c.status in ("OK", "ERROR") else "ADAPTER_" + c.status
            rec["adapter"]["error"] = f"printed {side} statement does not round-trip: " + (c.stdout + c.stderr)[-1500:]
            return rec
    rec["printed"] = printed
    cmd = A.engine_cmd(case["case_id"], printed["ref"], printed["cand"], work, engine)
    r = run_limited(cmd, budget, mem_mb, WALL_FACTOR * budget + 120, cwd=str(REPO), env=env, inputs=(cmd[4],))
    rec["run"] = _strip(r)
    rec["log_tail"] = (r.stdout + r.stderr)[-3000:]
    rec["status"] = r.status
    from . import outcomes
    rec.update(A.parse_engine(case["case_id"], work, outcomes.cjcs if engine.endswith("cjcs") else None))
    return rec


def run_semanteq(case, work: Path, budget: float, tier: int, mem_mb: int, tool_dir: Path) -> dict:
    from .adapters import semanteq as A
    prep = A.prepare(case, work, tool_dir, tier)
    r = run_limited(prep["cmd"], budget, mem_mb, WALL_FACTOR * budget + 120, cwd=prep["cwd"], inputs=(prep["input"],))
    rec = {"run": _strip(r), "log_tail": (r.stdout + r.stderr)[-3000:], "status": r.status}
    rec.update(A.parse(case, Path(prep["result"])))
    return rec


def run_beqplus(case, work: Path, budget: float, tier: int, mem_mb: int, tool_dir: Path, lean_version: str) -> dict:
    from .adapters import beqplus as A
    prep = A.prepare(case, work, tool_dir, lean_version)
    r = run_limited(prep["cmd"], budget, mem_mb, WALL_FACTOR * budget + 300, cwd=str(work), inputs=(prep["input"],))
    rec = {"run": _strip(r), "log_tail": (r.stdout + r.stderr)[-3000:], "status": r.status}
    rec.update(A.parse(case, work / "out.json"))
    return rec


def evaluation_class(rec: dict) -> str:
    """Machine-readable outcome class (SOTA-2, protocol amendment A8). Only EVALUATED_* records count as a
    mathematical evaluation; nothing else may be scored as an abstention or a verdict."""
    st = rec.get("status")
    if st in ("TIMEOUT_CPU", "TIMEOUT_WALL", "OOM"):
        return "RESOURCE_EXHAUSTED"
    if st in ("NON_ELABORATING", "UNSUPPORTED_INPUT", "INCOMPATIBLE"):
        return "INPUT_NOT_EVALUABLE"
    if st != "OK" or rec.get("native_verdict") is None:
        return "NOT_EVALUATED_INFRA"
    a, b = rec["track_A"]["certified"], rec["track_B"]["certified"]
    if a in ("NON_ELABORATING", "UNSUPPORTED_INPUT", "INCOMPATIBLE"):
        return "INPUT_NOT_EVALUABLE"          # the tool ran but reports that it could not read the input
    if a in ("TIMEOUT_WALL", "TIMEOUT_CPU", "OOM"):
        return "RESOURCE_EXHAUSTED"           # the tool's own limit (e.g. SemantEq `Timeout`)
    if a not in ("EQUIV", "NONEQUIV", "ABSTAIN"):
        return "NOT_EVALUATED_INFRA"          # ERROR / internal error reported by the tool
    kind = rec.get("certificate_kind")
    if a == "EQUIV" or b == "EQUIV":
        return "EVALUATED_POSITIVE_KERNEL" if kind == "kernel" else "EVALUATED_POSITIVE_STRUCTURAL"
    if a == "NONEQUIV":
        return "EVALUATED_NEGATIVE_LOGICAL"
    if b == "NONEQUIV":
        return "EVALUATED_NEGATIVE_FIDELITY"
    return "EVALUATED_ABSTAIN"


def measure_startup(system: str, case: dict, n: int, a) -> dict:
    """Startup allowance (amendment A1/A7): median whole-tree CPU of the calibration pair over n runs under
    a measurement ceiling. These runs are measurements, never scored."""
    vals, recs = [], []
    for k in range(n):
        work = a.out / "work" / system / "calibration" / f"m{k}"
        rec = RUNNERS[system](case, work, MEASURE_CEILING_S, a)
        recs.append({"status": rec.get("status"), "native_verdict": rec.get("native_verdict"), "run": rec.get("run")})
        if rec.get("status") == "OK" and rec.get("run"):
            vals.append(rec["run"]["cpu_tree_s"])
    vals.sort()
    med = vals[len(vals) // 2] if len(vals) == n else None
    return {"calibration_case": case["case_id"], "runs": recs, "ceiling_cpu_s": MEASURE_CEILING_S,
            "startup_allowance_cpu_s": med,
            "note": None if med is not None else "calibration did not complete in every run: no allowance derived"}


RUNNERS = {
    "proofscope": lambda c, w, b, a: run_proofscope(c, w, b, a.mem_mb, a.lean),
    "cjcs": lambda c, w, b, a: run_proofscope(c, w, b, a.mem_mb, a.lean, "proofscope.experimental.cjcs"),
    "semanteq": lambda c, w, b, a: run_semanteq(c, w, b, a.tier, a.mem_mb, a.tool_dir),
    "beqplus": lambda c, w, b, a: run_beqplus(c, w, b, a.tier, a.mem_mb, a.tool_dir, a.beq_lean_version),
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.runner")
    ap.add_argument("--system", required=True, choices=["proofscope", "cjcs", "semanteq", "beqplus"])
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--tier", type=int, required=True, choices=[20, 180])
    ap.add_argument("--startup-allowance", default="0",
                    help="CPU seconds, or 'measure' (availability only): median tree CPU of the calibration pair")
    ap.add_argument("--calibration-runs", type=int, default=3)
    ap.add_argument("--mem-mb", type=int, default=12000)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--shard")
    ap.add_argument("--tool-dir", type=Path)
    ap.add_argument("--lean", default="lean")
    ap.add_argument("--beq-lean-version", default="v4.8.0")
    ap.add_argument("--cache-state", default="unknown", choices=["cold", "warm", "unknown"])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    # every path absolute: tools are started in their own working directories (SOTA-1 defect: a relative
    # --out made every generated input path unresolvable from the tool's cwd)
    a.out = a.out.resolve()
    a.cases = a.cases.resolve()
    if a.tool_dir is not None:
        a.tool_dir = a.tool_dir.resolve()
    all_cases = read_jsonl(a.cases)
    cases = _shard(all_cases, a.shard)
    calibration = None
    if a.startup_allowance == "measure":
        cal = next((c for c in all_cases if c["case_id"] == CALIBRATION_ID), None)
        if cal is None:
            raise SystemExit(f"--startup-allowance measure needs the calibration case {CALIBRATION_ID}")
        calibration = measure_startup(a.system, cal, a.calibration_runs, a)
        allowance = calibration["startup_allowance_cpu_s"]
        if allowance is None:
            allowance = 0.0
    else:
        allowance = float(a.startup_allowance)
    budget = a.tier + allowance
    base = a.out / a.system / f"t{a.tier}"
    base.mkdir(parents=True, exist_ok=True)
    manifest = {"system": a.system, "tier_cpu_s": a.tier, "startup_allowance_cpu_s": allowance,
                "startup_allowance_source": "measured (calibration)" if calibration else "preregistered input",
                "calibration": calibration, "limit_cpu_s": budget,
                "budget_semantics": "whole process tree of one tool invocation per pair; polled enforcement "
                                    f"every {POLL_S}s; adapter conversion steps limited separately and not charged", "mem_mb": a.mem_mb, "repeat": a.repeat, "shard": a.shard,
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
                rec = RUNNERS[a.system](case, work, budget, a)
            except Exception as e:  # recorded, never dropped
                import traceback
                rec = {"status": "RUNNER_ERROR", "error": repr(e), "traceback": traceback.format_exc()[-3000:]}
            rec.update(case_id=case["case_id"], system=a.system, tier=a.tier, repeat=rep, group=case.get("group"),
                       source=case.get("source"), wall_total_s=round(time.time() - t0, 3))
            if rec.get("status") == "OK" and rec.get("native_verdict") is None:
                rec["status"] = "ERROR_NO_OUTPUT"
            for t in ("A", "B"):
                if f"track_{t}" not in rec or rec["status"] != "OK":
                    rec[f"track_{t}"] = {"certified": rec["status"], "native": rec["status"]}
            run = rec.get("run") or {}
            rec["budget"] = {"tier_cpu_s": a.tier, "startup_allowance_cpu_s": allowance, "limit_cpu_s": budget,
                             "cpu_tree_s": run.get("cpu_tree_s"),
                             "chargeable_cpu_s": None if run.get("cpu_tree_s") is None else round(run["cpu_tree_s"] - allowance, 3),
                             "compliant": rec["status"] == "OK" and run.get("cpu_tree_s") is not None
                                          and run["cpu_tree_s"] <= budget,
                             # SOTA-3: a TIMEOUT is never compliant (the budget was exhausted); separately, the
                             # limiter's own precision: overshoot beyond the preregistered tolerance is an
                             # infrastructure defect, flagged here and never attributed to the tool
                             "enforcement_overshoot_s": run.get("cpu_overshoot_s"),
                             "enforcement_tolerance_s": ENFORCEMENT_TOLERANCE_S,
                             "enforcement_ok": (run.get("cpu_overshoot_s") or 0.0) <= ENFORCEMENT_TOLERANCE_S}
            rec["evaluation_class"] = evaluation_class(rec)
            (base / f"{case['case_id']}.r{rep}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))
            print(case["case_id"], a.system, rec["status"], rec.get("native_verdict"), rec["evaluation_class"],
                  run.get("cpu_tree_s"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
