"""ClaimDelta (v0.8): certified, abstraction-relative statement strength.

Two true theorems are logically equivalent, so logical equivalence cannot see a formalization that
proves a *weaker true* claim (reference `n < 2^n`, Lean `n ≤ 2^n`). ClaimDelta compares the claims
the two statements make about the mathematical objects they **share**:

1. `lean/ProofScope/Abstract.lean` elaborates both statements and finds the shared opaque symbols
   (policy LINEAR_CORE_SHARED: linear arithmetic and logic are interpreted; every other operator that
   both sides use, e.g. `^`, `*` between variables, `Nat.gcd`, becomes a symbol; numerals stay arguments,
   so `2 ^ n` against `3 ^ n` is a change of claim about the shared symbol `^`).
2. For every nonempty subset A of symbols, both statements are abstracted over A, giving REF_A(x) and
   LEAN_A(x) with REF_A(actual symbols) ≡ REF (checked: `link_*` obligations, `Iff.rfl`).
3. Certificate obligations, each checked by `certify` (tactic, clean recompile, standard axioms, replay):
      fwd_A   ∀ x, REF_A x → LEAN_A x            uniform entailment (no facts about the symbols used)
      bwd_A   ∀ x, LEAN_A x → REF_A x
      sepW_A  ∃ x, LEAN_A x ∧ ¬ REF_A x          countermodel: LEAN does not uniformly give REF
      sepS_A  ∃ x, REF_A x ∧ ¬ LEAN_A x
4. Relation at A (soundness: lean/ProofScope/ClaimDelta.lean):
      SCHEMA_EQUIVALENT  fwd ∧ bwd        LEAN_WEAKER  fwd ∧ sepW      LEAN_STRONGER  bwd ∧ sepS
      INCOMPARABLE       sepW ∧ sepS      INCONCLUSIVE otherwise       INCONSISTENT  contradictory certificates
5. Law check: if a separation is found, ProofScope tries to prove the missing concrete direction using
   only equational laws of the symbols (commutativity, `pow_two`, ...) plus linear arithmetic. If it
   succeeds, the difference is a harmless rewriting and the verdict is EQUIVALENT_BY_LAWS (laws listed).

What a verdict does and does not say:
* LEAN_WEAKER at A: the Lean claim follows from the reference for every interpretation of A, and there
  is an interpretation where the Lean claim holds and the reference fails. Recovering the reference
  from the Lean statement needs specific facts about A beyond the listed equational laws. It does NOT
  say either statement is false, and both may be true (`two_pow_concretely_equivalent`).
* The verdict is relative to the declared policy; it is reported with the policy and the symbols.
"""

from __future__ import annotations

import argparse
import json
import re
from itertools import product
from pathlib import Path

from .certify import certify
from .toolchain import Toolchain

SRC = Path(__file__).resolve().parents[1] / "lean"
POLICY = "LINEAR_CORE_SHARED"
LAWS = ["Nat.mul_comm", "Nat.add_comm", "Nat.gcd_comm", "Nat.lcm_comm", "Nat.pow_two", "Nat.pow_succ",
        "Nat.pow_zero", "Nat.mul_one", "Nat.one_mul", "Nat.mul_assoc", "Nat.min_comm", "Nat.max_comm",
        "Nat.mul_zero", "Nat.zero_mul", "Nat.add_zero", "Nat.zero_add"]
REL = ["SCHEMA_EQUIVALENT", "LEAN_WEAKER", "LEAN_STRONGER", "INCOMPARABLE", "INCONCLUSIVE", "INCONSISTENT"]


def closed(binders, hyp, concl) -> str:
    b = " ".join(f"({n} : {t})" for n, t in binders)
    return f"∀ {b}, ({hyp}) → ({concl})"


def build_abstractor(tc: Toolchain, build: Path) -> dict:
    out = build / "ProofScope" / "Abstract.olean"
    if out.exists():
        return {"ok": True}
    r = tc.compile(SRC / "ProofScope" / "Abstract.lean", out, SRC, timeout=900)
    return {"ok": r.returncode == 0 and out.exists(), "log": r.as_dict()}


