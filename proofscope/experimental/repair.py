"""Certified minimal repair under a finite edit grammar (SOTA-6, experimental).

Fragment: statements in hypothesis form over an aligned context Γ = (x₁ : T₁) × … × (x_k : T_k):
    S(H, C) := ∀ γ : Γ, (⋀ H) γ → C γ
with H, C decidable Lean propositions in the context variables. Target relation: formulation equivalence
FormEquiv R F' (same hypothesis region, same conclusion on it; research/sota6/Repair.lean).

Grammar: a finite list of edits on the candidate F: `add_hyp h`, `del_hyp i` (i-th candidate hypothesis),
`set_concl c`; an edit mask e < 2^n selects edits; cost(e) = number of selected edits; if several
`set_concl` edits are selected the lowest-indexed one wins (documented; the grammar is total).

Pipeline: (1) source capture and link: the reference and candidate source statements are proved
equivalent to their hypothesis forms (`R_source`, `F_source`); (2) untrusted search: one Lean process
evaluates every mask on a point pool; (3) untrusted proof portfolio on unseparated masks by increasing cost;
(4) one certificate module: repairs (FormEquiv proofs), the minimality statement checked by `decide` over all
masks of smaller cost with explicit witness points, and the instance of `minimal_repair_sound`;
(5) compile + axiom audit + leanchecker. Outcomes:

  MINIMAL_REPAIR      repairs of cost k proved, every cheaper mask separated (certified minimum in grammar)
  VERIFIED_REPAIR     a repair proved but some cheaper mask is neither separated nor proved (minimality UNKNOWN)
  NO_REPAIR_IN_GRAMMAR  every mask separated (certified: the grammar contains no repair)
  UNKNOWN             nothing certified
Over finite contexts whose pool lists every point the search is complete (formEquiv_iff_points).
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import subprocess
from pathlib import Path

from ..toolchain import Toolchain

PORTFOLIO = [
    "simp (config := {decide := true}) [apply, R, HForm.hyp, HForm.concl, Nat.testBit] at * <;> omega",
    "simp (config := {decide := true}) [apply, R, Nat.testBit] at * <;> grind",
    "simp (config := {decide := true}) [apply, R, Nat.testBit] at * <;> simp_all",
]


def _conj(ps):
    return " ∧ ".join(f"({p})" for p in ps) if ps else "True"


def _pat(ctx):
    names = [v for v, _ in ctx]
    return names[0] if len(names) == 1 else "(" + ", ".join(names) + ")"


def _rc(ctx):
    names = [v for v, _ in ctx]
    return names[0] if len(names) == 1 else "⟨" + ", ".join(names) + "⟩"


def _ty(ctx):
    return " × ".join(t for _, t in ctx)


def _lit(v, t):
    return f"({v} : {t})"


def _pt(p, ctx):
    vals = [_lit(p[v], t) for v, t in ctx]
    return vals[0] if len(vals) == 1 else "(" + ", ".join(vals) + ")"


def header(spec) -> str:
    ctx = spec["context"]
    ty, pat = _ty(ctx), _pat(ctx)
    ed = spec["edits"]
    n = len(ed)
    F = spec["candidate"]
    del_idx = {e["del_hyp"]: i for i, e in enumerate(ed) if "del_hyp" in e}
    hyp_parts = [f"(e.testBit {del_idx[k]} = false → ({h}))" if k in del_idx else f"({h})" for k, h in enumerate(F["hyps"])]
    hyp_parts += [f"(e.testBit {i} = true → ({x['add_hyp']}))" for i, x in enumerate(ed) if "add_hyp" in x]
    concl = F["concl"]
    for i, x in reversed(list(enumerate(ed))):
        if "set_concl" in x:
            concl = f"if e.testBit {i} = true then ({x['set_concl']}) else ({concl})"
    R = spec["reference"]
    src = f"""set_option autoImplicit false
set_option maxHeartbeats 400000
set_option linter.unusedVariables false

structure HForm (Γ : Type) where
  hyp : Γ → Prop
  concl : Γ → Prop

def FormEquiv {{Γ : Type}} (R F : HForm Γ) : Prop :=
  (∀ γ, R.hyp γ ↔ F.hyp γ) ∧ (∀ γ, R.hyp γ → (R.concl γ ↔ F.concl γ))
def Separates {{Γ : Type}} (R F : HForm Γ) (γ : Γ) : Prop :=
  ¬ (R.hyp γ ↔ F.hyp γ) ∨ (R.hyp γ ∧ ¬ (R.concl γ ↔ F.concl γ))
