"""SOTA-9 mission B: audit two declarations straight from a Lean source file, by name.

    python -m proofscope.source_audit --file Paper.lean --ref Foo.main_thm --cand Foo.main_thm' --out DIR

Why: comparing statements as text loses context (imports, `namespace`, `open`, `variable` binders,
universes, local notation) and any re-typing can silently change meaning. Here nothing is re-typed:

1. The source file is compiled unchanged as its own module (`PSrc_<sha>`). Compile errors → NOT_EVALUABLE.
2. Lean itself reports each declaration's exact kernel type, universe parameters, kind and `sorry` use.
3. The compared statements are `type_of% @Name.{u…}` — the kernel types of the named constants, so the
   statement is identical to the source declaration by construction (variables, implicit binders and
   coercions are already elaborated). The search session and the certificate both `import PSrc_<sha>`;
   leanchecker replays the certificate against that module.

Universe parameters: when both declarations have the same number, they are instantiated positionally with
shared names; a certificate then proves the relation for every value of those parameters, which implies the
relation between the universe-polymorphic theorems. Otherwise each side gets its own names (still sound, but
derivations that need to instantiate one side at the other's universes will not be found).

SECURITY: compiling a Lean file runs its metaprograms (`#eval`, macros, `initialize`). Audit only files you
trust, inside a disposable environment (Colab, a container); never in CI jobs that hold secrets or write tokens.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from .auditor import audit, markdown
from .experimental import cjcs4 as E
from .toolchain import Toolchain

PROBE = r'''import Lean
import {module}
open Lean Meta

def psInfo (modName : Name) (q : String) : MetaM Json := do
  let env ← getEnv
  let n := q.toName
  let inMod (m : Name) : Bool :=
    match env.getModuleIdxFor? m with
    | some i => env.header.moduleNames[i.toNat]? == some modName
    | none => false
  let cands : Array Name :=
    if env.contains n then #[n]
    else env.constants.fold (init := #[]) fun acc m _ =>
      if inMod m && !m.isInternal && n.isSuffixOf m then acc.push m else acc
  if cands.size != 1 then
    return Json.mkObj [("query", q), ("found", false), ("candidates", toJson (cands.toList.map toString))]
  let r := cands[0]!
  let some ci := env.find? r | return Json.mkObj [("query", q), ("found", false), ("candidates", toJson ([] : List String))]
  let kind := match ci with
    | .thmInfo _ => "theorem" | .axiomInfo _ => "axiom" | .defnInfo _ => "def"
    | .opaqueInfo _ => "opaque" | _ => "other"
  let isP ← isProp ci.type
  let ty ← ppExpr ci.type
  let ownAx ← collectAxioms r
  let mut typeSorry : Array String := #[]
  for c in ci.type.getUsedConstants do
    if (← collectAxioms c).contains ``sorryAx then typeSorry := typeSorry.push c.toString
  return Json.mkObj [("query", q), ("found", true), ("name", r.toString), ("kind", kind),
    ("levelParams", toJson (ci.levelParams.map toString)), ("isProp", isP), ("type", toString ty),
    ("inSourceModule", inMod r), ("proofAxioms", toJson (ownAx.toList.map toString)),
    ("typeUsesSorry", toJson typeSorry.toList)]

#eval show MetaM Unit from do
  for q in {queries} do
    IO.println ("PSINFO " ++ (← psInfo `{module} q).compress)
'''


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _errors(output: str) -> list[str]:
    return [l for l in output.splitlines() if re.search(r":\d+:\d+: error", l)][:10]


def compile_source(tc: Toolchain, text: str, work: Path) -> dict:
    module = "PSrc_" + _sha(text)[:16]
    src, build = work / "src", work / "build"
    src.mkdir(parents=True, exist_ok=True)
    f = src / f"{module}.lean"
    f.write_text(text)
    cc = tc.compile(f, build / f"{module}.olean", src, timeout=900)
    errs = _errors(cc.output)
    return {"module": module, "build": str(build), "ok": cc.returncode == 0 and not errs,
            "errors": errs or ([cc.output[-1500:]] if cc.returncode else []),
            "sorry_warnings": len(re.findall(r"declaration uses 'sorry'|declaration uses `sorry`", cc.output))}


def inspect(tc: Toolchain, module: str, build: str, names: list[str], work: Path) -> list[dict]:
    probe = work / "probe"
    probe.mkdir(parents=True, exist_ok=True)
    f = probe / "Probe.lean"
    f.write_text(PROBE.format(module=module, queries="[" + ", ".join(E._lean_str(n) for n in names) + "]"))
    old = os.environ.get("LEAN_PATH")
    os.environ["LEAN_PATH"] = os.pathsep.join(p for p in [build, old or ""] if p)
    try:
        r = tc.compile(f, None, probe, timeout=600)
    finally:
        if old is None:
            os.environ.pop("LEAN_PATH", None)
        else:
            os.environ["LEAN_PATH"] = old
    rows = [json.loads(l[len("PSINFO "):]) for l in r.output.splitlines() if l.startswith("PSINFO ")]
    if len(rows) != len(names):
        raise RuntimeError(f"declaration probe failed: {_errors(r.output) or r.output[-1500:]}")
    return rows


def statements(ri: dict, ci: dict) -> tuple[str, str, list[str], str]:
    """Exact statements as `type_of% @Name.{…}` plus the universe lines they need."""
    lr, lc = ri["levelParams"], ci["levelParams"]
    if len(lr) == len(lc):
        ur = uc = [f"u_ps{i + 1}" for i in range(len(lr))]
        note = "shared positionally" if lr else "none"
    else:
        ur, uc = [f"u_psr{i + 1}" for i in range(len(lr))], [f"u_psc{i + 1}" for i in range(len(lc))]
        note = "different counts; separate names (sound, derivations across universes not attempted)"
    def term(name, us):
        return f"type_of% @{name}" + (".{" + ", ".join(us) + "}" if us else "")
    unis = sorted(set(ur) | set(uc))
    return term(ri["name"], ur), term(ci["name"], uc), ([f"universe {' '.join(unis)}"] if unis else []), note


def source_audit(text: str, ref: str, cand: str, out: Path | None = None) -> dict:
    out = Path(out or "proofscope_source_audit").resolve()
    out.mkdir(parents=True, exist_ok=True)
    tc = Toolchain.find()
    src_info = {"file_sha256": _sha(text), "ref_query": ref, "cand_query": cand}
    base = {"proved": [], "unknown": [], "not_established": [], "diagnostics": [], "hints": [], "source": src_info}

    def stop(why: str, diags: list[str]) -> dict:
        rep = {**base, "status": "NOT_EVALUABLE", "diagnostics": [why] + diags}
        (out / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
        return rep

    comp = compile_source(tc, text, out / "source")
    src_info.update(module=comp["module"], sorry_warnings=comp["sorry_warnings"])
    if not comp["ok"]:
        return stop("the source file does not compile unchanged (imports must be available on LEAN_PATH)", comp["errors"])
    info = inspect(tc, comp["module"], comp["build"], [ref, cand], out / "source")
    src_info["declarations"] = info
    for side, i in (("reference", info[0]), ("candidate", info[1])):
        if not i["found"]:
            c = i.get("candidates") or []
            return stop(f"{side} `{i['query']}` not found" + (f"; ambiguous: {c}" if c else ""), [])
        if not i["isProp"]:
            return stop(f"{side} `{i['name']}` is a {i['kind']} whose type is not a proposition", [])
    R, C, unis, note = statements(info[0], info[1])
    src_info["universes"] = note
    rep = audit(R, C, unis, out, extra_imports=[comp["module"]], extra_lean_path=comp["build"])
    rep["source"] = src_info
    rep["statements_display"] = {"R": f"{info[0]['name']} : {info[0]['type']}", "C": f"{info[1]['name']} : {info[1]['type']}"}
    for i in info:
        if i["typeUsesSorry"]:
            rep["not_established"].append(f"`{i['name']}` is stated in terms of {i['typeUsesSorry']}, whose definitions use "
                                          "sorry; any relation holds only relative to those placeholder definitions")
        if "sorryAx" in i["proofAxioms"] and not i["typeUsesSorry"]:
            rep["diagnostics"].append(f"note: the source proof of `{i['name']}` uses sorry (irrelevant here: only its statement is compared)")
    (out / "report.json").write_text(json.dumps({k: v for k, v in rep.items() if k != "engine_row"}, ensure_ascii=False, indent=1, default=str))
    (out / "report.md").write_text(markdown(rep))
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m proofscope.source_audit")
    ap.add_argument("--file", type=Path, required=True)
    ap.add_argument("--ref", required=True, help="declaration name (full, or a unique suffix within the file)")
    ap.add_argument("--cand", required=True)
    ap.add_argument("--out", type=Path, default=Path("proofscope_source_audit"))
    a = ap.parse_args(argv)
    rep = source_audit(a.file.read_text(), a.ref, a.cand, a.out)
    print(rep["status"], json.dumps(rep.get("statements_display"), ensure_ascii=False))
    print("\n".join(rep.get("diagnostics") or []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
