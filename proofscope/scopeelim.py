"""ScopeElim engine (SOTA-15): exact residual obligations and certificates for schematic comparison.

Supported fragments (anything else raises `Unsupported` and the caller abstains):

``horn``   Reference and formal claim are conjunctions of definite clauses over predicate symbols on
           `Nat`. If every clause variable has a bound (`x < B`), the fragment is *bounded*: grounding
           is finite, saturation terminates, and the procedure is complete (it returns a derivation or
           the least model as a separating interpretation; see `lean/ProofScope/HornFin.lean`). With
           unbounded variables the procedure is a sound semi-procedure: offset forward chaining for
           entailment, a template family of periodic/threshold sets for separation.
``func``   One function symbol `f : Nat → Nat` occurring once in each claim (SOTA-14 Theorem B). The
           engine emits the vacuity and fibre obligations and their negations and tries a tactic
           portfolio on each.

Every decisive answer is a set of Lean declarations accepted by `proofscope.certify` (tactic closes,
clean recompile, standard axioms only, `leanchecker` replay). Python search results are never
trusted; a wrong search result can only produce an abstention.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import time
from pathlib import Path

from .certify import certify
from .scope_expr import (Unsupported, evaluate, free_vars, linear_form, occurrences, opaque_head, parse,
                         replace_node, subst, to_lean)
from .toolchain import Toolchain

SRC = Path(__file__).resolve().parents[1] / "lean"
LIB = ["ScopeElim", "ScopeCert"]
HEADER = ("import ProofScope.ScopeCert\nopen ProofScope.ScopeElim ProofScope.ScopeCert\n"
          "set_option maxHeartbeats 1000000\nset_option maxRecDepth 8000\n"
          "set_option linter.unusedVariables false\n")
MAX_GROUND = 4000          # ground rule instances per schema (bounded fragment)
MAX_LEAVES = 400           # case-split leaves per formal clause


def build_lib(tc: Toolchain, out: Path) -> dict:
    (out / "ProofScope").mkdir(parents=True, exist_ok=True)
    for m in LIB:
        o = out / "ProofScope" / f"{m}.olean"
        if o.exists():
            continue
        r = tc.run([tc.lean, "-o", str(o), str(SRC / "ProofScope" / f"{m}.lean")], cwd=SRC, extra_path=out, timeout=900)
        if r.returncode != 0 or not o.exists():
            return {"ok": False, "log": r.as_dict()}
    return {"ok": True}


def lib_toolchain(tc: Toolchain, lib: Path) -> Toolchain:
    env = dict(tc.env)
    env["LEAN_PATH"] = ":".join(p for p in [str(lib), env.get("LEAN_PATH", "")] if p)
    return Toolchain(lean=tc.lean, leanchecker=tc.leanchecker, lake=tc.lake, project=tc.project, env=env)


# --------------------------------------------------------------------------------------------------
# Horn schemas
# --------------------------------------------------------------------------------------------------

class Clause:
    """`∀ vars (with optional bounds), HYP → concl`; HYP is a conjunction tree of guards, atoms and
    local rules (`('and', l, r) | ('guard', ast) | ('atom', sym, [ast]) | ('loc', [atoms], atom)`)."""

    def __init__(self, vars_, hyp, concl):
        self.vars, self.hyp, self.concl = vars_, hyp, concl
        self.leaves = []
        self._index(hyp)

    def _index(self, t):
        if t[0] == "and":
            self._index(t[1]), self._index(t[2])
        else:
            self.leaves.append(t)

    @classmethod
    def from_json(cls, d: dict) -> "Clause":
        vars_ = [(n, parse(str(b)) if b is not None else None) for n, b in d.get("vars", [])]
        atom = lambda a: (a[0], [parse(str(x)) for x in a[1]])
        leaves = [("guard", parse(d.get("guard", "True")))]
        leaves += [("atom",) + atom(a) for a in d.get("prems", [])]
        leaves += [("loc", [atom(a) for a in l["prems"]], atom(l["concl"])) for l in d.get("locals", [])]
        hyp = leaves[-1]
        for l in reversed(leaves[:-1]):
            hyp = ("and", l, hyp)
        return cls(vars_, hyp, atom(d["concl"]))

    @property
    def bounded(self) -> bool:
        return all(b is not None for _, b in self.vars)

    def lean(self) -> str:
        s = f"({_hyp_lean(self.hyp)}) → {_atom_lean(self.concl)}"
        for n, b in reversed(self.vars):
            s = f"∀ ({n} : Nat), " + (f"{n} < {to_lean(b)} → " if b is not None else "") + s
        return f"({s})"


def _atom_lean(a) -> str:
    return "(" + a[0] + "".join(" " + to_lean(t) for t in a[1]) + ")"


def _hyp_lean(t) -> str:
    if t[0] == "and":
        return f"({_hyp_lean(t[1])} ∧ {_hyp_lean(t[2])})"
    if t[0] == "guard":
        return to_lean(t[1])
    if t[0] == "atom":
        return _atom_lean(t[1:])
    return "(" + " → ".join([_atom_lean(a) for a in t[1]] + [_atom_lean(t[2])]) + ")"


class Schema:
    def __init__(self, name: str, symbols: dict, clauses: list):
        self.name, self.symbols, self.clauses = name, symbols, clauses
        for c in clauses:
            for a in [c.concl] + [l[1:] for l in c.leaves if l[0] == "atom"] + \
                     [x for l in c.leaves if l[0] == "loc" for x in l[1] + [l[2]]]:
                if a[0] not in symbols or len(a[1]) != symbols[a[0]] or not 1 <= len(a[1]) <= 3:
                    raise Unsupported(f"atom {a[0]} has an undeclared symbol or unsupported arity")

    def binders(self) -> str:
        return " ".join(f"({s} : {' → '.join(['Nat'] * k)} → Prop)" for s, k in self.symbols.items())

    def args(self) -> str:
        return " ".join(self.symbols)

    def body(self) -> str:
        return " ∧ ".join(c.lean() for c in self.clauses) if self.clauses else "True"

    def definition(self) -> str:
        return f"abbrev {self.name} {self.binders()} : Prop := {self.body()}\n"

    def acc(self, h: str, i: int) -> str:
        n = len(self.clauses)
        if n == 1:
            return h
        return f"{h}" + ".2" * i + (".1" if i < n - 1 else "")


def _envs(c: Clause, cap: int):
    """All assignments of a bounded clause's variables (bounds may mention earlier variables)."""
    out = [dict()]
    for n, b in c.vars:
        nxt = []
        for e in out:
            for v in range(evaluate(b, e)):
                nxt.append({**e, n: v})
                if len(nxt) > cap:
                    raise Unsupported("too many ground instances")
        out = nxt
    return out


