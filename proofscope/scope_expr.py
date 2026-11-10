"""Tiny expression language shared by Lean and Python (SOTA-15).

Natural-number terms and propositions written in a subset of Lean syntax that this module can parse,
evaluate with Lean's `Nat` semantics (truncated `-`, `/ 0 = 0`, `% 0 = id`), print back as Lean, and
scan for opaque (non-linear or named) operators. Anything outside the grammar raises `Unsupported`,
which callers must treat as "abstain". Python evaluation is only ever used to *search*; every result
is re-checked by Lean, so a semantic mismatch here can lose a verdict but cannot create one.
"""

from __future__ import annotations

import re

_TOK = re.compile(r"\s*(?:(\d+)|([A-Za-z_][A-Za-z0-9_.']*)|(≤|≥|≠|∧|∨|¬|→|<=|>=|!=|[-+*/%^()<>=]))")
REL = {"=", "≠", "<", "≤", ">", "≥"}
_ALIAS = {"<=": "≤", ">=": "≥", "!=": "≠"}


class Unsupported(Exception):
    pass


def tokenize(s: str) -> list[tuple[str, str]]:
    out, i = [], 0
    s = s.rstrip()
    while i < len(s):
        m = _TOK.match(s, i)
        if not m:
            raise Unsupported(f"cannot tokenize at {s[i:i + 12]!r}")
        i = m.end()
        if m.group(1):
            out.append(("num", m.group(1)))
        elif m.group(2):
            out.append(("id", m.group(2)))
        else:
            out.append(("op", _ALIAS.get(m.group(3), m.group(3))))
    return out


class _P:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else ("end", "")

    def eat(self, kind=None, val=None):
        k, v = self.peek()
        if (kind and k != kind) or (val and v != val):
            raise Unsupported(f"expected {val or kind}, found {v!r}")
        self.i += 1
        return v

    def imp(self):
        a = self.disj()
        if self.peek() == ("op", "→"):
            self.eat()
            return ("imp", a, self.imp())
        return a

    def disj(self):
        a = self.conj()
        while self.peek() == ("op", "∨"):
            self.eat()
            a = ("or", a, self.conj())
        return a

    def conj(self):
        a = self.neg()
        while self.peek() == ("op", "∧"):
            self.eat()
            a = ("and", a, self.neg())
        return a

    def neg(self):
        if self.peek() == ("op", "¬"):
            self.eat()
            return ("not", self.neg())
        return self.cmp()

    def cmp(self):
        a = self.add()
        k, v = self.peek()
        if k == "op" and v in REL:
            self.eat()
            return ("cmp", v, a, self.add())
        return a

    def add(self):
        a = self.mul()
        while self.peek()[0] == "op" and self.peek()[1] in "+-":
            op = self.eat()
            a = ("bin", op, a, self.mul())
        return a

    def mul(self):
        a = self.pow()
        while self.peek()[0] == "op" and self.peek()[1] in "*/%":
            op = self.eat()
            a = ("bin", op, a, self.pow())
        return a

    def pow(self):
        a = self.app()
        if self.peek() == ("op", "^"):
            self.eat()
            return ("bin", "^", a, self.pow())
        return a

    def _atom_start(self):
        k, v = self.peek()
        return k in ("num", "id") and v not in ("True", "False") or (k, v) == ("op", "(")

    def app(self):
        k, v = self.peek()
        if k == "id" and v not in ("True", "False"):
            self.eat()
            args = []
            while self._atom_start():
                args.append(self.atom())
            return ("app", v, args) if args else ("var", v)
        return self.atom()

    def atom(self):
        k, v = self.peek()
        if k == "num":
            self.eat()
            return ("num", int(v))
        if k == "id":
            self.eat()
            return {"True": ("true",), "False": ("false",)}.get(v, ("var", v))
        if (k, v) == ("op", "("):
            self.eat()
            a = self.imp()
            self.eat("op", ")")
            return a
        raise Unsupported(f"unexpected token {v!r}")


def parse(s: str):
    p = _P(tokenize(s))
    a = p.imp()
    if p.peek()[0] != "end":
        raise Unsupported(f"trailing input {p.peek()[1]!r}")
    return a


def to_lean(a) -> str:
    k = a[0]
    if k == "num":
        return str(a[1])
    if k == "var":
        return a[1]
    if k == "raw":
        return a[1]
    if k == "true":
        return "True"
    if k == "false":
        return "False"
    if k == "bin":
        return f"({to_lean(a[2])} {a[1]} {to_lean(a[3])})"
    if k == "app":
        return "(" + a[1] + "".join(" " + to_lean(x) for x in a[2]) + ")"
    if k == "cmp":
        return f"({to_lean(a[2])} {a[1]} {to_lean(a[3])})"
    if k in ("and", "or", "imp"):
        sym = {"and": "∧", "or": "∨", "imp": "→"}[k]
        return f"({to_lean(a[1])} {sym} {to_lean(a[2])})"
    if k == "not":
        return f"(¬ {to_lean(a[1])})"
    raise Unsupported(k)


