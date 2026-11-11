"""Run the frozen SOTA-16 cases with and without the Presburger certificates, and with Z3."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import argparse

HERE = Path(__file__).resolve().parent
_ap = argparse.ArgumentParser()
_ap.add_argument("out", type=Path)
_ap.add_argument("jobs", type=int, nargs="?", default=2)
_ap.add_argument("--engine-root", type=Path, default=HERE.parents[1],
                 help="checkout whose `proofscope` package is evaluated (cases and runner stay from this tree)")
_ap.add_argument("--lean-timeout", type=float, default=None,
                 help="per-Lean-call limit in seconds; stands in for the memory kill of the first frozen run")
ARGS = _ap.parse_args()
sys.path.insert(0, str(ARGS.engine_root.resolve()))
sys.path.insert(0, str(HERE.parents[0] / "sota15"))
from proofscope import scopeelim as se  # noqa: E402
from proofscope.toolchain import Toolchain  # noqa: E402
import z3_check  # noqa: E402


def main(out: Path, jobs: int):
    if ARGS.lean_timeout:
        # The frozen engine's Toolchain.run raises on a timeout (bytes/str bug, fixed on the branch).
        # Patch the runner's view of it so a timed-out Lean call is the INFRASTRUCTURE_ERROR the
        # engine intends; the frozen files themselves stay untouched.
        import subprocess
        import time as _t
        from proofscope import toolchain as _tcm

        def _run(self, cmd, cwd=None, extra_path=None, timeout=None):
            import os
            env = dict(os.environ)
            env.update(self.env)
            if extra_path:
                env["LEAN_PATH"] = os.pathsep.join(p for p in [str(extra_path), env.get("LEAN_PATH", "")] if p)
            t0 = _t.time()
            try:
                r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
                return _tcm.CmdResult(cmd, r.returncode, r.stdout, r.stderr, _t.time() - t0)
            except subprocess.TimeoutExpired:
                return _tcm.CmdResult(cmd, -9, "", "TIMEOUT", _t.time() - t0)
        _tcm.Toolchain.run = _run
        orig = se.certify
        se.certify = lambda *a, **k: orig(*a, **{**k, "timeout": ARGS.lean_timeout})
    base = Toolchain.find()
    assert se.build_lib(base, out / "lib")["ok"]
    tc = se.lib_toolchain(base, out / "lib")
    specs = [json.loads(p.read_text()) for p in sorted((HERE / "cases" / "func_lin").glob("*.json"))]
    res = {}
    for label, flag in (("sota15", False), ("sota16", True)):
        f = out / f"rows_{label}.json"              # stage results are saved so a killed run can resume
        if f.exists():
            res[label] = json.loads(f.read_text())
            continue
        se.PRESBURGER = flag
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            res[label] = list(ex.map(lambda s: se.compare(s, tc, out / "lib", out / label / s["id"]), specs))
        f.write_text(json.dumps(res[label], indent=1, ensure_ascii=False, default=str))
    z3_check.TIMEOUT_MS = 2000                      # the first run was killed in this stage at 8 s per query
    z = []
    for s in specs:
        try:
            z.append(z3_check.directions(s))
        except Exception as e:  # noqa: BLE001
            z.append({"error": str(e)[:100]})
    st = lambda r, d: (r.get("directions") or {}).get(d, "UNKNOWN")
    summ = {"cases": len(specs), "directions": 2 * len(specs), "engine_root": str(ARGS.engine_root),
            "lean_timeout": ARGS.lean_timeout}
    for label, rows in res.items():
        dirs = [(r, zz, d) for r, zz in zip(rows, z) for d in ("fwd", "bwd")]
        summ[label] = {
            "directions_certified": sum(st(r, d) != "UNKNOWN" for r, _, d in dirs),
            "decisive_verdicts": sum(r["verdict"] not in ("INCONCLUSIVE", "INCONSISTENT") for r in rows),
            "inconsistent": sum(r["verdict"] == "INCONSISTENT" for r in rows),
            "z3_disagreements": [(r["id"], d) for r, zz, d in dirs
                                 if zz.get(d) in ("ENTAILS", "SEPARATED") and st(r, d) not in ("UNKNOWN", zz[d])],
            "abstained": [(r["id"], d) for r, _, d in dirs if st(r, d) == "UNKNOWN"],
            "median_seconds": sorted(r["seconds"] for r in rows)[len(rows) // 2],
            "max_seconds": max(r["seconds"] for r in rows),
            "median_certificate_bytes": sorted(r.get("certificate_bytes", 0) for r in rows)[len(rows) // 2]}
    summ["z3_decided_directions"] = sum(zz.get(d) in ("ENTAILS", "SEPARATED") for zz in z for d in ("fwd", "bwd"))
    summ["engines_disagree"] = [(a["id"], d) for a, b in zip(res["sota15"], res["sota16"]) for d in ("fwd", "bwd")
                                if "UNKNOWN" not in (st(a, d), st(b, d)) and st(a, d) != st(b, d)]
    (out / "results.json").write_text(json.dumps({"rows": res, "z3": z}, indent=1, ensure_ascii=False, default=str))
    (out / "summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    print(json.dumps(summ, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(ARGS.out.resolve(), ARGS.jobs)
