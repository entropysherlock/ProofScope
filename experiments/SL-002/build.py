#!/usr/bin/env python3
"""Compile Lean modules in import order with plain `lean`, against a pinned Mathlib.

Usage: build.py <mathlib-project-dir> <source-root> <out-dir> <module>...

Mathlib comes from a Mathlib-only Lake project (the setup already proven in ProofScope CI).
Every other module (SL002.*, OAI.*) is compiled from <source-root> with `lean -o`, in dependency
order, four at a time. A module whose dependency failed is reported as `skipped_dependency`.
Writes <out-dir>/build.json and one log per module; prints public annotations.
"""
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait
from pathlib import Path

LOCAL = ("SL002.", "OAI.")


def deps(root: Path, mod: str) -> list[str]:
    src = (root / (mod.replace(".", "/") + ".lean")).read_text()
    return [m for m in re.findall(r'^\s*(?:public\s+)?import\s+(\S+)', src, re.M) if m.startswith(LOCAL)]


def main(ml, root, out, *targets):
    root, out = Path(root), Path(out)
    lib = out / "lib"
    lib.mkdir(parents=True, exist_ok=True)
    ml_path = subprocess.run(["lake", "env", "printenv", "LEAN_PATH"], cwd=ml, check=True,
                             capture_output=True, text=True).stdout.strip()
    env = {**os.environ, "LEAN_PATH": f"{lib}:{ml_path}"}
    graph, todo = {}, list(targets)
    while todo:
        m = todo.pop()
        if m not in graph:
            graph[m] = deps(root, m)
            todo += graph[m]
    status, times = {}, {}

    def compile_one(m):
        rel = m.replace(".", "/")
        (lib / rel).parent.mkdir(parents=True, exist_ok=True)
        t = time.time()
        p = subprocess.run(["lean", "-DautoImplicit=false", "-o", str(lib / f"{rel}.olean"),
                            "-i", str(lib / f"{rel}.ilean"), str(root / f"{rel}.lean")],
                           env=env, capture_output=True, text=True, timeout=3600)
        (out / f"build_{m}.log").write_text(p.stdout + p.stderr)
        bad = p.returncode != 0 or re.search(r'\berror\b', p.stdout + p.stderr)
        return m, ("failed" if bad else "ok"), time.time() - t, p.stdout + p.stderr

    start = time.time()
    with ThreadPoolExecutor(4) as pool:
        running = {}
        while len(status) < len(graph):
            for m, ds in graph.items():
                if m in status or m in running.values():
                    continue
                if any(status.get(d) in ("failed", "skipped_dependency") for d in ds):
                    status[m] = "skipped_dependency"
                elif all(status.get(d) == "ok" for d in ds):
                    running[pool.submit(compile_one, m)] = m
            if not running:
                if len(status) < len(graph):
                    for m in graph:
                        status.setdefault(m, "skipped_dependency")
                break
            done, _ = wait(running, return_when=FIRST_COMPLETED)
            for f in done:
                m = running.pop(f)
                m, st, dt, log = f.result()
                status[m], times[m] = st, round(dt, 1)
                if st == "failed":
                    for line in [l for l in log.splitlines() if "error" in l][:15]:
                        mm = re.search(r'([\w./-]+\.lean):(\d+):(\d+):\s*error:?\s*(.*)', line)
                        if mm and "SL002/" in mm.group(1):
                            print(f"::error file=experiments/SL-002/project/SL002/{mm.group(1).split('SL002/')[1]},"
                                  f"line={mm.group(2)},col={mm.group(3)}::{mm.group(4)[:900]}")
                        else:
                            print(f"::error title=build {m}::{line.strip()[:900]}")
    res = {"seconds": round(time.time() - start), "modules": len(graph),
           "ok": sum(v == "ok" for v in status.values()),
           "failed": sorted(k for k, v in status.items() if v == "failed"),
           "skipped_dependency": sorted(k for k, v in status.items() if v == "skipped_dependency"),
           "status": dict(sorted(status.items())), "compile_seconds": dict(sorted(times.items())),
           "lean_path_prefix": str(lib)}
    (out / "build.json").write_text(json.dumps(res, indent=1) + "\n")
    print(f"::notice title=SL-002 build::{res['ok']}/{res['modules']} modules ok in {res['seconds']}s; "
          f"failed {res['failed'][:5]}; skipped {len(res['skipped_dependency'])}")
    return 0 if res["ok"] == res["modules"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