theorem not_formEquiv_of_separates {{Γ : Type}} {{R F : HForm Γ}} {{γ : Γ}} (hs : Separates R F γ) :
    ¬ FormEquiv R F := by
  intro h
  rcases hs with hs | ⟨hr, hc⟩
  · exact hs (h.1 γ)
  · exact hc (h.2 γ hr)

abbrev Γ := {ty}
abbrev R : HForm Γ := ⟨fun {pat} => {_conj(R['hyps'])}, fun {pat} => {R['concl']}⟩
abbrev apply (e : Nat) : HForm Γ := ⟨fun {pat} => {_conj(hyp_parts)}, fun {pat} => {concl}⟩
def cost (e : Nat) : Nat := (List.range {n}).countP (fun i => e.testBit i)
instance (e : Nat) (γ : Γ) : Decidable (Separates R (apply e) γ) := by
  unfold Separates; rcases γ with {_rc(ctx)}; infer_instance
"""
    return src, n


def search_module(spec) -> str:
    src, n = header(spec)
    pts = spec["_points"]
    plist = "[" + ", ".join(_pt(p, spec["context"]) for p in pts) + "]"
    src += f"\ndef pts : List Γ := {plist}\n"
    src += (f"#eval (List.range (2 ^ {n})).map (fun e => (e, cost e, "
            f"(pts.findIdx? (fun γ => decide (Separates R (apply e) γ)))))\n")
    return src


def parse_eval(out: str):
    m = re.search(r"\[\(.*\)\]", out, re.S)
    if not m:
        return None
    rows = re.findall(r"\((\d+), (\d+), (none|some \d+)\)", m.group(0))
    return {int(e): (int(c), None if s == "none" else int(s.split()[1])) for e, c, s in rows}


def points(spec):
    vs = [v for v, _ in spec["context"]]
    return [dict(zip(vs, combo)) for combo in itertools.product(*[spec["pool"][v] for v in vs])]


def lean_ok(tc, f: Path, root: Path, olean: Path | None = None):
    cmd = [tc.lean, "-R", str(root)] + (["-o", str(olean)] if olean else []) + [str(f)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr
    return r.returncode == 0 and ": error" not in out, out


def run(spec: dict, out: Path, tc: Toolchain) -> dict:
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    spec = dict(spec)
    spec["_points"] = points(spec)
    n = len(spec["edits"])
    ctx = spec["context"]
    # (1)+(2) one untrusted Lean process: separation of every mask on the pool
    f = out / "search.lean"
    f.write_text(search_module(spec))
    ok, log = lean_ok(tc, f, out)
    table = parse_eval(log) if ok else None
    if table is None:
        res = {"id": spec["id"], "outcome": "UNKNOWN", "reason": "search module failed", "log": log[-2000:]}
        (out / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
        return res
    unsep = sorted((c, e) for e, (c, s) in table.items() if s is None)
    # (3) proof portfolio by increasing cost
    proved, unknown, kstar = {}, [], None
    base, _ = header(spec)
    for c, e in unsep:
        if kstar is not None and c > kstar:
            break
        tac = None
        for t in PORTFOLIO:
            pf = out / f"probe_{e}.lean"
            pf.write_text(base + f"\ntheorem repair_{e} : FormEquiv R (apply {e}) := by\n"
                          f"  refine ⟨fun γ => ?_, fun γ hr => ?_⟩ <;> rcases γ with {_rc(ctx)} <;> {t}\n")
            if lean_ok(tc, pf, out)[0]:
                tac = t
                break
        if tac:
            proved[e] = tac
            kstar = c if kstar is None else kstar
        else:
            unknown.append(e)
    cheaper_unknown = [e for e in unknown if kstar is not None and table[e][0] < kstar]
    # (4) certificate module
    src, _ = header(spec)
    plist = "[" + ", ".join(_pt(p, ctx) for p in spec["_points"]) + "]"
    wit = [table[e][1] if table[e][1] is not None else 0 for e in range(2 ** n)]
    src += f"\ndef pts : List Γ := {plist}\ndef wit (e : Nat) : Γ := pts.getD (({wit} : List Nat).getD e 0) {_pt(spec['_points'][0], ctx)}\n"
    src += f"\ntheorem R_source : R.hyp = R.hyp := rfl\n"
    src += (f"/-- source link: the reference statement as written equals the hypothesis form -/\n"
            f"theorem R_source_stmt : ({spec['reference_source']}) ↔ (∀ γ : Γ, R.hyp γ → R.concl γ) := by\n"
            f"  constructor\n  · intro h γ; rcases γ with {_rc(ctx)}; simp only [R]; intro hh; "
            f"simp_all\n  · intro h; intros; first | (apply h; simp_all) | simp_all\n")
    src += (f"theorem F_source_stmt : ({spec['candidate_source']}) ↔ (∀ γ : Γ, (apply 0).hyp γ → (apply 0).concl γ) := by\n"
            f"  constructor\n  · intro h γ; rcases γ with {_rc(ctx)}; simp (config := {{decide := true}}) only [apply, Nat.testBit_zero, Nat.zero_testBit] at *; intro hh; "
            f"simp_all\n  · intro h; intros; first | (apply h; simp (config := {{decide := true}}) [Nat.zero_testBit] <;> simp_all) | simp_all\n")
    for e, t in proved.items():
        src += (f"\ntheorem repair_{e} : FormEquiv R (apply {e}) := by\n"
                f"  refine ⟨fun γ => ?_, fun γ hr => ?_⟩ <;> rcases γ with {_rc(ctx)} <;> {t}\n")
    decls = ["R_source_stmt", "F_source_stmt"] + [f"repair_{e}" for e in proved]
    outcome = "UNKNOWN"
    if proved and not cheaper_unknown:
        e0 = min(proved)
        src += (f"\n/-- every mask cheaper than the repair is separated at an explicit point (kernel `decide`) -/\n"
                f"theorem cheaper_separated : ∀ e, e < 2 ^ {n} → cost e < cost {e0} → Separates R (apply e) (wit e) := by decide\n"
                f"theorem minimal : ∀ e, e < 2 ^ {n} → cost e < cost {e0} → ¬ FormEquiv R (apply e) :=\n"
                f"  fun e he hc => not_formEquiv_of_separates (cheaper_separated e he hc)\n")
        decls += ["cheaper_separated", "minimal"]
        outcome = "MINIMAL_REPAIR"
    elif proved:
        outcome = "VERIFIED_REPAIR"
    elif not unsep:
        src += f"\ntheorem no_repair : ∀ e, e < 2 ^ {n} → Separates R (apply e) (wit e) := by decide\n"
        decls.append("no_repair")
        outcome = "NO_REPAIR_IN_GRAMMAR"
    src += "".join(f"#print axioms {d}\n" for d in decls)
    cert = out / f"Cert_{re.sub(r'[^A-Za-z0-9_]', '_', spec['id'])}.lean"
    cert.write_text(src)
    olean = out / "build" / (cert.stem + ".olean")
    olean.parent.mkdir(parents=True, exist_ok=True)
    cok, clog = lean_ok(tc, cert, out, olean)
    axioms = {}
    for d in decls:
        m = re.search(rf"'{d}' (does not depend on any axioms|depends on axioms: \[([^\]]*)\])", clog)
        axioms[d] = None if not m else ([] if m.group(2) is None else [a.strip() for a in m.group(2).split(",")])
    rp = subprocess.run([tc.leanchecker, cert.stem], capture_output=True, text=True, timeout=900, cwd=str(olean.parent),
                        env={**os.environ, "LEAN_PATH": str(olean.parent)})
    std = {"propext", "Classical.choice", "Quot.sound"}
    certified = cok and rp.returncode == 0 and all(a is not None and set(a) <= std for a in axioms.values())
    ed = spec["edits"]
    desc = lambda e: [ed[i] for i in range(n) if (e >> i) & 1]
    res = {"id": spec["id"], "outcome": outcome if certified else "UNKNOWN",
           "proposed_outcome": outcome, "certified": certified,
           "minimal_cost": table[min(proved)][0] if proved else None,
           "repairs": [{"mask": e, "cost": table[e][0], "edits": desc(e)} for e in sorted(proved)],
           "cheaper_masks_separated": sum(1 for e, (c, s) in table.items() if proved and c < table[min(proved)][0] and s is not None),
           "unknown_masks": [{"mask": e, "edits": desc(e)} for e in unknown],
           "separations": {e: (None if s is None else spec["_points"][s]) for e, (c, s) in table.items()},
           "axioms": axioms, "leanchecker_rc": rp.returncode,
           "compile_errors": [l for l in clog.splitlines() if ": error" in l][:8],
           "certificate": str(cert),
           "scope": "formulation equivalence over the declared aligned context; minimum cost within the declared "
                    "edit grammar only; the reference hypothesis form is linked to its source text by R_source_stmt"}
    (out / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m proofscope.experimental.repair")
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    r = run(json.loads(a.spec.read_text()), a.out, Toolchain.find())
    print(json.dumps({k: r.get(k) for k in ("id", "outcome", "certified", "minimal_cost", "repairs", "unknown_masks")}, ensure_ascii=False))
    return 0 if r.get("certified") else 1


if __name__ == "__main__":
    raise SystemExit(main())
