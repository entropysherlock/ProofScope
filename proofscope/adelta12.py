"""Assumption Delta v1.2 (copy of frozen v1.1 with a countermodel-family registry and a Mathlib proof portfolio).

v1.2 changes: carriers come from `proofscope/models.py` (nonabelian groups, non-total partial orders,
rings with zero divisors, fields, sets and function points), filtered by Lean itself (a carrier without
the required instance fails to elaborate inside `first`). Refutations instantiate the universal claim
at the carrier's sample elements and close by `decide`/`simp`/`norm_num`. Sufficiency, redundancy and
unneeded-assumption proofs use a bounded Mathlib portfolio (`nlinarith`, `positivity`, `fun_prop`, `aesop`, ...).
Every accepted result passes the unchanged certify gate (recompile, standard axioms, kernel replay).

v1.1 description:
Assumption Delta v1.1 (copy of the frozen v1.0 engine with dependent-structure linking and minimality).

Changes from v1.0: clean binder names and instance binders printed as `[i : C α]` (linking of
dependent structures, Mathlib m04/m05); instance witnesses built from carrier operations; an
assumption-minimality mode (`lean/ProofScope/Composition.lean`, `inclusion_minimal`).

Original v1.0 description:
Assumption Delta (v1.0): certified meaning of assumptions added or dropped by a formalization.

For a reference R and a formal statement L, `lean/ProofScope/AssumptionExtract.lean` aligns the
elaborated binder telescopes and returns the shared model binders, the shared hypotheses, the added
and dropped assumptions (Prop binders, Prop-valued typeclasses, and data instances as `Nonempty (Cls)`),
and whether the conclusions agree. For each added assumption `A`, with shared conditions `C`:

    link_R / link_L   R and L are equivalent to the canonical telescopes the certificates talk about
    redundant         ∀ scope, C → A                        (theorem `redundant_schema_equiv`)
    restrictive       ∃ scope, C ∧ ¬ A        a model witness (theorem `restrictive_iff_strictly_weaker`)
    necessary         ∃ all,   C ∧ ¬ A ∧ ¬ P  the reference is false without A (`necessary_refutes_reference`)

Dropped assumptions are the mirror image (the Lean statement covers more; a `necessary` certificate
then shows the Lean claim is false). Each is checked by `certify` (clean recompile, standard axioms,
kernel replay). An assumption the rest of the statement depends on is DEPENDENT: no comparison is
defined, so it stays INCONCLUSIVE. Witness models are drawn from finite carriers (Bool, Fin 3, Unit,
Empty) and Nat/Int with small operation pools; failure to find one is reported, never read as redundancy.
"""

from __future__ import annotations

import argparse
import os
import json
import re
from itertools import product
from pathlib import Path

from .certify import certify
from .toolchain import Toolchain

SRC = Path(__file__).resolve().parents[1] / "lean"
# Mathlib mode: PROOFSCOPE_IMPORTS=Mathlib with LEAN_PATH pointing at a built Mathlib (GitHub workflow)
IMPORTS = [m for m in os.environ.get("PROOFSCOPE_IMPORTS", "").split(",") if m.strip()]
MATHLIB = "Mathlib" in IMPORTS


def import_lines() -> str:
    return "".join(f"import {m.strip()}\n" for m in IMPORTS)