def _ground_atom(a, env):
    return (a[0], tuple(evaluate(t, env) for t in a[1]))


def _num(v):
    return ("num", v)


def _cast(arity: int, proof: str) -> str:
    return f"(cast{arity} {proof}" + " (by ps_eq)" * arity + ")"


def _hyp_proof(t, counter, give):
    """Proof term for a hypothesis tree; `give(leaf_index, leaf)` supplies each leaf."""
    if t[0] == "and":
        l = _hyp_proof(t[1], counter, give)
        r = _hyp_proof(t[2], counter, give)
        return f"⟨{l}, {r}⟩"
    i = counter[0]
    counter[0] += 1
    return give(i, t)


def _hyp_pattern(t, counter) -> str:
    if t[0] == "and":
        l = _hyp_pattern(t[1], counter)
        return f"⟨{l}, {_hyp_pattern(t[2], counter)}⟩"
    i = counter[0]
    counter[0] += 1
    return {"guard": "hg", "atom": "hp", "loc": "hl"}[t[0]] + str(i)


def _saturate(rules, prems):
    """rules: (tag, body, head). Returns {atom: ('prem', i) | (tag, body)} in derivation order."""
    known = {}
    for i, a in enumerate(prems):
        known.setdefault(a, ("prem", i))
    pending = list(rules)
    changed = True
    while changed:
        changed = False
        rest = []
        for tag, body, head in pending:
            if all(b in known for b in body):
                if head not in known:
                    known[head] = (tag, body)
                    changed = True
            else:
                rest.append((tag, body, head))
        pending = rest
    return known


def _needed(known, goal):
    order, seen = [], set()

    def visit(a):
        if a in seen:
            return
        seen.add(a)
        why = known[a]
        if why[0] != "prem":
            for b in why[1]:
                visit(b)
        order.append(a)
    visit(goal)
    return order


def _derivation_tactic(R: Schema, c: Clause, prem_leaf: dict, order, known, goal, term) -> str:
    """Lean steps deriving `goal` inside one leaf. Atoms are (sym, args); `term` maps an arg to an AST."""
    name, steps = {}, []
    for a in order:
        why = known[a]
        ar = len(a[1])
        lit = _atom_lean((a[0], [term(x) for x in a[1]]))
        if why[0] == "prem":
            pf = _cast(ar, f"hp{prem_leaf[why[1]]}")
        elif why[0][0] == "R":
            _, ci, inst = why[0]
            rc = R.clauses[ci]
            body = iter(why[1])
            app = R.acc("hR", ci)
            for n, b in rc.vars:
                app += f" {to_lean(inst[n])}" + (" (by ps_triv)" if b is not None else "")
            hp = _hyp_proof(rc.hyp, [0], lambda i, l: "(by ps_triv)" if l[0] == "guard"
                            else _cast(len(l[2]), name[next(body)]))
            pf = _cast(ar, f"({app} {hp})")
        else:                                   # local rule of the formal clause
            li = why[0][1]
            pf = _cast(ar, "(" + f"hl{li}" + "".join(" " + _cast(len(b[1]), name[b]) for b in why[1]) + ")")
        name[a] = f"f{len(name)}"
        steps.append(f"have {name[a]} : {lit} := {pf}")
    return "; ".join(steps + [f"exact {_cast(len(goal[1]), name[goal])}"])


def _clause_intro(c: Clause) -> str:
    names = []
    for n, b in c.vars:
        names += [n] + ([f"hb_{n}"] if b is not None else [])
    pat = _hyp_pattern(c.hyp, [0])
    if c.hyp[0] != "and":
        return f"intro {' '.join(names + [pat])}"
    return f"intro {' '.join(names + ['hH'])}; obtain {pat} := hH"


