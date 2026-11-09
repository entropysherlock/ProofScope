"""Theorem-level semantic comparison (v0.6) with certificates (v0.7).

A comparison spec gives a formal statement and a reference statement over the same binders x:

    Lean:       ∀ x, H_L x → C_L x
    Reference:  ∀ x, H_R x → C_R x      (the intended claim, e.g. read from a paper: AI_PRELIMINARY
                                          unless a person has confirmed it)

ProofScope tries to certify each of these propositions (see certify.py for what "certified" means):

  hyp_cover      ∀ x, H_R x → H_L x                 Lean applies wherever the reference does
  concl_cover    ∀ x, H_R x → C_L x → C_R x         where both apply, Lean's conclusion gives the reference's
  transfer       (∀ x, H_L x → C_L x) → (∀ x, H_R x → C_R x)     proved from the two above
  hyp_back       ∀ x, H_L x → H_R x
  concl_back     ∀ x, H_L x → C_R x → C_L x
  app_gap        ∃ x, H_R x ∧ ¬ H_L x               an object the reference covers and Lean does not
  concl_gap      ∃ x, H_R x ∧ H_L x ∧ C_L x ∧ ¬ C_R x   Lean's conclusion holds there, the reference's fails
  strict_hyp     ∃ x, H_L x ∧ ¬ H_R x               Lean covers an object the reference does not
  strict_concl   ∃ x, H_L x ∧ H_R x ∧ C_R x ∧ ¬ C_L x
  vacuous        ¬ ∃ x, H_L x                       Lean's hypotheses can never hold
  inhabited      ∃ x, H_L x

Classification and exactly what each establishes (soundness):

  VACUOUS               `vacuous` certified: the formal theorem says nothing.
  APPLICABILITY_GAP     `app_gap` certified: at a concrete object the reference's hypotheses hold and Lean's fail,
                        so the formal theorem cannot be applied there. It does NOT show the reference claim false.
  CONCLUSION_GAP        `concl_gap` certified: at a concrete object both hypotheses hold and Lean's conclusion
                        holds but the reference's does not, so the formal theorem does not yield the reference
                        claim there. It does NOT show the reference claim false.
  EQUIVALENT            hyp_cover, concl_cover, hyp_back, concl_back certified: each theorem implies the other
                        *uniformly in x*. (Not the vacuous "both closed statements are true" equivalence.)
  LEAN_STRONGER         transfer certified and strict_hyp or strict_concl certified: the formal theorem implies the
                        reference and covers strictly more.
  COVERS                transfer certified: the formal theorem implies the reference claim. Possible strengthening
                        not established.
  INCONCLUSIVE          none of the above.

Certificates are about the two *formal* statements. Whether the reference statement matches a paper is a human
judgement and is reported as such.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path

from .certify import certify
from .toolchain import Toolchain

TACTIC_LIB = (Path(__file__).resolve().parents[1] / "lean" / "ProofScope" / "Tactics.lean").read_text()
_TAC_BODY = TACTIC_LIB.split("open Lean Meta Elab Tactic", 1)[1]

FORALL = ["intros; omega", "intros; ps_arith", "intros; simp_all", "intros; simp_all <;> omega", "intros; grind", "decide",
          "intros; constructor <;> intros <;> omega", "intros; exact ‹_›", "intros; trivial"]
EXISTS = ["decide +kernel", "decide", "grind", "simp"]
NEG_EXISTS = ["intro h; obtain ⟨{pat}, h⟩ := h; omega", "intro h; obtain ⟨{pat}, h⟩ := h; simp_all",
              "intro h; obtain ⟨{pat}, h⟩ := h; grind", "decide"]
LABELS = ["VACUOUS", "APPLICABILITY_GAP", "CONCLUSION_GAP", "EQUIVALENT", "LEAN_STRONGER", "COVERS", "INCONCLUSIVE"]


@dataclass
class CompareSpec:
    id: str
    binders: list[list[str]]
    lean_hyp: str
    lean_concl: str
    ref_hyp: str
    ref_concl: str
    preamble: str = ""
    imports: list[str] = field(default_factory=list)
    bounds: dict[str, int] = field(default_factory=dict)
    tactics: dict[str, list[str]] = field(default_factory=dict)
    lemmas: str = ""
    expected: str | None = None
    family: str = ""
    split: str = "dev"
    description: str = ""
    reference_source: str = "AI_PRELIMINARY"

    @classmethod
    def load(cls, path) -> "CompareSpec":
        d = json.loads(Path(path).read_text())
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @property
    def ident(self) -> str:
        parts = [p for p in re.split(r"[^A-Za-z0-9]+", self.id) if p]
        name = "".join(p[:1].upper() + p[1:] for p in parts)
        return name if name and not name[0].isdigit() else "P" + name

    def b(self) -> str:
        return " ".join(f"({n} : {t})" for n, t in self.binders)

    def nat_box(self) -> bool:
        return bool(self.bounds) and all(t.strip() == "Nat" and n in self.bounds for n, t in self.binders)

    def ex_box(self, body: str) -> str:
        return " ".join(f"∃ {n}, {n} < {self.bounds[n]} ∧" for n, _ in self.binders) + f" {body}"

    def obligations(self) -> dict[str, tuple[str, list[str]]]:
        b, HL, CL, HR, CR = self.b(), f"({self.lean_hyp})", f"({self.lean_concl})", f"({self.ref_hyp})", f"({self.ref_concl})"
        pat = ", ".join(n for n, _ in self.binders)
        ex = lambda body: [*EXISTS, *self._witnesses(body)]  # noqa: E731
        ob = {
            "hyp_cover": (f"∀ {b}, {HR} → {HL}", list(FORALL)),
            "concl_cover": (f"∀ {b}, {HR} → {CL} → {CR}", list(FORALL)),
            "hyp_back": (f"∀ {b}, {HL} → {HR}", list(FORALL)),
            "concl_back": (f"∀ {b}, {HL} → {CR} → {CL}", list(FORALL)),
            "app_gap": (f"∃ {b}, {HR} ∧ ¬ {HL}", ex("app")),
            "concl_gap": (f"∃ {b}, {HR} ∧ {HL} ∧ {CL} ∧ ¬ {CR}", ex("concl")),
            "strict_hyp": (f"∃ {b}, {HL} ∧ ¬ {HR}", ex("sh")),
            "strict_concl": (f"∃ {b}, {HL} ∧ {HR} ∧ {CR} ∧ ¬ {CL}", ex("sc")),
            "vacuous": (f"¬ ∃ {b}, {HL}", [t.format(pat=pat) for t in NEG_EXISTS]),
            "inhabited": (f"∃ {b}, {HL}", ex("inh")),
        }
        if self.nat_box():
            # A witness found inside a finite box is a full certificate of the unbounded existential.
            for k, body in (("app_gap", f"{HR} ∧ ¬ {HL}"), ("concl_gap", f"{HR} ∧ {HL} ∧ {CL} ∧ ¬ {CR}"),
                            ("strict_hyp", f"{HL} ∧ ¬ {HR}"), ("strict_concl", f"{HL} ∧ {HR} ∧ {CR} ∧ ¬ {CL}"),
                            ("inhabited", HL)):
                ob[k][1].append(self._box_tactic(body))
        for k, extra in self.tactics.items():
            ob[k][1].extend(extra)
        return ob

    def _box_tactic(self, body: str) -> str:
        """One-line tactic: decide the boxed existential by kernel computation, then drop the box bounds.
        (Multi-line tactics inside `first | ...` would be a parse error that disables every alternative.)"""
        names = [n for n, _ in self.binders]
        boxed = self.ex_box(body)
        # (h : ∃ x₁, x₁ < B₁ ∧ ∃ x₂, x₂ < B₂ ∧ … ∧ body)  ↦  ⟨x₁, x₂, …, proof of body⟩
        inner = f"⟨{', '.join(names)}, h{len(names)}.2⟩"
        for i in range(len(names), 0, -1):
            prev = "hb" if i == 1 else f"h{i - 1}.2"
            inner = f"{prev}.elim (fun {names[i - 1]} h{i} => {inner})"
        return f"exact (by decide +kernel : {boxed}).elim (fun {names[0]} h1 => " + \
            (inner.split("(fun", 1)[1].split("=>", 1)[1].strip()[:-1] if len(names) == 1 else
             inner.split(f"(fun {names[0]} h1 => ", 1)[1][:-1]) + ")"

    def _witnesses(self, _tag: str) -> list[str]:
        """Witness search for existential obligations over Nat, Int and List Nat binders (at most two).
        For each candidate tuple: `refine ⟨v, ?_⟩; and_intros`, then close every conjunct with one of:
        decision procedures, ps_arith, a concrete existential witness, refutation of a universal by a
        concrete instance (`h c`), or diagonal instantiation of a refuted ∃∀ (`hy y`, `hy (y+1)`).
        Every successful alternative is an ordinary Lean proof, checked like any other."""
        pools = {"Nat": [str(i) for i in range(6)], "Int": ["0", "1", "-1", "2", "-2"],
                 "List Nat": ["[]", "[0]", "[1]", "[1, 0]", "[0, 1]"]}
        cols = [pools.get(t.strip()) for _, t in self.binders]
        if any(c is None for c in cols) or len(cols) > 2:
            return []
        names = [n for n, _ in self.binders]
        inst = [str(i) for i in range(4)] + names + [f"{n} + 1" for n in names]
        closers = (
            ["decide", "trivial", "omega", "ps_arith", "simp"]
            + [f"(exact ⟨{c}, by decide⟩)" for c in ("0", "1", "2", "3")]
            + [f"(intro h; exact absurd (h {c}) (by decide))" for c in inst]
            + [f"(intro h; exact absurd (h {c}) (by omega))" for c in inst]
            + ["(intro k; exact ⟨k + 1, by omega⟩)",
               "(intro h; obtain ⟨y, hy⟩ := h; exact absurd (hy y) (by omega))",
               "(intro h; obtain ⟨y, hy⟩ := h; exact absurd (hy (y + 1)) (by omega))"])
        # every closer must finish its goal: a closer that only rewrites (e.g. `simp`) must not be accepted
        closer = " | ".join(f"({c}; done)" for c in closers)
        out = []
        for v in product(*cols):
            out.append(f"exact ⟨{', '.join(v)}, by decide⟩")
            out.append(f"refine ⟨{', '.join(v)}, ?_⟩; and_intros <;> first | {closer}")
        return out

    def header(self) -> str:
        imports = list(dict.fromkeys(["Lean"] + self.imports))
        return ("".join(f"import {m}\n" for m in imports)
                + "\nsection ProofScopeTactics\nopen Lean Meta Elab Tactic\n" + _TAC_BODY + "\nend ProofScopeTactics\n\n"
                + "set_option maxHeartbeats 400000\nset_option maxRecDepth 20000\n"
                + "set_option linter.unusedVariables false\n\n"
                + (self.preamble.strip() + "\n\n" if self.preamble.strip() else "")
                + (self.lemmas.strip() + "\n" if self.lemmas.strip() else ""))


def classify(c: set[str]) -> str:
    if "vacuous" in c:
        return "VACUOUS"
    if "app_gap" in c:
        return "APPLICABILITY_GAP"
    if "concl_gap" in c:
        return "CONCLUSION_GAP"
    cover = "transfer" in c
    if cover and {"hyp_back", "concl_back"} <= c:
        return "EQUIVALENT"
    if cover and ({"strict_hyp", "strict_concl"} & c):
        return "LEAN_STRONGER"
    if cover:
        return "COVERS"
    return "INCONCLUSIVE"


def contradictions(c: set[str]) -> list[str]:
    """Pairs that cannot both be true; if both are certified the run is unsound and must be investigated."""
    pairs = [("hyp_cover", "app_gap"), ("concl_cover", "concl_gap"), ("hyp_back", "strict_hyp"),
             ("concl_back", "strict_concl"), ("vacuous", "inhabited")]
    return [f"{a} & {b}" for a, b in pairs if a in c and b in c]


SOUNDNESS = {
    "VACUOUS": "certified: ¬ ∃ x, H_L x. The formal theorem has no instances.",
    "APPLICABILITY_GAP": "certified: ∃ x, H_R x ∧ ¬ H_L x. The formal theorem does not apply to an object the reference covers.",
    "CONCLUSION_GAP": "certified: ∃ x, H_R x ∧ H_L x ∧ C_L x ∧ ¬ C_R x. At that object the formal conclusion does not give the reference conclusion.",
    "EQUIVALENT": "certified: hypotheses and conclusions imply each other uniformly in x, so each theorem implies the other.",
    "LEAN_STRONGER": "certified: the formal theorem implies the reference claim and covers strictly more.",
    "COVERS": "certified: the formal theorem implies the reference claim; whether it is strictly stronger was not settled.",
    "INCONCLUSIVE": "no classifying certificate was found; no claim is made.",
}


def run_compare(spec: CompareSpec, tc: Toolchain, workdir: Path) -> dict:
    r = certify(spec.ident, spec.header(), spec.obligations(), tc, workdir)
    got = set(r["certificates"])
    # transfer: (∀x, H_L → C_L) → (∀x, H_R → C_R), proved from the two cover certificates and itself certified
    if {"hyp_cover", "concl_cover"} <= got:
        xs = " ".join(n for n, _ in spec.binders)
        base = r["certificate_source"].split("\n#print axioms", 1)[0]
        tr_ob = {"transfer": (f"(∀ {spec.b()}, ({spec.lean_hyp}) → ({spec.lean_concl})) → "
                              f"(∀ {spec.b()}, ({spec.ref_hyp}) → ({spec.ref_concl}))",
                              [f"intro hT {xs} hR; exact ProofScopeCert.{spec.ident}.concl_cover {xs} hR "
                               f"(hT {xs} (ProofScopeCert.{spec.ident}.hyp_cover {xs} hR))"])}
        t = certify(spec.ident + "Transfer", base, tr_ob, tc, Path(workdir) / "transfer")
        if "transfer" in t["certificates"]:
            r["certificates"]["transfer"] = t["certificates"]["transfer"]
            got.add("transfer")
        else:
            r["rejected"]["transfer"] = t["rejected"].get("transfer", t["status"])
    label = classify(got)
    bad = contradictions(got)
    if bad:
        label = "INCONSISTENT"
    out = {"id": spec.id, "family": spec.family, "split": spec.split, "description": spec.description,
           "expected": spec.expected, "classification": label,
           "soundness": SOUNDNESS.get(label, "contradictory certificates: soundness failure, investigate"),
           "contradictions": bad, "certificates": r["certificates"], "rejected": r["rejected"],
           "engine_status": r["status"], "reference_source": spec.reference_source,
           "pair_specific": sorted(spec.tactics) + (["lemmas"] if spec.lemmas.strip() else [])}
    if spec.expected:
        out["correct"] = label == spec.expected
    return out
