"""Oracle-labelled benchmark generator (v0.6).

Seed statements ("references") are mutated by operators matching the error families; every case is labelled by a
Python oracle that re-implements Lean's ℕ semantics (truncated subtraction, n / 0 = 0, n % 0 = n, 0 ∣ a ↔ a = 0,
bounded quantifiers) and evaluates every obligation exhaustively on the grid n, m ∈ [0, G).

What the labels mean:
  * existential facts (a gap witness, a strict witness, inhabitation) found on the grid are certain;
  * universal facts (covers, back, vacuity) are only grid-verified, so labels that depend on them
    (EQUIVALENT, COVERS, LEAN_STRONGER, VACUOUS) are probable, not proved.
The label rule is the engine's published classification table applied to the oracle facts; the oracle never
calls Lean or the engine's proof search. Cases were generated after the engine freeze recorded in
ENGINE_FREEZE.txt and run once.
"""

from __future__ import annotations

import itertools
import json
import random
import sys
from pathlib import Path

G = 24          # oracle grid
BOX = 12        # finite search box handed to the engine (independent of the oracle grid)


# ---------------------------------------------------------------- tiny expression language
def V(x): return ("var", x)
def L(k): return ("lit", k)
def add(a, b): return ("add", a, b)
def sub(a, b): return ("sub", a, b)
def mul(a, b): return ("mul", a, b)
def div(a, b): return ("div", a, b)
def mod(a, b): return ("mod", a, b)
def pw(a, k): return ("pow", a, k)
def le(a, b): return ("le", a, b)
def lt(a, b): return ("lt", a, b)
def eq(a, b): return ("eq", a, b)
def ne(a, b): return ("ne", a, b)
def dvd(a, b): return ("dvd", a, b)
def AND(p, q): return ("and", p, q)
def OR(p, q): return ("or", p, q)
def NOT(p): return ("not", p)
TRUE = ("true",)
def fa_lt(x, b, p): return ("fa_lt", x, b, p)   # ∀ x, x < b → p
def ex_lt(x, b, p): return ("ex_lt", x, b, p)   # ∃ x, x < b ∧ p

N, M = V("n"), V("m")


def lean(e) -> str:
    t = e[0]
    if t == "var": return e[1]
    if t == "lit": return str(e[1])
    ops = {"add": "+", "sub": "-", "mul": "*", "div": "/", "mod": "%", "le": "≤", "lt": "<", "eq": "=",
           "ne": "≠", "dvd": "∣", "and": "∧", "or": "∨"}
    if t in ops: return f"({lean(e[1])} {ops[t]} {lean(e[2])})"
    if t == "pow": return f"({lean(e[1])} ^ {lean(e[2])})"
    if t == "not": return f"(¬ {lean(e[1])})"
    if t == "true": return "True"
    if t == "fa_lt": return f"(∀ {e[1]} : Nat, {e[1]} < {lean(e[2])} → {lean(e[3])})"
    if t == "ex_lt": return f"(∃ {e[1]} : Nat, {e[1]} < {lean(e[2])} ∧ {lean(e[3])})"
    raise ValueError(t)


def ev(e, env):
    t = e[0]
    if t == "var": return env[e[1]]
    if t == "lit": return e[1]
    if t == "add": return ev(e[1], env) + ev(e[2], env)
    if t == "sub": return max(0, ev(e[1], env) - ev(e[2], env))
    if t == "mul": return ev(e[1], env) * ev(e[2], env)
    if t == "div":
        b = ev(e[2], env); return 0 if b == 0 else ev(e[1], env) // b
    if t == "mod":
        b = ev(e[2], env); a = ev(e[1], env); return a if b == 0 else a % b
    if t == "pow": return ev(e[1], env) ** ev(e[2], env)
    if t == "le": return ev(e[1], env) <= ev(e[2], env)
    if t == "lt": return ev(e[1], env) < ev(e[2], env)
    if t == "eq": return ev(e[1], env) == ev(e[2], env)
    if t == "ne": return ev(e[1], env) != ev(e[2], env)
    if t == "dvd":
        a, b = ev(e[1], env), ev(e[2], env); return b == 0 if a == 0 else b % a == 0
    if t == "and": return ev(e[1], env) and ev(e[2], env)
    if t == "or": return ev(e[1], env) or ev(e[2], env)
    if t == "not": return not ev(e[1], env)
    if t == "true": return True
    if t == "fa_lt": return all(ev(e[3], {**env, e[1]: k}) for k in range(ev(e[2], env)))
    if t == "ex_lt": return any(ev(e[3], {**env, e[1]: k}) for k in range(ev(e[2], env)))
    raise ValueError(t)


def lits(e):
    if e[0] == "lit": yield e
    for x in e[1:]:
        if isinstance(x, tuple): yield from lits(x)


