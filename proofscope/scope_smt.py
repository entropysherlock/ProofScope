"""Untrusted witness search with Z3 (SOTA-16).

Nothing returned from this module is believed: integers found here are pasted into Lean tactics as
candidate witnesses and the Lean kernel decides. If `z3` is not installed every function returns an
empty list and the engine falls back to its fixed pools.
"""

from __future__ import annotations

try:
    import z3
except Exception:  # noqa: BLE001
    z3 = None

import threading

TIMEOUT_MS = 3000
_LOCK = threading.Lock()   # Z3's default context is not thread-safe (it crashed CI and local runs)


def available() -> bool:
    return z3 is not None


def enc(a, env):
    """Encode a `scope_expr` AST over the integers with Lean's `Nat` semantics."""
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
        op = a[1]
        if op == "+":
            return x + y
        if op == "*":
            return x * y
        if op == "-":
            return z3.If(x >= y, x - y, 0)
        if op == "/":
            return z3.If(y == 0, 0, x / y)
        if op == "%":
            return z3.If(y == 0, x, x % y)
        raise ValueError("opaque operator")
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


def _models(formula, vs, n):
    s = z3.Solver()
    s.set("timeout", TIMEOUT_MS)
    s.add(formula, *[v >= 0 for v in vs])
    out = []
    while len(out) < n and s.check() == z3.sat:
        m = s.model()
        vals = [m.eval(v, model_completion=True).as_long() for v in vs]
        out.append(vals)
        s.add(z3.Or([v != c for v, c in zip(vs, vals)]))
    return out


def nfib_witnesses(R, F, n: int = 3) -> list[list[int]]:
    """Candidates (y, w) with `B y`, every reference constraint landing on `t y` satisfied by `w`,
    and `θ y w` false. `R`, `F` are `scopeelim.FunClaim`s."""
    if z3 is None:
        return []
    with _LOCK:
        return _nfib(R, F, n)


def _nfib(R, F, n):
    try:
        x, y, w = z3.Ints("x y w")
        adm = z3.ForAll([x], z3.Implies(z3.And(x >= 0, enc(R.guard, {R.var: x}),
                                               enc(R.arg, {R.var: x}) == enc(F.arg, {F.var: y})),
                                        enc(R.rel, {R.var: x, "w_": w})))
        f = z3.And(enc(F.guard, {F.var: y}), adm, z3.Not(enc(F.rel, {F.var: y, "w_": w})))
        return _models(f, [y, w], n)
    except Exception:  # noqa: BLE001
        return []


def vac_witnesses(R, n: int = 2) -> list[int]:
    """Candidates z at which no value satisfies all reference constraints."""
    if z3 is None:
        return []
    with _LOCK:
        return _vac(R, n)


def _vac(R, n):
    try:
        x, z, w = z3.Ints("x z w")
        bad = z3.Exists([x], z3.And(x >= 0, enc(R.guard, {R.var: x}), enc(R.arg, {R.var: x}) == z,
                                    z3.Not(enc(R.rel, {R.var: x, "w_": w}))))
        f = z3.ForAll([w], z3.Implies(w >= 0, bad))
        return [m[0] for m in _models(f, [z], n)]
    except Exception:  # noqa: BLE001
        return []