def _bounded_direction(R: Schema, F: Schema) -> dict:
    """Complete procedure for the bounded fragment: entailment tactic or a separating model."""
    rules = []
    for ci, rc in enumerate(R.clauses):
        if any(l[0] == "loc" for l in rc.leaves):
            raise Unsupported("a rule with a nested implication in its hypothesis is not definite")
        for env in _envs(rc, MAX_GROUND):
            if all(evaluate(l[1], env) for l in rc.leaves if l[0] == "guard"):
                body = tuple(_ground_atom(l[1:], env) for l in rc.leaves if l[0] == "atom")
                rules.append((("R", ci, {k: _num(v) for k, v in env.items()}), body, _ground_atom(rc.concl, env)))
                if len(rules) > MAX_GROUND:
                    raise Unsupported("too many ground rule instances")
    clause_tacs, active = [], 0
    for fc in F.clauses:
        prem_ix = [i for i, l in enumerate(fc.leaves) if l[0] == "atom"]
        envs = _envs(fc, MAX_LEAVES)

        def leaf(env):
            nonlocal active
            for i, l in enumerate(fc.leaves):
                if l[0] == "guard" and not evaluate(l[1], env):
                    return f"(exact absurd hg{i} (by decide))", None
            active += 1
            prems = [_ground_atom(fc.leaves[i][1:], env) for i in prem_ix]
            loc = [(("L", i), tuple(_ground_atom(a, env) for a in l[1]), _ground_atom(l[2], env))
                   for i, l in enumerate(fc.leaves) if l[0] == "loc"]
            known = _saturate(rules + loc, prems)
            goal = _ground_atom(fc.concl, env)
            if goal not in known:
                return None, {"model": sorted(known), "instance": dict(env), "clause": F.clauses.index(fc)}
            pl = {j: prem_ix[j] for j in range(len(prem_ix))}
            return "(" + _derivation_tactic(R, fc, pl, _needed(known, goal), known, goal, _num) + ")", None

        def split(k, env):
            if k == len(fc.vars):
                return leaf(env)
            n, b = fc.vars[k]
            vals = list(range(evaluate(b, env)))
            if not vals:
                return "(omega)", None
            subs = []
            for v in vals:
                t, cex = split(k + 1, {**env, n: v})
                if cex:
                    return None, cex
                subs.append(t)
            pat = " | ".join(["rfl"] * len(vals))
            dis = " ∨ ".join(f"{n} = {v}" for v in vals)
            return f"(rcases (by omega : {dis}) with {pat}; " + "; ".join(subs) + ")", None

        t, cex = split(0, {})
        if cex:
            return {"status": "SEPARATED", "cex": cex, "active": active}
        clause_tacs.append(f"({_clause_intro(fc)}; {t})")
    n = len(F.clauses)
    pre = f"intro {R.args()} hR"
    if n == 0:
        tac = f"{pre}; trivial"
    elif n == 1:
        tac = f"{pre}; {clause_tacs[0]}"
    else:
        tac = f"{pre}; refine ⟨{', '.join(['?_'] * n)}⟩; " + "; ".join(clause_tacs)
    return {"status": "ENTAILS", "tactics": [tac], "active": active}


def _finite_model(symbols: dict, atoms) -> list[str]:
    out = []
    for s, k in symbols.items():
        vs = [f"a{i}" for i in range(k)]
        rows = [a[1] for a in atoms if a[0] == s]
        if not rows:
            out.append(f"(fun {' '.join('_' for _ in vs)} => False)")
            continue
        alt = " ∨ ".join("(" + " ∧ ".join(f"{v} = {x}" for v, x in zip(vs, r)) + ")" for r in rows)
        out.append(f"(fun {' '.join(vs)} => {alt})")
    return out


def _refute_tactic(F: Schema, ci: int, env: dict) -> str:
    fc = F.clauses[ci]
    app = F.acc("h", ci)
    for n, b in fc.vars:
        app += f" {env[n]}" + (" (by ps_triv)" if b is not None else "")
    hp = _hyp_proof(fc.hyp, [0], lambda i, l: "(by ps_triv)" if l[0] == "guard"
                    else ("(by first | omega | decide | trivial)" if l[0] == "atom" else "(by intros; first | omega | trivial)"))
    return f"intro h; have h1 := {app} {hp}; first | omega | exact h1 | (exact absurd h1 (by decide))"


def _sep_tactics(R: Schema, F: Schema, models: list[str], ci: int, env: dict, decidable: bool) -> list[str]:
    m = ", ".join(models)
    holds = "(repeat' constructor) <;> (intros; first | omega | trivial | simp_all | (simp_all; omega) | decide)"
    slow = (f"refine ⟨{m}, ?_, ?_⟩; (dsimp only [{R.name}]; {holds}); "
            f"(dsimp only [{F.name}]; {_refute_tactic(F, ci, env)})")
    return ([f"refine ⟨{m}, ?_, ?_⟩ <;> decide"] if decidable else []) + [slow]


# ---- unbounded (symbolic) Horn: sound semi-procedures ---------------------------------------------

def _lf_ast(lf, var):
    c, k = lf
    if c == 0:
        return _num(k)
    return ("var", var) if k == 0 else ("bin", "+", ("var", var), _num(k))


def _symbolic_entails(R: Schema, F: Schema) -> list[str] | None:
    """Offset forward chaining for single-variable clauses with terms `v + c` or `c`."""
    clause_tacs = []
    for fc in F.clauses:
        if len(fc.vars) != 1 or fc.vars[0][1] is not None or any(l[0] == "loc" for l in fc.leaves):
            return None
        y = fc.vars[0][0]
        guards = [l[1] for l in fc.leaves if l[0] == "guard"]
        samples = [v for v in range(48) if all(evaluate(g, {y: v}) for g in guards)]
        prem_ix = [i for i, l in enumerate(fc.leaves) if l[0] == "atom"]

        def lf_atom(a, var):
            fs = [linear_form(t, var) for t in a[1]]
            return None if any(f is None for f in fs) else (a[0], tuple(fs))
        prems = [lf_atom(fc.leaves[i][1:], y) for i in prem_ix]
        goal = lf_atom(fc.concl, y)
        if goal is None or any(p is None for p in prems):
            return None
        known = {}
        for i, p in enumerate(prems):
            known.setdefault(p, ("prem", i))
        rdata = []
        for ci, rc in enumerate(R.clauses):
            if len(rc.vars) != 1 or rc.vars[0][1] is not None or any(l[0] == "loc" for l in rc.leaves):
                return None
            x = rc.vars[0][0]
            body = [lf_atom(l[1:], x) for l in rc.leaves if l[0] == "atom"]
            head = lf_atom(rc.concl, x)
            if head is None or any(b is None for b in body):
                return None
            rdata.append((ci, x, body, head, [l[1] for l in rc.leaves if l[0] == "guard"]))

        def inst(a, xv):               # substitute x := xv (a linear form in y) into an atom over x
            return (a[0], tuple((c * xv[0], c * xv[1] + k) for c, k in a[1]))
        for _ in range(10):
            if goal in known or len(known) > 300:
                break
            new = {}
            for ci, x, body, head, rg in rdata:
                cands = {(1, 0)} | {(0, k) for k in range(4)}
                for b in body + [head]:
                    for (c, k) in b[1]:
                        if c == 1:
                            for f in list(known) + [goal]:
                                if f[0] == b[0]:
                                    for (fc_, fk) in f[1]:
                                        if fk - k >= 0:
                                            cands.add((fc_, fk - k))
                for xv in cands:
                    ib = tuple(inst(b, xv) for b in body)
                    h = inst(head, xv)
                    if h in known or h in new or not all(b in known for b in ib):
                        continue
                    if not all(evaluate(g, {x: xv[0] * v + xv[1]}) for g in rg for v in samples):
                        continue
                    new[h] = (("R", ci, {x: _lf_ast(xv, y)}), ib)
            if not new:
                break
            known.update(new)
        if goal not in known:
            return None
        pl = {j: prem_ix[j] for j in range(len(prem_ix))}
        term = lambda lf: _lf_ast(lf, y)
        clause_tacs.append(f"({_clause_intro(fc)}; "
                           f"{_derivation_tactic(R, fc, pl, _needed(known, goal), known, goal, term)})")
    n = len(F.clauses)
    pre = f"intro {R.args()} hR"
    if n == 1:
        return [f"{pre}; {clause_tacs[0]}"]
    return [f"{pre}; refine ⟨{', '.join(['?_'] * n)}⟩; " + "; ".join(clause_tacs)] if n else [f"{pre}; trivial"]