def replace_first_lit(e, f, done=None):
    done = done if done is not None else [False]
    if e[0] == "lit" and not done[0]:
        done[0] = True
        return ("lit", f(e[1]))
    return tuple(replace_first_lit(x, f, done) if isinstance(x, tuple) else x for x in e)


def flip_first_ineq(e, done=None):
    done = done if done is not None else [False]
    if e[0] in ("le", "lt") and not done[0]:
        done[0] = True
        return ("lt" if e[0] == "le" else "le", e[1], e[2])
    return tuple(flip_first_ineq(x, done) if isinstance(x, tuple) else x for x in e)


def swap_first_ineq(e, done=None):
    done = done if done is not None else [False]
    if e[0] in ("le", "lt") and not done[0]:
        done[0] = True
        return (e[0], e[2], e[1])
    return tuple(swap_first_ineq(x, done) if isinstance(x, tuple) else x for x in e)


# ---------------------------------------------------------------- seeds (references), by area
POS_M = lt(L(0), M)
SEEDS = [
    # area, id, binders, H, C
    ("order", "s_le_add", ["n", "m"], TRUE, le(N, add(N, M))),
    ("order", "s_sub_add", ["n", "m"], le(M, N), eq(add(sub(N, M), M), N)),
    ("order", "s_lt_trans", ["n", "m"], AND(lt(N, M), lt(M, L(10))), lt(N, L(10))),
    ("order", "s_max_like", ["n", "m"], le(N, M), le(sub(N, M), L(0))),
    ("multiplication", "s_mul_mono", ["n", "m"], AND(le(L(1), M), le(L(1), N)), le(N, mul(N, M))),
    ("multiplication", "s_sq_ge", ["n"], le(L(1), N), le(N, mul(N, N))),
    ("multiplication", "s_two_n", ["n"], le(L(2), N), le(add(N, L(2)), mul(L(2), N))),
    ("multiplication", "s_sq_gap", ["n"], le(L(3), N), lt(add(mul(L(2), N), L(1)), mul(N, N))),
    ("division", "s_div_le", ["n", "m"], POS_M, le(div(N, M), N)),
    ("division", "s_div_mul_le", ["n", "m"], POS_M, le(mul(div(N, M), M), N)),
    ("division", "s_div_lt", ["n", "m"], AND(lt(L(1), M), lt(L(0), N)), lt(div(N, M), N)),
    ("modular", "s_mod_lt", ["n", "m"], POS_M, lt(mod(N, M), M)),
    ("modular", "s_mod_le", ["n", "m"], TRUE, le(mod(N, M), N)),
    ("modular", "s_mod_two", ["n"], TRUE, OR(eq(mod(N, L(2)), L(0)), eq(mod(N, L(2)), L(1)))),
    ("modular", "s_div_mod", ["n", "m"], POS_M, eq(add(mul(div(N, M), M), mod(N, M)), N)),
    ("divisibility", "s_dvd_mul", ["n", "m"], TRUE, dvd(N, mul(N, M))),
    ("divisibility", "s_dvd_even", ["n"], dvd(L(4), N), dvd(L(2), N)),
    ("divisibility", "s_dvd_mod", ["n"], eq(mod(N, L(3)), L(0)), dvd(L(3), N)),
    ("powers", "s_pow_lt", ["n"], le(L(1), N), lt(N, pw(L(2), N))),
    ("powers", "s_pow_sq", ["n"], le(L(4), N), le(mul(N, N), pw(L(2), N))),
    ("bounded quantifiers", "s_all_below", ["n"], lt(L(0), N), fa_lt("k", N, le(V("k"), sub(N, L(1))))),
    ("bounded quantifiers", "s_exists_below", ["n"], lt(L(0), N), ex_lt("k", N, eq(add(V("k"), L(1)), N))),
    ("bounded quantifiers", "s_forall_exists", ["n"], le(L(2), N), fa_lt("k", N, ex_lt("j", N, ne(V("j"), V("k"))))),
    ("bounded quantifiers", "s_exists_forall", ["n"], lt(L(0), N), ex_lt("j", N, fa_lt("k", N, le(V("k"), V("j"))))),
]


