"""Certified drift localization (v0.9): which edit changed the claim, and a checked reason why.

Pipeline for a reference R and a formal statement L (both elaborated by Lean):

1. `lean/ProofScope/DriftExtract.lean` finds the edit sites e1..en of the elaborated terms, builds the
   chain S0 = R, S1, ..., Sn = L (Sk applies the first k edits), and abstracts every Sk over the same
   shared opaque symbols (policy LINEAR_CORE_SHARED_OCC, per occurrence).
2. Certificates (`certify`: tactic, clean recompile, standard axioms only, kernel replay):
      link_R, link_L     abstraction of S0 / Sn is definitionally the elaborated R / L    (Iff.rfl)
      fwd_k  ∀x, S(k-1) x → S(k) x      bwd_k  ∀x, S(k) x → S(k-1) x
      sepW_k ∃x, S(k) x ∧ ¬S(k-1) x     sepS_k ∃x, S(k-1) x ∧ ¬S(k) x               (countermodels)
      the same four for the global pair (S0, Sn).
3. Verdict, using only theorems proved in `DriftSoundness.lean`:
      * every edit forward-entailing and some edit strictly weakening → CLAIM_LEAN_WEAKER, localized at
        those edits; each localized edit's countermodel is a global countermodel (`monotone_strict`);
      * the mirror case → CLAIM_LEAN_STRONGER (`localize_stronger`);
      * every edit schema-equivalent → SCHEMA_EQUIVALENT (`equiv_trans`);
      * mixed directions → per-edit relations plus the separately certified global relation, and NO
        localized claim (`cancellation`: mixed edits can cancel).
   With no shared symbols nothing is certified as fidelity evidence (two true statements entail each
   other trivially), and the verdict is NO_SHARED_SYMBOLS.

An LLM may propose nothing here; every decisive statement in the output is a Lean-checked certificate.
"""

from __future__ import annotations

import argparse
import json
import re
from itertools import product
from pathlib import Path

from .certify import certify
from .claimdelta import relation, pool as nat_pool
from .toolchain import Toolchain

SRC = Path(__file__).resolve().parents[1] / "lean"
POLICY = "LINEAR_CORE_SHARED_OCC"
LAWS = ["Nat.mul_comm", "Nat.add_comm", "Nat.gcd_comm", "Nat.lcm_comm", "Nat.pow_two", "Nat.mul_assoc",
        "Int.mul_comm", "Int.add_comm", "Nat.min_comm", "Nat.max_comm", "List.length_append", "List.length_reverse"]


def law_tactics() -> list[str]:
    """Concrete rewriting with equational laws only. Every alternative ends by using the antecedent `h`,
    so a proof that ignores the other statement (proving the target separately) is not produced."""
    laws = ", ".join(LAWS)
    return [f"intro h; simpa only [{laws}] using h", f"intro h; simp only [{laws}] at h ⊢; exact h",
            "intro h; exact fun x => (h x).symm", "intro h; intro x; exact Eq.symm (h x)",
            "intro h; exact fun a b => (h a b).symm"]
STRICT = ("LEAN_WEAKER", "LEAN_STRONGER", "INCOMPARABLE")


def build(tc: Toolchain, out: Path) -> dict:
    o = out / "ProofScope" / "DriftExtract.olean"
    if o.exists():
        return {"ok": True}
    r = tc.compile(SRC / "ProofScope" / "DriftExtract.lean", o, SRC, timeout=900)
    return {"ok": r.returncode == 0 and o.exists(), "log": r.as_dict()}


def extract(ref: str, lean: str, tc: Toolchain, buildp: Path, work: Path) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    f = work / "Drift_input.lean"
    f.write_text(f"import ProofScope.DriftExtract\n\n#proofscope_drift ({ref}) ({lean})\n")
    r = tc.run([tc.lean, str(f)], cwd=work, extra_path=buildp, timeout=600)
    for line in r.output.splitlines():
        i = line.find("PROOFSCOPE_DRIFT ")
        if i >= 0:
            return json.loads(line[i + len("PROOFSCOPE_DRIFT "):])
    return {"error": r.output[-3000:]}


def lits(*texts: str) -> list[int]:
    return sorted({int(x) for t in texts for x in re.findall(r"\b(\d+)\b", t) if int(x) <= 12} | {0, 1, 2, 3})