def _templates():
    t = [("(fun _ => False)", lambda z: False), ("(fun _ => True)", lambda z: True)]
    for c in range(1, 7):
        t.append((f"(fun z => {c} ≤ z)", lambda z, c=c: z >= c))
    for c in range(0, 7):
        t.append((f"(fun z => z ≤ {c})", lambda z, c=c: z <= c))
    for c in range(0, 5):
        t.append((f"(fun z => z = {c})", lambda z, c=c: z == c))
    for m in (2, 3, 4):
        for r in range(m):
            t.append((f"(fun z => z % {m} = {r})", lambda z, m=m, r=r: z % m == r))
            t.append((f"(fun z => z % {m} ≠ {r})", lambda z, m=m, r=r: z % m != r))
    for m in (2, 3):
        for r in range(m):
            for c in range(1, 5):
                t.append((f"(fun z => {c} ≤ z ∧ z % {m} = {r})", lambda z, m=m, r=r, c=c: z >= c and z % m == r))
    return t


def _clause_holds(c: Clause, env: dict, model: dict) -> bool:
    def at(a):
        return model[a[0]](*[evaluate(t, env) for t in a[1]])

    def hyp(t):
        if t[0] == "and":
            return hyp(t[1]) and hyp(t[2])
        if t[0] == "guard":
            return bool(evaluate(t[1], env))
        if t[0] == "atom":
            return at(t[1:])
        return (not all(at(a) for a in t[1])) or at(t[2])
    return (not hyp(c.hyp)) or at(c.concl)


def _window(c: Clause, w: int):
    out = [dict()]
    for n, b in c.vars:
        out = [{**e, n: v} for e in out for v in range(min(w, evaluate(b, e)) if b is not None else w)]
        if len(out) > 20000:
            raise Unsupported("window too large")
    return out


def _symbolic_separation(R: Schema, F: Schema) -> list[tuple]:
    if any(k != 1 for k in R.symbols.values()) or len(R.symbols) > 2:
        return []
    temps, syms, found = _templates(), list(R.symbols), []
    nv = max([len(c.vars) for c in R.clauses + F.clauses] + [1])
    w = 36 if nv == 1 else 10
    for combo in itertools.product(temps, repeat=len(syms)):
        model = {s: t[1] for s, t in zip(syms, combo)}
        if not all(_clause_holds(c, e, model) for c in R.clauses for e in _window(c, w)):
            continue
        for ci, fc in enumerate(F.clauses):
            bad = next((e for e in _window(fc, 14) if not _clause_holds(fc, e, model)), None)
            if bad is not None:
                found.append(([t[0] for t in combo], ci, bad))
                break
        if len(found) >= 4:
            break
    return found


def horn_direction(R: Schema, F: Schema) -> dict:
    """Obligations for 'does R uniformly entail F?' together with what the search found."""
    ent_stmt = f"∀ {R.binders()}, {R.name} {R.args()} → {F.name} {F.args()}"
    sep_stmt = f"∃ {R.binders()}, {R.name} {R.args()} ∧ ¬ {F.name} {F.args()}"
    out = {"entails_stmt": ent_stmt, "sep_stmt": sep_stmt, "entails": [], "sep": [], "complete": False}
    bounded = all(c.bounded for c in R.clauses + F.clauses)
    if bounded:
        r = _bounded_direction(R, F)
        out["complete"] = True
        out["active_instances"] = r["active"]
        if r["status"] == "ENTAILS":
            out["entails"] = r["tactics"]
        else:
            cex = r["cex"]
            out["sep"] = _sep_tactics(R, F, _finite_model(R.symbols, cex["model"]), cex["clause"], cex["instance"], True)
            out["model"] = cex
    else:
        out["entails"] = _symbolic_entails(R, F) or []
        if not out["entails"]:
            for models, ci, env in _symbolic_separation(R, F):
                out["sep"] += _sep_tactics(R, F, models, ci, env, False)
                out.setdefault("model", {"templates": models, "instance": env, "clause": ci})
    return out


def horn_schemas(spec: dict) -> tuple[Schema, Schema]:
    syms = dict(spec["symbols"])
    return (Schema("Ref", syms, [Clause.from_json(c) for c in spec["reference"]]),
            Schema("Frm", syms, [Clause.from_json(c) for c in spec["formal"]]))


# --------------------------------------------------------------------------------------------------
# One-occurrence function symbols (SOTA-14 Theorem B)
# --------------------------------------------------------------------------------------------------

