"""PS-25R Problem A: stage-resolved memory telemetry for one engine run (no limit enforced except a 15 GB
safety kill). Samples the whole process tree every 0.25 s: per process VmRSS, RssAnon (private), RssFile
(file-backed: mmapped .olean files and libraries), and its command line, from which the stage is read:
BUILD (extractor compile), SEARCH (Lean REPL), VERIFY (certificate compile), REPLAY (leanchecker), DRIVER.

    python -m bench.pilot25r.telemetry --engine-root DIR --spec spec.json --out tele.json
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def status(pid):
    d = {}
    try:
        for l in open(f"/proc/{pid}/status"):
            k = l.split(":")[0]
            if k in ("VmRSS", "RssAnon", "RssFile", "RssShmem", "PPid"):
                d[k] = int(l.split()[1])
        d["cmd"] = open(f"/proc/{pid}/cmdline").read().replace("\0", " ")[:300]
    except OSError:
        return None
    return d


def tree(root):
    kids = {}
    for p in os.listdir("/proc"):
        if p.isdigit():
            s = status(int(p))
            if s:
                kids.setdefault(s.get("PPid"), []).append((int(p), s))
    out, stack = [], [root]
    rs = status(root)
    if rs:
        out.append((root, rs))
    while stack:
        q = stack.pop()
        for pid, s in kids.get(q, []):
            out.append((pid, s)); stack.append(pid)
    return out


def stage(cmd):
    if "/repl" in cmd or cmd.startswith("repl"):
        return "SEARCH"
    if "leanchecker" in cmd:
        return "REPLAY"
    if " -o " in cmd and "ProofScopeCert" in cmd:
        return "VERIFY"
    if " -o " in cmd and "AssumptionExtract11" in cmd:
        return "BUILD"
    if "lean" in cmd.split(" ")[0]:
        return "LEAN_OTHER"
    return "DRIVER"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.pilot25r.telemetry")
    ap.add_argument("--engine-root", type=Path, required=True)
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--kill-mb", type=int, default=15000)
    ap.add_argument("--kill-s", type=float, default=900.0)
    a = ap.parse_args(argv)
    work = a.out.with_suffix(".work")
    env = dict(os.environ, PYTHONPATH=str(a.engine_root.resolve()))
    t0 = time.monotonic()
    p = subprocess.Popen([sys.executable, "-m", "proofscope.experimental.cjcs4", "run", str(a.spec.resolve()), "--out",
                          str(work.resolve()), "--jobs", "1"], cwd=str(a.engine_root), env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    peak = {"tree_vmrss_mb": 0, "tree_anon_mb": 0, "tree_file_mb": 0}
    stages, samples, killed = {}, [], False
    while p.poll() is None:
        t = tree(p.pid)
        v = sum(s.get("VmRSS", 0) for _, s in t) // 1024
        an = sum(s.get("RssAnon", 0) for _, s in t) // 1024
        fi = sum(s.get("RssFile", 0) for _, s in t) // 1024
        for k, x in (("tree_vmrss_mb", v), ("tree_anon_mb", an), ("tree_file_mb", fi)):
            peak[k] = max(peak[k], x)
        for pid, s in t:
            st = stage(s["cmd"])
            e = stages.setdefault(st, {"peak_vmrss_mb": 0, "peak_anon_mb": 0, "peak_file_mb": 0, "first_s": None, "last_s": 0, "pids": set()})
            e["peak_vmrss_mb"] = max(e["peak_vmrss_mb"], s.get("VmRSS", 0) // 1024)
            e["peak_anon_mb"] = max(e["peak_anon_mb"], s.get("RssAnon", 0) // 1024)
            e["peak_file_mb"] = max(e["peak_file_mb"], s.get("RssFile", 0) // 1024)
            el = round(time.monotonic() - t0, 2)
            e["first_s"] = el if e["first_s"] is None else e["first_s"]; e["last_s"] = el; e["pids"].add(pid)
        samples.append([round(time.monotonic() - t0, 2), v, an, fi, len(t)])
        if v > a.kill_mb or time.monotonic() - t0 > a.kill_s:
            os.killpg(p.pid, signal.SIGKILL); killed = True
            break
        time.sleep(0.25)
    p.wait()
    log = p.stdout.read().decode(errors="replace")[-3000:]
    rows = list((work / "rows").glob("*.json"))
    row = json.loads(rows[0].read_text()) if rows else {}
    res = {"spec": json.loads(a.spec.read_text())["id"], "wall_s": round(time.monotonic() - t0, 2), "killed_at_safety_cap": killed,
           "peak": peak, "stages": {k: {**v, "pids": len(v["pids"])} for k, v in stages.items()},
           "verdict": row.get("verdict"), "failure_class": row.get("failure_class"), "reason": row.get("reason"),
           "detail": row.get("detail"), "stats": row.get("stats"), "samples": samples[::4], "log_tail": log}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    print(json.dumps({k: res[k] for k in ("spec", "verdict", "failure_class", "wall_s", "peak")}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
