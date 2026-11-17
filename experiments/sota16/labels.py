"""Independent labels for the SOTA-16 cases (no use of Theorem B, of Lean, or of the engine).

For 'does the reference entail the formal claim for every f : Nat → Nat?' a direction is labelled

* ENTAILS   when Z3 or cvc5 refutes `R(f) ∧ ¬F(f)` with `f` an uninterpreted function;
* SEPARATED when an explicit function `f z = if z = z0 then v else a * q(z) + b` is found for which
            Z3 proves, as pure Presburger sentences without uninterpreted symbols, that the
            reference holds and the formal claim fails (or when a solver returns a model with
            the uninterpreted `f`);
* otherwise it has no independent label, and is reported as such.

Shares only the expression parser with the engine.
"""
import json
import sys
from pathlib import Path

import z3

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from proofscope.scope_expr import parse  # noqa: E402

try:
    import cvc5.pythonic as cv
except Exception:  # noqa: BLE001
    cv = None

UF_MS, TPL_MS = 3000, 2000


def enc(m, a, env):
    k = a[0]
    if k == "num":
        return m.IntVal(a[1])
    if k == "var":
        return env[a[1]]
    if k == "true":
        return m.BoolVal(True)
    if k == "false":
        return m.BoolVal(False)
    if k == "bin":
        x, y = enc(m, a[2], env), enc(m, a[3], env)
        op = a[1]
        if op == "+":
            return x + y
        if op == "*":
            return x * y
        if op == "-":
            return m.If(x >= y, x - y, m.IntVal(0))
        if op == "/":
            return x / y
        if op == "%":
            return x % y
        raise ValueError(op)
    if k == "cmp":
        x, y = enc(m, a[2], env), enc(m, a[3], env)
        return {"=": x == y, "≠": x != y, "<": x < y, "≤": x <= y, ">": x > y, "≥": x >= y}[a[1]]
    if k == "and":
        return m.And(enc(m, a[1], env), enc(m, a[2], env))
    if k == "or":
        return m.Or(enc(m, a[1], env), enc(m, a[2], env))
    if k == "not":
        return m.Not(enc(m, a[1], env))
    if k == "imp":
        return m.Implies(enc(m, a[1], env), enc(m, a[2], env))
    raise ValueError(k)


def claim(m, c, f, name="n"):
    n = m.Int(name)
    body = m.Implies(m.And(n >= 0, enc(m, parse(c.get("guard", "True")), {c["var"]: n})),
                     enc(m, parse(c["rel"]), {c["var"]: n, "w": f(enc(m, parse(c["arg"]), {c["var"]: n}))}))
    return n, body


def uf(m, R, F, ms):
    f = m.Function("f", m.IntSort(), m.IntSort())
    z = m.Int("z")
    n1, r = claim(m, R, f, "n1")
    n2, g = claim(m, F, f, "n2")
    s = m.Solver()
    s.set("timeout", ms) if m is z3 else s.setOption("tlimit-per", str(ms))
    s.add(m.ForAll([z], f(z) >= 0), m.ForAll([n1], r), m.Not(m.ForAll([n2], g)))
    return str(s.check())


def template(R, F):
    """Explicit separating function, checked by Z3 without uninterpreted symbols."""
    from proofscope.scopeelim import affine
    qs = [lambda z: z, lambda z: z / 2, lambda z: z / 3, lambda z: z3.IntVal(0)]
    ka = affine(parse(R["arg"]), R["var"])
    if ka and ka[0] >= 1:
        k, c = ka
        qs.insert(0, lambda z, k=k, c=c: z3.If(z >= c, (z - c) / k, 0))
    b, z0, v = z3.Ints("b z0 v")
    for qi, q in enumerate(qs):
        for a in (1, 0, 2, 3):
            f = lambda z, q=q, a=a: z3.If(z == z0, v, a * q(z) + b)
            n1, r = claim(z3, R, f, "n1")
            n2, g = claim(z3, F, f, "n2")
            s = z3.Solver()
            s.set("timeout", TPL_MS)
            s.add(b >= 0, z0 >= 0, v >= 0, z3.ForAll([n1], r), z3.Not(z3.ForAll([n2], g)))
            if s.check() == z3.sat:
                mdl = s.model()
                return {"q": qi, "a": a, **{str(x): mdl.eval(x, model_completion=True).as_long() for x in (b, z0, v)}}
    return None


def label(R, F):
    out = {}
    out["z3"] = uf(z3, R, F, UF_MS)
    if out["z3"] == "unsat":
        return {"label": "ENTAILS", "by": "z3", **out}
    if out["z3"] == "sat":
        return {"label": "SEPARATED", "by": "z3-model", **out}
    if cv is not None:
        try:
            out["cvc5"] = uf(cv, R, F, UF_MS)
        except Exception as e:  # noqa: BLE001
            out["cvc5"] = "error: " + str(e)[:60]
        if out["cvc5"] == "unsat":
            return {"label": "ENTAILS", "by": "cvc5", **out}
    w = template(R, F)
    if w:
        return {"label": "SEPARATED", "by": "explicit-function", "witness": w, **out}
    return {"label": None, **out}


def main(out: Path):
    rows = {}
    for p in sorted((HERE / "cases" / "func_lin").glob("*.json")):
        s = json.loads(p.read_text())
        rows[s["id"]] = {"fwd": label(s["reference"], s["formal"]), "bwd": label(s["formal"], s["reference"])}
        print(s["id"], rows[s["id"]]["fwd"]["label"], rows[s["id"]]["bwd"]["label"], flush=True)
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    lab = [d["label"] for r in rows.values() for d in r.values()]
    print("labelled", sum(x is not None for x in lab), "of", len(lab))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
