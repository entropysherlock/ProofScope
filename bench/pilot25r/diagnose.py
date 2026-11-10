"""PS-25R Problem B: elaboration matrix for every adapted Pilot-25 case (no engine verdicts, no gold).

For each case and side (R, F), in three contexts — declaration (`theorem … : S := sorry`), term (`#check (S)`),
and the frozen extractor (`#proofscope_assumptions11 (S) (S)`, plus the combined `(R) (F)`) — and in two
preambles: AS_EXECUTED (none, exactly what Pilot-25 ran) and DIAGNOSTIC_OPENS (common ProofNet `open`/`universe`
lines; diagnostic only: it says which errors are missing context, it is never used for execution). One Lean
process per (preamble, context) file; errors are mapped to cases by line.

Classes: OK · INVALID_SOURCE (parse error, or an identifier no diagnostic context resolves) · MISSING_CONTEXT
(resolved by `open`/`universe` lines) · UNSUPPORTED_FORMALIZATION (declaration elaborates, term context
does not, e.g. universe metavariables) · ENGINE_BUG (term elaborates, extractor fails) · ENVIRONMENT_ERROR.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from bench.pilot25r.cases import adapted

DIAG_OPENS = ["open Filter Topology Function Set Ideal Polynomial Real Nat Finset BigOperators",
              "open scoped BigOperators Topology Real", "universe u v w"]


def run_file(lean: str, src: str, path: Path, lean_path: str) -> tuple[int, list[dict]]:
    path.write_text(src)
    env = dict(os.environ, LEAN_PATH=lean_path)
    r = subprocess.run([lean, "--json", str(path)], capture_output=True, text=True, timeout=3600, env=env)
    msgs = []
    for line in r.stdout.splitlines():
        try:
            m = json.loads(line)
            msgs.append({"line": m["pos"]["line"], "severity": m["severity"], "data": m["data"][:400]})
        except (json.JSONDecodeError, KeyError):
            pass
    return r.returncode, msgs


def build(cases, ctx, pre, imports=("Mathlib",)):
    lines = [f"import {m}" for m in imports] + (["import ProofScope.AssumptionExtract11"] if ctx == "extract" else []) + pre
    owner = {}
    for i, c in enumerate(cases):
        for side, S in (("R", c["R"]), ("F", c["F"])):
            text = {"decl": f"theorem ps_{side}_{i} : {S} := sorry", "term": f"#check ({S})",
                    "extract": f"#proofscope_assumptions11 ({S}) ({S})"}[ctx]
            lines.append(text); owner[len(lines)] = (c["id"], side)
        if ctx == "extract":
            lines.append(f"#proofscope_assumptions11 ({c['R']}) ({c['F']})"); owner[len(lines)] = (c["id"], "RF")
    return "\n".join(lines) + "\n", owner


def classify(res: dict) -> str:
    a, d = res["AS_EXECUTED"], res["DIAGNOSTIC_OPENS"]
    errs = lambda v, ctx: [e for side in v[ctx].values() for e in side]
    if not any(errs(a, c) for c in ("decl", "term", "extract")):
        return "OK"
    allm = " ".join(errs(a, "decl") + errs(a, "term"))
    if re.search(r"unexpected token|expected term|unexpected identifier", allm) and errs(d, "decl"):
        return "INVALID_SOURCE"
    if errs(a, "decl") and not errs(d, "decl"):
        return "MISSING_CONTEXT" if not errs(d, "term") and not errs(d, "extract") else "MISSING_CONTEXT+UNSUPPORTED"
    if errs(d, "decl"):
        return "INVALID_SOURCE"
    if errs(d, "term"):
        return "UNSUPPORTED_FORMALIZATION"
    if errs(d, "extract"):
        return "ENGINE_BUG"
    return "MISSING_CONTEXT"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.pilot25r.diagnose")
    ap.add_argument("--build", type=Path, required=True, help="directory with ProofScope/AssumptionExtract11.olean")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--imports", default="Mathlib", help="comma list; Mathlib for real runs (local smoke: empty)")
    a = ap.parse_args(argv)
    imports = tuple(x for x in a.imports.split(",") if x)
    a.out.mkdir(parents=True, exist_ok=True)
    cases = adapted()
    lean = "lean"
    lp = os.pathsep.join([str(a.build.resolve()), os.environ.get("LEAN_PATH", "")])
    res = {c["id"]: {"original_sha256": c["original_sha256"], "R": c["R"], "F": c["F"]} for c in cases}
    for pname, pre in (("AS_EXECUTED", []), ("DIAGNOSTIC_OPENS", DIAG_OPENS)):
        for ctx in ("decl", "term", "extract"):
            src, owner = build(cases, ctx, pre, imports)
            rc, msgs = run_file(lean, src, a.out / f"{pname}_{ctx}.lean", lp)
            (a.out / f"{pname}_{ctx}.messages.json").write_text(json.dumps(msgs, ensure_ascii=False, indent=1))
            for c in cases:
                res[c["id"]].setdefault(pname, {}).setdefault(ctx, {"R": [], "F": [], "RF": []})
            for m in msgs:
                if m["severity"] == "error" and m["line"] in owner:
                    cid, side = owner[m["line"]]
                    res[cid][pname][ctx][side].append(m["data"])
            print(pname, ctx, "rc", rc, "errors", sum(m["severity"] == "error" for m in msgs), flush=True)
    for cid, r in res.items():
        r["class"] = classify(r)
        r["unknown_identifiers"] = sorted({m for v in r["AS_EXECUTED"].values() for e in v.values() for x in e
                                           for m in re.findall(r"[Uu]nknown (?:identifier|constant) `([^`]+)`", x)})
    (a.out / "matrix.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print("| case | class | unknown identifiers (as executed) | first error (as executed) |\n|---|---|---|---|")
    for cid, r in res.items():
        first = next((x for v in r["AS_EXECUTED"].values() for e in v.values() for x in e), "")
        print(f"| {cid} | {r['class']} | {', '.join(r['unknown_identifiers'])} | {first[:110].replace('|', '/')} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
