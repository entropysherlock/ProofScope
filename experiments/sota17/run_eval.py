"""Run the SOTA-17 engine and the SOTA-16 baseline on the frozen cases and compare with the labels.

    python3 experiments/sota17/run_eval.py OUT [JOBS]

Baseline: `proofscope.scopeelim.compare` (v1.3 + SOTA-16) on the cases it can express, i.e. both
sides have exactly one site; every other case counts as unsupported for the baseline.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from proofscope import multiocc, scopeelim  # noqa: E402
from proofscope.scope_expr import Unsupported, subst, to_lean  # noqa: E402
from proofscope.toolchain import Toolchain  # noqa: E402


def baseline(spec, tc, lib, work):
    try:
        R, F = multiocc.Claim.from_json(spec["reference"]), multiocc.Claim.from_json(spec["formal"])
    except Unsupported:
        return {"fwd": "UNSUPPORTED", "bwd": "UNSUPPORTED"}
    if len(R.sites) != 1 or len(F.sites) != 1:
        return {"fwd": "UNSUPPORTED", "bwd": "UNSUPPORTED"}
    side = lambda c: {"var": c.var, "guard": to_lean(c.guard), "arg": to_lean(c.sites[0]),
                      "rel": to_lean(subst(c.body_w, {"w0_": ("var", "w")}))}
    row = scopeelim.compare({"id": spec["id"], "kind": "func", "reference": side(R), "formal": side(F)}, tc, lib, work)
    return row.get("directions", {"fwd": "UNKNOWN", "bwd": "UNKNOWN"})


def main():
    out = Path(sys.argv[1]).resolve()
    jobs = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    base = Toolchain.find()
    b = multiocc.build_lib(base, out / "lib")
    assert b["ok"], b
    tc = scopeelim.lib_toolchain(base, out / "lib")
    specs = [json.loads(p.read_text()) for p in sorted((HERE / "cases").glob("*.json"))]
    labels = json.loads((out / "labels.json").read_text()) if (out / "labels.json").exists() else {}

    def one(spec):
        row = multiocc.compare(spec, tc, out / "work" / spec["id"])
        row["family"] = spec["family"]
        row["baseline"] = baseline(spec, tc, out / "lib", out / "base" / spec["id"])
        return row
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        rows = list(ex.map(one, specs))
    summ = {"cases": len(rows), "directions": 2 * len(rows), "by_family": {}, "wrong": [], "unlabelled_certified": [],
            "label_only": [], "engine_only": []}
    for r in rows:
        fam = summ["by_family"].setdefault(r["family"], {"cases": 0, "directions": 0, "certified": 0, "entails": 0, "separated": 0,
                                                         "unsupported": 0, "abstained": 0, "baseline_certified": 0,
                                                         "labelled": 0})
        fam["cases"] += 1
        for tag in ("fwd", "bwd"):
            fam["directions"] += 1
            st = r["directions"][tag]
            lab = labels.get(r["id"], {}).get(tag, {}).get("label")
            fam["labelled"] += lab is not None
            fam["baseline_certified"] += r["baseline"].get(tag) in ("ENTAILS", "SEPARATED")
            if st in ("ENTAILS", "SEPARATED"):
                fam["certified"] += 1
                fam["entails" if st == "ENTAILS" else "separated"] += 1
                if lab is None:
                    summ["unlabelled_certified"].append([r["id"], tag, st])
                elif lab != st:
                    summ["wrong"].append([r["id"], tag, st, lab])
                if lab is None:
                    summ["engine_only"].append([r["id"], tag])
            else:
                fam["unsupported" if st == "UNSUPPORTED" else "abstained"] += 1
                if lab is not None:
                    summ["label_only"].append([r["id"], tag, st, lab])
    tot = lambda k: sum(f[k] for f in summ["by_family"].values())
    summ["total"] = {k: tot(k) for k in ("certified", "entails", "separated", "unsupported", "abstained", "baseline_certified", "labelled")}
    summ["median_seconds"] = sorted(r["seconds"] for r in rows)[len(rows) // 2]
    summ["max_seconds"] = max(r["seconds"] for r in rows)
    (out / "results.json").write_text(json.dumps({"rows": rows}, indent=1, ensure_ascii=False, default=str))
    (out / "summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in summ.items() if k not in ("label_only", "engine_only")}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
