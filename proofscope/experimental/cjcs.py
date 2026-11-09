"""CJCS — Certified Joint-drift Countermodel Search (experimental; SOTA-3).

Decides **logical** (Track A) relations between two closed statements R (reference) and L
(formalization), with a kernel-checked certificate for every decisive answer, and explains a difference by
certified drift regions. Theory: research/cjcs/CJCS.lean.

Certificates (each a declaration accepted by the unchanged certify gate: recompile, standard axioms,
leanchecker replay):

    CERTIFIED_LOGICAL_DIFFERENCE   ¬ (R ↔ L), from a proof of one side and a refutation of the other
                                   (`CJCS.cjcs_sound`). Every certificate of a logical difference must
                                   contain a proof of one side (`CJCS.difference_needs_a_proof`); a refuter
                                   alone or a prover alone cannot produce one.
    CERTIFIED_LOGICAL_EQUIVALENCE  R ↔ L because they are definitionally equal (`Iff.rfl`), or both are
                                   refuted, or both are proved. Logical equivalence only; the latter two
                                   never certify a faithful formalization.
    ABSTAIN                        anything else, with whatever one-sided certificates were found.

Refutations are synthesized without an LLM: each side is put in its own telescope normal form by the frozen
v1.1 extractor, linked to it by a certified `X ↔ canonical` lemma, and a countermodel is searched with the
frozen v1.2 carrier registry and closers (`∃ m, H m ∧ ¬ C m`), then turned into `¬ X`.

Algorithmic principles:
* **Refute first.** Stage 1 searches countermodels only. A side with a certified countermodel is never sent
  to the prover (proving it is impossible, `CJCS.refuted_unprovable`), which removes the most expensive
  failing searches.
* **Bounded search.** Every alternative runs under `maxHeartbeats 200000`.
* **Drift regions.** When the two telescopes align (same binders), a separating point is classified by
  certified region obligations over shared hypotheses H, reference-only assumptions D, formalization-only
  assumptions A and conclusions P, Q: `ref_excluded` (H ∧ D ∧ ¬A ∧ ¬P), `lean_excluded` (H ∧ A ∧ ¬D ∧ ¬Q),
  `conclusion_lean_stronger` (H ∧ D ∧ A ∧ P ∧ ¬Q), `conclusion_ref_stronger` (H ∧ D ∧ A ∧ Q ∧ ¬P) and
  `joint` (H ∧ A ∧ ¬D ∧ P ∧ ¬Q). `CJCS.joint_failure_iff` proves that when each single change is harmless
  on its own, the combined statement fails exactly at points of the `joint` region.

Search failure is never evidence: no countermodel or no proof gives ABSTAIN.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .. import adelta12 as A
from ..certify import _failed, _module, certify
from ..toolchain import Toolchain

HEADER = "set_option maxHeartbeats 200000\nset_option linter.unusedVariables false\n"
# identical to the link tactic of the frozen adelta12.run_case
LINK_TAC = [
    "constructor <;> intro h <;> intros <;> (first | (apply h <;> assumption) | (apply h <;> first | assumption | "
    "exact ⟨‹_›⟩) | (rename_i hn; obtain ⟨_⟩ := hn; apply h <;> assumption) | (simp_all))"]


# Quantifier-exchange patterns (generic, not case-specific): an existential is introduced with a witness
# built from the variables in scope (x, x + 1, 0, 1); an `∃ y, ∀ x, …` is refuted by instantiating the
# universal at the existential's own witness or its successor (the diagonal certificates of ∀∃ vs ∃∀).
EX_TERMS = ["{v}", "{v} + 1", "0", "1"]


def exists_intro_tactics() -> list[str]:
    out = []
    for vs in (["x0"], ["x0", "x1"]):
        for t in EX_TERMS:
            w = t.format(v=vs[-1])
            for fin in ("omega", "decide", "simp_all", "trivial"):
                out.append(f"(intro {' '.join(vs)}; refine ⟨{w}, ?_⟩; {fin})")
    for t in ("0", "1"):
        for fin in ("omega", "decide", "simp_all", "trivial"):
            out.append(f"(refine ⟨{t}, ?_⟩; {fin})")
    return out


def exists_refute_tactics() -> list[str]:
    out = []
    for inst in ("y0", "y0 + 1", "0", "1"):
        for fin in ("omega", "simp_all", "(revert this; decide)"):
            out.append(f"(intro hx; obtain ⟨y0, hy⟩ := hx; have := hy ({inst}); {fin})")
            out.append(f"(intro hx; obtain ⟨y0, hy⟩ := hx; have := hy ({inst}) ({inst}); {fin})")
    return out


def prove_tactics() -> list[str]:
    return list(A.SUFFICIENT) + exists_intro_tactics() + ["(intros; exact?)"]


def with_literal_points(*texts: str) -> None:
    """Numerals of the statements and their successors join the ℕ point pool (as the frozen engine does)."""
    lits = sorted({int(x) for t in texts for x in re.findall(r"\b(\d+)\b", t) if int(x) <= 20})
    for t in ("Nat", "ℕ"):
        if t in A.POINT_POOLS or t == "Nat":
            A.POINT_POOLS[t] = sorted(set(A.POINT_POOLS.get(t, [])) | {str(c) for c in lits} |
                                      {str(c + 1) for c in lits}, key=int)
    for t in ("Int", "ℤ"):
        if t in A.POINT_POOLS:
            A.POINT_POOLS[t] = list(dict.fromkeys(A.POINT_POOLS[t] + [str(c) for c in lits] + [str(c + 1) for c in lits]))


def extract_many(pairs: list[tuple[str, str]], tc: Toolchain, buildp: Path, work: Path) -> list[dict]:
    """The frozen extractor on several pairs in ONE Lean process (one environment load)."""
    work.mkdir(parents=True, exist_ok=True)
    f = work / "Assumptions_input.lean"
    f.write_text(f"{A.import_lines()}import ProofScope.AssumptionExtract11\n\n" +
                 "".join(f"#proofscope_assumptions11 ({r}) ({l})\n" for r, l in pairs))
    r = tc.run([tc.lean, str(f)], cwd=work, extra_path=buildp, timeout=600)
    got = []
    for line in r.output.splitlines():
        i = line.find("PROOFSCOPE_ASSUMPTIONS11 ")
        if i >= 0:
            got.append(json.loads(line[i + len("PROOFSCOPE_ASSUMPTIONS11 "):]))
    if len(got) != len(pairs):
        return [{"error": r.output[-3000:]}] * len(pairs)
    return got


def _conj(xs: list[str]) -> str:
    return " ∧ ".join(f"({x})" for x in xs) if xs else "True"


def side_obligations(tag: str, stmt: str, d: dict) -> dict:
    """link_X, wit_X, false_X for one statement X from its self-extraction `d`."""
    model, hyps, concl = d["model"], d["hyps"], d["conclusion_ref"]
    allb, ex = A.binders(model), A.binders(model, True)
    canon = (f"∀ {allb}, " if model else "") + "".join(f"({h}) → " for h in hyps) + concl
    H = _conj(hyps)
    ob = {f"link_{tag}": (f"({stmt}) ↔ ({canon})", LINK_TAC)}
    if model:
        ob[f"wit_{tag}"] = (f"∃ {ex}, ¬ ({concl}) ∧ {H}", A.sep_tactics(model, len(hyps)))
    else:
        ob[f"wit_{tag}"] = (f"¬ ({concl}) ∧ {H}",
                            [f"and_intros <;> first | {A.closers(A.ALL_VALS)} | " + " | ".join(f"({t}; done)" for t in exists_refute_tactics())])
    ws = [f"w{i}" for i in range(len(model))]
    hs = [f"hh{i}" for i in range(len(hyps))]
    pat = ", ".join(ws + ["hn"] + (hs if hs else ["-"]))
    app = f"@hc {' '.join(ws + hs)}" if (ws or hs) else "hc"
    ob[f"false_{tag}"] = (f"¬ ({stmt})", [f"intro h; have hc := (link_{tag}).mp h; obtain ⟨{pat}⟩ := wit_{tag}; exact hn ({app})"])
    return ob


def region_obligations(e: dict) -> dict:
    """Certified drift-region witnesses over the aligned telescope `e` = extract(R, L)."""
    if "error" in e or not e.get("model"):
        return {}
    model = e["model"]
    ex = A.binders(model, True)
    H = _conj(e["hyps"])
    D = _conj([a["prop"] for a in e["dropped"]])
    Aa = _conj([a["prop"] for a in e["added"]])
    P, Q = e["conclusion_ref"], e["conclusion_lean"]
    reg = {}
    tac = A.sep_tactics(model, 0)
    if e["added"]:
        reg["region_ref_excluded"] = f"∃ {ex}, {H} ∧ {D} ∧ ¬ ({Aa}) ∧ ¬ ({P})"
    if e["dropped"]:
        reg["region_lean_excluded"] = f"∃ {ex}, {H} ∧ {Aa} ∧ ¬ ({D}) ∧ ¬ ({Q})"
    if not e.get("conclusion_same"):
        reg["region_conclusion_lean_stronger"] = f"∃ {ex}, {H} ∧ {D} ∧ {Aa} ∧ ({P}) ∧ ¬ ({Q})"
        reg["region_conclusion_ref_stronger"] = f"∃ {ex}, {H} ∧ {D} ∧ {Aa} ∧ ({Q}) ∧ ¬ ({P})"
        if e["dropped"]:
            reg["region_joint"] = f"∃ {ex}, {H} ∧ {Aa} ∧ ¬ ({D}) ∧ ({P}) ∧ ¬ ({Q})"
    return {k: (v, tac) for k, v in reg.items()}


def probe(ident: str, obligations: dict, tc: Toolchain, work: Path) -> set[str]:
    """Search only (no certificate): which obligations elaborate. One Lean process."""
    src_root = (work / "src").resolve()
    mod = src_root / "ProofScopeCert"
    mod.mkdir(parents=True, exist_ok=True)
    src, spans = _module(f"ProofScopeCert.{ident}", A.import_lines() + HEADER, obligations, None)
    (mod / f"{ident}Search.lean").write_text(src)
    r = tc.compile(mod / f"{ident}Search.lean", None, src_root, timeout=900)
    failed, outside = _failed(r.output, spans)
    if r.returncode not in (0, 1) or outside:
        return set()
    return set(spans) - failed


def run_case(spec: dict, tc: Toolchain, buildp: Path, work: Path) -> dict:
    R, L = spec["reference"], spec["lean"]
    out = {"id": spec["id"], "reference": R, "lean": L, "engine": "cjcs-experimental"}
    dR, dL, e = extract_many([(R, R), (L, L), (R, L)], tc, buildp, work / "extract")
    if "error" in dR or "error" in dL:
        out.update(verdict="INCONCLUSIVE", reason="extraction failed", detail=(dR.get("error") or dL.get("error"))[-600:])
        return out
    ident = "CJ_" + re.sub(r"[^A-Za-z0-9_]", "_", spec["id"])
    with_literal_points(R, L)
    sides = {**side_obligations("R", R, dR), **side_obligations("L", L, dL)}
    # stage 1: countermodels only (refute first)
    ok1 = probe(ident + "_s1", sides, tc, work / "stage1")
    refuted = {t for t in ("R", "L") if {f"link_{t}", f"wit_{t}", f"false_{t}"} <= ok1}
    out["stage1_refuted"] = sorted(refuted)
    # stage 2 (final, certified): keep successful stage-1 obligations, prove only unrefuted sides
    # a lemma that elaborated on top of a failed dependency is not kept (dependencies are explicit)
    # definitional equality is checked first: `Iff.rfl` is accepted by the kernel exactly when R and L are
    # definitionally equal (alpha-renaming, notation), independently of whether either is true
    ob = {"equiv_defeq": (f"({R}) ↔ ({L})", ["exact Iff.rfl"])}
    for t in ("R", "L"):
        for k in (f"link_{t}", f"wit_{t}"):
            if k in ok1:
                ob[k] = sides[k]
        if t in refuted:
            ob[f"false_{t}"] = sides[f"false_{t}"]
    stmts = {"R": R, "L": L}
    for t in ("R", "L"):
        if t not in refuted:
            ob[f"true_{t}"] = (stmts[t], prove_tactics())
    if "R" in refuted and "L" not in refuted:
        ob["diff_RL"] = (f"¬ (({R}) ↔ ({L}))", ["exact fun h => false_R (h.mpr true_L)"])
    if "L" in refuted and "R" not in refuted:
        ob["diff_LR"] = (f"¬ (({R}) ↔ ({L}))", ["exact fun h => false_L (h.mp true_R)"])
    if refuted == {"R", "L"}:
        ob["equiv_both_false"] = (f"({R}) ↔ ({L})", ["exact ⟨fun h => absurd h false_R, fun h => absurd h false_L⟩"])
    if not refuted:
        ob["equiv_both_true"] = (f"({R}) ↔ ({L})", ["exact ⟨fun _ => true_L, fun _ => true_R⟩"])
    ob.update(region_obligations(e))
    r = certify(ident, A.import_lines() + HEADER, ob, tc, work / "certify")
    certs = set(r["certificates"])
    out["certify_status"] = r["status"]
    out["certificates"] = r["certificates"]
    wit_names = [k for k in certs if k.startswith(("wit_", "region_"))]
    out["witnesses"] = A.read_witnesses(ident, wit_names, tc, buildp, work / "certify")
    out["regions"] = sorted(k for k in certs if k.startswith("region_"))
    if "equiv_defeq" in certs and ({"diff_RL", "diff_LR"} & certs):
        out.update(verdict="INCONSISTENT", reason="definitional equality and a logical difference were both certified")
    elif "equiv_defeq" in certs:
        out.update(verdict="CERTIFIED_LOGICAL_EQUIVALENCE", direction="definitional", theorem="Iff.rfl")
    elif "diff_RL" in certs:
        out.update(verdict="CERTIFIED_LOGICAL_DIFFERENCE", direction="reference_false_formalization_true",
                   theorem="CJCS.cjcs_sound")
    elif "diff_LR" in certs:
        out.update(verdict="CERTIFIED_LOGICAL_DIFFERENCE", direction="reference_true_formalization_false",
                   theorem="CJCS.cjcs_sound")
    elif "equiv_both_false" in certs:
        out.update(verdict="CERTIFIED_LOGICAL_EQUIVALENCE", direction="both_false", theorem="CJCS.both_false_equiv")
    elif "equiv_both_true" in certs:
        out.update(verdict="CERTIFIED_LOGICAL_EQUIVALENCE", direction="both_true", theorem="CJCS.both_true_equiv")
    else:
        one = sorted(k for k in certs if k.startswith(("false_", "true_")))
        out.update(verdict="ABSTAIN", partial=one,
                   reason="no certified countermodel for one side together with a certified proof of the other")
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
    ap = argparse.ArgumentParser(prog="python -m proofscope.experimental.cjcs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("specs", nargs="+")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args(argv)
    out = a.out.resolve()
    b = A.build(Toolchain.find(), out / "build")
    if not b["ok"]:
        print(json.dumps(b, indent=2)[:3000])
        return 2
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        rows = list(ex.map(_one, [(p, out / "build", out) for p in a.specs]))
    for row in rows:
        ok = "" if not row.get("expected") else ("OK" if row["verdict"] == row["expected"] else f"MISS(expected {row['expected']})")
        print(row["id"], row["verdict"], row.get("direction"), row.get("regions"), ok, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
