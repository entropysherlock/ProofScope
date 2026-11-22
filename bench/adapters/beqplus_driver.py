"""BEq+ driver: runs the upstream `beq_plus` function (LeanInteract, pinned commit) on ONE pair.

    python beqplus_driver.py --leaninteract DIR --lean-version v4.8.0 pair.json out.json

The algorithm is imported unmodified from the pinned `examples/beq_plus.py`. The REPL project is the one
upstream's own ProofNetVerif driver uses (`TempRequireProject(lean_version=..., require="mathlib")`).
The two sides' headers are merged (imports and `open`s, de-duplicated) into BEq+'s single `src_header`
argument; this is disclosed as the only adapter transformation.
"""
import argparse
import importlib.util
import json
import sys
import time


def merge_headers(h1: str, h2: str) -> str:
    seen, imps, rest = set(), [], []
    for line in (h1 + "\n" + h2).splitlines():
        s = line.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        (imps if s.startswith("import ") else rest).append(s)
    return "\n".join(imps + rest) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leaninteract", required=True)
    ap.add_argument("--lean-version", default="v4.8.0")
    ap.add_argument("--timeout", type=int, default=None, help="default: upstream DEFAULT_TIMEOUT")
    ap.add_argument("pair")
    ap.add_argument("out")
    a = ap.parse_args()
    pair = json.load(open(a.pair))
    spec = importlib.util.spec_from_file_location("beq_plus_mod", f"{a.leaninteract}/examples/beq_plus.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    per_proof = a.timeout if a.timeout is not None else m.DEFAULT_TIMEOUT
    from lean_interact import AutoLeanServer, LeanREPLConfig, TempRequireProject
    t0 = time.time()
    server = AutoLeanServer(config=LeanREPLConfig(project=TempRequireProject(lean_version=a.lean_version, require="mathlib")))
    t_start = time.time() - t0
    res = m.beq_plus(pair["ref_decl"], pair["cand_decl"], merge_headers(pair["ref_header"], pair["cand_header"]),
                     server, timeout_per_proof=per_proof)
    json.dump({"beq_plus": bool(res), "startup_s": round(t_start, 3), "total_s": round(time.time() - t0, 3),
               "per_proof_timeout_s": per_proof}, open(a.out, "w"))


if __name__ == "__main__":
    sys.exit(main())