def abstract(ref: str, lean: str, tc: Toolchain, build: Path, work: Path) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    f = work / "Abstract_input.lean"
    f.write_text(f"import ProofScope.Abstract\n\n#proofscope_abstract ({ref}) ({lean})\n")
    r = tc.run([tc.lean, str(f)], cwd=work, extra_path=build, timeout=600)
    for line in r.output.splitlines():
        i = line.find("PROOFSCOPE_ABSTRACT ")
        if i >= 0:
            return json.loads(line[i + len("PROOFSCOPE_ABSTRACT "):])
    return {"error": r.output[-3000:]}


def _literals(*texts: str) -> list[int]:
    nums = {int(x) for t in texts for x in re.findall(r"\b(\d+)\b", t) if int(x) <= 64}
    return sorted(nums | {0, 1, 2, 3})


def pool(typ: str, lits: list[int]) -> list[str]:
    t = re.sub(r"\s+", " ", typ.strip())
    patch = [c for c in lits if c <= 12]
    if t == "Nat":
        return sorted({str(c) for c in lits} | {str(c + 1) for c in lits} | {str(i) for i in range(6)}, key=int)[:12]
    if t == "Nat → Nat":
        return (["fun _ => 0", "fun k => k", "fun k => k + 1", "fun _ => 1", "fun k => 2 * k", "fun _ => 2"]
                + [f"fun k => if k = {c} then 0 else k" for c in patch]
                + [f"fun k => if k = {c} then 0 else k + 1" for c in patch])
    if t == "Nat → Nat → Nat":
        return (["fun _ _ => 0", "fun a _ => a", "fun _ b => b", "fun a b => a + b", "fun _ _ => 1",
                 "fun a b => a * b"]
                + [f"fun a _ => if a = {c} then 0 else a" for c in patch]
                + [f"fun a b => if a = {c} then 0 else a * b" for c in patch]
                + [f"fun a b => if a = {c} then 0 else b + 1" for c in patch]
                + [f"fun a b => if a = {c} then b + 1 else 0" for c in patch]
                + [f"fun _ b => if b = {c} then 0 else b + 1" for c in patch]
                + [f"fun a b => if b = {c} then 0 else a + 1" for c in patch])
    if t == "Nat → Nat → Prop":
        return ["fun _ _ => True", "fun _ _ => False", "fun a b => a = b", "fun a b => a ≤ b", "fun a b => a < b"]
    if t == "Nat → Prop":
        return ["fun _ => True", "fun _ => False", "fun k => k = 0", "fun k => 0 < k"]
    return []


def _instances(k: int, lits: list[int]) -> list[list[str]]:
    vals = [str(c) for c in sorted(set(range(5)) | {c for c in lits if c <= 12})]
    return [list(v) for v in product(vals, repeat=k)][:120]


