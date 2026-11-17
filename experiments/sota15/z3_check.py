"""Independent comparison with Z3: is `reference → formal` valid for every interpretation of the
abstracted symbol (uninterpreted predicate or function over the naturals)?  `unsat` of
`R ∧ ¬F` means ENTAILS, `sat` means SEPARATED, anything else UNKNOWN."""
import json
import sys
from pathlib import Path

import z3

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from proofscope.scope_expr import parse  # noqa: E402

TIMEOUT_MS = 8000


def enc(a, env):
    k = a[0]
    if k == "num":
        return z3.IntVal(a[1])
    if k == "var":
        return env[a[1]]
    if k == "true":
        return z3.BoolVal(True)
    if k == "false":
        return z3.BoolVal(False)
    if k == "bin":
        x, y = enc(a[2], env), enc(a[3], env)
        if a[1] == "^" or (a[1] == "app"):
            raise ValueError("opaque")
        return {"+": x + y, "*": x * y, "/": x / y, "%": x % y}[a[1]]
    if k == "app":
        return env[a[1]](*[enc(x, env) for x in a[2]])
    if k == "cmp":
        x, y = enc(a[2], env), enc(a[3], env)
        return {"=": x == y, "≠": x != y, "<": x < y, "≤": x <= y, ">": x > y, "≥": x >= y}[a[1]]
    if k == "and":
        return z3.And(enc(a[1], env), enc(a[2], env))
    if k == "or":
        return z3.Or(enc(a[1], env), enc(a[2], env))
    if k == "imp":
        return z3.Implies(enc(a[1], env), enc(a[2], env))
    if k == "not":
        return z3.Not(enc(a[1], env))
    raise ValueError(k)


def _forall(vs, body):
    return z3.ForAll(vs, body) if vs else body


def horn_side(clauses, syms):
    out = []
    for c in clauses:
        vs = [z3.Int(n) for n, _ in c.get("vars", [])]
        env = {**syms, **{str(v): v for v in vs}}
        at = lambda a: syms[a[0]](*[enc(parse(str(t)), env) for t in a[1]])
        hyp = [v >= 0 for v in vs]
        hyp += [v < enc(parse(str(b)), env) for v, (_, b) in zip(vs, c.get("vars", [])) if b is not None]
        hyp += [enc(parse(c.get("guard", "True")), env)] + [at(a) for a in c.get("prems", [])]
        hyp += [z3.Implies(z3.And([at(a) for a in l["prems"]]), at(l["concl"])) for l in c.get("locals", [])]
        out.append(_forall(vs, z3.Implies(z3.And(hyp), at(c["concl"]))))
    return z3.And(out) if out else z3.BoolVal(True)


def func_side(c, f):
    n = z3.Int(c["var"])
    w = f(enc(parse(c["arg"]), {c["var"]: n}))
    return z3.ForAll([n], z3.Implies(z3.And(n >= 0, enc(parse(c.get("guard", "True")), {c["var"]: n})),
                                     enc(parse(c["rel"]), {c["var"]: n, "w": w})))


def check(a, b, extra=()):
    s = z3.Solver()
    s.set("timeout", TIMEOUT_MS)
    s.add(*extra)
    s.add(a, z3.Not(b))
    r = s.check()
    return {"unsat": "ENTAILS", "sat": "SEPARATED"}.get(str(r), "UNKNOWN")


def directions(spec):
    if spec["kind"] == "horn":
        syms = {s: z3.Function(s, *([z3.IntSort()] * k), z3.BoolSort()) for s, k in spec["symbols"].items()}
        R, F, extra = horn_side(spec["reference"], syms), horn_side(spec["formal"], syms), ()
    else:
        f = z3.Function("f", z3.IntSort(), z3.IntSort())
        z = z3.Int("z")
        R, F = func_side(spec["reference"], f), func_side(spec["formal"], f)
        extra = (z3.ForAll([z], f(z) >= 0),)
    return {"fwd": check(R, F, extra), "bwd": check(F, R, extra)}


def claimdelta_directions(spec):
    """Schematic comparison of a ClaimDelta case with its single opaque binary symbol uninterpreted."""
    g = z3.Function("g", z3.IntSort(), z3.IntSort(), z3.IntSort())
    n = z3.Int("n")

    def e(a, env):
        if a[0] == "bin" and a[1] == "^":
            return g(e(a[2], env), e(a[3], env))
        if a[0] == "app":
            return g(*[e(x, env) for x in a[2]])
        if a[0] in ("bin", "cmp"):
            x, y = e(a[2], env), e(a[3], env)
            return {"+": lambda: x + y, "*": lambda: x * y, "/": lambda: x / y, "%": lambda: x % y, "=": lambda: x == y,
                    "≠": lambda: x != y, "<": lambda: x < y, "≤": lambda: x <= y, ">": lambda: x > y, "≥": lambda: x >= y}[a[1]]()
        if a[0] in ("and", "or"):
            return (z3.And if a[0] == "and" else z3.Or)(e(a[1], env), e(a[2], env))
        if a[0] == "not":
            return z3.Not(e(a[1], env))
        return enc(a, env)
    side = lambda h, c: z3.ForAll([n], z3.Implies(z3.And(n >= 0, e(parse(spec[h]), {"n": n})), e(parse(spec[c]), {"n": n})))
    R, F = side("ref_hyp", "ref_concl"), side("lean_hyp", "lean_concl")
    a, b = z3.Ints("a b")
    extra = (z3.ForAll([a, b], g(a, b) >= 0),)
    return {"fwd": check(R, F, extra), "bwd": check(F, R, extra)}


if __name__ == "__main__":
    for p in sys.argv[1:]:
        s = json.loads(Path(p).read_text())
        print(p, claimdelta_directions(s) if "binders" in s else directions(s))