CARRIERS = {
    "Bool": {"vals": ["true", "false"],
             "op2": ["fun a _ => a", "fun _ b => b", "fun a b => a && b", "fun a b => a || b", "fun a b => Bool.xor a b",
                     "fun a b => !a || b", "fun _ _ => true"],
             "op1": ["fun a => a", "fun a => !a", "fun _ => true"],
             "rel": ["fun _ _ => True", "fun a b => a = b", "fun a b => a ≠ b", "fun _ _ => False",
                     "fun a b => a = true ∨ b = false"]},
    "Fin 3": {"vals": ["(0 : Fin 3)", "(1 : Fin 3)", "(2 : Fin 3)"],
              "op2": ["fun a _ => a", "fun a b => a + b", "fun a b => a * b", "fun a b => max a b", "fun a b => a - b"],
              "op1": ["fun a => a", "fun a => a + 1", "fun _ => 0"],
              "rel": ["fun a b => a ≤ b", "fun a b => a < b", "fun a b => a = b", "fun _ _ => True"]},
    "Unit": {"vals": ["()"], "op2": ["fun _ _ => ()"], "op1": ["fun a => a"], "rel": ["fun _ _ => True", "fun _ _ => False"]},
    "Empty": {"vals": [], "op2": ["fun a _ => a"], "op1": ["fun a => a"], "rel": ["fun _ _ => True"]},
    "Nat": {"vals": ["0", "1", "2"],
            "op2": ["fun a b => a + b", "fun a b => a * b", "fun a _ => a", "fun a b => a - b", "fun _ _ => 0", "fun a b => max a b"],
            "op1": ["fun a => a", "fun a => a + 1", "fun _ => 0", "fun a => a / 2"],
            "rel": ["fun a b => a ≤ b", "fun a b => a < b", "fun a b => a = b", "fun _ _ => True"]},
}
POINT_POOLS = {"Nat": ["0", "1", "2", "3"], "Int": ["(-1 : Int)", "0", "1", "2"], "Bool": ["true", "false"]}
if MATHLIB:
    from .models import MATHLIB_CARRIERS, MATHLIB_POINTS, MATHLIB_PROOF_PORTFOLIO, MATHLIB_REFUTE
    CARRIERS.update(MATHLIB_CARRIERS)
    CARRIERS["Equiv.Perm (Fin 3)"] = {
        "vals": ["(1 : Equiv.Perm (Fin 3))", "(Equiv.swap 0 1 : Equiv.Perm (Fin 3))", "(Equiv.swap 1 2 : Equiv.Perm (Fin 3))"],
        "op2": ["fun a b => a * b"], "op1": ["fun a => a⁻¹", "fun a => a"], "rel": ["fun a b => a = b"]}
    CARRIERS["Bool × Bool"] = {"vals": ["((true, false) : Bool × Bool)", "((false, true) : Bool × Bool)"],
                              "op2": ["fun a _ => a"], "op1": ["fun a => a"], "rel": ["fun a b => a = b"]}
    POINT_POOLS.update({"ℝ": ["(-2 : ℝ)", "(-1 : ℝ)", "(0 : ℝ)", "(1 / 2 : ℝ)", "(1 : ℝ)", "(2 : ℝ)"],
                        "Set ℕ": ["(∅ : Set ℕ)", "(Set.univ : Set ℕ)", "({0} : Set ℕ)", "({1} : Set ℕ)"],
                        "ℕ": ["0", "1", "2", "3"], "ℤ": ["(-1 : ℤ)", "0", "1", "2"]})
    POINT_POOLS.update(MATHLIB_POINTS)


def build(tc: Toolchain, out: Path) -> dict:
    o = out / "ProofScope" / "AssumptionExtract11.olean"
    if o.exists():
        return {"ok": True}
    r = tc.compile(SRC / "ProofScope" / "AssumptionExtract11.lean", o, SRC, timeout=900)
    return {"ok": r.returncode == 0 and o.exists(), "log": r.as_dict()}


def extract(ref: str, lean: str, tc: Toolchain, buildp: Path, work: Path) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    f = work / "Assumptions_input.lean"
    f.write_text(f"{import_lines()}import ProofScope.AssumptionExtract11\n\n#proofscope_assumptions11 ({ref}) ({lean})\n")
    r = tc.run([tc.lean, str(f)], cwd=work, extra_path=buildp, timeout=600)
    for line in r.output.splitlines():
        i = line.find("PROOFSCOPE_ASSUMPTIONS11 ")
        if i >= 0:
            return json.loads(line[i + len("PROOFSCOPE_ASSUMPTIONS11 "):])
    return {"error": r.output[-3000:]}


def _subst(typ: str, carrier_names: dict[str, str]) -> str:
    for n, c in carrier_names.items():
        typ = re.sub(rf"(?<![\w.]){re.escape(n)}(?![\w.])", f"({c})" if " " in c else c, typ)
    return re.sub(r"\s+", " ", typ.strip())


