"""ProofScope v1.2 adapter (frozen engine: `proofscope.v12` / `proofscope.adelta12`).

ProofScope takes two closed propositions, not two declarations. Step 1 (`closed`) elaborates each
declaration in its own header and prints its type with `pp.fullNames`, outside the section that holds the
header's `open`s, so the printed text needs no `open`. Step 2 re-elaborates the printed text under the
imports only and checks `printed = type_of% decl` by `with_reducible rfl` (a meaning-preservation
certificate for the adapter). A side that fails either step is NON_ELABORATING or UNSUPPORTED_INPUT, and
counted as such. Step 3 runs the frozen engine on the two printed propositions.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .. import outcomes
from ._decl import merged_imports, rename, split_header, with_sorry

PRINT = r'''
open Lean Elab Command in
#eval show CommandElabM Unit from do
  let some ci := (← getEnv).find? `{name} | throwError "PS_NO_DECL"
  let fmt ← liftTermElabM <| withOptions (fun o =>
      (((o.setBool `pp.fullNames true).setBool `pp.funBinderTypes true).setBool `pp.proofs true).setBool `pp.deepTerms true)
    <| Meta.ppExpr ci.type
  logInfo m!"PS_CLOSED {(toString fmt).replace "\n" " "}"
'''


def side_file(header: str, decl: str, name: str, imports: list[str]) -> str:
    imps, rest = split_header(header)
    if any(l.strip().startswith(("namespace", "end ")) for l in rest):
        raise ValueError("header opens a namespace")
    body = "\n".join(rest)
    return "\n".join(["import Lean"] + imports) + f"\n\nsection\n{body}\n\n{rename(with_sorry(decl), name)}\n\nend\n" + PRINT.replace("{name}", name)


def check_file(header: str, decl: str, name: str, imports: list[str], printed: str) -> str:
    imps, rest = split_header(header)
    body = "\n".join(rest)
    return ("\n".join(imports) + f"\n\nsection\n{body}\n\n{rename(with_sorry(decl), name)}\n\nend\n\n"
            f"example : ({printed}) = type_of% @{name} := by with_reducible rfl\n")


def prepare(case: dict, workdir: Path, lean_cmd: list[str]) -> dict:
    workdir = workdir.resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    imports = merged_imports(case["ref_header"], case["cand_header"])
    steps = []
    for side, h, d in (("ref", case["ref_header"], case["ref_decl"]), ("cand", case["cand_header"], case["cand_decl"])):
        try:
            (workdir / f"{side}_print.lean").write_text(side_file(h, d, f"ps_{side}_decl", imports))
        except ValueError as e:
            return {"unsupported": str(e)}
        steps.append(lean_cmd + [str(workdir / f"{side}_print.lean")])
    return {"imports": imports, "print_cmds": steps}


def extract_printed(output: str) -> str | None:
    for line in output.splitlines():
        i = line.find("PS_CLOSED ")
        if i >= 0:
            return line[i + len("PS_CLOSED "):].strip()
    return None


def engine_cmd(case_id: str, ref: str, cand: str, workdir: Path, module: str = "proofscope.v12") -> list[str]:
    workdir = workdir.resolve()
    spec = workdir / f"{case_id}.json"
    spec.write_text(json.dumps({"id": case_id, "reference": ref, "lean": cand}, ensure_ascii=False))
    return [sys.executable, "-m", module, "run", str(spec), "--out", str(workdir / "ps_out"), "--jobs", "1"]


def parse_engine(case_id: str, workdir: Path, mapper=None) -> dict:
    p = workdir.resolve() / "ps_out" / "rows" / f"{case_id}.json"
    if not p.exists():
        return {"native_verdict": None}
    row = json.loads(p.read_text())
    v = row.get("verdict", "INCONCLUSIVE")
    certs = sorted((row.get("certificates") or {}).keys())
    out = {"native_verdict": v, "reason": row.get("reason"), "theorem": row.get("theorem"), "certificates": certs,
           "certify_status": row.get("certify_status"),
           # NO_ASSUMPTION_DELTA is decided by meta-level comparison of the elaborated telescopes, with no
           # kernel certificate; decisive verdicts carry kernel-replayed certificates (certify gate)
           "certificate_kind": "structural" if v == "NO_ASSUMPTION_DELTA" else ("kernel" if certs and row.get("theorem") else None)}
    if mapper is not None:
        out["certificate_kind"] = "kernel" if v.startswith("CERTIFIED_") else None
        out["direction"] = row.get("direction")
        out["regions"] = row.get("regions")
    for t in ("A", "B"):
        o = (mapper or outcomes.proofscope)(v, t)
        if row.get("reason") == "extraction failed":
            o = {"certified": "NON_ELABORATING", "native": "NON_ELABORATING"}
        out[f"track_{t}"] = o
    return out


def imports_env(imports: list[str]) -> dict:
    mods = [l.split(None, 1)[1].strip() for l in imports if l.startswith("import ")]
    return dict(os.environ, PROOFSCOPE_IMPORTS=",".join(mods))
