"""SOTA-8 relation engine: certified directional derivation ("semantic delta") + the CJCS refuter.

Why: the CJCS engine (cjcs4) certifies equivalence only by definitional equality or by proving / refuting each
statement on its own. For real theorems (ProofNet-style) proving the theorem itself is research-hard, but
deriving one formulation from the other (binder order, implicit vs explicit binders, hypothesis splitting,
instance variants) is often routine. Prior art: BEq+ (Poiroux et al., EMNLP 2025) proves each statement from
the other with restricted tactics; this engine does the same kind of derivation, keeps the two directions
separate, and combines them with CJCS's certified refutations.

Obligations (one REPL session, the untrusted `#cjcs_search` proposer, then the unchanged clean verifier):
  wf_R  : (R) → (R)      — R elaborates in declaration context (universe parameters, `Type*`, implicit binders)
  wf_C  : (C) → (C)
  impl_RC : (R) → (C)    — derivation portfolio, R available as hypothesis
  impl_CR : (C) → (R)
  equiv : (R) ↔ (C) := ⟨impl_RC, impl_CR⟩
Outcomes (only from verified certificates):
  both directions        → CERTIFIED_LOGICAL_EQUIVALENCE, direction "mutual_derivation"
  one direction          → CERTIFIED_IMPLICATION ("reference_implies_candidate" / "candidate_implies_reference");
                           the converse is UNKNOWN unless CJCS certifies a difference
  neither                → CJCS (cjcs4.run_case) for refutations and the remaining CJCS verdicts
  wf fails               → INCONCLUSIVE / EXTRACTION (input not evaluable), with the Lean error
A failed search is never a negative result.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from .. import adelta12 as A
from ..toolchain import Toolchain
from . import cjcs as S3
from . import cjcs4 as E

DERIVE = [
    "intro h; exact h",
    "intro h; intros; exact h ..",
    "intro h; intros; first | (apply h <;> first | assumption | infer_instance | (intros; assumption)) | exact h ..",
    "intro h; intros; solve_by_elim (maxDepth := 8)",
    "intro h; intros; simp_all",
    "intro h; simpa using h",
    "intro h; intros; omega",
    "intro h; intros; exact?",
]
MATHLIB_ONLY = ["intro h; intros; aesop", "intro h; intros; tauto"]   # unknown tactics in core Lean would break parsing


def portfolio() -> list[str]:
    return DERIVE + (MATHLIB_ONLY if A.MATHLIB else [])


def obligations(R: str, C: str) -> dict:
    # wf: the statement elaborates in declaration context. `(S) → True` rather than `(S) → (S)`: each `Type _` /
    # `Type*` occurrence becomes its own universe parameter, so two copies of S need not unify.
    return {"wf_R": (f"({R}) → True", ["exact fun _ => trivial"]),
            "wf_C": (f"({C}) → True", ["exact fun _ => trivial"]),
            "impl_RC": (f"({R}) → ({C})", portfolio()),
            "impl_CR": (f"({C}) → ({R})", portfolio()),
            "equiv": (f"({R}) ↔ ({C})", ["exact ⟨impl_RC, impl_CR⟩"])}


DEPS = {"impl_RC": ["wf_R", "wf_C"], "impl_CR": ["wf_R", "wf_C"], "equiv": ["impl_RC", "impl_CR"]}


def delta(spec: dict, tc: Toolchain, buildp: Path, work: Path) -> dict:
    R, C = spec["reference"], spec["lean"]
    ident = "CJ_" + re.sub(r"[^A-Za-z0-9_]", "_", spec["id"])
    ns = f"ProofScopeCert.{ident}"
    out = {"stage": "delta"}
    pre = E.preamble()
    work = Path(work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    repl = E.Repl(E.find_repl(), os.pathsep.join(p for p in [str(buildp), os.environ.get("LEAN_PATH", "")] if p), work)
    t0 = time.monotonic()
    try:
        r0 = repl.send(A.import_lines() + "import Lean\n" + E.search_source() + "\nset_option linter.unusedVariables false\nset_option autoImplicit false\n" + pre, None)
        if "env" not in r0 or E._errors(r0):
            return {**out, "status": "SEARCH_ENV_LOAD", "detail": E._errors(r0)[:3]}
        ob = obligations(R, C)
        req = {"budget": E.BUDGET, "obligations": [{"name": k, "stmt": s, "alts": a, "deps": DEPS.get(k, [])} for k, (s, a) in ob.items()]}
        r = repl.send(f"namespace {ns}\n#cjcs_search {E._lean_str(json.dumps(req, ensure_ascii=False))}\nend {ns}", r0["env"])
        rows = E._infos(r, "CJCS_SEARCH")
        if len(rows) != 1:
            return {**out, "status": "SEARCH_PROCESS", "detail": E._errors(r)[:3]}
        res = {x["name"]: x for x in rows[0]}
    except E.ReplError as err:
        return {**out, "status": "SEARCH_TIMEOUT" if "timed out" in str(err) else "SEARCH_PROCESS", "detail": str(err)[:500]}
    finally:
        repl.close()
    out["search_s"] = round(time.monotonic() - t0, 2)
    out["search"] = res
    if any(res[k]["status"] != "proposed" for k in ("wf_R", "wf_C")):
        bad = {k: res[k].get("last_error") for k in ("wf_R", "wf_C") if res[k]["status"] != "proposed"}
        return {**out, "status": "NOT_EVALUABLE", "detail": bad}
    props = {k: (s, [a[res[k]["alt"]]]) for k, (s, a) in ob.items() if res[k]["status"] == "proposed"}
    v = E.verify(ident, A.import_lines() + pre + "set_option autoImplicit false\n" + S3.HEADER, props, tc, work / "certify")
    out.update(status="OK", certificates=v["certificates"], rejected=v["rejected"], certify_status=v["status"],
               certificate_source=v.get("certificate_source"))
    return out


def run_case(spec: dict, tc: Toolchain, buildp: Path, work: Path) -> dict:
    work = Path(work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    row = {"id": spec["id"], "reference": spec["reference"], "lean": spec["lean"], "engine": "sota8-delta+cjcs4"}
    try:
        E.preamble()
    except ValueError as err:
        row.update(verdict="INCONCLUSIVE", reason=f"extraction failed: {err}", failure_class="EXTRACTION")
        return row
    d = delta(spec, tc, buildp, work / "delta")
    row["delta"] = {k: v for k, v in d.items() if k != "certificate_source"}
    if d.get("status") == "NOT_EVALUABLE":
        row.update(verdict="INCONCLUSIVE", reason="extraction failed", failure_class="EXTRACTION", detail=d["detail"])
        return row
    certs = set(d.get("certificates") or {})
    if "equiv" in certs:
        row.update(verdict="CERTIFIED_LOGICAL_EQUIVALENCE", direction="mutual_derivation", theorem="Iff.intro",
                   certificates=d["certificates"], certificate_source=d["certificate_source"])
        return row
    one = [k for k in ("impl_RC", "impl_CR") if k in certs]
    c = E.run_case(spec, tc, buildp, work / "cjcs")                       # refutations and CJCS verdicts
    row["cjcs"] = {k: c.get(k) for k in ("verdict", "direction", "reason", "failure_class", "stats")}
    if c.get("verdict") in ("CERTIFIED_LOGICAL_DIFFERENCE", "CERTIFIED_LOGICAL_EQUIVALENCE", "INCONSISTENT"):
        for k in ("verdict", "direction", "theorem", "certificates", "certificate_source", "witnesses", "regions"):
            if k in c:
                row[k] = c[k]
        row["delta_one_way"] = one
        return row
    if one:
        k = one[0]
        row.update(verdict="CERTIFIED_IMPLICATION",
                   direction="reference_implies_candidate" if k == "impl_RC" else "candidate_implies_reference",
                   certificates={x: d["certificates"][x] for x in ("wf_R", "wf_C", k) if x in d["certificates"]},
                   certificate_source=d["certificate_source"],
                   note="converse not certified (unknown, not refuted)")
        return row
    for k in ("verdict", "reason", "failure_class", "detail", "partial"):
        if k in c:
            row[k] = c[k]
    return row


def main(argv=None) -> int:
    import argparse
    from concurrent.futures import ProcessPoolExecutor
    ap = argparse.ArgumentParser(prog="python -m proofscope.experimental.sota8")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("specs", nargs="+")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args(argv)
    out = a.out.resolve()
    E.find_repl()
    b = E.build(Toolchain.find(), out / "build")
    if not b["ok"]:
        print(json.dumps(b)[:3000])
        return 2
    (out / "rows").mkdir(parents=True, exist_ok=True)
    for p in a.specs:
        spec = json.loads(Path(p).read_text())
        row = run_case(spec, Toolchain.find(), out / "build", out / "work" / Path(p).stem)
        for k in ("expected", "must_not_be"):
            row[k] = spec.get(k)
        (out / "rows" / (Path(p).stem + ".json")).write_text(json.dumps(row, ensure_ascii=False, indent=1))
        print(row["id"], row["verdict"], row.get("direction"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