class Case:
    def __init__(self, spec: dict):
        self.spec = spec
        self.id = spec["id"]
        self.binders = spec["binders"]
        self.names = [n for n, _ in self.binders]
        self.ref = closed(self.binders, spec["ref_hyp"], spec["ref_concl"])
        self.lean = closed(self.binders, spec["lean_hyp"], spec["lean_concl"])
        self.lits = _literals(self.ref, self.lean)

    @property
    def ident(self) -> str:
        return "CD_" + re.sub(r"[^A-Za-z0-9_]", "_", self.id)

    def _entail_tactics(self, nx: int) -> list[str]:
        xs = " ".join(f"_x{i}" for i in range(nx))
        ns = " ".join(self.names)
        pre = f"intro {xs} h {ns} hyp; have h' := h {ns}; (try simp only [] at *)"
        return [f"{pre}; {c}" for c in
                ["omega", "exact h' hyp", "exact h' (by omega)", "(have := h' (by omega); omega)",
                 "(have := h' hyp; omega)", "simp_all", "(simp_all; omega)", "(cases h' (by omega) <;> omega)",
                 "exact ⟨_, ‹_›⟩", "exact Or.inl (h' hyp)", "exact (h' hyp).symm", "exact (h' trivial).symm",
                 "(have := h' (by omega); exact ⟨this.2, this.1⟩)", "(have := h' hyp; exact ⟨this.2, this.1⟩)",
                 "(have := h' (by omega); exact ⟨_, this⟩)", "(constructor <;> omega)",
                 "(have := h' (by omega); constructor <;> omega)"]]

    def _sep_tactics(self, typs: list[str]) -> list[str]:
        cols = [pool(t, self.lits) for t in typs]
        if any(not c for c in cols):
            return []
        ns = " ".join(self.names)
        holds = [f"(intro {ns} hyp; (try simp only [] at *); {c})"
                 for c in ["omega", "(split <;> omega)", "trivial", "simp_all", "decide", "rfl"]]
        holds += ["(intros; trivial)", "decide"]
        holds += [f"(intro {ns} hyp; exact ⟨{c}, by (try simp only []); omega⟩)" for c in range(4)]
        holds += [f"(intro {ns} hyp; refine ⟨?_, ?_⟩ <;> (try simp only [] at *) <;> omega)"]
        refute = []
        for inst in _instances(len(self.names), self.lits):
            a = " ".join(inst)
            for hy in ("(by decide)", "trivial", "(by omega)"):
                refute.append(f"(intro h; have := h {a} {hy}; (try simp only [] at this); omega)")
                refute.append(f"(intro h; have := h {a} {hy}; (try simp only [] at this); simp at this)")
        hold = " | ".join(f"({c}; done)" for c in holds)
        ref = " | ".join(f"({c}; done)" for c in refute)
        tuples = list(product(*cols))[:200]
        return [f"refine ⟨{', '.join(t)}, ?_, ?_⟩ <;> first | {hold} | {ref}" for t in tuples]

    def _law_tactics(self) -> list[str]:
        ns = " ".join(self.names)
        laws = ", ".join(LAWS)
        return [f"intro h {ns} hyp; have h' := h {ns}; simp only [{laws}] at *; {c}"
                for c in ["omega", "exact h' hyp", "exact h' (by omega)", "(have := h' (by omega); omega)",
                          "simp_all", "exact h' trivial"]]

    def _reference_refutation_tactics(self) -> list[str]:
        # A refutation must be certified by Lean, never inferred from failed proof search.
        out = []
        for k in sorted(set(range(8)) | set(self.lits)):
            if len(self.names) != 1:
                continue
            for hyp in ("(by omega)", "(by decide)", "trivial"):
                for close in ("simp at hbad", "simp_all", "omega", "decide at hbad"):
                    out.append(f"intro h; have hbad := h {k} {hyp}; {close}")
        return out

    def _reference_validity_tactics(self) -> list[str]:
        # We demand a positive, kernel-checked proof before calling a law match
        # harmless rewriting. Absence of a refutation is NOT evidence of validity.
        names = " ".join(self.names)
        return [f"intro {names} hyp; {t}" for t in
                ("omega", "simp_all", "simp", "decide", "exact hyp", "trivial")]

    def obligations(self, ab: dict) -> tuple[dict, dict]:
        syms = ab["symbols"]
        ob, meta = {}, {}
        for s in ab["subsets"]:
            idx = s["symbols"]
            tag = "s" + "_".join(map(str, idx))
            binders = " ".join(f"(x{i} : {syms[i - 1]['type']})" for i in idx)
            args = " ".join(f"({syms[i - 1]['symbol']} : {syms[i - 1]['type']})" for i in idx)
            R, L = s["ref"], s["lean"]
            meta[tag] = {"symbols": [syms[i - 1]["symbol"] for i in idx], "ref": R, "lean": L}
            ob[f"linkR_{tag}"] = (f"((fun {binders} => {R}) {args}) ↔ ({self.ref})", ["exact Iff.rfl"])
            ob[f"linkL_{tag}"] = (f"((fun {binders} => {L}) {args}) ↔ ({self.lean})", ["exact Iff.rfl"])
            ob[f"fwd_{tag}"] = (f"∀ {binders}, ({R}) → ({L})", self._entail_tactics(len(idx)))
            ob[f"bwd_{tag}"] = (f"∀ {binders}, ({L}) → ({R})", self._entail_tactics(len(idx)))
            typs = [syms[i - 1]["type"] for i in idx]
            ob[f"sepW_{tag}"] = (f"∃ {binders}, ({L}) ∧ ¬ ({R})", self._sep_tactics(typs))
            ob[f"sepS_{tag}"] = (f"∃ {binders}, ({R}) ∧ ¬ ({L})", self._sep_tactics(typs))
        ob["lawW"] = (f"({self.lean}) → ({self.ref})", self._law_tactics())
        ob["lawS"] = (f"({self.ref}) → ({self.lean})", self._law_tactics())
        # A directional implication can hold vacuously if the reference is false.
        # Only a kernel-checked positive reference proof licenses harmless-rewrite wording.
        ob["refValid"] = (f"({self.ref})", self._reference_validity_tactics())
        ob["refFalse"] = (f"¬ ({self.ref})", self._reference_refutation_tactics())
        return ob, meta


