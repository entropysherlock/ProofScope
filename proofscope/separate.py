"""Definition-fidelity separation engine.

Given a custom definition D_c, a reference definition D_r, and the domain H on which the theorem actually
uses them, ProofScope tries to prove, in Lean, each of these obligations:

  equal_all          forall x, D_c(x) ~ D_r(x)
  agree_domain       forall x, H(x) -> D_c(x) ~ D_r(x)
  witness_all        exists x, not (D_c(x) ~ D_r(x))
  witness_domain     exists x, H(x) and not (D_c(x) ~ D_r(x))
  *_bounded          the same on a finite box (natural-number binders only)

A bounded *witness* is a full certificate of difference (it exhibits a concrete instance). Bounded
*agreement* is only evidence on the stated box and is reported as such.

Two passes:
  1. probe: every obligation is elaborated with a tactic portfolio; errors are mapped back by line.
  2. certify: only the obligations that succeeded are written to a module, compiled to an .olean,
     checked with `#print axioms` (anything depending on `sorryAx` is rejected), and replayed with
     leanchecker. Only obligations that survive all three steps count as certificates.
"""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path

from .toolchain import Toolchain

STD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}

CORE_FORALL = [
    "intros; omega", "intros; rfl", "intros; simp_all", "intros; simp_all <;> omega", "intros; grind",
    "decide", "intros; split <;> omega", "intros; constructor <;> intro <;> omega",
]
CORE_EXISTS_BOUNDED = ["decide +kernel", "decide"]
CORE_EXISTS = ["grind", "simp", "decide"]
MATHLIB_EXTRA = [
    "intros; norm_num", "intros; ring", "intros; simp; ring", "intros; field_simp; ring", "intros; linarith",
    "intros; nlinarith", "aesop", "intros; positivity",
]

# Classification labels
EQUIVALENT = "EQUIVALENT_CERTIFIED"
IN_DOMAIN = "DISCREPANCY_IN_DOMAIN_CERTIFIED"
OUTSIDE_ONLY = "DISCREPANCY_OUTSIDE_DOMAIN_ONLY_CERTIFIED"
AGREE_DOMAIN = "AGREEMENT_ON_DOMAIN_CERTIFIED"
BOUNDED_ONLY = "BOUNDED_AGREEMENT_ONLY"
INCONCLUSIVE = "INCONCLUSIVE"
INCONSISTENT = "INCONSISTENT_CERTIFICATES"  # would indicate a soundness problem; must never happen


@dataclass
class PairSpec:
    id: str
    custom: str
    reference: str
    binders: list[list[str]]
    domain: str = "True"
    relation: str = "eq"                     # "eq" or "iff"
    preamble: str = ""
    lemmas: str = ""                         # pair-specific helper lemmas (kernel-checked, reported as such)
    imports: list[str] = field(default_factory=list)
    bounds: dict[str, int] = field(default_factory=dict)
    tactics: dict[str, list[str]] = field(default_factory=dict)   # pair-specific extras (reported as such)
    description: str = ""
    reference_source: str = ""
    expected: str | None = None
    group: str = "real"

    @classmethod
    def load(cls, path: str | Path) -> "PairSpec":
        data = json.loads(Path(path).read_text())
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    @property
    def ident(self) -> str:
        parts = re.split(r"[^A-Za-z0-9]+", self.id)
        name = "".join(p[:1].upper() + p[1:] for p in parts if p)
        return name if name and not name[0].isdigit() else "P" + name

    def rel(self) -> str:
        op = "=" if self.relation == "eq" else "↔"
        return f"(({self.custom}) {op} ({self.reference}))"

    def binder_str(self) -> str:
        return " ".join(f"({n} : {t})" for n, t in self.binders)

    def bounded_ok(self) -> bool:
        return bool(self.bounds) and all(t.strip() == "Nat" and n in self.bounds for n, t in self.binders)

    def obligations(self) -> dict[str, str]:
        b, r, h = self.binder_str(), self.rel(), self.domain
        ob = {
            "equal_all": f"∀ {b}, {r}",
            "agree_domain": f"∀ {b}, ({h}) → {r}",
            "witness_all": f"∃ {b}, ¬ {r}",
            "witness_domain": f"∃ {b}, ({h}) ∧ ¬ {r}",
        }
        if self.bounded_ok():
            fa = " ".join(f"∀ {n}, {n} < {self.bounds[n]} →" for n, _ in self.binders)
            ex = " ".join(f"∃ {n}, {n} < {self.bounds[n]} ∧" for n, _ in self.binders)
            ob["agree_domain_bounded"] = f"{fa} ({h}) → {r}"
            ob["witness_all_bounded"] = f"{ex} ¬ {r}"
            ob["witness_domain_bounded"] = f"{ex} ({h}) ∧ ¬ {r}"
        return ob

    def portfolio(self, kind: str, mathlib: bool) -> list[str]:
        if kind.endswith("_bounded") and kind.startswith("witness"):
            base = list(CORE_EXISTS_BOUNDED)
        elif kind.endswith("_bounded"):
            base = ["decide +kernel", "decide"]
        elif kind.startswith("witness"):
            base = list(CORE_EXISTS) + self._small_witnesses(kind)
        else:
            base = list(CORE_FORALL)
            if kind == "agree_domain" and self.bounded_ok():
                base.append(self._lift_from_box())
        if mathlib and not kind.endswith("_bounded"):
            base += MATHLIB_EXTRA
        return base + list(self.tactics.get(kind, []))

    def _lift_from_box(self) -> str:
        """If the domain itself forces every binder into the finite box, the bounded check proves the
        unbounded agreement statement: `omega` discharges the box bounds from the domain hypothesis."""
        boxed = self.obligations()["agree_domain_bounded"]
        names = [n for n, _ in self.binders]
        args = " ".join(f"{n} (by omega)" for n in names)
        return (f"exact fun {' '.join(names)} h => (by decide +kernel : {boxed}) {args} h")

    def _small_witnesses(self, kind: str) -> list[str]:
        """Try small concrete natural-number witnesses for existentials over Nat binders."""
        if not all(t.strip() == "Nat" for _, t in self.binders) or len(self.binders) > 3:
            return []
        out = []
        for vals in product(range(4), repeat=len(self.binders)):
            v = ", ".join(map(str, vals))
            out.append(f"exact ⟨{v}, by decide⟩")
        return out