def pool(typ: str, ls: list[int]) -> list[str]:
    t = re.sub(r"\s+", " ", typ.strip())
    base = nat_pool(t, ls)
    if t == "Nat → Nat → Nat":
        base = (base[:6] + ["fun a b => if a = b then 1 else 0", "fun a b => if a = b then 0 else 1"]
                + [f"fun _ _ => {c}" for c in ls if c > 1] + base[6:])
    if t == "Int":
        return ["0", "1", "-1", "2", "-2"]
    if t == "Int → Int":
        return (["fun _ => 0", "fun a => a", "fun a => a + 1", "fun a => -a", "fun _ => 1", "fun a => a - 1"]
                + [f"fun a => if a = {c} then 0 else a + 1" for c in ls[:6]])
    if t == "Int → Int → Int":
        return ["fun _ _ => 0", "fun a _ => a", "fun _ b => b", "fun a b => a + b", "fun a b => a - b",
                "fun a _ => a - 1", "fun _ b => b - 1", "fun a _ => a + 1", "fun a _ => if a < 0 then a - 1 else a",
                "fun a b => if a = b then 1 else 0", "fun _ _ => 1"]
    if t == "List Nat → Nat":
        return ["fun _ => 0", "fun l => List.length l", "fun l => List.length l + 1", "fun _ => 1"]
    if t == "List Nat → List Nat":
        return ["fun l => l", "fun _ => []", "fun l => l ++ l", "fun l => 0 :: l", "fun l => List.drop 1 l"]
    if t == "List Nat → List Nat → List Nat":
        return ["fun a _ => a", "fun _ b => b", "fun _ _ => []", "fun a b => b ++ a"]
    return base


def values(ls: list[int]) -> list[str]:
    # numerals, a negative integer and small lists; an instance of the wrong type fails to elaborate
    # inside `first` and is skipped
    return [str(c) for c in sorted(set(range(4)) | set(ls))][:8] + ["(-1)", "[]", "[0]", "[0, 1]"]


def entail_tactics(nx: int) -> list[str]:
    xs = " ".join(f"_x{i}" for i in range(nx))
    pre = f"intro {xs} h" if nx else "intro h"
    return [f"{pre}; {c}" for c in [
        "grind", "simp_all", "exact h", "(intros; simp_all)", "(intros; grind)",
        "(obtain ⟨y, hy⟩ := h; intro x; exact ⟨y, hy x⟩)", "(intro x; obtain ⟨y, hy⟩ := h; exact ⟨y, hy x⟩)",
        "(intros; (try simp only [] at *); omega)",
        "(intro x; obtain ⟨y, hy⟩ := h x; exact ⟨y, hy.symm⟩)", "(intro x; obtain ⟨y, hy⟩ := h x; exact ⟨y, hy⟩)",
        "(intro x; obtain ⟨y, hy⟩ := h x; refine ⟨y, ?_⟩; omega)", "(intro x; obtain ⟨y, hy⟩ := h x; refine ⟨y, ?_⟩; simp_all)",
        "(obtain ⟨y, hy⟩ := h; exact ⟨y, hy.1⟩)", "(obtain ⟨y, hy⟩ := h; refine ⟨y, ?_⟩; simp_all)"]]


def sep_tactics(typs: list[str], ls: list[int]) -> list[str]:
    cols = [pool(t, ls) for t in typs]
    if not typs or any(not c for c in cols):
        return []
    vs = values(ls)
    hold = ["(intros; simp_all)", "(intros; (try simp only [] at *); omega)",
            "(intros; (try simp only [] at *); split <;> omega)", "decide", "trivial",
            "(intro x; refine ⟨x, ?_⟩; simp)", "(intro x; refine ⟨x + 1, ?_⟩; simp)"]
    # no nested `by` blocks: a failing nested block is logged, not thrown, and would stop `first`
    hold += [f"(refine ⟨{c}, fun _ => ?_⟩; simp)" for c in vs[:4]] + ["grind"]
    refute = ["simp", "(intro ⟨y, h⟩; have := h (y + 1); simp at this)",
              "(intro ⟨y, _, h2⟩; have := h2 (y + 1); simp at this)",
              "(intro ⟨y, _, h2⟩; have := h2 (y + 1); (try simp only [] at this); omega)",
              "(intro ⟨y, h⟩; have := h (y + 1); (try simp only [] at this); omega)"]
    for c in vs:
        for arg in (f"{c}", f"{c} trivial"):
            refute.append(f"(intro h; have := h {arg}; (try simp only [] at this); omega)")
            refute.append(f"(intro h; have := h {arg}; simp at this)")
        for d in vs[:5]:
            refute.append(f"(intro h; have := h {c} {d}; (try simp only [] at this); omega)")
    refute.append("grind")
    closer = " | ".join(f"({c}; done)" for c in hold + refute)
    return [f"refine ⟨{', '.join(t)}, ?_, ?_⟩ <;> first | {closer}" for t in list(product(*cols))[:120]]


