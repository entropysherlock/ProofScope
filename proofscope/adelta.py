"""Assumption Delta (v1.0): certified meaning of assumptions added or dropped by a formalization.

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
    CARRIERS["Equiv.Perm (Fin 3)"] = {
        "vals": ["(1 : Equiv.Perm (Fin 3))", "(Equiv.swap 0 1 : Equiv.Perm (Fin 3))", "(Equiv.swap 1 2 : Equiv.Perm (Fin 3))"],
        "op2": ["fun a b => a * b"], "op1": ["fun a => a⁻¹", "fun a => a"], "rel": ["fun a b => a = b"]}
    POINT_POOLS.update({"ℝ": ["(-1 : ℝ)", "(0 : ℝ)", "(1 / 2 : ℝ)", "(1 : ℝ)", "(2 : ℝ)"],
                        "Set ℕ": ["(∅ : Set ℕ)", "(Set.univ : Set ℕ)", "({0} : Set ℕ)", "({1} : Set ℕ)"],
                        "ℕ": ["0", "1", "2", "3"], "ℤ": ["(-1 : ℤ)", "0", "1", "2"]})


def build(tc: Toolchain, out: Path) -> dict:
    o = out / "ProofScope" / "AssumptionExtract.olean"
    if o.exists():
        return {"ok": True}
    r = tc.compile(SRC / "ProofScope" / "AssumptionExtract.lean", o, SRC, timeout=900)
    return {"ok": r.returncode == 0 and o.exists(), "log": r.as_dict()}


def extract(ref: str, lean: str, tc: Toolchain, buildp: Path, work: Path) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    f = work / "Assumptions_input.lean"
    f.write_text(f"{import_lines()}import ProofScope.AssumptionExtract\n\n#proofscope_assumptions ({ref}) ({lean})\n")
    r = tc.run([tc.lean, str(f)], cwd=work, extra_path=buildp, timeout=600)
    for line in r.output.splitlines():
        i = line.find("PROOFSCOPE_ASSUMPTIONS ")
        if i >= 0:
            return json.loads(line[i + len("PROOFSCOPE_ASSUMPTIONS "):])
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
        # an instance binder over the carrier (e.g. `Group (Equiv.Perm (Fin 3))`): use the instance
        if typ.endswith(cc) and re.match(r"^[A-Z][\w.]*\s", typ):
            return ["inferInstance"]
    return POINT_POOLS.get(typ, [])


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
            out += [list(t) for t in product(*cols)][:60]
    return out[:150]


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


def sep_tactics(scope: list[dict], body_count: int) -> list[str]:
    tac = []
    for w in witnesses(scope):
        vals = [v for v in ALL_VALS]
        tac.append(f"refine ⟨{', '.join(w)}, ?_⟩; and_intros <;> first | {closers(vals)}")
    return tac


REDUNDANT = (["(intros; positivity)", "(intros; norm_num)", "(intros; linarith)"] if MATHLIB else []) + ["(intros; infer_instance)", "(intros; exact ⟨inferInstance⟩)", "(intros; exact ⟨Classical.decEq _⟩)",
             "(intros; exact ⟨fun _ => Classical.propDecidable _⟩)", "(intros; constructor; assumption)",
             "(intros; constructor; intros; simp_all)", "(intros; exact ⟨‹_›⟩)", "(intros; omega)", "(intros; simp_all)",
             "(intros; grind)", "(intros; trivial)"]


def read_witnesses(ident: str, names: list[str], tc: Toolchain, buildp: Path, certdir: Path) -> dict:
    """Witness models, read from the kernel-checked declarations of the certified module."""
    if not names:
        return {}
    f = certdir / "Witness_read.lean"
    f.write_text(f"{import_lines()}import ProofScope.AssumptionExtract\nimport ProofScopeCert.{ident}\n\n"
                 + "".join(f"#proofscope_witness ProofScopeCert.{ident}.{n}\n" for n in names))
    r = tc.run([tc.lean, str(f)], cwd=certdir, extra_path=os.pathsep.join([str(buildp), str(certdir / "build")]), timeout=300)
    got = [json.loads(l[l.index("PROOFSCOPE_WITNESS ") + 19:]) for l in r.output.splitlines() if "PROOFSCOPE_WITNESS " in l]
    return dict(zip(names, got)) if len(got) == len(names) else {}


def run_case(spec: dict, tc: Toolchain, buildp: Path, work: Path) -> dict:
    ref, lean = spec["reference"], spec["lean"]
    out = {"id": spec["id"], "reference": ref, "lean": lean}
    d = extract(ref, lean, tc, buildp, work / "extract")
    if "error" in d:
        out.update(verdict="INCONCLUSIVE", reason="extraction failed", detail=d["error"][-600:])
        return out
    out["extraction"] = d
    if not d["added"] and not d["dropped"]:
        out.update(verdict="NO_ASSUMPTION_DELTA")
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
    allb = " ".join(f"({b['name']} : {b['type']})" for b in model)
    hyps = d["hyps"]
    H = " ∧ ".join(f"({h})" for h in hyps) if hyps else "True"
    Himp = "".join(f"({h}) → " for h in hyps)
    P = d["conclusion_ref"]
    ob = {}
    link_tac = ["constructor <;> intro h <;> intros <;> (first | (apply h <;> assumption) | (apply h <;> first | assumption | exact ⟨‹_›⟩)"
                " | (rename_i hn; obtain ⟨_⟩ := hn; apply h <;> assumption) | (simp_all))"]
    ob["link_R"] = (f"({ref}) ↔ (∀ {allb}, {Himp}{''.join(f'({a['prop']}) → ' for a in d['dropped'])}{P})", link_tac)
    ob["link_L"] = (f"({lean}) ↔ (∀ {allb}, {Himp}{''.join(f'({a['prop']}) → ' for a in d['added'])}{P})", link_tac)
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
                ob[f"{side}{j}_restrictive"] = (f"∃ {preb}, ¬ ({A}) ∧ {pH}", sep_tactics(pre, ph))
            ob[f"{side}{j}_necessary"] = (f"∃ {allb}, ¬ ({A}) ∧ ¬ ({P}) ∧ {H}", sep_tactics(model, len(hyps)))
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


def _one(a):
    p, buildp, out = a
    spec = json.loads(Path(p).read_text())
    row = run_case(spec, Toolchain.find(), buildp, out / "work" / Path(p).stem)
    for k in ("expected", "domain", "family", "split", "must_not_be"):
        row[k] = spec.get(k)
    (out / "rows").mkdir(parents=True, exist_ok=True)
    (out / "rows" / (Path(p).stem + ".json")).write_text(json.dumps(row, ensure_ascii=False, indent=1))
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m proofscope.adelta")
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