def _pool_for(typ: str, carrier: str | None) -> list[str]:
    if carrier is not None:
        c = CARRIERS[carrier]
        cc = f"({carrier})" if " " in carrier else carrier
        if typ == f"{cc} → {cc} → {cc}":
            return c["op2"]
        if typ == f"{cc} → {cc}":
            return c["op1"]
        if typ == f"{cc} → {cc} → Prop":
            return c["rel"]
        if typ == cc:
            return c["vals"]
        # an instance binder over the carrier (e.g. `Group (Equiv.Perm (Fin 3))`, `Mul Bool`): the inferred
        # instance, or a one-field structure built from the carrier's operations (two structures on one
        # carrier are thereby both explored)
        if typ.endswith(cc) and re.match(r"^[A-Z][\w.]*\s", typ):
            return ["inferInstance"] + [f"⟨{o}⟩" for o in c["op2"] + c["op1"]]
    return POINT_POOLS.get(typ, [])


WITNESS_CAP = 240


def witnesses(scope: list[dict]) -> list[list[str]]:
    """Witness tuples for the in-scope binders: choose a carrier for each `Type` binder first, then
    operations and points from that carrier's pools (types printed by Lean, carriers substituted)."""
    types = [b for b in scope if b["type"] == "Type"]
    out = []
    for carriers in product(list(CARRIERS), repeat=len(types)):
        names = {b["name"]: c for b, c in zip(types, carriers)}
        cols = []
        for b in scope:
            if b["type"] == "Type":
                cols.append([names[b["name"]]])
                continue
            t = _subst(b["type"], names)
            car = next((c for c in carriers if t.startswith(f"({c})" if " " in c else c)), carriers[0] if carriers else None)
            cols.append(_pool_for(t, car))
        if all(cols):
            out.append([list(t) for t in product(*cols)][:60])
    # v1.2: round-robin across carrier choices. v1.1 concatenated per-carrier lists and truncated at 150,
    # so carriers late in the registry (every Mathlib family) were never tried for binders with large pools.
    rr = []
    for i in range(60):
        rr += [lst[i] for lst in out if i < len(lst)]
    return rr[:WITNESS_CAP]


def closers(vals: list[str]) -> str:
    base = ["decide", "trivial", "(intros; decide)", "(intro a; cases a)", "(intros; simp_all)", "(intros; omega)",
            "(intro h; obtain ⟨e⟩ := h; cases e)", "(intros; trivial)", "(constructor; decide)", "simp", "omega"]
    if MATHLIB:
        base += ["norm_num", "(intros; norm_num)", "(intros; linarith)", "(intros; positivity)", "(intros; nlinarith)",
                 "(intro h; have := h 1 (by norm_num); norm_num at this)", "(simp [Set.Nonempty])",
                 "(intro h; have := h (1 / 2) (by norm_num); norm_num at this)", "(intro h; obtain ⟨x, hx⟩ := h; simp at hx)"]
    pts = vals[:3] or ["true", "false"]
    for a in pts:
        for b in pts:
            base.append(f"(intro h; obtain ⟨h⟩ := h; have := h {a} {b}; revert this; decide)")
            base.append(f"(intro h; have := h {a} {b}; revert this; decide)")
            for c in pts[:2]:
                base.append(f"(intro h; have := h {a} {b} {c}; revert this; decide)")
        base.append(f"(intro h; have := h {a}; revert this; decide)")
        base.append(f"(intro h; have := h {a}; omega)")
    return " | ".join(f"({c}; done)" for c in base)


ALL_VALS = ["true", "false", "(0 : Fin 3)", "(1 : Fin 3)", "(2 : Fin 3)", "0", "1", "2", "(-1 : Int)", "()"]


def _vals_for(w: list[str], scope: list[dict]) -> list[str]:
    """Sample elements for refutations: those of the carriers chosen in this witness tuple (v1.2),
    plus the point values already in the tuple."""
    vals = []
    for b, x in zip(scope, w):
        if b["type"] == "Type" and x in CARRIERS:
            vals += CARRIERS[x]["vals"]
        elif b["type"] != "Type":
            vals.append(x)
    seen, out = set(), []
    for v in vals + ALL_VALS:
        if v not in seen:
            seen.add(v); out.append(v)
    return out[:6]


