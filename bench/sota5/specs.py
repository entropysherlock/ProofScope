"""Engine specs for SOTA-5 measurements, with the adapter round-trip enforced (repairs bench/sota4/specs.py).

For each case and side: print with adapter v1 (frozen) and v2 (bench/sota5/adapter2.py), run the v1 check
(frozen runner) and the v2 standalone check, and record all four outcomes. A spec is written only from v2
statements that pass the v2 check; otherwise the case is INPUT_NOT_EVALUABLE (never silently passed on).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from bench.adapters import proofscope as V1
from bench.adapters._decl import merged_imports
from bench.canonical import read_jsonl
from bench.runner import _shard
from bench.sota5 import adapter2 as V2

MAP = {"equivalent": ("CERTIFIED_LOGICAL_EQUIVALENCE", ["CERTIFIED_LOGICAL_DIFFERENCE"]),
       "non_equivalent": ("CERTIFIED_LOGICAL_DIFFERENCE", ["CERTIFIED_LOGICAL_EQUIVALENCE"])}


def _lean(lean, f: Path, env) -> tuple[bool, str]:
    r = subprocess.run([lean, str(f)], cwd=str(f.parent), env=env, capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr
    return r.returncode == 0 and ": error" not in out, out


def prepare_case(c: dict, work: Path, lean: str) -> dict:
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    imports = merged_imports(c["ref_header"], c["cand_header"])
    env = V1.imports_env(imports)
    rec = {"case_id": c["case_id"], "sides": {}}
    for side, h, d in (("ref", c["ref_header"], c["ref_decl"]), ("cand", c["cand_header"], c["cand_decl"])):
        name = f"ps_{side}_decl"
        s = {}
        for ver, mod in (("v1", V1), ("v2", V2)):
            f = work / f"{side}_{ver}_print.lean"
            try:
                f.write_text(mod.side_file(h, d, name, imports))
            except ValueError as e:
                s[ver] = {"printed": None, "error": str(e)}
                continue
            ok, out = _lean(lean, f, env)
            p = V1.extract_printed(out)
            s[ver] = {"printed": p}
            if p is None:
                s[ver]["error"] = out[-800:]
                continue
            for cver, cmod in (("v1_check", V1), ("v2_standalone_check", V2)):
                cf = work / f"{side}_{ver}_{cver}.lean"
                cf.write_text(cmod.check_file(h, d, name, imports, p))
                cok, cout = _lean(lean, cf, env)
                s[ver][cver] = cok
                if not cok:
                    s[ver][cver + "_log"] = cout[-800:]
        rec["sides"][side] = s
    v2ok = all(rec["sides"][x].get("v2", {}).get("v2_standalone_check") for x in ("ref", "cand"))
    rec["status"] = "OK" if v2ok else "INPUT_NOT_EVALUABLE"
    if v2ok:
        rec["reference"] = rec["sides"]["ref"]["v2"]["printed"]
        rec["lean"] = rec["sides"]["cand"]["v2"]["printed"]
    rec["v1_unchecked_would_differ"] = any(
        rec["sides"][x].get("v1", {}).get("printed") and not rec["sides"][x]["v1"].get("v2_standalone_check")
        for x in ("ref", "cand"))
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.sota5.specs")
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--gold", type=Path)
    ap.add_argument("--shard")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    gold = {g["case_id"]: g for g in read_jsonl(a.gold)} if a.gold else {}
    a.out.mkdir(parents=True, exist_ok=True)
    lean = shutil.which("lean")
    log = []
    for c in _shard(read_jsonl(a.cases), a.shard):
        rec = prepare_case(c, a.out / "_prep" / c["case_id"], lean)
        log.append(rec)
        if rec["status"] == "OK":
            g = gold.get(c["case_id"], {})
            exp, mn = MAP.get(g.get("gold_A"), (None, []))
            (a.out / f"{c['case_id']}.json").write_text(json.dumps(
                {"id": c["case_id"], "reference": rec["reference"], "lean": rec["lean"], "expected": exp,
                 "must_not_be": mn, "split": "dev_sota3", "gold_A": g.get("gold_A"), "adapter": "v2"}, ensure_ascii=False))
        print(c["case_id"], rec["status"], "v1-unchecked-differs" if rec["v1_unchecked_would_differ"] else "", flush=True)
    (a.out / "_adapter_audit.log").write_text(json.dumps(log, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