def _header(spec: PairSpec) -> str:
    imps = "".join(f"import {m}\n" for m in spec.imports)
    return (imps + "set_option maxHeartbeats 400000\n"
            + "set_option maxRecDepth 20000\n"
            + "set_option linter.unusedVariables false\n\n"
            + (spec.preamble.rstrip() + "\n\n" if spec.preamble.strip() else "")
            + (spec.lemmas.rstrip() + "\n\n" if spec.lemmas.strip() else ""))


def _theorem(name: str, stmt: str, tactics: list[str]) -> str:
    alts = "\n".join(f"    | (({t}); done)" for t in tactics)
    return f"theorem {name} : {stmt} := by\n  first\n{alts}\n"


def build_module(spec: PairSpec, mathlib: bool, keep: set[str] | None = None) -> tuple[str, dict[str, tuple[int, int]]]:
    """Return Lean source and the line span of each obligation."""
    src = _header(spec)
    spans: dict[str, tuple[int, int]] = {}
    ns = f"ProofScopeCert.{spec.ident}"
    src += f"namespace {ns}\n\n"
    for kind, stmt in spec.obligations().items():
        if keep is not None and kind not in keep:
            continue
        start = src.count("\n") + 1
        src += _theorem(kind, stmt, spec.portfolio(kind, mathlib)) + "\n"
        spans[kind] = (start, src.count("\n"))
    src += f"end {ns}\n"
    if keep:
        src += "\n" + "".join(f"#print axioms {ns}.{k}\n" for k in spans)
    return src, spans


_ERR = re.compile(r":(\d+):\d+: error", re.M)


def _failed_kinds(output: str, spans: dict[str, tuple[int, int]]) -> set[str]:
    bad = set()
    for m in _ERR.finditer(output):
        line = int(m.group(1))
        for k, (a, b) in spans.items():
            if a <= line <= b:
                bad.add(k)
    return bad


def _axioms(output: str, ns: str) -> dict[str, list[str] | None]:
    res: dict[str, list[str] | None] = {}
    for m in re.finditer(r"'%s\.(\w+)' depends on axioms: \[([^\]]*)\]" % re.escape(ns), output):
        res[m.group(1)] = [a.strip() for a in m.group(2).split(",") if a.strip()]
    for m in re.finditer(r"'%s\.(\w+)' does not depend on any axioms" % re.escape(ns), output):
        res[m.group(1)] = []
    return res


def classify(proved: set[str]) -> str:
    w_dom = {"witness_domain", "witness_domain_bounded"} & proved
    w_all = {"witness_all", "witness_all_bounded"} & proved or w_dom
    if "equal_all" in proved and w_all:
        return INCONSISTENT
    if "agree_domain" in proved and w_dom:
        return INCONSISTENT
    if "equal_all" in proved:
        return EQUIVALENT
    if w_dom:
        return IN_DOMAIN
    if "agree_domain" in proved and w_all:
        return OUTSIDE_ONLY
    if "agree_domain" in proved:
        return AGREE_DOMAIN
    if "agree_domain_bounded" in proved:
        return BOUNDED_ONLY
    return INCONCLUSIVE


