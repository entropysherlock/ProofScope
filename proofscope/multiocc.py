"""MultiOcc engine (SOTA-17): certified comparison of claims in which `f : Nat → Nat` occurs at several sites.

A claim is `∀ n, guard → body`, where `body` may mention `f` at any number of argument terms.
For a direction "H entails C" the hypothesis side `H` must belong to one of three classes, for which
`lean/ProofScope/MultiOcc.lean` proves that a finite set of points extends to a model exactly when
an explicit consistency condition holds:

``step``       `H` is equivalent to `f n + a ≤ f (n + 1) ∧ f (n + 1) ≤ f n + b` (literals `a`, `b`).
``lower``      `H` is equivalent to `f n + a ≤ f (n + 1)` (monotone at 0, strictly monotone at 1).
``pointwise``  `f` occurs once in `H`, at `k * n + c` with `k ≥ 1` (the reference shape of SOTA-14/16).

The conclusion side `C` is unrestricted in the number of sites; nested applications `f (f t)` and
other opaque symbols are not supported (the engine abstains).

* ENTAILS  certificate: the necessary conditions at the sites of `C` (`step_pair`, `lower_pair`,
  `adm_of_ref`), then `omega`.
* SEPARATED certificate: an instance `n` and values for the sites from Z3 (untrusted), joint extension
  by `step_points` / `lower_points` / `pointwise_points`, then evaluation of `C` at that instance.

The class of `H` is guessed with Z3; the guess is only used through a Lean lemma `H f ↔ class f`
that is part of the certificate. Every decisive answer is accepted by `proofscope.certify`.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import time
from pathlib import Path

from . import scope_smt
from .certify import certify
from .scope_expr import Unsupported, free_vars, opaque_head, parse, replace_node, subst, to_lean
from .scopeelim import (FunClaim, _ident, _status, affine, build_lib as _build_base, func_residuals,
                        lib_toolchain, verdict, SRC)
from .toolchain import Toolchain

try:
    import z3
except Exception:  # noqa: BLE001
    z3 = None

HEADER = ("import ProofScope.MultiOcc\nimport ProofScope.ScopeCert\n"
          "open ProofScope.ScopeElim ProofScope.ScopeCert ProofScope.MultiOcc\n"
          "set_option maxHeartbeats 400000\nset_option maxRecDepth 8000\n"
          "set_option linter.unusedVariables false\n")
MAX_SITES = 6
SYM = "f"


def build_lib(tc: Toolchain, out: Path) -> dict:
    b = _build_base(tc, out)
    if not b["ok"]:
        return b
    o = out / "ProofScope" / "MultiOcc.olean"
    if not o.exists():
        r = tc.run([tc.lean, "-o", str(o), str(SRC / "ProofScope" / "MultiOcc.lean")], cwd=SRC, extra_path=out, timeout=900)
        if r.returncode != 0 or not o.exists():
            return {"ok": False, "log": r.as_dict()}
    return {"ok": True}


# --------------------------------------------------------------------------------------------------
# Claims
# --------------------------------------------------------------------------------------------------

def _apps(a, acc):
    """All applications of the symbol, and a check that nothing else is opaque."""
    h = opaque_head(a)
    if h:
        if a[0] != "app" or a[1] != SYM or len(a[2]) != 1:
            raise Unsupported(f"opaque operator {h[0]!r}")
        if _contains_sym(a[2][0]):
            raise Unsupported("nested application of the symbol")
        if a not in acc:
            acc.append(a)
        return
    k = a[0]
    if k in ("bin", "cmp"):
        _apps(a[2], acc), _apps(a[3], acc)
    elif k == "not":
        _apps(a[1], acc)
    elif k in ("and", "or", "imp"):
        _apps(a[1], acc), _apps(a[2], acc)


def _contains_sym(a) -> bool:
    k = a[0]
    if k == "app":
        return a[1] == SYM or any(_contains_sym(x) for x in a[2])
    if k in ("bin", "cmp"):
        return _contains_sym(a[2]) or _contains_sym(a[3])
    if k == "not":
        return _contains_sym(a[1])
    if k in ("and", "or", "imp"):
        return _contains_sym(a[1]) or _contains_sym(a[2])
    return False


class Claim:
    """`∀ var, guard → body` with `f` applied to the argument terms `sites`."""

    def __init__(self, var: str, guard, body):
        if var in ("w_", "z_", "x_", "y_", "v_", SYM) or re.fullmatch(r"w\d+_", var):
            raise Unsupported("reserved variable name")
        if _contains_sym(guard):
            raise Unsupported("the symbol occurs in the guard")
        if (free_vars(guard) | free_vars(body)) - {var}:
            raise Unsupported("free variables other than the bound one")
        self.var, self.guard, self.body = var, guard, body
        occ = []
        _apps(guard, occ)
        _apps(body, occ)
        self.sites = [o[2][0] for o in occ]
        if len(self.sites) > MAX_SITES:
            raise Unsupported("too many sites")
        self.body_w = body
        for i, o in enumerate(occ):
            self.body_w = replace_node(self.body_w, o, ("var", f"w{i}_"))

    @classmethod
    def from_json(cls, d: dict) -> "Claim":
        return cls(d.get("var", "n"), parse(d.get("guard", "True")), parse(d["body"]))

    def lean(self) -> str:
        return f"∀ ({self.var} : Nat), {to_lean(self.guard)} → {to_lean(self.body)}"

    def inst(self, a, n: int):
        return subst(a, {self.var: ("num", n)})


def _z3_enc(a, env):
    return scope_smt.enc(a, env)


def classify(H: Claim) -> dict:
    """Class of a hypothesis-side claim. Raises `Unsupported` if it is in none of the three classes."""
    m = len(H.sites)
    if m == 1:
        ka = affine(H.sites[0], H.var)
        if ka and ka[0] >= 1:
            fc = FunClaim(H.var, H.guard, H.sites[0], subst(H.body_w, {"w0_": ("var", "w_")}))
            return {"class": "pointwise", "k": ka[0], "c": ka[1], "fc": fc}
        raise Unsupported("single site that is not k * n + c with k ≥ 1")
    if m == 2 and z3 is not None:
        forms = [affine(s, H.var) for s in H.sites]
        if None not in forms and sorted(forms) == [(1, 0), (1, 1)] and H.var not in free_vars(H.body_w):
            lo, hi = (0, 1) if forms[0] == (1, 0) else (1, 0)
            ab = _step_params(H, lo, hi)
            if ab:
                return {"class": "step" if ab[1] is not None else "lower", "a": ab[0], "b": ab[1]}
    raise Unsupported("hypothesis side is not a step, lower-step or pointwise claim")


def _step_params(H: Claim, lo: int, hi: int):
    """(a, b) with `guard → body` equivalent to `u + a ≤ v ∧ v ≤ u + b` (b None: no upper bound).
    Untrusted: the Lean bridge lemma decides."""
    with scope_smt._LOCK:
        try:
            u, v, n = z3.Ints("u v n")
            env = {f"w{lo}_": u, f"w{hi}_": v, H.var: n}
            body = z3.Implies(_z3_enc(H.guard, env), _z3_enc(H.body_w, env))
            base = [u >= 0, v >= 0, n >= 0]

            def valid(phi):
                s = z3.Solver()
                s.set("timeout", 3000)
                s.add(*base, z3.Not(phi))
                return s.check() == z3.unsat

            for a in range(0, 13):
                if valid(body == (u + a <= v)):
                    return a, None
                for b in range(a, 13):
                    if valid(body == z3.And(u + a <= v, v <= u + b)):
                        return a, b
        except Exception:  # noqa: BLE001
            return None
    return None


# --------------------------------------------------------------------------------------------------
# Certificates for one direction
# --------------------------------------------------------------------------------------------------

def _site(C: Claim, i: int, n=None) -> str:
    a = C.sites[i] if n is None else C.inst(C.sites[i], n)
    return to_lean(a)


def _bridge(cls: dict, hname: str) -> tuple[str, str]:
    """Lean terms proving `class f` from `hname : H f`, and `H f` from `hS : class f`."""
    if cls["class"] == "step":
        to = f"(show Step {cls['a']} {cls['b']} f from fun x => by have := {hname} x (by ps_triv); omega)"
        back = "(fun x _ => by have := hS x; omega)"
    else:
        to = f"(show Lower {cls['a']} f from fun x => by have := {hname} x (by ps_triv); omega)"
        back = "(fun x _ => by have := hS x; omega)"
    return to, back


def _witnesses(cls: dict, C: Claim, count: int = 3) -> list[tuple[int, list[int]]]:
    """Instances `n` and site values that are consistent for the class and falsify `C`. Untrusted."""
    if z3 is None:
        return []
    with scope_smt._LOCK:
        try:
            n = z3.Int("n")
            ws = [z3.Int(f"w{i}") for i in range(len(C.sites))]
            env = {C.var: n, **{f"w{i}_": w for i, w in enumerate(ws)}}
            zs = [_z3_enc(s, {C.var: n}) for s in C.sites]
            cons = []
            if cls["class"] in ("step", "lower"):
                a, b = cls["a"], cls["b"]
                for i, j in itertools.product(range(len(ws)), repeat=2):
                    cons.append(a * zs[i] <= ws[i])
                    c = [ws[i] + a * (zs[j] - zs[i]) <= ws[j]]
                    if b is not None:
                        c.append(ws[j] <= ws[i] + b * (zs[j] - zs[i]))
                    cons.append(z3.Implies(zs[i] <= zs[j], z3.And(c)))
                    cons.append(z3.Implies(zs[i] == zs[j], ws[i] == ws[j]))
            else:
                fc = cls["fc"]
                x = z3.Int("x")
                for i, j in itertools.product(range(len(ws)), repeat=2):
                    cons.append(z3.Implies(zs[i] == zs[j], ws[i] == ws[j]))
                for i in range(len(ws)):
                    cons.append(z3.ForAll([x], z3.Implies(
                        z3.And(x >= 0, _z3_enc(fc.guard, {fc.var: x}), _z3_enc(fc.arg, {fc.var: x}) == zs[i]),
                        _z3_enc(fc.rel, {fc.var: x, "w_": ws[i]}))))
            core = z3.And(_z3_enc(C.guard, env), z3.Not(_z3_enc(C.body_w, env)), *cons)
            out = []
            for cap in (12, 60, None):                      # small witnesses first
                extra = [] if cap is None else [n <= cap] + [w <= 8 * cap for w in ws]
                for vals in scope_smt._models(z3.And(core, *extra), [n] + ws, count - len(out)):
                    if (vals[0], vals[1:]) not in out:
                        out.append((vals[0], vals[1:]))
                if len(out) >= count:
                    break
            return out
        except Exception:  # noqa: BLE001
            return []


def direction(H: Claim, C: Claim, hname: str, cname: str) -> dict:
    """Statements and tactic portfolios for 'H entails C' and its negation."""
    cls = classify(H)
    m = len(C.sites)
    ent_stmt = f"∀ (f : Nat → Nat), {hname} f → {cname} f"
    nent_stmt = f"¬ ∀ (f : Nat → Nat), {hname} f → {cname} f"
    v = C.var
    ent, nent, extra = [], [], {}
    wits = _witnesses(cls, C)
    kind = cls["class"]

    def points(n0, vals):
        pts, seen = [], set()
        for i in range(m):
            zi = _eval_site(C, i, n0)
            if (zi, vals[i]) not in seen:
                seen.add((zi, vals[i]))
                pts.append((zi, vals[i]))
        return pts

    def evals(n0, vals):
        return "; ".join(
            f"have e{i} : f {_site(C, i, n0)} = {vals[i]} := hT ({_eval_site(C, i, n0)}, {vals[i]}) (by simp)"
            for i in range(m))

    close = "first | omega | (simp at hC; omega) | (simp at hC)"
    if kind in ("step", "lower"):
        a, b = cls["a"], cls["b"]
        to, back = _bridge(cls, "hR")
        lem = "step_pair" if kind == "step" else "lower_pair"
        pairs = "; ".join(f"have c{i}_{j} := {lem} hS {_site(C, i)} {_site(C, j)}"
                          for i, j in itertools.product(range(m), repeat=2)) or "skip"
        ent.append(f"intro f hR; have hS := {to}; intro {v} hg; {pairs}; omega")
        if kind == "step" and b < a:
            ent.append(f"intro f hR; exact absurd {to} (step_unsat (by decide) f)")
        for n0, vals in wits:
            lst = "[" + ", ".join(f"({z}, {w})" for z, w in points(n0, vals)) + "]"
            if kind == "step":
                ext = f"step_points (a := {a}) (b := {b}) (by decide) {lst} (by unfold StepConsAll; decide)"
            else:
                ext = f"lower_points {a} {lst} (by unfold LowerConsAll; decide)"
            nent.append(f"intro h; obtain ⟨f, hS, hT⟩ := {ext}; {evals(n0, vals)}; "
                        f"have hC := h f {back} {n0} (by ps_triv); {close}")
    else:
        fc, k, c = cls["fc"], cls["k"], cls["c"]
        lam = fc.lambdas()
        res = func_residuals(fc, fc, pres=True)
        res0 = func_residuals(fc, fc, pres=False)
        vac_stmt, nvac_stmt = res["vac"][0], res["nvac"][0]
        extra["vac"] = (vac_stmt, [res0["vac"][1], res["vac"][1]])
        extra["nvac"] = (nvac_stmt, [res0["nvac"][1], res["nvac"][1]])
        show = lambda key: "(show %s from by first | (%s) | (%s))" % (extra[key][0], extra[key][1][0], extra[key][1][1])
        insts = []
        for i in range(m):
            t = _site(C, i)
            x = t if (k, c) == (1, 0) else f"(({t} - {c}) / {k})"
            g, s, r = (to_lean(subst(e, {fc.var: ("raw", x)})) for e in (fc.guard, fc.arg, fc.rel))
            r = r.replace("w_", f"(f {t})")
            insts.append(f"have a{i} : {g} → {s} = {t} → {r} := adm_of_ref {lam} hR {t} {x}")
        ent.append(f"intro f hR {v} hg; " + "; ".join(insts) + "; omega")
        ent.append(f"exact vacuous_entails {lam} {show('vac')} _")
        for n0, vals in wits:
            pts = points(n0, vals)
            lst = "[" + ", ".join(f"({z}, {w})" for z, w in pts) + "]"
            alts = " | ".join(["rfl"] * len(pts))
            adm = (f"(by intro p hp; simp only [List.mem_cons, List.not_mem_nil, or_false] at hp; "
                   f"rcases hp with {alts} <;> (show ∀ (x_ : Nat), _ → _ → _; intro x_ hA hs; "
                   f"dsimp only at hA hs ⊢; omega))")
            ext = f"pointwise_points {lam} {show('nvac')} {lst} ⟨{adm}, by decide⟩"
            nent.append(f"intro h; obtain ⟨f, hS, hT⟩ := {ext}; {evals(n0, vals)}; "
                        f"have hC := h f hS {n0} (by ps_triv); {close}")
    return {"class": {k_: v_ for k_, v_ in cls.items() if k_ != "fc"}, "entails_stmt": ent_stmt,
            "nent_stmt": nent_stmt, "entails": ent, "nent": nent, "witnesses": wits, "sites": m}


def _eval_site(C: Claim, i: int, n0: int) -> int:
    from .scope_expr import evaluate
    return evaluate(C.sites[i], {C.var: n0})


# --------------------------------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------------------------------

def compare(spec: dict, tc: Toolchain, work: Path) -> dict:
    """Compare a native `multi` spec: {"id", "kind": "multi", "reference": claim, "formal": claim}."""
    t0 = time.time()
    out = {"id": spec["id"], "kind": "multi"}
    try:
        R, F = Claim.from_json(spec["reference"]), Claim.from_json(spec["formal"])
    except Unsupported as e:
        out.update(verdict="INCONCLUSIVE", reason=f"unsupported: {e}", directions={"fwd": "UNSUPPORTED", "bwd": "UNSUPPORTED"},
                   seconds=round(time.time() - t0, 2))
        return out
    header = HEADER + (f"abbrev Ref (f : Nat → Nat) : Prop := {R.lean()}\n"
                       f"abbrev Frm (f : Nat → Nat) : Prop := {F.lean()}\n")
    ob, notes, info = {}, {}, {}
    for tag, (a, b, an, bn) in {"fwd": (R, F, "Ref", "Frm"), "bwd": (F, R, "Frm", "Ref")}.items():
        try:
            d = direction(a, b, an, bn)
        except Unsupported as e:
            notes[tag] = f"unsupported: {e}"
            continue
        info[tag] = {"class": d["class"], "sites": d["sites"], "witnesses": d["witnesses"]}
        ob[tag] = (d["entails_stmt"], d["entails"])
        if d["nent"]:
            ob["n" + tag] = (d["nent_stmt"], d["nent"])
    st = {tag: "UNSUPPORTED" for tag in ("fwd", "bwd")}
    r = {"certificates": {}, "rejected": {}, "status": "SKIPPED"}
    if ob:
        r = certify(_ident(spec), header, ob, tc, work / "certify")
        certs = set(r["certificates"])
        for tag in ("fwd", "bwd"):
            if tag not in notes:
                st[tag] = _status(certs, tag, "n" + tag)
    dec = {k: (v if v in ("ENTAILS", "SEPARATED", "INCONSISTENT") else "UNKNOWN") for k, v in st.items()}
    v = "INCONSISTENT" if "INCONSISTENT" in dec.values() else verdict(dec["fwd"], dec["bwd"])
    out.update(verdict=v, directions=st, notes=notes, info=info, certify_status=r["status"],
               certificates=sorted(r["certificates"]),
               axioms={k: c["axioms"] for k, c in r["certificates"].items()}, rejected=r["rejected"],
               certificate_bytes=len(r.get("certificate_source", "").encode()),
               seconds=round(time.time() - t0, 2))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m proofscope.multiocc")
    ap.add_argument("specs", nargs="+", help="native multi-occurrence specs (JSON)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args(argv)
    out = a.out.resolve()
    base = Toolchain.find()
    b = build_lib(base, out / "lib")
    if not b["ok"]:
        print(json.dumps(b, indent=2)[:3000])
        return 2
    tc = lib_toolchain(base, out / "lib")
    from concurrent.futures import ThreadPoolExecutor

    def one(p):
        spec = json.loads(Path(p).read_text())
        row = compare(spec, tc, out / "work" / re.sub(r"[^A-Za-z0-9_]", "_", spec["id"]))
        for k in ("expected", "family", "split"):
            if k in spec:
                row[k] = spec[k]
        return row
    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        rows = list(ex.map(one, a.specs))
    for r in rows:
        print(r["id"], r["verdict"], r["directions"], r.get("reason", ""), flush=True)
    (out / "multiocc_results.json").write_text(json.dumps({"rows": rows}, indent=1, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
