"""Turn benchmark cases (bench/dev_sota3/combined.cases.jsonl) into engine specs for bench.sota4.measure.

Uses the unchanged ProofScope adapter (bench/adapters/proofscope.py): each declaration is printed as a closed
statement by Lean (`PS_CLOSED`), exactly the string the benchmark runner hands to the engine. This step is
preparation and is not measured. Provisional developer labels are copied for reporting only:
gold_A equivalent -> expected CERTIFIED_LOGICAL_EQUIVALENCE (must not: difference);
gold_A non_equivalent -> expected CERTIFIED_LOGICAL_DIFFERENCE (must not: equivalence); otherwise no label.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from bench.adapters import proofscope as AD
from bench.canonical import read_jsonl
from bench.runner import _shard

MAP = {"equivalent": ("CERTIFIED_LOGICAL_EQUIVALENCE", ["CERTIFIED_LOGICAL_DIFFERENCE"]),
       "non_equivalent": ("CERTIFIED_LOGICAL_DIFFERENCE", ["CERTIFIED_LOGICAL_EQUIVALENCE"])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.sota4.specs")
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--gold", type=Path, required=True)
    ap.add_argument("--shard")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    gold = {g["case_id"]: g for g in read_jsonl(a.gold)}
    cases = _shard(read_jsonl(a.cases), a.shard)
    a.out.mkdir(parents=True, exist_ok=True)
    lean = shutil.which("lean")
    log = []
    for c in cases:
        work = (a.out / "_prep" / c["case_id"]).resolve()
        prep = AD.prepare(c, work, [lean])
        if "unsupported" in prep:
            log.append({"case_id": c["case_id"], "status": "UNSUPPORTED_INPUT", "detail": prep["unsupported"]})
            continue
        env = AD.imports_env(prep["imports"])
        printed = []
        for cmd in prep["print_cmds"]:
            r = subprocess.run(cmd, cwd=str(work), env=env, capture_output=True, text=True, timeout=900)
            printed.append(AD.extract_printed(r.stdout + r.stderr))
        if None in printed:
            log.append({"case_id": c["case_id"], "status": "PRINT_FAILED"})
            continue
        g = gold.get(c["case_id"], {})
        exp, mn = MAP.get(g.get("gold_A"), (None, []))
        spec = {"id": c["case_id"], "reference": printed[0], "lean": printed[1], "expected": exp, "must_not_be": mn,
                "split": "dev_sota3", "gold_A": g.get("gold_A"), "labeler": g.get("labeler")}
        (a.out / f"{c['case_id']}.json").write_text(json.dumps(spec, ensure_ascii=False))
        log.append({"case_id": c["case_id"], "status": "OK"})
    (a.out / "_specs.log").write_text(json.dumps(log, indent=1))
    print(json.dumps(log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