INTERPRETATION = {
    EQUIVALENT: "Kernel-checked proof that the custom definition equals the reference everywhere: no scope change.",
    IN_DOMAIN: "Kernel-checked witness of disagreement on the theorem's own domain: candidate scope change, needs expert review.",
    OUTSIDE_ONLY: "Certified difference, but certified agreement on the theorem's domain: a convention (e.g. junk values), not a scope change.",
    AGREE_DOMAIN: "Certified agreement on the theorem's domain; behaviour outside it not settled.",
    BOUNDED_ONLY: "Agreement verified by kernel computation on a finite box only; no general certificate.",
    INCONCLUSIVE: "Search found no certificate either way: no claim is made.",
    INCONSISTENT: "Contradictory certificates: treat as a soundness failure of this run and investigate.",
}


def run_pair(spec: PairSpec, tc: Toolchain, workdir: Path | None = None, mathlib: bool | None = None,
             replay: bool = True, timeout: float | None = 900) -> dict:
    mathlib = any(i.startswith("Mathlib") for i in spec.imports) if mathlib is None else mathlib
    root = Path(workdir or tempfile.mkdtemp(prefix="proofscope_sep_"))
    src_root = root / "src"
    build = root / "build"
    mod_dir = src_root / "ProofScopeCert"
    mod_dir.mkdir(parents=True, exist_ok=True)
    ns = f"ProofScopeCert.{spec.ident}"

    # Pass 1: probe all obligations.
    probe_src, spans = build_module(spec, mathlib)
    probe_file = mod_dir / f"{spec.ident}Probe.lean"
    probe_file.write_text(probe_src)
    probe = tc.compile(probe_file, None, src_root, timeout=timeout)
    preamble_broken = bool(_ERR.search(probe.output)) and not _failed_kinds(probe.output, spans) \
        and probe.returncode != 0
    failed = _failed_kinds(probe.output, spans)
    candidates = set(spans) - failed if probe.returncode in (0, 1) and not preamble_broken else set()

    result = {"id": spec.id, "group": spec.group, "description": spec.description,
              "custom": spec.custom, "reference": spec.reference, "reference_source": spec.reference_source,
              "domain": spec.domain, "binders": spec.binders, "bounds": spec.bounds,
              "expected": spec.expected, "pair_specific_tactics": sorted(spec.tactics),
              "pair_specific_lemmas": bool(spec.lemmas.strip()),
              "obligations": spec.obligations(), "probe": probe.as_dict(),
              "probe_candidates": sorted(candidates), "certificates": {}, "rejected": {}}
    if probe.returncode not in (0, 1) or preamble_broken:
        result["classification"] = INCONCLUSIVE
        result["error"] = "Lean could not elaborate the pair (environment or preamble problem)."
        result["interpretation"] = INTERPRETATION[INCONCLUSIVE]
        return result

    proved: set[str] = set()
    if candidates:
        # Pass 2: certify survivors in a clean module.
        cert_src, _ = build_module(spec, mathlib, keep=candidates)
        cert_file = mod_dir / f"{spec.ident}.lean"
        cert_file.write_text(cert_src)
        cc = tc.compile(cert_file, build / "ProofScopeCert" / f"{spec.ident}.olean", src_root, timeout=timeout)
        result["certify_compile"] = cc.as_dict()
        ax = _axioms(cc.output, ns)
        if cc.returncode == 0:
            rp = tc.replay(f"ProofScopeCert.{spec.ident}", build) if replay else None
            result["replay"] = rp.as_dict() if rp else {"skipped": True}
            replay_ok = (rp is None) or rp.returncode == 0
            for k in candidates:
                axs = ax.get(k)
                if axs is None:
                    result["rejected"][k] = "axiom report missing"
                elif "sorryAx" in axs:
                    result["rejected"][k] = "depends on sorryAx"
                elif not set(axs) <= STD_AXIOMS:
                    result["rejected"][k] = f"non-standard axioms {axs}"
                elif not replay_ok:
                    result["rejected"][k] = "leanchecker replay failed"
                else:
                    proved.add(k)
                    result["certificates"][k] = {"declaration": f"{ns}.{k}", "axioms": axs,
                                                 "statement": spec.obligations()[k]}
        else:
            for k in candidates:
                result["rejected"][k] = "certificate module failed to compile"
        result["certificate_source"] = str(cert_file)
    result["classification"] = classify(proved)
    result["interpretation"] = INTERPRETATION[result["classification"]]
    if spec.expected:
        result["correct"] = result["classification"] == spec.expected
    return result