class FunClaim:
    """`∀ v, guard → rel[v, f (arg v)]`, with the value written as the variable `w` in `rel`."""

    def __init__(self, var: str, guard, arg, rel):
        self.var, self.guard, self.arg, self.rel = var, guard, arg, rel
        if "w_" in free_vars(guard) | free_vars(arg) or var in ("w_", "z_", "x_", "y_"):
            raise Unsupported("reserved variable name")

    @classmethod
    def from_json(cls, d: dict) -> "FunClaim":
        return cls(d["var"], parse(d.get("guard", "True")), parse(d["arg"]),
                   subst(parse(d["rel"]), {"w": ("var", "w_")}))

    def at(self, v: str):
        m = {self.var: ("var", v)}
        return to_lean(subst(self.guard, m)), to_lean(subst(self.arg, m)), to_lean(subst(self.rel, m))

    def lambdas(self) -> str:
        g, a, r = self.at("v_")
        return f"(fun (v_ : Nat) => {g}) (fun (v_ : Nat) => {a}) (fun (v_ : Nat) (w_ : Nat) => {r})"

    def lean(self, f: str = "f") -> str:
        g, a, _ = self.at(self.var)
        r = to_lean(subst(self.rel, {"w_": ("raw", f"({f} {a})")}))
        return f"∀ ({self.var} : Nat), {g} → {r}"


_OFFS = ["y_", "(y_ + 1)", "(y_ + 2)", "(y_ + 3)", "(y_ - 1)", "(y_ - 2)", "(y_ - 3)", "0", "1", "2", "3"]


def func_residuals(R: FunClaim, F: FunClaim) -> dict:
    """The four symbol-free obligations of Theorem B for 'R entails F', each with a tactic portfolio."""
    A, s, rho = R.at("x_")
    B, t, theta = F.at("y_")
    adm_y = f"(∀ (x_ : Nat), {A} → {s} = {t} → {rho})"
    adm_z = f"(∀ (x_ : Nat), {A} → {s} = z_ → {rho})"
    fib = f"∀ (y_ : Nat) (w_ : Nat), {B} → {adm_y} → {theta}"
    nfib = f"∃ (y_ : Nat) (w_ : Nat), {B} ∧ {adm_y} ∧ ¬ {theta}"
    vac = f"∃ (z_ : Nat), ∀ (w_ : Nat), ¬ {adm_z}"
    nvac = f"∀ (z_ : Nat), ∃ (w_ : Nat), {adm_z}"
    lits = sorted({int(x) for x in re.findall(r"\b\d+\b", " ".join([A, s, rho, B, t, theta]))} - set(range(7)))[:4]
    inst = lambda x: f"(have h1 := hadm {x} (by ps_triv) (by ps_triv); first | omega | exact h1)"
    fib_t = ["omega"] + [inst(x) for x in [t] + _OFFS]
    fib_t += [f"(have h1 := hadm {x} (by ps_triv) (by ps_triv); have h2 := hadm {x2} (by ps_triv) (by ps_triv); omega)"
              for x, x2 in [("y_", "(y_ + 1)"), ("(y_ - 1)", "y_"), ("(y_ + 1)", "(y_ + 2)")]]
    fib_tac = "intro y_ w_ hB hadm; first | " + " | ".join(fib_t)
    adm_pf = "(by intro x_ hA hs; omega)"
    nfib_tac = "first | " + " | ".join(
        f"exact ⟨{y}, {w}, by ps_triv, {adm_pf}, by omega⟩" for y in list(range(7)) + lits for w in list(range(7)) + lits + [l + 1 for l in lits])
    nvac_tac = "intro z_; first | " + " | ".join(
        f"exact ⟨{w}, {adm_pf}⟩" for w in ["z_", "(z_ + 1)", "(z_ + 2)", "0", "1", "2", "(2 * z_ + 1)", "(z_ - 1)", "3"] + [str(l) for l in lits])
    vac_alts = [f"exact ⟨{z}, fun w_ hadm => by have h1 := hadm {x} (by ps_triv) (by ps_triv); omega⟩"
                for z in range(4) for x in range(5)]
    vac_alts += [f"exact ⟨{z}, fun w_ hadm => by have h1 := hadm {x} (by ps_triv) (by ps_triv); "
                 f"have h2 := hadm {x2} (by ps_triv) (by ps_triv); omega⟩"
                 for z in range(3) for x in range(4) for x2 in range(x + 1, 5)]
    vac_tac = "first | " + " | ".join(vac_alts)
    return {"fib": (fib, fib_tac), "nfib": (nfib, nfib_tac), "vac": (vac, vac_tac), "nvac": (nvac, nvac_tac)}


def func_direction(R: FunClaim, F: FunClaim, rname: str, fname: str) -> dict:
    res = func_residuals(R, F)
    show = lambda k: f"(show {res[k][0]} from by {res[k][1]})"
    lam = f"{R.lambdas()} {F.lambdas()}"
    ent_stmt = f"∀ (f : Nat → Nat), {rname} f → {fname} f"
    nent_stmt = f"¬ ∀ (f : Nat → Nat), {rname} f → {fname} f"
    ent = [f"exact fun_schematic_sound {lam} (Or.inr {show('fib')})",
           f"exact fun_schematic_sound {lam} (Or.inl {show('vac')})"]
    nent = [f"intro h; rcases (fun_schematic {lam}).1 h with ⟨z_, hz⟩ | hf; "
            f"(obtain ⟨w_, hw⟩ := {show('nvac')} z_; exact hz w_ hw); "
            f"(obtain ⟨y_, w_, hB, hadm, hθ⟩ := {show('nfib')}; exact hθ (hf y_ w_ hB hadm))"]
    return {"entails_stmt": ent_stmt, "nent_stmt": nent_stmt, "entails": ent, "nent": nent, "residuals": res, "lam": lam}


# --------------------------------------------------------------------------------------------------
# Verdicts
# --------------------------------------------------------------------------------------------------

def verdict(fwd: str, bwd: str) -> str:
    """fwd/bwd in {'ENTAILS', 'SEPARATED', 'UNKNOWN'} for 'reference ⇒ formal' and its converse."""
    if fwd == "ENTAILS" and bwd == "ENTAILS":
        return "SCHEMA_EQUIVALENT"
    if fwd == "ENTAILS" and bwd == "SEPARATED":
        return "LEAN_WEAKER"
    if fwd == "SEPARATED" and bwd == "ENTAILS":
        return "LEAN_STRONGER"
    if fwd == "SEPARATED" and bwd == "SEPARATED":
        return "INCOMPARABLE"
    return "INCONCLUSIVE"