def relation(c: set, tag: str) -> str:
    f, b, w, s = (f"{k}_{tag}" in c for k in ("fwd", "bwd", "sepW", "sepS"))
    if (f and s) or (b and w):
        return "INCONSISTENT"
    if f and b:
        return "SCHEMA_EQUIVALENT"
    if f and w:
        return "LEAN_WEAKER"
    if b and s:
        return "LEAN_STRONGER"
    if w and s:
        return "INCOMPARABLE"
    return "INCONCLUSIVE"


def run_case(spec: dict, tc: Toolchain, build: Path, work: Path) -> dict:
    case = Case(spec)
    out = {"id": case.id, "policy": POLICY, "reference": case.ref, "lean": case.lean}
    ab = abstract(case.ref, case.lean, tc, build, work / "abstract")
    if "error" in ab:
        out.update(verdict="INCONCLUSIVE", reason="abstraction failed", detail=ab["error"][-800:])
        return out
    out["symbols"] = ab["symbols"]
    out["one_sided_symbols"] = ab["one_sided_symbols"]
    if not ab["subsets"]:
        out.update(verdict="NO_SHARED_SYMBOLS",
                   reason="no opaque symbol occurs in both statements; only the concrete (v0.6) comparison applies")
        return out
    ob, meta = case.obligations(ab)
    r = certify(case.ident, "set_option maxHeartbeats 400000\nset_option linter.unusedVariables false\n",
                ob, tc, work / "certify")
    certs = set(r["certificates"])
    out["certify_status"] = r["status"]
    subsets = {}
    for tag, m in meta.items():
        linked = f"linkR_{tag}" in certs and f"linkL_{tag}" in certs
        rel = relation(certs, tag) if linked else "INCONCLUSIVE"
        subsets[tag] = {**m, "linked": linked, "relation": rel,
                        "certificates": {k: r["certificates"][k] for k in certs if k.endswith("_" + tag)}}
    out["subsets"] = subsets
    # consistency with the refinement theorems: separation at A persists at every B ⊇ A
    sets = {tag: set(m["symbols"]) for tag, m in subsets.items()}
    for a, sa in sets.items():
        for b, sb in sets.items():
            if sa < sb and subsets[a]["relation"] in ("LEAN_WEAKER", "LEAN_STRONGER", "INCOMPARABLE") \
                    and subsets[b]["relation"] == "SCHEMA_EQUIVALENT":
                subsets[b]["relation"] = "INCONSISTENT"
    separating = {t: v for t, v in subsets.items() if v["relation"] in ("LEAN_WEAKER", "LEAN_STRONGER", "INCOMPARABLE")}
    minimal = [t for t in separating if not any(sets[u] < sets[t] for u in separating)]
    out["minimal_separating_subsets"] = minimal
    out["law_certificates"] = {k: r["certificates"][k] for k in ("lawW", "lawS") if k in certs}
    out["reference_status"] = ("INCONSISTENT" if {"refValid", "refFalse"} <= certs
                              else "REFUTED" if "refFalse" in certs
                              else "VERIFIED" if "refValid" in certs else "UNVERIFIED")
    out["reference_certificates"] = {k: r["certificates"][k]
                                      for k in ("refValid", "refFalse") if k in certs}
    if any(v["relation"] == "INCONSISTENT" for v in subsets.values()) or out["reference_status"] == "INCONSISTENT":
        out["verdict"] = "INCONSISTENT"
    elif out["reference_status"] == "REFUTED":
        out["verdict"] = "REFERENCE_REFUTED"
        out["reason"] = ("Lean certified a counterexample to the concrete reference; "
                         "a vacuous implication must not be reported as harmless rewriting")
    elif minimal:
        rels = {subsets[t]["relation"] for t in minimal}
        rel = rels.pop() if len(rels) == 1 else "INCOMPARABLE"
        need = {"LEAN_WEAKER": ["lawW"], "LEAN_STRONGER": ["lawS"], "INCOMPARABLE": ["lawW", "lawS"]}[rel]
        if all(k in certs for k in need) and out["reference_status"] == "VERIFIED":
            out["verdict"] = "EQUIVALENT_BY_LAWS"
            out["reason"] = ("The reference itself is kernel-verified, and the missing concrete "
                             "implication follows from certified mathematical laws")
        else:
            if all(k in certs for k in need):
                out["law_status"] = "IMPLICATION_PROVED_REFERENCE_UNVERIFIED"
            out["verdict"] = "CLAIM_" + rel
            out["explanation"] = [{"symbols": subsets[t]["symbols"], "relation": subsets[t]["relation"],
                                   "countermodel": subsets[t]["certificates"].get(
                                       "sepW_" + t if rel != "LEAN_STRONGER" else "sepS_" + t, {}).get("statement")}
                                  for t in minimal]
    else:
        full = max(sets, key=lambda t: len(sets[t]))
        out["verdict"] = "SCHEMA_EQUIVALENT" if subsets[full]["relation"] == "SCHEMA_EQUIVALENT" else "INCONCLUSIVE"
    return out