def run_case(spec: dict, tc: Toolchain, buildp: Path, work: Path) -> dict:
    ref, lean = spec["reference"], spec["lean"]
    out = {"id": spec["id"], "policy": POLICY, "reference": ref, "lean": lean}
    d = extract(ref, lean, tc, buildp, work / "extract")
    if "error" in d:
        out.update(verdict="INCONCLUSIVE", reason="extraction failed", detail=d["error"][-800:])
        return out
    out.update(symbols=d["symbols"], edits=d["edits"], symbols_truncated=d["symbols_truncated"])
    n = len(d["edits"])
    if n == 0:
        out.update(verdict="IDENTICAL")
        return out
    if not d["symbols"]:
        out.update(verdict="NO_SHARED_SYMBOLS",
                   reason="no shared opaque symbol: two true statements entail each other trivially, so no "
                          "fidelity certificate is issued")
        return out
    syms = d["symbols"]
    binders = " ".join(f"(x{i + 1} : {s['type']})" for i, s in enumerate(syms))
    args = " ".join(f"({s['symbol']} : {s['type']})" for s in syms)
    S = [c["abstract"] for c in d["chain"]]
    C = [c["concrete"] for c in d["chain"]]
    ls = lits(ref, lean)
    typs = [s["type"] for s in syms]
    ob = {"link_R": (f"((fun {binders} => {S[0]}) {args}) ↔ ({ref})", ["exact Iff.rfl"]),
          "link_L": (f"((fun {binders} => {S[n]}) {args}) ↔ ({lean})", ["exact Iff.rfl"])}

    def pair(tag, a, b):
        ob[f"fwd_{tag}"] = (f"∀ {binders}, ({a}) → ({b})", entail_tactics(len(syms)))
        ob[f"bwd_{tag}"] = (f"∀ {binders}, ({b}) → ({a})", entail_tactics(len(syms)))
        ob[f"sepW_{tag}"] = (f"∃ {binders}, ({b}) ∧ ¬ ({a})", sep_tactics(typs, ls))
        ob[f"sepS_{tag}"] = (f"∃ {binders}, ({a}) ∧ ¬ ({b})", sep_tactics(typs, ls))

    for k in range(1, n + 1):
        pair(f"e{k}", S[k - 1], S[k])
        ob[f"lawF_e{k}"] = (f"({C[k - 1]}) → ({C[k]})", law_tactics())
        ob[f"lawB_e{k}"] = (f"({C[k]}) → ({C[k - 1]})", law_tactics())
    if n > 1:
        pair("g", S[0], S[n])
    ob["lawF_g"] = (f"({ref}) → ({lean})", law_tactics())
    ob["lawB_g"] = (f"({lean}) → ({ref})", law_tactics())
    ident = "CMCD_" + re.sub(r"[^A-Za-z0-9_]", "_", spec["id"])
    r = certify(ident, "set_option maxHeartbeats 4000000\nset_option linter.unusedVariables false\n",
                ob, tc, work / "certify")
    certs = set(r["certificates"])
    out["certify_status"] = r["status"]
    linked = {"link_R", "link_L"} <= certs
    steps = []
    for k in range(1, n + 1):
        tag = f"e{k}"
        steps.append({"edit": k, "from": d["edits"][k - 1]["from"], "to": d["edits"][k - 1]["to"],
                      "relation": relation(certs, tag),
                      "certificates": {c: r["certificates"][c] for c in certs if c.endswith("_" + tag)}})
    for st in steps:
        k = st["edit"]
        if st["relation"] in STRICT and {f"lawF_e{k}", f"lawB_e{k}"} <= certs:
            st["relation"] = "EQUIVALENT_BY_LAWS"
            st["law_certificates"] = {c: r["certificates"][c] for c in (f"lawF_e{k}", f"lawB_e{k}")}
    out["steps"] = steps
    gtag = "g" if n > 1 else "e1"
    out["global_relation"] = relation(certs, gtag)
    out["global_certificates"] = {c: r["certificates"][c] for c in certs if c.endswith("_" + gtag)}
    if not linked:
        out.update(verdict="INCONCLUSIVE", reason="abstraction not linked to the elaborated statements")
        return out
    rels = [s["relation"] for s in steps]
    lawsteps = [s["edit"] for s in steps if s["relation"] == "EQUIVALENT_BY_LAWS"]
    fwd_all = all(f"fwd_e{k}" in certs for k in range(1, n + 1))
    bwd_all = all(f"bwd_e{k}" in certs for k in range(1, n + 1))
    weak = [k for k in range(1, n + 1) if f"sepW_e{k}" in certs]
    strong = [k for k in range(1, n + 1) if f"sepS_e{k}" in certs]
    if "INCONSISTENT" in rels or out["global_relation"] == "INCONSISTENT":
        out["verdict"] = "INCONSISTENT"
    elif {"lawF_g", "lawB_g"} <= certs and out["global_relation"] != "SCHEMA_EQUIVALENT":
        out.update(verdict="EQUIVALENT_BY_LAWS", law_certificates={c: r["certificates"][c] for c in ("lawF_g", "lawB_g")},
                   reason="the two statements are rewritings of each other by the listed equational laws; the proof "
                          "of each direction uses the other statement")
    elif all(x == "SCHEMA_EQUIVALENT" for x in rels):
        out.update(verdict="SCHEMA_EQUIVALENT", theorem="equiv_trans",
                   harmless_edits=list(range(1, n + 1)))
    elif all(x in ("SCHEMA_EQUIVALENT", "EQUIVALENT_BY_LAWS") for x in rels):
        out.update(verdict="EQUIVALENT_BY_LAWS", harmless_edits=list(range(1, n + 1)), law_edits=lawsteps,
                   reason="every edit is schema-equivalent or a rewriting by the listed equational laws")
    elif lawsteps:
        g = out["global_relation"]
        out.update(verdict=("CLAIM_" + g) if g in STRICT else ("SCHEMA_EQUIVALENT" if g == "SCHEMA_EQUIVALENT" else "INCONCLUSIVE"),
                   localized_at=[s["edit"] for s in steps if s["relation"] in STRICT] or None, law_edits=lawsteps,
                   theorem=None, reason="some edits are law rewritings (concrete, not schema-level); localization is "
                                        "reported per edit and the global relation is certified directly")
    elif fwd_all and weak:
        out.update(verdict="CLAIM_LEAN_WEAKER", theorem="monotone_strict", localized_at=weak,
                   harmless_edits=[k for k in range(1, n + 1) if rels[k - 1] == "SCHEMA_EQUIVALENT"],
                   explanation=[{"edit": k, **{x: d["edits"][k - 1][x] for x in ("from", "to")},
                                 "global_countermodel": r["certificates"][f"sepW_e{k}"]["statement"]} for k in weak])
    elif bwd_all and strong:
        out.update(verdict="CLAIM_LEAN_STRONGER", theorem="localize_stronger/monotone_strict", localized_at=strong,
                   harmless_edits=[k for k in range(1, n + 1) if rels[k - 1] == "SCHEMA_EQUIVALENT"],
                   explanation=[{"edit": k, **{x: d["edits"][k - 1][x] for x in ("from", "to")},
                                 "global_countermodel": r["certificates"][f"sepS_e{k}"]["statement"]} for k in strong])
    else:
        g = out["global_relation"]
        out.update(verdict=("CLAIM_" + g) if g in STRICT else ("SCHEMA_EQUIVALENT" if g == "SCHEMA_EQUIVALENT" else "INCONCLUSIVE"),
                   localized_at=[1] if n == 1 and g in STRICT else None,
                   reason="single edit" if n == 1 else "edits do not all point in one direction; per-edit relations are reported but not composed "
                          "(theorem `cancellation`)")
    return out


def _one(a):
    p, buildp, out = a
    spec = json.loads(Path(p).read_text())
    row = run_case(spec, Toolchain.find(), buildp, out / "work" / Path(p).stem)
    for k in ("expected", "expected_localized_at", "domain", "family", "split"):
        row[k] = spec.get(k)
    (out / "rows").mkdir(parents=True, exist_ok=True)
    (out / "rows" / (Path(p).stem + ".json")).write_text(json.dumps(row, ensure_ascii=False, indent=1))
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m proofscope.cmcd")
    ap.add_argument("specs", nargs="+", help="case JSON files with 'reference' and 'lean' statements")
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
        print(r["id"], r["verdict"], r.get("localized_at"), ok, flush=True)
    (out / "cmcd_results.json").write_text(json.dumps({"policy": POLICY, "rows": rows}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