def _status(certs: set, ent: str, sep: str) -> str:
    if ent in certs and sep in certs:
        return "INCONSISTENT"
    return "ENTAILS" if ent in certs else ("SEPARATED" if sep in certs else "UNKNOWN")


def _ident(spec: dict) -> str:
    return "SE_" + re.sub(r"[^A-Za-z0-9_]", "_", spec["id"])


def compare(spec: dict, tc: Toolchain, lib: Path, work: Path) -> dict:
    """Compare a native ScopeElim spec. `tc` must already see the library (`lib_toolchain`)."""
    t0 = time.time()
    out = {"id": spec["id"], "kind": spec.get("kind")}
    try:
        ob, header, notes = {}, HEADER, {}
        if spec["kind"] == "horn":
            R, F = horn_schemas(spec)
            header += R.definition() + F.definition()
            dirs = {}
            for tag, (a, b) in {"fwd": (R, F), "bwd": (F, R)}.items():
                try:
                    dirs[tag] = horn_direction(a, b)
                except Unsupported as e:
                    notes[tag] = f"unsupported: {e}"
                    continue
                d = dirs[tag]
                if d["entails"]:
                    ob[tag] = (d["entails_stmt"], d["entails"])
                if d["sep"]:
                    ob["sepS" if tag == "fwd" else "sepW"] = (d["sep_stmt"], d["sep"])
            out["complete_fragment"] = bool(dirs) and all(d["complete"] for d in dirs.values()) and len(dirs) == 2
            out["vacuous"] = {k: d.get("active_instances") == 0 for k, d in dirs.items() if "active_instances" in d}
            out["models"] = {k: d["model"] for k, d in dirs.items() if "model" in d}
            pairs = {"fwd": ("fwd", "sepS"), "bwd": ("bwd", "sepW")}
        elif spec["kind"] == "func":
            R, F = FunClaim.from_json(spec["reference"]), FunClaim.from_json(spec["formal"])
            header += f"abbrev Ref (f : Nat → Nat) : Prop := {R.lean()}\nabbrev Frm (f : Nat → Nat) : Prop := {F.lean()}\n"
            for tag, (a, b, an, bn) in {"fwd": (R, F, "Ref", "Frm"), "bwd": (F, R, "Frm", "Ref")}.items():
                d = func_direction(a, b, an, bn)
                ob[tag] = (d["entails_stmt"], d["entails"])
                ob["n" + tag] = (d["nent_stmt"], d["nent"])
                for k, (stmt, tac) in d["residuals"].items():
                    ob[f"{tag}_{k}"] = (stmt, [tac])
            pairs = {"fwd": ("fwd", "nfwd"), "bwd": ("bwd", "nbwd")}
        else:
            raise Unsupported(f"unknown kind {spec.get('kind')!r}")
    except Unsupported as e:
        out.update(verdict="INCONCLUSIVE", reason=f"unsupported: {e}", seconds=round(time.time() - t0, 2))
        return out
    r = certify(_ident(spec), header, ob, tc, work / "certify")
    certs = set(r["certificates"])
    st = {tag: _status(certs, e, s) for tag, (e, s) in pairs.items()}
    v = "INCONSISTENT" if "INCONSISTENT" in st.values() else verdict(st["fwd"], st["bwd"])
    if spec["kind"] == "func":
        out["reference_vacuous"] = "fwd_vac" in certs
        out["formal_vacuous"] = "bwd_vac" in certs
        out["residuals_certified"] = sorted(k for k in certs if "_" in k)
    src = r.get("certificate_source", "")
    out.update(verdict=v, directions=st, notes=notes, certify_status=r["status"], certificates=sorted(certs),
               axioms={k: c["axioms"] for k, c in r["certificates"].items()}, rejected=r["rejected"],
               certificate_bytes=len(src.encode()), seconds=round(time.time() - t0, 2))
    return out


# --------------------------------------------------------------------------------------------------
# Adapter: ClaimDelta case format → supported fragment (automatic detection)
# --------------------------------------------------------------------------------------------------

_ACTUAL = {"^": "(fun (a b : Nat) => a ^ b)", "*": "(fun (a b : Nat) => a * b)",
           "/": "(fun (a b : Nat) => a / b)", "%": "(fun (a b : Nat) => a % b)"}


def _abstract(a, sym: str):
    """Replace every application of `sym` by the bound variable `x1`."""
    h = opaque_head(a)
    k = a[0]
    if k in ("bin", "cmp"):
        b = (k, a[1], _abstract(a[2], sym), _abstract(a[3], sym))
    elif k == "app":
        b = (k, a[1], [_abstract(x, sym) for x in a[2]])
    elif k == "not":
        b = (k, _abstract(a[1], sym))
    elif k in ("and", "or", "imp"):
        b = (k, _abstract(a[1], sym), _abstract(a[2], sym))
    else:
        b = a
    if h and h[0] == sym:
        return ("app", "x1", [_abstract(x, sym) for x in h[1]])
    return b