def sep_tactics(scope: list[dict], body_count: int) -> list[str]:
    tac = []
    for w in witnesses(scope):
        vals = _vals_for(w, scope)
        extra = (" | " + " | ".join(f"({c}; done)" for c in MATHLIB_REFUTE(vals))) if MATHLIB else ""
        tac.append(f"refine ⟨{', '.join(w)}, ?_⟩; and_intros <;> first | {closers(vals)}{extra}")
    return tac


REDUNDANT = (MATHLIB_PROOF_PORTFOLIO if MATHLIB else []) + (["(intros; positivity)", "(intros; norm_num)", "(intros; linarith)", "(intros; exact mul_comm _ _)",
              "(intros; simp [mul_comm])", "(intros; exact le_total _ _)"] if MATHLIB else []) + [
             "(intros; exact ⟨⟨‹_›⟩⟩)", "(intros; exact ⟨default⟩)", "(intros; exact ⟨fun _ _ => ‹∀ _ _, _› _ _⟩)","(intros; infer_instance)", "(intros; exact ⟨inferInstance⟩)", "(intros; exact ⟨Classical.decEq _⟩)",
             "(intros; exact ⟨fun _ => Classical.propDecidable _⟩)", "(intros; constructor; assumption)",
             "(intros; constructor; intros; simp_all)", "(intros; exact ⟨‹_›⟩)", "(intros; omega)", "(intros; simp_all)",
             "(intros; grind)", "(intros; trivial)"]


def read_witnesses(ident: str, names: list[str], tc: Toolchain, buildp: Path, certdir: Path) -> dict:
    """Witness models, read from the kernel-checked declarations of the certified module."""
    if not names:
        return {}
    f = certdir / "Witness_read.lean"
    f.write_text(f"{import_lines()}import ProofScope.AssumptionExtract11\nimport ProofScopeCert.{ident}\n\n"
                 + "".join(f"#proofscope_witness11 ProofScopeCert.{ident}.{n}\n" for n in names))
    r = tc.run([tc.lean, str(f)], cwd=certdir, extra_path=os.pathsep.join([str(buildp), str(certdir / "build")]), timeout=300)
    got = [json.loads(l[l.index("PROOFSCOPE_WITNESS11 ") + 21:]) for l in r.output.splitlines() if "PROOFSCOPE_WITNESS11 " in l]
    return dict(zip(names, got)) if len(got) == len(names) else {}


def binders(model: list[dict], exists: bool = False) -> str:
    """Instance binders are re-declared as instance binders, so the canonical context resolves instances
    exactly as the original statement did (checked by the link certificates). In `∃` they are explicit."""
    return " ".join(f"[{b['name']} : {b['type']}]" if b.get("inst") and not exists else f"({b['name']} : {b['type']})"
                    for b in model)


