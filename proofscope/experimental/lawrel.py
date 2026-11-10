"""Law-relative comparison prototype (SOTA-5, experimental).

Fragment: one binary operation `op` on an arbitrary type; background laws and the two statements are
universally quantified equations `∀ x y z, s = t` (terms over variables and `op`). For a finite candidate
law family Φ the tool decides, for every subset S ⊆ Φ, one of

  ENTAILS   Lean proof:   ∀ magma m, (∀ φ ∈ S, m ⊨ φ) → (m ⊨ P ↔ m ⊨ Q)
  REFUTED   a finite magma (table on Fin 2 or Fin 3) satisfying every law of S in which P and Q disagree,
            checked by the Lean kernel with `decide`; it also refutes every subset of S (monotonicity)
  UNKNOWN   neither found (bounded model search, bounded proof portfolio): never a negative result

and reports, all certified in one Lean module (compile + axioms + leanchecker replay):

  * inclusion-minimal sufficient sets: S ENTAILS and, for every φ ∈ S, S∖{φ} has a separating model
    (instance of `minimal_of_witnesses`, research/sota5/Relations.lean, restated in the module)
  * laws necessary within the family: Φ∖{φ} has a separating model, so every sufficient subset of Φ
    contains φ

Trust: the Python model search and the proof portfolio are untrusted proposers; the generated module is the
certificate. Semantics: entailment is proved in Lean over all Lean types (sound for set-theoretic
semantics); separation is witnessed by a concrete finite model (absolute). Minimality is relative to the
candidate family Φ only, and is inclusion-minimality, not minimum size. Minimal sets need not be unique.

    python -m proofscope.experimental.lawrel spec.json --out DIR
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import subprocess
from pathlib import Path

from ..toolchain import Toolchain

PROOF_PORTFOLIO = [
    "constructor <;> intro hpq <;> intros <;> grind",
    "constructor <;> intro hpq <;> intros <;> simp_all",
]


# ---------------------------------------------------------------- tiny equation language
def parse_term(s: str):
    s = s.replace(" ", "")
    pos = 0

    def atom():
        nonlocal pos
        if s[pos] == "(":
            pos += 1
            t = expr()
            assert s[pos] == ")", s
            pos += 1
            return t
        m = re.match(r"[a-z]", s[pos:])
        assert m, f"bad term {s!r} at {pos}"
        pos += 1
        return m.group(0)

    def expr():
        nonlocal pos
        t = atom()
        while pos < len(s) and s[pos] == "*":
            pos += 1
            t = ("*", t, atom())
        return t

    t = expr()
    assert pos == len(s), s
    return t


def parse_eq(s: str):
    l, r = s.split("=")
    return parse_term(l), parse_term(r)


def vars_of(t, acc=None):
    acc = [] if acc is None else acc
    if isinstance(t, str):
        if t not in acc:
            acc.append(t)
    else:
        vars_of(t[1], acc)
        vars_of(t[2], acc)
    return acc


def lean_term(t, op):
    return t if isinstance(t, str) else f"({op} {lean_term(t[1], op)} {lean_term(t[2], op)})"


def lean_eq(eq, op, ty):
    vs = vars_of(eq[0], vars_of(eq[1]))
    vs = sorted(set(vars_of(eq[0]) + vars_of(eq[1])))
    return f"∀ {' '.join(vs)} : {ty}, {lean_term(eq[0], op)} = {lean_term(eq[1], op)}"


def ev(t, tbl, n, env):
    if isinstance(t, str):
        return env[t]
    return tbl[ev(t[1], tbl, n, env) * n + ev(t[2], tbl, n, env)]


def holds(eq, tbl, n):
    vs = sorted(set(vars_of(eq[0]) + vars_of(eq[1])))
    for vals in itertools.product(range(n), repeat=len(vs)):
        env = dict(zip(vs, vals))
        if ev(eq[0], tbl, n, env) != ev(eq[1], tbl, n, env):
            return False
    return True


def find_model(laws, P, Q):
    """Smallest table (Fin 2 then Fin 3) satisfying all `laws` where P and Q disagree. Untrusted."""
    for n in (2, 3):
        for tbl in itertools.product(range(n), repeat=n * n):
            if all(holds(l, tbl, n) for l in laws) and holds(P, tbl, n) != holds(Q, tbl, n):
                return n, list(tbl)
    return None


# ---------------------------------------------------------------- Lean module generation
def module(spec, names, entails: dict, models: dict, minimal, necessary) -> str:
    laws = {k: parse_eq(v) for k, v in spec["laws"].items()}
    P, Q = parse_eq(spec["P"]), parse_eq(spec["Q"])
    ns = "LR_" + re.sub(r"[^A-Za-z0-9_]", "_", spec["id"])
    L = []
    L.append("set_option autoImplicit false\nset_option maxHeartbeats 400000\n")
    L.append(f"namespace {ns}\n")
    L.append("structure Magma where\n  α : Type\n  op : α → α → α\n")
    L.append("inductive Law where\n" + "".join(f"  | {k}\n" for k in names) + "  deriving DecidableEq\n")
    L.append("def sat (m : Magma) : Law → Prop\n" + "".join(
        f"  | .{k} => {lean_eq(laws[k], 'm.op', 'm.α')}\n" for k in names))
    L.append(f"def P (m : Magma) : Prop := {lean_eq(P, 'm.op', 'm.α')}")
    L.append(f"def Q (m : Magma) : Prop := {lean_eq(Q, 'm.op', 'm.α')}\n")
    L.append("def Suffices (S : List Law) : Prop := ∀ m : Magma, (∀ φ ∈ S, sat m φ) → (P m ↔ Q m)\n")
    L.append("""theorem minimal_of_witnesses (S : List Law)
    (wit : ∀ φ ∈ S, ∃ m, (∀ ψ ∈ S, ψ ≠ φ → sat m ψ) ∧ ¬ (P m ↔ Q m))
    (T : List Law) (hT : ∀ ψ ∈ T, ψ ∈ S) (φ : Law) (hφS : φ ∈ S) (hφT : φ ∉ T) : ¬ Suffices T := by
  obtain ⟨m, hm, hne⟩ := wit φ hφS
  intro h
  exact hne (h m (fun ψ hψ => hm ψ (hT ψ hψ) (fun e => hφT (e ▸ hψ))))

