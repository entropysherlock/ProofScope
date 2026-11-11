"""Run the frozen SOTA-16 cases with and without the Presburger certificates, and with Z3."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0] / "sota15"))
from proofscope import scopeelim as se  # noqa: E402
from proofscope.toolchain import Toolchain  # noqa: E402
import z3_check  # noqa: E402


def main(out: Path, jobs: int):
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
    summ = {"cases": len(specs), "directions": 2 * len(specs)}
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
    main(Path(sys.argv[1]).resolve(), int(sys.argv[2]) if len(sys.argv) > 2 else 2)