def run_case(spec: dict, tc: Toolchain, buildp: Path, work: Path) -> dict:
    ref, lean = spec["reference"], spec["lean"]
    out = {"id": spec["id"], "reference": ref, "lean": lean}
    d = extract(ref, lean, tc, buildp, work / "extract")
    if "error" in d:
        out.update(verdict="INCONCLUSIVE", reason="extraction failed", detail=d["error"][-600:])
        return out
    out["extraction"] = d
    if not d["added"] and not d["dropped"]:
        # v1.1.1: never report "no delta" when the conclusions differ
        out.update(verdict="NO_ASSUMPTION_DELTA" if d["conclusion_same"] else "CONCLUSION_ONLY_CHANGE",
                   reason=None if d["conclusion_same"] else "assumptions agree, conclusions differ: not an "
                          "assumption-level question (use CMCD on the conclusion)")
        return out
    if not d["conclusion_same"]:
        out.update(verdict="INCONCLUSIVE", reason="the conclusion also changed: assumption and conclusion deltas are not "
                                                   "composed here (use CMCD on the conclusion)")
        return out
    if any(a["dependent"] for a in d["added"] + d["dropped"]):
        out.update(verdict="INCONCLUSIVE_DEPENDENT",
                   reason="the rest of the statement depends on an added/dropped binder; no well-typed statement "
                          "without it exists, so no comparison is defined")
        return out
    model = d["model"]
    allb = binders(model)
    hyps = d["hyps"]
    H = " ∧ ".join(f"({h})" for h in hyps) if hyps else "True"
    Himp = "".join(f"({h}) → " for h in hyps)
    P = d["conclusion_ref"]
    ob = {}
    link_tac = ["constructor <;> intro h <;> intros <;> (first | (apply h <;> assumption) | (apply h <;> first | assumption | exact ⟨‹_›⟩)"
                " | (rename_i hn; obtain ⟨_⟩ := hn; apply h <;> assumption) | (simp_all))"]
    ob["link_R"] = (f"({ref}) ↔ (∀ {allb}, {Himp}{''.join(f'({a['prop']}) → ' for a in d['dropped'])}{P})", link_tac)
    ob["link_L"] = (f"({lean}) ↔ (∀ {allb}, {Himp}{''.join(f'({a['prop']}) → ' for a in d['added'])}{P})", link_tac)
    # v1.2: numerals in either statement and their successors join the ℕ point pool (as in minimality mode)
    lits = sorted({int(x) for x in re.findall(r"\b(\d+)\b", ref + " " + lean) if int(x) <= 20})
    for t in ("Nat", "ℕ"):
        if t in POINT_POOLS or t == "Nat":
            POINT_POOLS[t] = sorted(set(POINT_POOLS.get(t, [])) | {str(c) for c in lits} | {str(c + 1) for c in lits}, key=int)
    if d["added"] and d["dropped"]:
        return _mixed(spec, out, d, ob, allb, H, Himp, P, tc, buildp, work)
    for side, items, prefixes in (("add", d["added"], d["added_prefix"]), ("drop", d["dropped"], d["dropped_prefix"])):
        for j, a in enumerate(items):
            A = a["prop"]
            # v1.0.2: the model is ALL binders and ALL shared hypotheses of the reference telescope, exactly
            # as in `restrictive_iff_strictly_weaker` (R = ∀ m, C m → P m). Order does not matter (non-dependent
            # hypotheses commute). Minimizing to "mentioned" binders (v1.0) or to the prefix (v1.0.1) is unsound:
            # adversarial cases x01 (a point x : α proves Nonempty α) and ad04 (a later hypothesis implies A).
            pre = model
            preb = allb
            pH, pHimp, ph = H, Himp, len(hyps)
            scope_q = f"∀ {preb}, " if pre else ""
            ob[f"{side}{j}_redundant"] = (f"{scope_q}{pHimp}{A}", REDUNDANT)
            if pre:
                ob[f"{side}{j}_restrictive"] = (f"∃ {binders(model, True)}, ¬ ({A}) ∧ {pH}", sep_tactics(pre, ph))
            ob[f"{side}{j}_necessary"] = (f"∃ {binders(model, True)}, ¬ ({A}) ∧ ¬ ({P}) ∧ {H}", sep_tactics(model, len(hyps)))
    ident = "AD_" + re.sub(r"[^A-Za-z0-9_]", "_", spec["id"])
    r = certify(ident, import_lines() + "set_option maxHeartbeats 4000000\nset_option linter.unusedVariables false\n",
                ob, tc, work / "certify")
    certs = set(r["certificates"])
    out["certify_status"] = r["status"]
    out["certificates"] = r["certificates"]
    if not {"link_R", "link_L"} <= certs:
        out.update(verdict="INCONCLUSIVE", reason="canonical telescope not linked to the elaborated statements")
        return out
    witness_text = read_witnesses(ident, [k for k in certs if k.endswith(("_restrictive", "_necessary"))],
                                  tc, buildp, work / "certify")
    items = []
    for side, lst in (("add", d["added"]), ("drop", d["dropped"])):
        for j, a in enumerate(lst):
            k = f"{side}{j}"
            red, res, nec = (f"{k}_{x}" in certs for x in ("redundant", "restrictive", "necessary"))
            cls = "INCONSISTENT" if red and (res or nec) else ("NECESSARY" if nec else "RESTRICTIVE" if res else
                                                                "REDUNDANT" if red else "INCONCLUSIVE")
            items.append({"side": "added" if side == "add" else "dropped", "assumption": a["prop"], "class": cls,
                          "witness_model": witness_text.get(f"{k}_necessary") or witness_text.get(f"{k}_restrictive"),
                          "witness_statement": (r["certificates"].get(f"{k}_necessary") or r["certificates"].get(f"{k}_restrictive") or {}).get("statement")})
    out["assumptions"] = items
    cl = [(i["side"], i["class"]) for i in items]
    if any(c == "INCONSISTENT" for _, c in cl):
        out["verdict"] = "INCONSISTENT"
    elif ("added", "NECESSARY") in cl:
        out.update(verdict="REFERENCE_NEEDS_ASSUMPTION", theorem="necessary_refutes_reference",
                   reason="a certified model satisfies the shared conditions, violates the added assumption and "
                          "falsifies the conclusion: the reference claim is false without it")
    elif ("dropped", "NECESSARY") in cl:
        out.update(verdict="LEAN_CLAIM_FALSE", theorem="necessary_refutes_reference",
                   reason="the Lean statement dropped an assumption and a certified model falsifies it")
    elif ("added", "RESTRICTIVE") in cl and ("dropped", "RESTRICTIVE") not in cl:
        out.update(verdict="LEAN_WEAKER_BY_ASSUMPTION", theorem="restrictive_iff_strictly_weaker")
    elif ("dropped", "RESTRICTIVE") in cl and ("added", "RESTRICTIVE") not in cl:
        out.update(verdict="LEAN_STRONGER_BY_ASSUMPTION", theorem="restrictive_iff_strictly_weaker")
    elif all(c == "REDUNDANT" for _, c in cl):
        out.update(verdict="ASSUMPTION_EQUIVALENT", theorem="redundant_schema_equiv")
    elif ("added", "RESTRICTIVE") in cl and ("dropped", "RESTRICTIVE") in cl:
        out.update(verdict="ASSUMPTION_INCOMPARABLE")
    else:
        out["verdict"] = "INCONCLUSIVE"
    return out