theorem necessary_of_witness (φ : Law) (m : Magma) (hm : ∀ ψ, ψ ≠ φ → sat m ψ) (hne : ¬ (P m ↔ Q m))
    (T : List Law) (hT : φ ∉ T) : ¬ Suffices T :=
  fun h => hne (h m (fun ψ hψ => hm ψ (fun e => hT (e ▸ hψ))))
""")
    # entailments
    for key, (S, tac) in entails.items():
        lst = "[" + ", ".join(f"Law.{k}" for k in S) + "]"
        hyps = "".join(f"  have h_{k} : sat m Law.{k} := hm _ (by simp)\n  simp only [sat] at h_{k}\n" for k in S)
        L.append(f"theorem suff_{key} : Suffices {lst} := by\n  intro m hm\n{hyps}  unfold P Q\n  {tac}\n")
    # models
    for key, (n, tbl, sat_laws) in models.items():
        vals = ", ".join(str(v) for v in tbl)
        L.append(f"def t_{key} (a b : Fin {n}) : Fin {n} := ([{vals}] : List (Fin {n})).getD (a.val * {n} + b.val) 0")
        L.append(f"def M_{key} : Magma := ⟨Fin {n}, t_{key}⟩")
        for k in sat_laws:
            L.append(f"theorem M_{key}_{k} : sat M_{key} Law.{k} := "
                     f"(by decide : {lean_eq(laws[k], f't_{key}', f'Fin {n}')})")
        L.append(f"theorem M_{key}_sep : ¬ (P M_{key} ↔ Q M_{key}) := "
                 f"(by decide : ¬ (({lean_eq(P, f't_{key}', f'Fin {n}')}) ↔ ({lean_eq(Q, f't_{key}', f'Fin {n}')})))\n")
    # minimality and necessity
    for S, keys in minimal:
        lst = "[" + ", ".join(f"Law.{k}" for k in S) + "]"
        branches = "\n".join(
            f"  · exact ⟨M_{keys[k]}, fun ψ hψ hne => by cases ψ <;> simp_all <;> "
            + "first " + " ".join(f"| exact M_{keys[k]}_{j}" for j in S if j != k) + (" | skip" if len(S) == 1 else "")
            + f", M_{keys[k]}_sep⟩" for k in S)
        L.append(f"theorem minimal_{'_'.join(S)} : Suffices {lst} ∧ ∀ T : List Law, (∀ ψ ∈ T, ψ ∈ {lst}) → "
                 f"∀ φ ∈ {lst}, φ ∉ T → ¬ Suffices T := by\n"
                 f"  refine ⟨suff_{'_'.join(S)}, minimal_of_witnesses {lst} ?_⟩\n"
                 f"  intro φ hφ\n  simp only [List.mem_cons, List.not_mem_nil, or_false] at hφ\n"
                 f"  rcases hφ with " + " | ".join("rfl" for _ in S) + "\n" + branches + "\n")
    for k, key in necessary.items():
        others = [j for j in names if j != k]
        L.append(f"theorem necessary_{k} : ∀ T : List Law, Law.{k} ∉ T → ¬ Suffices T :=\n"
                 f"  necessary_of_witness Law.{k} M_{key} (fun ψ hne => by cases ψ <;> simp_all <;> "
                 + "first " + " ".join(f"| exact M_{key}_{j}" for j in others) + " | skip) M_{key}_sep\n".replace("M_{key}", f"M_{key}"))
    L.append(f"end {ns}\n")
    decls = [f"suff_{k}" for k in entails] + [f"M_{k}_sep" for k in models] + \
            [f"minimal_{'_'.join(S)}" for S, _ in minimal] + [f"necessary_{k}" for k in necessary]
    L += [f"#print axioms {ns}.{d}" for d in decls]
    return "\n".join(L) + "\n", ns, decls


def run(spec: dict, out: Path, tc: Toolchain) -> dict:
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    names = list(spec["laws"])
    laws = {k: parse_eq(v) for k, v in spec["laws"].items()}
    P, Q = parse_eq(spec["P"]), parse_eq(spec["Q"])
    subsets = [list(c) for r in range(len(names) + 1) for c in itertools.combinations(names, r)]
    key = lambda S: "_".join(S) if S else "none"
    status, models, model_of = {}, {}, {}
    # 1. untrusted model search, largest subsets first (a model of S refutes every subset of S)
    for S in sorted(subsets, key=len, reverse=True):
        if key(S) in model_of:
            continue
        m = find_model([laws[k] for k in S], P, Q)
        if m:
            n, tbl = m
            sat_laws = [k for k in names if holds(laws[k], tbl, n)]
            mk = f"m{len(models)}"
            models[mk] = (n, tbl, sat_laws)
            for T in subsets:
                if set(T) <= set(sat_laws) and key(T) not in model_of:
                    model_of[key(T)] = mk
    # 2. proof attempts for subsets with no separating model (smallest first), each probed separately
    entails = {}
    for S in subsets:
        if key(S) in model_of:
            status[key(S)] = {"status": "REFUTED", "model": model_of[key(S)]}
            continue
        if any(set(T) <= set(S) for T in [entails[k][0] for k in entails]):
            sup = next(k for k in entails if set(entails[k][0]) <= set(S))
            status[key(S)] = {"status": "ENTAILS_BY_MONOTONICITY", "from": sup}
            continue
        ok = None
        for tac in PROOF_PORTFOLIO:
            src, _, _ = module(spec, names, {key(S): (S, tac)}, {}, [], {})
            f = out / f"probe_{key(S)}.lean"
            f.write_text(src)
            r = subprocess.run([tc.lean, str(f)], capture_output=True, text=True, timeout=600)
            if r.returncode == 0 and ": error" not in r.stdout + r.stderr:
                ok = tac
                break
        if ok:
            entails[key(S)] = (S, ok)
            status[key(S)] = {"status": "ENTAILS", "tactic": ok}
        else:
            status[key(S)] = {"status": "UNKNOWN"}
    # 3. certified structure: minimal sufficient sets and necessary laws
    minimal = []
    for k, (S, _) in entails.items():
        if S and all(key([j for j in S if j != x]) in model_of for x in S):
            minimal.append((S, {x: model_of[key([j for j in S if j != x])] for x in S}))
        elif not S:
            minimal.append((S, {}))
    necessary = {x: model_of[key([j for j in names if j != x])] for x in names
                 if key([j for j in names if j != x]) in model_of}
    minimal = [(S, ks) for S, ks in minimal if S]
    src, ns, decls = module(spec, names, entails, models, minimal, necessary)
    cert = out / f"{ns}.lean"
    cert.write_text(src)
    olean = out / "build" / f"{ns}.olean"
    olean.parent.mkdir(parents=True, exist_ok=True)
    c = subprocess.run([tc.lean, "-R", str(out), "-o", str(olean), str(cert)], capture_output=True, text=True, timeout=900)
    log = c.stdout + c.stderr
    axioms = {}
    for d in decls:
        m = re.search(rf"'{re.escape(ns)}\.{d}' (does not depend on any axioms|depends on axioms: \[([^\]]*)\])", log)
        axioms[d] = None if not m else ([] if m.group(2) is None else [a.strip() for a in m.group(2).split(",")])
    rp = subprocess.run([tc.leanchecker, ns], capture_output=True, text=True, timeout=900, cwd=str(olean.parent),
                        env={**__import__("os").environ, "LEAN_PATH": str(olean.parent)})
    std = {"propext", "Classical.choice", "Quot.sound"}
    certified = c.returncode == 0 and ": error" not in log and rp.returncode == 0 and \
        all(a is not None and set(a) <= std for a in axioms.values())
    res = {"id": spec["id"], "laws": spec["laws"], "P": spec["P"], "Q": spec["Q"], "subsets": status,
           "models": {k: {"size": n, "table": t, "satisfies": s} for k, (n, t, s) in models.items()},
           "minimal_sufficient": [S for S, _ in minimal], "necessary_in_family": sorted(necessary),
           "certified": certified, "axioms": axioms, "compile_rc": c.returncode, "leanchecker_rc": rp.returncode,
           "compile_errors": [l for l in log.splitlines() if not l.startswith("'")][:10], "certificate": str(cert),
           "scope": "relative to the declared candidate family and the magma signature; inclusion-minimal, not "
                    "minimum; UNKNOWN is not a negative result"}
    (out / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m proofscope.experimental.lawrel")
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    res = run(json.loads(a.spec.read_text()), a.out, Toolchain.find())
    print(json.dumps({k: res[k] for k in ("id", "minimal_sufficient", "necessary_in_family", "certified")}, ensure_ascii=False))
    for k, v in res["subsets"].items():
        print(f"  {{{k}}}: {v['status']}")
    return 0 if res["certified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
