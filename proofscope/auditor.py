"""ProofScope audit: one entry point from two statements to an honest, verifiable report (SOTA-9).

    python -m proofscope.auditor --ref "∀ (n : Nat), n + 0 = n" --cand "∀ (m : Nat), m = m + 0" --out report/

The report has exactly one status:
  PROVED_EQUIVALENT        both directions certified (or definitional equality)
  PROVED_IMPLICATION       one direction certified; the other is UNKNOWN (never "false")
  DISPROVED_EQUIVALENCE    a certified counterexample: one statement refuted, the other proved
  UNKNOWN                  nothing decisive certified (search failure is not evidence)
  NOT_EVALUABLE            a statement does not elaborate; Lean diagnostics and hints are given
Every "proved" line names a Lean declaration that passed the clean verifier (compile, axioms ⊆ {propext,
Classical.choice, Quot.sound}, leanchecker replay). The report never upgrades UNKNOWN. Hints (e.g. a
namespace that would resolve an unknown identifier) are suggestions only and are never applied.

Engine: proofscope.experimental.sota8 (derivation + CJCS), unchanged. Imports are fixed per process by
PROOFSCOPE_IMPORTS (e.g. "Mathlib"), as for every ProofScope engine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import resource
import subprocess
import time
from pathlib import Path

from . import adelta12 as A
from .experimental import cjcs4 as E
from .experimental import sota8 as S8
from .toolchain import Toolchain

# common Mathlib homes of names that need an `open` (suggestions only)
HINTS = {"Tendsto": "Filter", "atTop": "Filter", "atBot": "Filter", "𝓝": "Topology (open scoped Topology)",
         "Injective": "Function", "Surjective": "Function", "Bijective": "Function", "span": "Ideal or Submodule",
         "X": "Polynomial", "C": "Polynomial", "Icc": "Set", "Ioo": "Set", "Ico": "Set", "Ioc": "Set",
         "range": "Set or Finset", "card": "Fintype or Finset", "succ": "Nat", "sqrt": "Real", "π": "Real (open Real)",
         "deriv": "(root; check imports)", "orderOf": "(root; check imports)"}
PROVED_TEXT = {
    "equiv": "R ↔ C, by deriving each statement from the other",
    "impl_RC": "R → C (C derived from R)", "impl_CR": "C → R (R derived from C)",
    "equiv_defeq": "R ↔ C by definitional equality (Iff.rfl)",
    "equiv_both_true": "R ↔ C because both R and C were proved", "equiv_both_false": "R ↔ C because both were refuted",
    "true_R": "R is true", "true_L": "C is true", "false_R": "R is false", "false_L": "C is false",
    "diff_RL": "¬(R ↔ C): R is false and C is true", "diff_LR": "¬(R ↔ C): R is true and C is false",
}
NOT_ESTABLISHED = {
    "mutual_derivation": "That R and C say the same thing: a derivation may ignore its hypothesis when the conclusion "
                         "is provable on its own, so this is equivalence of closed propositions.",
    "both_true": "That R and C are related: two unrelated true statements are logically equivalent.",
    "both_false": "That R and C are related: two false statements are logically equivalent; their open forms may differ.",
    "definitional": "Nothing beyond the elaborated terms.",
    "implication": "The converse direction (unknown — not refuted).",
}


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _hints(text: str) -> list[dict]:
    out = []
    for name in sorted(set(re.findall(r"[Uu]nknown (?:identifier|constant) `([^`]+)`", text))):
        base = name.split(".")[-1]
        out.append({"unknown": name, "suggestion": (f"may need `open {HINTS[base]}` or a qualified name"
                                                    if base in HINTS else "undefined here: check spelling, imports, or "
                                                    "whether the source defines it"), "applied": False})
    if re.search(r"unknown universe level", text):
        out.append({"unknown": "universe", "suggestion": "declare it (e.g. `universe u`) in the preamble, as the source does",
                    "applied": False})
    if "unexpected token" in text:
        out.append({"unknown": "syntax", "suggestion": "the statement does not parse as Lean 4 (e.g. `...` or Lean 3 syntax)",
                    "applied": False})
    return out


# A positive status is shown only if the certificate that justifies it is present in the row.
REQUIRED = {
    ("CERTIFIED_LOGICAL_EQUIVALENCE", "mutual_derivation"): "equiv",
    ("CERTIFIED_LOGICAL_EQUIVALENCE", "definitional"): "equiv_defeq",
    ("CERTIFIED_LOGICAL_EQUIVALENCE", "both_true"): "equiv_both_true",
    ("CERTIFIED_LOGICAL_EQUIVALENCE", "both_false"): "equiv_both_false",
    ("CERTIFIED_IMPLICATION", "reference_implies_candidate"): "impl_RC",
    ("CERTIFIED_IMPLICATION", "candidate_implies_reference"): "impl_CR",
    ("CERTIFIED_LOGICAL_DIFFERENCE", "reference_false_formalization_true"): "diff_RL",
    ("CERTIFIED_LOGICAL_DIFFERENCE", "reference_true_formalization_false"): "diff_LR",
}


def report_from_row(row: dict) -> dict:
    """Pure mapping from an engine row to the user report (tested without Lean)."""
    certs = row.get("certificates") or {}
    v, d = row.get("verdict"), row.get("direction")
    downgraded = None
    if v == "INCONSISTENT":
        return {"status": "ENGINE_INCONSISTENT", "proved": [], "not_established": ["Anything: the engine certified contradictory facts; report this as a bug."],
                "unknown": [], "diagnostics": [str(row.get("reason", ""))[:1000]], "hints": []}
    if str(v).startswith("CERTIFIED_"):
        need = REQUIRED.get((v, d))
        if need is None or need not in certs:
            downgraded = f"engine verdict {v}/{d} arrived without its certificate {need!r}; shown as UNKNOWN"
            v = None
    proved = [{"declaration": c.get("declaration"), "statement": c.get("statement"), "axioms": c.get("axioms"),
               "meaning": PROVED_TEXT.get(k, k)} for k, c in certs.items() if not k.startswith(("wf_", "link_", "wit_", "region_"))]
    rep = {"proved": proved, "not_established": [], "unknown": [], "diagnostics": [], "hints": []}
    if v == "CERTIFIED_LOGICAL_EQUIVALENCE":
        rep["status"] = "PROVED_EQUIVALENT"
        rep["basis"] = d
        rep["not_established"].append(NOT_ESTABLISHED.get(d, "Formulation-level sameness."))
    elif v == "CERTIFIED_IMPLICATION":
        rep["status"] = "PROVED_IMPLICATION"
        rep["basis"] = d
        rep["unknown"].append("C → R" if d == "reference_implies_candidate" else "R → C")
        rep["not_established"].append(NOT_ESTABLISHED["implication"])
    elif v == "CERTIFIED_LOGICAL_DIFFERENCE":
        rep["status"] = "DISPROVED_EQUIVALENCE"
        rep["basis"] = d
        w = row.get("witnesses") or {}
        rep["counterexample"] = w.get("wit_R") if d == "reference_false_formalization_true" else w.get("wit_L")
        rep["not_established"].append("Which statement is the intended one.")
    elif (row.get("failure_class") == "EXTRACTION" or "extraction failed" in str(row.get("reason", ""))) \
            and (row.get("delta") or {}).get("status") != "OK":
        rep["status"] = "NOT_EVALUABLE"
        text = json.dumps(row.get("detail"), ensure_ascii=False) + str(row.get("reason", ""))
        rep["diagnostics"].append(text[-2000:])
        rep["hints"] = _hints(text)
    else:
        rep["status"] = "UNKNOWN"
        rep["unknown"].append("R → C and C → R: no certificate found within the search budget (not evidence of difference)")
        if row.get("reason"):
            rep["diagnostics"].append(str(row["reason"])[:1000])
        if downgraded:
            rep["diagnostics"].append(downgraded)
    if rep["status"] in ("UNKNOWN", "NOT_EVALUABLE"):
        # partial facts (e.g. "R is true") stay visible but never a relation claim
        rep["proved"] = [p for p, k in zip(proved, [k for k in certs if not k.startswith(("wf_", "link_", "wit_", "region_"))])
                         if not k.startswith(("equiv", "impl_", "diff_"))]
    return rep


def engine_commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(Path(__file__).resolve().parents[1]), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip() or "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def audit(reference: str, candidate: str, preamble: list[str] | None = None, out: Path | None = None,
          extra_imports: list[str] | None = None, extra_lean_path: str | None = None) -> dict:
    """extra_imports / extra_lean_path: used by source_audit to make a compiled source module visible to the
    search session and to the certificate (the certificate then `import`s it, so replay rechecks against it)."""
    out = Path(out or "proofscope_audit").resolve()
    out.mkdir(parents=True, exist_ok=True)
    tc = Toolchain.find()
    build = out / "build"
    b = E.build(tc, build)
    if not b["ok"]:
        raise RuntimeError(f"extractor build failed: {b}")
    old = os.environ.get("PROOFSCOPE_PREAMBLE")
    os.environ["PROOFSCOPE_PREAMBLE"] = "\n".join(preamble or [])
    old_imports, old_lp = list(A.IMPORTS), os.environ.get("LEAN_PATH")
    if extra_imports:
        A.IMPORTS[:] = old_imports + [m for m in extra_imports if m not in old_imports]
    if extra_lean_path:
        os.environ["LEAN_PATH"] = os.pathsep.join(p for p in [extra_lean_path, old_lp or ""] if p)
    t0, r0 = time.monotonic(), resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        spec = {"id": "audit_" + _sha(f"{reference}\0{candidate}\0{preamble}")[:12], "reference": reference, "lean": candidate}
        row = S8.run_case(spec, tc, build, out / "work")
        imports_used = list(A.IMPORTS)
    finally:
        if old is None:
            os.environ.pop("PROOFSCOPE_PREAMBLE", None)
        else:
            os.environ["PROOFSCOPE_PREAMBLE"] = old
        A.IMPORTS[:] = old_imports
        if old_lp is None:
            os.environ.pop("LEAN_PATH", None)
        else:
            os.environ["LEAN_PATH"] = old_lp
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    rep = report_from_row(row)
    rep.update(inputs={"reference": reference, "candidate": candidate, "preamble": preamble or [],
                       "imports": imports_used, "sha256": _sha(f"{reference}\0{candidate}")},
               environment={"lean": tc.version() if hasattr(tc, "version") else "4.34.1", "engine": "sota8 (derivation + CJCS4)",
                            "engine_commit": engine_commit()},
               resources={"wall_s": round(time.monotonic() - t0, 2),
                          "child_cpu_s": round((r1.ru_utime + r1.ru_stime) - (r0.ru_utime + r0.ru_stime), 2),
                          "child_peak_rss_mb": round(r1.ru_maxrss / 1024)},
               certificate_source=row.get("certificate_source"), engine_row=row)
    (out / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str))
    (out / "report.md").write_text(markdown(rep))
    if rep.get("certificate_source"):
        (out / "certificate.lean").write_text(rep["certificate_source"])
    return rep


def markdown(rep: dict) -> str:
    L = [f"# ProofScope audit — **{rep['status']}**", "",
         f"- Reference R: `{rep['inputs']['reference']}`", f"- Candidate C: `{rep['inputs']['candidate']}`",
         f"- Preamble: {rep['inputs']['preamble'] or 'none'} · imports: {rep['inputs'].get('imports') or 'core Lean'}", ""]
    if rep["proved"]:
        L += ["## Proved (kernel-checked, replayed)"] + [f"- {p['meaning']} — `{p['declaration']}` (axioms: {p['axioms']})" for p in rep["proved"]] + [""]
    if rep.get("counterexample"):
        L += [f"**Counterexample:** {rep['counterexample']}", ""]
    if rep["unknown"]:
        L += ["## Unknown"] + [f"- {u}" for u in rep["unknown"]] + [""]
    if rep["not_established"]:
        L += ["## Not established by these certificates"] + [f"- {n}" for n in rep["not_established"]] + [""]
    if rep["diagnostics"] or rep["hints"]:
        L += ["## Diagnostics"] + [f"```\n{d}\n```" for d in rep["diagnostics"]] + \
             [f"- `{h['unknown']}`: {h['suggestion']} (not applied)" for h in rep["hints"]] + [""]
    r = rep.get("resources")
    if r:
        L += [f"Resources: {r['wall_s']} s wall, {r['child_cpu_s']} s CPU, peak child RSS {r['child_peak_rss_mb']} MB. "
              f"Engine {rep['environment']['engine']} @ {rep['environment']['engine_commit'][:12]}."]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m proofscope.auditor")
    ap.add_argument("--ref", required=True)
    ap.add_argument("--cand", required=True)
    ap.add_argument("--preamble", action="append", default=[], help="verbatim source line: open … / universe …")
    ap.add_argument("--out", type=Path, default=Path("proofscope_audit"))
    a = ap.parse_args(argv)
    rep = audit(a.ref, a.cand, a.preamble, a.out)
    print(markdown(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
