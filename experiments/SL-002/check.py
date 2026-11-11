#!/usr/bin/env python3
"""SL-002 checks.  Fails closed; every negative outcome is named.

  verbatim  -- the copied OpenAI definitions and Formal Conjectures statements in SL002/*.lean
               match the sources at the frozen commits, character for character after
               whitespace normalization.
  scan      -- no escape hatches (sorry, axiom, native_decide, ...) in SL-002's own Lean files.
  audit     -- parse a Lean log: errors become public annotations; '#print axioms' output is
               checked against the allowed set.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
PROJ = HERE / "project"
OAI_HEAD = "4eaee87548250b2682affda7d05d947c05554bae"
FC_HEAD = "da703a5f239f734a47ede2f4e99b9ccc9e644cb5"
ALLOWED = {"propext", "Classical.choice", "Quot.sound"}
ESCAPES = re.compile(r'\b(sorry|admit|native_decide|implemented_by|unsafe|axiom|opaque|extern|'
                     r'run_cmd|run_tac|elab|macro|set_option\s+debug|decreasing_by\s+sorry)\b')


def norm(s: str) -> str:
    return " ".join(s.split())


def git_show(repo, commit, path):
    return subprocess.run(["git", "-C", repo, "show", f"{commit}:{path}"], check=True,
                          capture_output=True, text=True).stdout


def def_body(src: str, name: str) -> str | None:
    """Text of `def name ...` up to the next blank line, docstring excluded."""
    m = re.search(r'^(?:noncomputable\s+)?def\s+' + re.escape(name) + r'\b(.*?)(?=\n\s*\n|\Z)', src, re.M | re.S)
    return norm(m.group(1)) if m else None


def thm_stmt(src: str, name: str) -> str | None:
    m = re.search(r'^\s*theorem\s+' + re.escape(name) + r'(?=[\s:({\[])(.*?):=', src, re.M | re.S)
    return norm(m.group(1)) if m else None


def verbatim(oai_repo: str, fc_repo: str) -> list[dict]:
    rows = []
    ours = {k: (PROJ / f"SL002/{k}.lean").read_text() for k in ("E952", "E1150", "Assembly952", "Assembly1150")}
    ch952 = git_show(oai_repo, OAI_HEAD, "lean/ComparatorChallenges/GaussianMoat.lean")
    ch1150 = git_show(oai_repo, OAI_HEAD, "lean/ComparatorChallenges/AsymptoticallyMinimalLittlewood.lean")
    fc952 = git_show(fc_repo, FC_HEAD, "FormalConjectures/ErdosProblems/952.lean")
    fc1150 = git_show(fc_repo, FC_HEAD, "FormalConjectures/ErdosProblems/1150.lean")
    for case, ours_src, theirs, names in (("952", ours["E952"], ch952, ["MainEndpoint"]),
                                          ("1150", ours["E1150"], ch1150,
                                           ["littlewoodValue", "IsRealSigning", "MainStatement"])):
        for n in names:
            a, b = def_body(ours_src, n), def_body(theirs, n)
            rows.append({"case": case, "item": f"OAI def {n}", "match": a is not None and a == b})
    for case, bridge, asm, fc, fcname, asmname in (
            ("952", ours["E952"], ours["Assembly952"], fc952, "erdos_952", "erdos_952"),
            ("1150", ours["E1150"], ours["Assembly1150"], fc1150, "erdos_1150", "erdos_1150")):
        src = thm_stmt(fc, fcname)                      # ": ¬ ∃ ..."
        d = def_body(bridge, "FCStatement")             # ": Prop := ¬ ∃ ..."
        rows.append({"case": case, "item": "bridge FCStatement = FC statement",
                     "match": bool(src and d and d.removeprefix(": Prop :=").strip() == src.removeprefix(":").strip())})
        rows.append({"case": case, "item": "assembly theorem statement = FC statement",
                     "match": bool(src and thm_stmt(asm, asmname) == src)})
    return rows


def scan() -> list[dict]:
    rows = []
    for f in sorted(PROJ.glob("SL002/*.lean")):
        code = re.sub(r'/-.*?-/', '', f.read_text(), flags=re.S)
        code = re.sub(r'--.*', '', code)
        hit = ESCAPES.search(code)
        rows.append({"file": str(f.relative_to(HERE)), "clean": hit is None,
                     "found": hit.group(1) if hit else None})
    return rows


def audit(log_path: str, expect: list[str]) -> dict:
    log = Path(log_path).read_text(errors="replace") if Path(log_path).exists() else ""
    errors = [l for l in log.splitlines()
              if re.search(r'\berror\b', l) and (re.search(r'\.lean:\d+:\d+', l) or l.lstrip().startswith("error:"))]
    for e in errors[:40]:
        m = re.search(r'([\w./-]+\.lean):(\d+):(\d+):?\s*(?:error:)?\s*(.*)', e)
        if m:
            path = m.group(1).removeprefix("./")
            if path.startswith(("SL002/", "Audit")):
                path = "experiments/SL-002/project/" + path
            print(f"::error file={path},line={m.group(2)},col={m.group(3)}::{m.group(4)[:900]}")
        else:
            print(f"::error::{e.strip()[:900]}")
    found = {}
    for m in re.finditer(r"'([^']+)' (depends on axioms: \[([^\]]*)\]|does not depend on any axioms)", log):
        found[m.group(1)] = sorted(a.strip() for a in (m.group(3) or "").split(",") if a.strip())
    res = {"log": log_path, "n_errors": len(errors), "axioms": found, "missing": [], "unapproved": {}}
    for name in expect:
        if name not in found:
            res["missing"].append(name)
        else:
            bad = [a for a in found[name] if a not in ALLOWED]
            if bad:
                res["unapproved"][name] = bad
    res["ok"] = not errors and not res["missing"] and not res["unapproved"]
    return res


def main():
    cmd = sys.argv[1]
    if cmd == "verbatim":
        rows = verbatim(sys.argv[2], sys.argv[3])
        for r in rows:
            if not r["match"]:
                print(f"::error::verbatim mismatch: case {r['case']}: {r['item']}")
        print(json.dumps(rows, indent=1, ensure_ascii=False))
        return 0 if all(r["match"] for r in rows) else 1
    if cmd == "scan":
        rows = scan()
        print(json.dumps(rows, indent=1))
        return 0 if all(r["clean"] for r in rows) else 1
    if cmd == "audit":
        res = audit(sys.argv[2], sys.argv[3:])
        print(f"::notice title=SL-002 audit {Path(sys.argv[2]).name}::"
              + json.dumps({k: res[k] for k in ('ok', 'n_errors', 'axioms', 'missing', 'unapproved')}))
        print(json.dumps(res, indent=1))
        return 0 if res["ok"] else 1
    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    sys.exit(main())
