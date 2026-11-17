"""Run the frozen SOTA-15 cases through the ScopeElim engine, the exhaustive oracle and Z3."""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
from proofscope import scopeelim as se  # noqa: E402
from proofscope.toolchain import Toolchain  # noqa: E402
import oracle  # noqa: E402
import z3_check  # noqa: E402


def main(out: Path, jobs: int):
    base = Toolchain.find()
    assert se.build_lib(base, out / "lib")["ok"]
    tc = se.lib_toolchain(base, out / "lib")
    rows = []
    for group in ("horn_bounded", "horn_symbolic", "func"):
        specs = [json.loads(p.read_text()) for p in sorted((HERE / "cases" / group).glob("*.json"))]

        def one(spec):
            r = se.compare(spec, tc, out / "lib", out / "work" / spec["id"])
            r["group"] = group
            r["oracle"] = oracle.truth(spec) if group == "horn_bounded" else None
            return r
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            got = list(ex.map(one, specs))
        for r, spec in zip(got, specs):                 # Z3 is not thread-safe: run it serially
            t0 = time.time()
            try:
                r["z3"] = z3_check.directions(spec)
            except Exception as e:                      # noqa: BLE001
                r["z3"] = {"error": str(e)[:200]}
            r["z3_seconds"] = round(time.time() - t0, 2)
        rows += got
    (out / "native_results.json").write_text(json.dumps({"rows": rows}, indent=1, ensure_ascii=False, default=str))
    summary = {}
    for g in ("horn_bounded", "horn_symbolic", "func"):
        rs = [r for r in rows if r["group"] == g]
        dirs = [(r, d) for r in rs for d in ("fwd", "bwd")]
        st = lambda r, d: (r.get("directions") or {}).get(d, "UNKNOWN")
        s = {"cases": len(rs), "decisive_verdicts": sum(r["verdict"] not in ("INCONCLUSIVE", "INCONSISTENT") for r in rs),
             "inconsistent": sum(r["verdict"] == "INCONSISTENT" for r in rs),
             "directions": len(dirs), "directions_certified": sum(st(r, d) != "UNKNOWN" for r, d in dirs),
             "median_seconds": sorted(r["seconds"] for r in rs)[len(rs) // 2],
             "max_seconds": max(r["seconds"] for r in rs),
             "median_certificate_bytes": sorted(r.get("certificate_bytes", 0) for r in rs)[len(rs) // 2],
             "max_certificate_bytes": max(r.get("certificate_bytes", 0) for r in rs)}
        if g == "horn_bounded":
            with_truth = [(r, d) for r, d in dirs if r["oracle"]]
            s["oracle_directions"] = len(with_truth)
            s["wrong_vs_oracle"] = [(r["id"], d) for r, d in with_truth if st(r, d) not in ("UNKNOWN", r["oracle"][d])]
            s["abstained_vs_oracle"] = sum(st(r, d) == "UNKNOWN" for r, d in with_truth)
        z = [(r, d) for r, d in dirs if r["z3"].get(d) in ("ENTAILS", "SEPARATED")]
        s["z3_decided_directions"] = len(z)
        s["z3_disagreements"] = [(r["id"], d) for r, d in z if st(r, d) not in ("UNKNOWN", r["z3"][d])]
        s["engine_only"] = sum(st(r, d) != "UNKNOWN" and r["z3"].get(d) not in ("ENTAILS", "SEPARATED") for r, d in dirs)
        s["z3_only"] = sum(st(r, d) == "UNKNOWN" for r, d in z)
        summary[g] = s
    (out / "native_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(), int(sys.argv[2]) if len(sys.argv) > 2 else 4)