def _mixed(spec, out, d, ob, allb, H, Himp, P, tc, buildp, work) -> dict:
    """v1.2: the formalization drops `D` and adds `A` (both non-empty). Decided jointly
    (`CompositionV12.lean`: mixed_strict, mixed_incomparable, mixed_ref_false). v1.1 classified `A` and
    `D` separately against the shared conditions, which is unsound here
    (`separate_restrictions_not_incomparable`; hostile cases z01, z02)."""
    model = d["model"]
    A = " ∧ ".join(f"({a['prop']})" for a in d["added"])
    D = " ∧ ".join(f"({a['prop']})" for a in d["dropped"])
    ex = binders(model, True)
    ob["d_implies_a"] = (f"∀ {allb}, {Himp}({D}) → {A}", REDUNDANT)
    ob["a_implies_d"] = (f"∀ {allb}, {Himp}({A}) → {D}", REDUNDANT)
    ob["a_not_d"] = (f"∃ {ex}, ({A}) ∧ ¬ ({D}) ∧ {H}", sep_tactics(model, 0))
    ob["d_not_a"] = (f"∃ {ex}, ({D}) ∧ ¬ ({A}) ∧ {H}", sep_tactics(model, 0))
    ob["ref_false"] = (f"∃ {ex}, ({D}) ∧ ¬ ({P}) ∧ {H}", sep_tactics(model, 0))
    ob["lean_false"] = (f"∃ {ex}, ({A}) ∧ ¬ ({P}) ∧ {H}", sep_tactics(model, 0))
    ident = "AD_" + re.sub(r"[^A-Za-z0-9_]", "_", spec["id"])
    r = certify(ident, import_lines() + "set_option maxHeartbeats 4000000\nset_option linter.unusedVariables false\n",
                ob, tc, work / "certify")
    c = set(r["certificates"])
    out.update(certify_status=r["status"], certificates=r["certificates"], mode="mixed",
               added=[a["prop"] for a in d["added"]], dropped=[a["prop"] for a in d["dropped"]])
    if not {"link_R", "link_L"} <= c:
        out.update(verdict="INCONCLUSIVE", reason="canonical telescope not linked to the elaborated statements")
        return out
    wit = read_witnesses(ident, [k for k in ("a_not_d", "d_not_a", "ref_false", "lean_false") if k in c],
                         tc, buildp, work / "certify")
    out["witnesses"] = wit
    if ("d_implies_a" in c and "d_not_a" in c) or ("a_implies_d" in c and "a_not_d" in c):
        out.update(verdict="INCONSISTENT")
    elif "ref_false" in c and "lean_false" in c:
        out.update(verdict="BOTH_CLAIMS_FALSE", theorem="mixed_ref_false",
                   reason="certified models falsify the reference (with its assumption) and the Lean statement (with its own)")
    elif "lean_false" in c:
        out.update(verdict="LEAN_CLAIM_FALSE", theorem="mixed_ref_false",
                   reason="a certified model satisfies the shared conditions and the Lean statement's assumptions and falsifies its conclusion")
    elif "ref_false" in c:
        out.update(verdict="REFERENCE_NEEDS_ASSUMPTION", theorem="mixed_ref_false",
                   reason="a certified model satisfies the shared conditions and the reference's own assumptions and falsifies the conclusion")
    elif {"d_implies_a", "a_implies_d"} <= c:
        out.update(verdict="ASSUMPTION_EQUIVALENT", theorem="mixed_entails")
    elif {"d_implies_a", "a_not_d"} <= c:
        out.update(verdict="LEAN_STRONGER_BY_ASSUMPTION", theorem="mixed_strict")
    elif {"a_implies_d", "d_not_a"} <= c:
        out.update(verdict="LEAN_WEAKER_BY_ASSUMPTION", theorem="mixed_strict")
    elif {"a_not_d", "d_not_a"} <= c:
        out.update(verdict="ASSUMPTION_INCOMPARABLE", theorem="mixed_incomparable")
    else:
        out.update(verdict="INCONCLUSIVE", reason="no joint certificate for the mixed assumption change")
    return out