def mutations(H, C, binders):
    """Yield (family, H_lean, C_lean). Each operator is generic; not every operator applies to every seed."""
    if H[0] == "and":
        yield "missing hypothesis", H[2], C
        yield "missing hypothesis", H[1], C
    elif H != TRUE:
        yield "missing hypothesis", TRUE, C
    pick = sum(map(ord, lean(C))) % 4  # deterministic (Python's str hash is randomized per process)
    extra = [le(L(2), N), eq(mod(N, L(2)), L(0)), lt(N, L(10))] + ([lt(L(0), M)] if "m" in binders else [])
    yield "extra hypothesis", (extra[pick % len(extra)] if H == TRUE else AND(H, extra[pick % len(extra)])), C
    if any(True for _ in lits(H)):
        yield "incorrect constant (hypothesis)", replace_first_lit(H, lambda k: k + 1), C
    if any(True for _ in lits(C)):
        yield "incorrect constant (conclusion)", H, replace_first_lit(C, lambda k: k + 1)
    if C[0] in ("le", "lt") or "'le'" in repr(C) or "'lt'" in repr(C):
        yield "strict vs weak inequality", H, flip_first_ineq(C)
        yield "reversed inequality", H, swap_first_ineq(C)
    yield "vacuous hypotheses", AND(H, lt(N, L(0))) if H != TRUE else lt(N, L(0)), C
    yield "weakened conclusion", H, OR(C, eq(N, L(3)))
    if C[0] == "fa_lt":
        yield "quantifier swap", H, ("ex_lt", C[3][1], C[3][2], ("fa_lt", C[1], C[2], C[3][3])) if C[3][0] == "ex_lt" else C
        yield "quantifier bound", H, ("fa_lt", C[1], add(C[2], L(1)), C[3])
    if C[0] == "ex_lt":
        if C[3][0] == "fa_lt":
            yield "quantifier swap", H, ("fa_lt", C[3][1], C[3][2], ("ex_lt", C[1], C[2], C[3][3]))
        yield "quantifier bound", H, ("ex_lt", C[1], sub(C[2], L(1)), C[3])
    # harmless rewrites of the hypothesis
    if H == POS_M:
        yield "harmless rewrite", ne(M, L(0)), C
    if H == le(L(1), N):
        yield "harmless rewrite", lt(L(0), N), C
    if H[0] == "le" and H != le(L(1), N):
        yield "harmless rewrite", NOT(lt(H[2], H[1])), C
    if H[0] == "dvd" and H[1][0] == "lit":
        yield "harmless rewrite", eq(mod(H[2], H[1]), L(0)), C


def oracle(binders, HL, CL, HR, CR):
    pts = [dict(zip(binders, v)) for v in itertools.product(range(G), repeat=len(binders))]
    f = {}
    f["app_gap"] = any(ev(HR, e) and not ev(HL, e) for e in pts)
    f["concl_gap"] = any(ev(HR, e) and ev(HL, e) and ev(CL, e) and not ev(CR, e) for e in pts)
    f["strict_hyp"] = any(ev(HL, e) and not ev(HR, e) for e in pts)
    f["strict_concl"] = any(ev(HL, e) and ev(HR, e) and ev(CR, e) and not ev(CL, e) for e in pts)
    f["inhabited"] = any(ev(HL, e) for e in pts)
    f["hyp_cover"] = not f["app_gap"]
    f["concl_cover"] = all((not ev(HR, e)) or (not ev(CL, e)) or ev(CR, e) for e in pts)
    f["hyp_back"] = not f["strict_hyp"]
    f["concl_back"] = all((not ev(HL, e)) or (not ev(CR, e)) or ev(CL, e) for e in pts)
    f["vacuous"] = not f["inhabited"]
    return f


def label(f):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from proofscope.compare import classify  # the published label table, not proof search
    facts = {k for k, v in f.items() if v}
    if f["hyp_cover"] and f["concl_cover"]:
        facts.add("transfer")
    return classify(facts)


def main():
    out = Path(__file__).resolve().parent / "heldout_oracle"
    out.mkdir(exist_ok=True)
    n = 0
    seen = set()
    for area, sid, binders, HR, CR in SEEDS:
        for fam, HL, CL in mutations(HR, CR, binders):
            key = (lean(HL), lean(CL), lean(HR), lean(CR))
            if key in seen or (HL == HR and CL == CR):
                continue
            seen.add(key)
            f = oracle(binders, HL, CL, HR, CR)
            lab = label(f)
            n += 1
            cid = f"o{n:03d}_{sid}"
            (out / f"{cid}.json").write_text(json.dumps({
                "id": cid, "family": fam, "area": area, "split": "heldout_oracle",
                "binders": [[b, "Nat"] for b in binders],
                "lean_hyp": lean(HL), "lean_concl": lean(CL), "ref_hyp": lean(HR), "ref_concl": lean(CR),
                "bounds": {b: BOX for b in binders}, "expected": lab,
                "fidelity_failure": lab in ("APPLICABILITY_GAP", "CONCLUSION_GAP", "VACUOUS"),
                "label_source": f"python oracle, Lean ℕ semantics, exhaustive on [0,{G})^{len(binders)}",
                "label_certainty": "certain" if lab in ("APPLICABILITY_GAP", "CONCLUSION_GAP") else "grid-verified",
                "oracle_facts": f, "tactics": {}}, indent=2, ensure_ascii=False))
    print(n, "oracle-labelled cases")


if __name__ == "__main__":
    main()