def evaluate(a, env: dict):
    k = a[0]
    if k == "num":
        return a[1]
    if k == "var":
        if a[1] not in env:
            raise Unsupported(f"free variable {a[1]}")
        return env[a[1]]
    if k == "true":
        return True
    if k == "false":
        return False
    if k == "bin":
        x, y = evaluate(a[2], env), evaluate(a[3], env)
        op = a[1]
        if op == "+":
            return x + y
        if op == "-":
            return max(0, x - y)
        if op == "*":
            return x * y
        if op == "/":
            return x // y if y else 0
        if op == "%":
            return x % y if y else x
        if op == "^":
            if y > 64:
                raise Unsupported("exponent too large")
            return x ** y
    if k == "app":
        f = env.get(a[1])
        if not callable(f):
            raise Unsupported(f"uninterpreted function {a[1]}")
        return f(*[evaluate(x, env) for x in a[2]])
    if k == "cmp":
        x, y = evaluate(a[2], env), evaluate(a[3], env)
        return {"=": x == y, "≠": x != y, "<": x < y, "≤": x <= y, ">": x > y, "≥": x >= y}[a[1]]
    if k == "and":
        return evaluate(a[1], env) and evaluate(a[2], env)
    if k == "or":
        return evaluate(a[1], env) or evaluate(a[2], env)
    if k == "imp":
        return (not evaluate(a[1], env)) or evaluate(a[2], env)
    if k == "not":
        return not evaluate(a[1], env)
    raise Unsupported(k)


def subst(a, m: dict):
    """Replace variables by ASTs."""
    k = a[0]
    if k == "var":
        return m.get(a[1], a)
    if k in ("num", "true", "false", "raw"):
        return a
    if k == "bin" or k == "cmp":
        return (k, a[1], subst(a[2], m), subst(a[3], m))
    if k == "app":
        return (k, a[1], [subst(x, m) for x in a[2]])
    if k == "not":
        return (k, subst(a[1], m))
    return (k, subst(a[1], m), subst(a[2], m))


def free_vars(a, acc=None) -> set:
    acc = set() if acc is None else acc
    k = a[0]
    if k == "var":
        acc.add(a[1])
    elif k in ("bin", "cmp"):
        free_vars(a[2], acc), free_vars(a[3], acc)
    elif k == "app":
        for x in a[2]:
            free_vars(x, acc)
    elif k == "not":
        free_vars(a[1], acc)
    elif k in ("and", "or", "imp"):
        free_vars(a[1], acc), free_vars(a[2], acc)
    return acc


def _is_num(a):
    return a[0] == "num"


def opaque_head(a):
    """(symbol, args) if `a` is an application outside linear arithmetic, else None."""
    if a[0] == "app":
        return a[1], a[2]
    if a[0] == "bin":
        op, x, y = a[1], a[2], a[3]
        if op == "^":
            return "^", [x, y]
        if op == "*" and not _is_num(x) and not _is_num(y):
            return "*", [x, y]
        if op in "/%" and not _is_num(y):
            return op, [x, y]
    return None


def occurrences(a, acc=None) -> list:
    """All opaque applications in `a`, outermost first."""
    acc = [] if acc is None else acc
    h = opaque_head(a)
    if h:
        acc.append(a)
    k = a[0]
    if k in ("bin", "cmp"):
        occurrences(a[2], acc), occurrences(a[3], acc)
    elif k == "app":
        for x in a[2]:
            occurrences(x, acc)
    elif k == "not":
        occurrences(a[1], acc)
    elif k in ("and", "or", "imp"):
        occurrences(a[1], acc), occurrences(a[2], acc)
    return acc


def replace_node(a, target, new):
    """Replace every node structurally equal to `target`."""
    if a == target:
        return new
    k = a[0]
    if k in ("bin", "cmp"):
        return (k, a[1], replace_node(a[2], target, new), replace_node(a[3], target, new))
    if k == "app":
        return (k, a[1], [replace_node(x, target, new) for x in a[2]])
    if k == "not":
        return (k, replace_node(a[1], target, new))
    if k in ("and", "or", "imp"):
        return (k, replace_node(a[1], target, new), replace_node(a[2], target, new))
    return a


def linear_form(a, var: str):
    """(coef, const) with `a = coef * var + const`, coef in {0, 1}; None if not of that shape."""
    k = a[0]
    if k == "num":
        return 0, a[1]
    if k == "var":
        return (1, 0) if a[1] == var else None
    if k == "bin" and a[1] == "+":
        l, r = linear_form(a[2], var), linear_form(a[3], var)
        if l and r and l[0] + r[0] <= 1:
            return l[0] + r[0], l[1] + r[1]
    return None