def detect(spec: dict) -> dict:
    """Recognise a supported fragment in a ClaimDelta case; raise `Unsupported` otherwise."""
    binders = spec["binders"]
    if any(re.sub(r"\s+", "", t) not in ("Nat", "ℕ") for _, t in binders):
        raise Unsupported("non-Nat binder")
    parts = {k: parse(spec[k]) for k in ("ref_hyp", "ref_concl", "lean_hyp", "lean_concl")}
    occs = [o for p in parts.values() for o in occurrences(p)]
    heads = {opaque_head(o)[0] for o in occs}
    if len(heads) != 1:
        raise Unsupported(f"needs exactly one opaque symbol, found {sorted(heads)}")
    sym = heads.pop()
    if any(occurrences(x) for o in occs for x in opaque_head(o)[1]):
        raise Unsupported("nested occurrences of the symbol")
    arity = {len(opaque_head(o)[1]) for o in occs}
    if len(arity) != 1:
        raise Unsupported("symbol used at different arities")
    k = arity.pop()
    typ = " → ".join(["Nat"] * (k + 1))
    names = [n for n, _ in binders]
    if {"x1", "w_", "z_", "x_", "y_", "v_", "S"} & set(names):
        raise Unsupported("reserved binder name")
    # argument positions holding one and the same numeral everywhere are projected away
    const = {i: opaque_head(occs[0])[1][i] for i in range(k)
             if all(opaque_head(o)[1][i] == opaque_head(occs[0])[1][i] and opaque_head(o)[1][i][0] == "num" for o in occs)}
    live = [i for i in range(k) if i not in const]
    if len(live) != 1:
        raise Unsupported("after projecting constant positions the symbol is not unary")
    p = live[0]
    bs = " ".join(f"({n} : Nat)" for n in names)
    closed = lambda h, c: f"∀ {bs}, ({to_lean(_abstract(h, sym))}) → ({to_lean(_abstract(c, sym))})"
    info = {"symbol": sym, "type": typ, "actual": _ACTUAL.get(sym, sym), "position": p,
            "ref_abs": closed(parts["ref_hyp"], parts["ref_concl"]),
            "lean_abs": closed(parts["lean_hyp"], parts["lean_concl"])}
    args = [f"a{i}" for i in range(k)]
    info["proj"] = lambda f: f"(fun {' '.join(args)} => {f} a{p})"
    info["spec_of"] = lambda z: "(x1" + "".join(" " + (z if i == p else to_lean(const[i])) for i in range(k)) + ")"
    n_occ = {key: len(occurrences(parts[key])) for key in parts}
    # --- once-occurring function symbol
    if len(names) == 1 and n_occ["ref_hyp"] == 0 and n_occ["lean_hyp"] == 0 and n_occ["ref_concl"] == 1 \
            and n_occ["lean_concl"] == 1:
        def claim(h, c):
            o = occurrences(c)[0]
            return FunClaim(names[0], h, opaque_head(o)[1][p], replace_node(c, o, ("var", "w_")))
        info.update(fragment="func", R=claim(parts["ref_hyp"], parts["ref_concl"]),
                    F=claim(parts["lean_hyp"], parts["lean_concl"]))
        return info
    # --- definite clauses over the atom `sym(...) = c`
    cs = set()

    def atom_of(a):
        if a[0] == "cmp" and a[1] == "=" and opaque_head(a[2]) and a[3][0] == "num" and not occurrences(a[3]):
            cs.add(a[3][1])
            return ("atom", "S", [opaque_head(a[2])[1][p]])
        return None

    def tree(a):
        at = atom_of(a)
        if at:
            return at
        if a[0] == "and":
            return ("and", tree(a[1]), tree(a[2]))
        if occurrences(a):
            raise Unsupported("the symbol occurs outside an atom `sym(..) = c`")
        return ("guard", a)

    def clause(h, c):
        at = atom_of(c)
        if not at:
            raise Unsupported("conclusion is not an atom `sym(..) = c`")
        return Clause([(n, None) for n in names], tree(h), at[1:])
    R = Schema("Ref", {"S": 1}, [clause(parts["ref_hyp"], parts["ref_concl"])])
    F = Schema("Frm", {"S": 1}, [clause(parts["lean_hyp"], parts["lean_concl"])])
    if len(cs) != 1:
        raise Unsupported("atoms compare the symbol with different constants")
    info.update(fragment="horn", R=R, F=F, const=cs.pop())
    return info


def claimdelta_obligations(spec: dict) -> tuple[dict, str, dict]:
    """ClaimDelta-shaped obligations (`link*`, `fwd`, `bwd`, `sepW`, `sepS` at tag `s1`) proved through
    the fragment criteria. Statements are exactly those `proofscope.claimdelta` would certify."""
    d = detect(spec)
    bs = " ".join(f"({n} : {t})" for n, t in spec["binders"])
    orig = lambda h, c: f"∀ {bs}, ({spec[h]}) → ({spec[c]})"
    T, RA, LA = d["type"], d["ref_abs"], d["lean_abs"]
    ob = {"linkR_s1": (f"((fun (x1 : {T}) => {RA}) {d['actual']}) ↔ ({orig('ref_hyp', 'ref_concl')})", ["exact Iff.rfl"]),
          "linkL_s1": (f"((fun (x1 : {T}) => {LA}) {d['actual']}) ↔ ({orig('lean_hyp', 'lean_concl')})", ["exact Iff.rfl"])}
    ent = {"fwd": f"∀ (x1 : {T}), ({RA}) → ({LA})", "bwd": f"∀ (x1 : {T}), ({LA}) → ({RA})"}
    sep = {"fwd": ("sepS", f"∃ (x1 : {T}), ({RA}) ∧ ¬ ({LA})", RA, LA),
           "bwd": ("sepW", f"∃ (x1 : {T}), ({LA}) ∧ ¬ ({RA})", LA, RA)}
    header = HEADER
    if d["fragment"] == "func":
        for tag, (a, b) in {"fwd": (d["R"], d["F"]), "bwd": (d["F"], d["R"])}.items():
            fd = func_direction(a, b, "_", "_")
            spec_f = f"(fun z_ => {d['spec_of']('z_')})"
            ob[f"{tag}_s1"] = (ent[tag], [f"intro x1 h; {t} {spec_f} h" for t in fd["entails"]])
            name, stmt, P, Q = sep[tag]
            body = fd["nent"][0].replace(").1 h with", f").1 (fun f => h {d['proj']('f')}) with", 1)
            ob[f"{name}_s1"] = (stmt, [f"refine sep_of_not_entails (P := fun (x1 : {T}) => {P}) "
                                       f"(Q := fun (x1 : {T}) => {Q}) ?_; {body}"])
    else:
        R, F, c = d["R"], d["F"], d["const"]
        header += R.definition() + F.definition()
        atom = f"(fun z_ => {d['spec_of']('z_')} = {c})"
        real = f"(fun z_ => realize S {c} z_ = {c})"
        for tag, (a, b) in {"fwd": (R, F), "bwd": (F, R)}.items():
            hd = horn_direction(a, b)
            if hd["entails"]:
                inner = " | ".join(f"({t})" for t in hd["entails"])
                ob[f"{tag}_s1"] = (ent[tag], [f"intro x1; exact (show {hd['entails_stmt']} from by first | {inner}) {atom}"])
            if hd["sep"]:
                inner = " | ".join(f"({t})" for t in hd["sep"])
                name, stmt, _, _ = sep[tag]
                g = d["proj"](f"(realize S {c})")
                ob[f"{name}_s1"] = (stmt, [
                    f"obtain ⟨S, hA, hB⟩ := (show {hd['sep_stmt']} from by first | {inner}); "
                    f"refine ⟨{g}, ?_, ?_⟩; "
                    f"(exact Eq.mpr (congrArg {a.name} (realize_eq S {c})) hA); "
                    f"(exact fun h => hB (Eq.mp (congrArg {b.name} (realize_eq S {c})) h))"])
    return ob, header, {"fragment": d["fragment"], "symbol": d["symbol"], "type": T}