SUFFICIENT = (MATHLIB_PROOF_PORTFOLIO if MATHLIB else []) + ["decide", "(intros; decide)", "(intros; omega)", "(intros; simp_all)", "(intros; grind)",
              "(intro _ _ _ h a b; cases a <;> cases b <;> simp_all)", "(intros; trivial)", "(intros; assumption)"]


def minimality(spec: dict, tc: Toolchain, buildp: Path, work: Path) -> dict:
    """Which of a statement's assumptions are needed (`Composition.lean`: inclusion_minimal,
    redundant_drop, substitutable_example). Every assumption gets a removal witness (NECESSARY given the
    others), a proof from the others (REDUNDANT given the others), or stays UNRESOLVED. Inclusion-minimality
    is claimed only if sufficiency is certified and every assumption is NECESSARY."""
    L = spec["statement"]
    out = {"id": spec["id"], "statement": L, "mode": "minimality"}
    d = extract(L, L, tc, buildp, work / "extract")
    if "error" in d:
        out.update(verdict="INCONCLUSIVE", reason="extraction failed", detail=d["error"][-600:])
        return out
    model, hyps, P = d["model"], d["hyps"], d["conclusion_ref"]
    lits = sorted({int(x) for x in re.findall(r"\b(\d+)\b", L) if int(x) <= 20})
    for t in ("Nat", "ℕ"):
        POINT_POOLS[t] = sorted(set(POINT_POOLS.get(t, [])) | {str(c) for c in lits} | {str(c + 1) for c in lits}, key=int)
    if not hyps:
        out.update(verdict="NO_ASSUMPTIONS")
        return out
    allf, alle = binders(model), binders(model, True)
    conj = lambda xs: " ∧ ".join(f"({x})" for x in xs) if xs else "True"
    imp = lambda xs: "".join(f"({x}) → " for x in xs)
    ob = {"link": (f"({L}) ↔ (∀ {allf}, {imp(hyps)}{P})",
                   ["constructor <;> intro h <;> intros <;> (first | (apply h <;> assumption) | simp_all)"]),
          "sufficient": (f"∀ {allf}, {imp(hyps)}{P}", SUFFICIENT)}
    for i, a in enumerate(hyps):
        others = [h for j, h in enumerate(hyps) if j != i]
        ob[f"removal{i}"] = (f"∃ {alle}, {conj(others)} ∧ ¬ ({P})", sep_tactics(model, 0))
        ob[f"redundant{i}"] = (f"∀ {allf}, {imp(others)}{a}", REDUNDANT)
        # UNNEEDED: the conclusion follows from the other assumptions (weaker than REDUNDANT, which says the
        # assumption itself follows from them)
        ob[f"unneeded{i}"] = (f"∀ {allf}, {imp(others)}{P}", SUFFICIENT)
    for i in range(len(hyps)):
        for j in range(i + 1, len(hyps)):
            rest = [h for k, h in enumerate(hyps) if k not in (i, j)]
            ob[f"joint{i}_{j}"] = (f"∃ {alle}, {conj(rest)} ∧ ¬ ({P})", sep_tactics(model, 0))
    ident = "MIN_" + re.sub(r"[^A-Za-z0-9_]", "_", spec["id"])
    r = certify(ident, import_lines() + "set_option maxHeartbeats 4000000\nset_option linter.unusedVariables false\n",
                ob, tc, work / "certify")
    certs = set(r["certificates"])
    out["certify_status"] = r["status"]
    if "link" not in certs:
        out.update(verdict="INCONCLUSIVE", reason="canonical telescope not linked")
        return out
    wit = read_witnesses(ident, [k for k in certs if k.startswith(("removal", "joint"))], tc, buildp, work / "certify")
    items = []
    for i, a in enumerate(hyps):
        nec, red, unn = f"removal{i}" in certs, f"redundant{i}" in certs, f"unneeded{i}" in certs
        items.append({"assumption": a, "class": "INCONSISTENT" if nec and (red or unn) else "NECESSARY" if nec else
                      "REDUNDANT" if red else "UNNEEDED" if unn else "UNRESOLVED",
                      "removal_witness": wit.get(f"removal{i}")})
    out["assumptions"] = items
    out["sufficiency"] = "CERTIFIED" if "sufficient" in certs else "NOT_CERTIFIED"
    red = [i for i, x in enumerate(items) if x["class"] in ("REDUNDANT", "UNNEEDED")]
    out["jointly_necessary_pairs"] = [[i, j] for i in red for j in red if i < j and f"joint{i}_{j}" in certs]
    cls = [x["class"] for x in items]
    if "INCONSISTENT" in cls:
        out["verdict"] = "INCONSISTENT"
    elif all(c == "NECESSARY" for c in cls):
        out.update(verdict="INCLUSION_MINIMAL" if out["sufficiency"] == "CERTIFIED" else "INCLUSION_MINIMAL_IF_THEOREM_HOLDS",
                   theorem="inclusion_minimal")
    elif any(c in ("REDUNDANT", "UNNEEDED") for c in cls):
        out.update(verdict="HAS_REDUNDANT_ASSUMPTIONS", theorem="redundant_drop",
                   note="drop redundant assumptions one at a time and re-check: individual redundancy does not "
                        "compose (substitutable_example)")
    else:
        out["verdict"] = "INCONCLUSIVE"
    return out


def _one(a):
    p, buildp, out = a
    spec = json.loads(Path(p).read_text())
    fn = minimality if "statement" in spec else run_case
    row = fn(spec, Toolchain.find(), buildp, out / "work" / Path(p).stem)
    for k in ("expected", "domain", "family", "split", "must_not_be"):
        row[k] = spec.get(k)
    (out / "rows").mkdir(parents=True, exist_ok=True)
    (out / "rows" / (Path(p).stem + ".json")).write_text(json.dumps(row, ensure_ascii=False, indent=1))
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m proofscope.adelta12")
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args(argv)
    out = a.out.resolve()
    b = build(Toolchain.find(), out / "build")
    if not b["ok"]:
        print(json.dumps(b, indent=2)[:3000])
        return 2
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        rows = list(ex.map(_one, [(p, out / "build", out) for p in a.specs]))
    for r in rows:
        ok = "" if not r.get("expected") else ("OK" if r["verdict"] == r["expected"] else f"MISS(expected {r['expected']})")
        print(r["id"], r["verdict"], ok, flush=True)
    (out / "adelta_results.json").write_text(json.dumps({"rows": rows}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