def _one(args) -> dict:
    p, build, out = args[:3]
    spec = json.loads(Path(p).read_text())
    row = run_case(spec, Toolchain.find(), build, out / "work" / Path(p).stem)
    if len(args) > 3 and args[3] and row["verdict"] == "INCONCLUSIVE":
        # SOTA-15, opt-in: exact fragment criteria for cases the witness registry leaves open
        from .scopeelim import fallback
        row = fallback(spec, row, Toolchain.find(), out)
    row["expected_claimdelta"] = spec.get("expected_claimdelta")
    row["family"] = spec.get("family")
    row["split"] = spec.get("split")
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m proofscope.claimdelta")
    ap.add_argument("specs", nargs="+", help="case JSON files (binders, *_hyp, *_concl)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--scopeelim", action="store_true",
                    help="on INCONCLUSIVE, try the ScopeElim fragment criteria (SOTA-15; off by default)")
    a = ap.parse_args(argv)
    tc = Toolchain.find()
    out = a.out.resolve()
    build = out / "build"
    b = build_abstractor(tc, build)
    if not b["ok"]:
        print(json.dumps(b, indent=2)[:3000])
        return 2
    if a.scopeelim:
        from .scopeelim import build_lib
        b = build_lib(tc, out / "scopeelim_lib")
        if not b["ok"]:
            print(json.dumps(b, indent=2)[:3000])
            return 2
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        rows = list(ex.map(_one, [(p, build, out, a.scopeelim) for p in a.specs]))
    for row in rows:
        print(row["id"], row["verdict"], "expected:", row["expected_claimdelta"], flush=True)
    (out / "claimdelta_results.json").write_text(json.dumps({"policy": POLICY, "rows": rows}, indent=2,
                                                            ensure_ascii=False))
    counts: dict = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print(json.dumps(counts, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
