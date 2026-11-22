"""Independent labels for the SOTA-17 cases. No use of the engine, of Lean, of the pairwise
criterion, or of the theorems in MultiOcc.lean. Shares only the expression parser with the engine.

For 'does H entail C for every f : Nat → Nat?' a direction is labelled

* ENTAILS    when Z3 or cvc5 refutes `H(f) ∧ ¬C(f)` with `f` an uninterpreted function;
* SEPARATED  (a) prefix model: integers `v_0 .. v_N` are found (Z3, no uninterpreted symbol) such that
             every instance of H that only reads arguments `≤ N` holds, and C fails at an instance
             that only reads arguments `≤ N`; the prefix extends to a total model of H by an
             elementary argument that depends on the family recorded by the generator
             (step / lower: continue with increment `a`; pointwise: every later argument has an
             admissible value, checked as a Presburger sentence);
             (b) explicit function `f z = α * z + β`: Z3 proves, without uninterpreted symbols,
             that H holds and C fails;
* otherwise the direction has no label.
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

UF_MS, PRE_MS = 4000, 4000


def enc(m, a, env, app):
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
        x, y = enc(m, a[2], env, app), enc(m, a[3], env, app)
        op = a[1]
        if op == "+":
            return x + y
        if op == "*":
            return x * y
        if op == "-":
            return m.If(x >= y, x - y, m.IntVal(0))
        if op in "/%" and a[3][0] == "num" and a[3][1] > 0:
            return x / y if op == "/" else x % y
        raise ValueError(op)
    if k == "app":
        if a[1] != "f" or len(a[2]) != 1:
            raise ValueError("app")
        return app(a[2][0], env)
    if k == "cmp":
        x, y = enc(m, a[2], env, app), enc(m, a[3], env, app)
        return {"=": x == y, "≠": x != y, "<": x < y, "≤": x <= y, ">": x > y, "≥": x >= y}[a[1]]
    if k == "and":
        return m.And(enc(m, a[1], env, app), enc(m, a[2], env, app))
    if k == "or":
        return m.Or(enc(m, a[1], env, app), enc(m, a[2], env, app))
    if k == "imp":
        return m.Implies(enc(m, a[1], env, app), enc(m, a[2], env, app))
    if k == "not":
        return m.Not(enc(m, a[1], env, app))
    raise ValueError(k)


def claim(d):
    return d.get("var", "n"), parse(d.get("guard", "True")), parse(d["body"])


def uf_refute(m, H, C, ms):
    """unsat of H(f) ∧ ¬C(f)."""
    f = m.Function("f", m.IntSort(), m.IntSort())
    x, n = m.Ints("x n")
    app = lambda arg, env: f(enc(m, arg, env, app))
    hv, hg, hb = H
    cv_, cg, cb = C
    s = m.Solver()
    try:
        s.set("timeout", ms) if m is z3 else s.set("tlimit-per", ms)
    except Exception:  # noqa: BLE001
        pass
    s.add(m.ForAll([x], m.Implies(x >= 0, f(x) >= 0)))
    s.add(m.ForAll([x], m.Implies(m.And(x >= 0, enc(m, hg, {hv: x}, app)), enc(m, hb, {hv: x}, app))))
    s.add(n >= 0, enc(m, cg, {cv_: n}, app), m.Not(enc(m, cb, {cv_: n}, app)))
    return str(s.check()) == "unsat"


def _sites(a, acc):
    k = a[0]
    if k == "app":
        acc.append(a[2][0])
        _sites(a[2][0], acc)
    elif k in ("bin", "cmp"):
        _sites(a[2], acc), _sites(a[3], acc)
    elif k == "not":
        _sites(a[1], acc)
    elif k in ("and", "or", "imp"):
        _sites(a[1], acc), _sites(a[2], acc)
    return acc


def _ground(a, var, val):
    """Value of a symbol-free term at var = val (Lean Nat semantics)."""
    k = a[0]
    if k == "num":
        return a[1]
    if k == "var":
        return val
    if k == "bin":
        x, y = _ground(a[2], var, val), _ground(a[3], var, val)
        return {"+": x + y, "*": x * y, "-": max(x - y, 0), "/": x // y if y else 0, "%": x % y if y else x}[a[1]]
    raise ValueError(k)


def _extends(family, meta, H):
    """Is every finite prefix that satisfies the readable instances of H extendable? Elementary
    argument per family; for `pointwise` it needs a Presburger check."""
    hv, hg, hb = H
    if family in ("step", "lower"):
        a, b = meta["a"], meta["b"]
        u, v = z3.Ints("u v")
        app = lambda arg, env: v if arg != ("var", hv) else u       # sites are n and n + 1
        tmpl = z3.And(u + a <= v, v <= u + b) if b is not None else (u + a <= v)
        s = z3.Solver()
        s.set("timeout", PRE_MS)
        s.add(u >= 0, v >= 0, z3.Int("n_") >= 0,
              z3.Not(z3.Implies(enc(z3, hg, {hv: z3.Int("n_")}, app), enc(z3, hb, {hv: z3.Int("n_")}, app)) == tmpl))
        return s.check() == z3.unsat and (b is None or a <= b)
    if family == "pointwise":
        x, w = z3.Ints("x w")
        app = lambda arg, env: w
        s = z3.Solver()
        s.set("timeout", PRE_MS)
        s.add(x >= 0, enc(z3, hg, {hv: x}, app),
              z3.ForAll([w], z3.Implies(w >= 0, z3.Not(enc(z3, hb, {hv: x}, app)))))
        return s.check() == z3.unsat
    return False


def prefix_model(family, meta, H, C, nmax=14):
    hv, hg, hb = H
    cv_, cg, cb = C
    if not _extends(family, meta, H):
        return None
    hs, cs = _sites(hb, []), _sites(cb, [])
    for n0 in range(nmax + 1):
        try:
            N = max([_ground(s, cv_, n0) for s in cs] + [0])
        except ValueError:
            return None
        if N > 60:
            continue
        vs = [z3.Int(f"v{i}") for i in range(N + 1)]
        app_at = lambda val: (lambda arg, env: vs[_ground(arg, None, val)])
        s = z3.Solver()
        s.set("timeout", PRE_MS)
        s.add(*[v >= 0 for v in vs])
        for x in range(N + 1):
            if all(_ground(t, hv, x) <= N for t in hs):
                s.add(z3.Implies(enc(z3, hg, {hv: z3.IntVal(x)}, app_at(x)), enc(z3, hb, {hv: z3.IntVal(x)}, app_at(x))))
        s.add(enc(z3, cg, {cv_: z3.IntVal(n0)}, app_at(n0)), z3.Not(enc(z3, cb, {cv_: z3.IntVal(n0)}, app_at(n0))))
        if s.check() == z3.sat:
            m = s.model()
            return {"n": n0, "prefix": [m.eval(v, model_completion=True).as_long() for v in vs]}
    return None


def affine_model(H, C):
    hv, hg, hb = H
    cv_, cg, cb = C
    x, n = z3.Ints("x n")
    for al in range(0, 4):
        for be in range(0, 4):
            app = lambda arg, env: al * enc(z3, arg, env, app) + be
            s = z3.Solver()
            s.set("timeout", 1500)
            s.add(x >= 0, enc(z3, hg, {hv: x}, app), z3.Not(enc(z3, hb, {hv: x}, app)))
            if s.check() != z3.unsat:
                continue
            s = z3.Solver()
            s.set("timeout", 1500)
            s.add(n >= 0, enc(z3, cg, {cv_: n}, app), z3.Not(enc(z3, cb, {cv_: n}, app)))
            if s.check() == z3.sat:
                return {"alpha": al, "beta": be, "n": s.model().eval(n, model_completion=True).as_long()}
    return None


def label(spec, tag):
    R, F = claim(spec["reference"]), claim(spec["formal"])
    H, C = (R, F) if tag == "fwd" else (F, R)
    try:
        if uf_refute(z3, H, C, UF_MS):
            return {"label": "ENTAILS", "method": "z3"}
    except Exception:  # noqa: BLE001
        pass
    try:
        if tag == "fwd":
            pm = prefix_model(spec.get("family"), spec.get("meta", {}), H, C)
            if pm:
                return {"label": "SEPARATED", "method": "prefix-model", "witness": pm}
        am = affine_model(H, C)
        if am:
            return {"label": "SEPARATED", "method": "explicit-function", "witness": am}
    except Exception:  # noqa: BLE001
        pass
    if cv is not None:
        try:
            if uf_refute(cv, H, C, UF_MS):
                return {"label": "ENTAILS", "method": "cvc5"}
        except Exception:  # noqa: BLE001
            pass
    return {"label": None, "method": None}


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results" / "labels.json"
    rows = {}
    for p in sorted((HERE / "cases").glob("*.json")):
        spec = json.loads(p.read_text())
        rows[spec["id"]] = {tag: label(spec, tag) for tag in ("fwd", "bwd")}
        print(spec["id"], spec["family"], rows[spec["id"]]["fwd"]["label"], rows[spec["id"]]["bwd"]["label"], flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    n = sum(1 for r in rows.values() for t in r.values() if t["label"])
    print(f"labelled {n} / {2 * len(rows)} directions")


if __name__ == "__main__":
    main()