def compare_claimdelta(spec: dict, tc: Toolchain, work: Path) -> dict:
    """Decide a ClaimDelta case through ScopeElim; verdict labels and the linking rule are ClaimDelta's."""
    from .claimdelta import relation
    t0 = time.time()
    out = {"id": spec["id"], "engine": "scopeelim"}
    try:
        ob, header, meta = claimdelta_obligations(spec)
    except Unsupported as e:
        out.update(verdict="INCONCLUSIVE", reason=f"unsupported: {e}", seconds=round(time.time() - t0, 2))
        return out
    r = certify(_ident(spec), header, ob, tc, work / "certify")
    certs = set(r["certificates"])
    linked = {"linkR_s1", "linkL_s1"} <= certs
    v = relation(certs, "s1") if linked else "INCONCLUSIVE"
    src = r.get("certificate_source", "")
    out.update(meta, verdict=v, linked=linked, certify_status=r["status"], certificates=sorted(certs),
               axioms={k: c["axioms"] for k, c in r["certificates"].items()}, rejected=r["rejected"],
               certificate_bytes=len(src.encode()), seconds=round(time.time() - t0, 2))
    if not linked:
        out["reason"] = "abstraction not linked to the original statements by Iff.rfl"
    return out


def fallback(spec: dict, row: dict, tc: Toolchain, out: Path) -> dict:
    """Opt-in hook for `proofscope.claimdelta`: only called on an INCONCLUSIVE row. ClaimDelta's own
    certificates are kept and merged, so contradictory certificates surface as INCONSISTENT, and its
    law check still downgrades a separation that equational laws explain."""
    from .claimdelta import relation
    lib = out / "scopeelim_lib"
    se = compare_claimdelta(spec, lib_toolchain(tc, lib), out / "work" / (Path(spec["id"]).name + "_scopeelim"))
    row["scopeelim"] = se
    if se["verdict"] not in ("SCHEMA_EQUIVALENT", "LEAN_WEAKER", "LEAN_STRONGER", "INCOMPARABLE"):
        return row
    own = set()
    subs = row.get("subsets") or {}
    if len(subs) == 1:
        (tag, sub), = subs.items()
        own = {k.rsplit("_", 1)[0] + "_s1" for k in sub.get("certificates", {})}
    elif subs:
        return row                                # several shared symbols: outside the fragment
    rel = relation(own | set(se["certificates"]), "s1")
    if rel == "INCONSISTENT":
        row.update(verdict="INCONSISTENT", verdict_source="scopeelim+claimdelta")
    elif rel == "SCHEMA_EQUIVALENT":
        row.update(verdict="SCHEMA_EQUIVALENT", verdict_source="scopeelim")
    elif rel in ("LEAN_WEAKER", "LEAN_STRONGER", "INCOMPARABLE"):
        need = {"LEAN_WEAKER": ["lawW"], "LEAN_STRONGER": ["lawS"], "INCOMPARABLE": ["lawW", "lawS"]}[rel]
        laws = row.get("law_certificates") or {}
        # v1.3 guard: a law implication is harmless rewriting only for a kernel-verified reference
        by_laws = all(k in laws for k in need) and row.get("reference_status") == "VERIFIED"
        if all(k in laws for k in need) and not by_laws:
            row["law_status"] = "IMPLICATION_PROVED_REFERENCE_UNVERIFIED"
        row.update(verdict="EQUIVALENT_BY_LAWS" if by_laws else "CLAIM_" + rel, verdict_source="scopeelim")
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m proofscope.scopeelim")
    ap.add_argument("specs", nargs="+", help="native ScopeElim specs, or ClaimDelta cases with --claimdelta")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--claimdelta", action="store_true")
    ap.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args(argv)
    out = a.out.resolve()
    base = Toolchain.find()
    b = build_lib(base, out / "lib")
    if not b["ok"]:
        print(json.dumps(b, indent=2)[:3000])
        return 2
    from concurrent.futures import ThreadPoolExecutor
    tc = lib_toolchain(base, out / "lib")

    def one(p):
        spec = json.loads(Path(p).read_text())
        w = out / "work" / re.sub(r"[^A-Za-z0-9_]", "_", spec["id"])
        row = compare_claimdelta(spec, tc, w) if a.claimdelta else compare(spec, tc, out / "lib", w)
        for k in ("expected", "family", "split"):
            if k in spec:
                row[k] = spec[k]
        return row
    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        rows = list(ex.map(one, a.specs))
    for r in rows:
        print(r["id"], r["verdict"], r.get("reason", ""), flush=True)
    (out / "scopeelim_results.json").write_text(json.dumps({"rows": rows}, indent=1, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
