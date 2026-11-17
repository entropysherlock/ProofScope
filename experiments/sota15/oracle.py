"""Ground truth for bounded Horn specs by exhaustive enumeration of interpretations.

Independent of the engine's saturation: for each direction it enumerates every interpretation of the
predicate symbols on the finite universe `[0..M]^k` (M = largest term value that occurs) and evaluates
the two schemas directly. Shares only the expression parser/evaluator with the engine.
"""
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from proofscope.scope_expr import evaluate, parse  # noqa: E402


def _envs(c):
    out = [dict()]
    for n, b in c.get("vars", []):
        out = [{**e, n: v} for e in out for v in range(evaluate(parse(str(b)), e))]
    return out


def _atoms(c, env):
    al = list(c.get("prems", [])) + [c["concl"]]
    for l in c.get("locals", []):
        al += l["prems"] + [l["concl"]]
    return [(a[0], tuple(evaluate(parse(str(t)), env) for t in a[1])) for a in al]


def _holds(c, env, I):
    at = lambda a: (a[0], tuple(evaluate(parse(str(t)), env) for t in a[1])) in I
    if not evaluate(parse(c.get("guard", "True")), env):
        return True
    if not all(at(a) for a in c.get("prems", [])):
        return True
    for l in c.get("locals", []):
        if all(at(a) for a in l["prems"]) and not at(l["concl"]):
            return True
    return at(c["concl"])


def truth(spec, limit=20):
    cl = spec["reference"] + spec["formal"]
    used = {a for c in cl for e in _envs(c) for a in _atoms(c, e)}
    m = max([v for a in used for v in a[1]] + [0])
    universe = [(s, t) for s, k in spec["symbols"].items() for t in itertools.product(range(m + 1), repeat=k)]
    universe = [a for a in universe if a in used]          # atoms never mentioned cannot matter
    if len(universe) > limit:
        return None
    sat = lambda side, I: all(_holds(c, e, I) for c in spec[side] for e in _envs(c))
    fwd = bwd = True
    for bits in itertools.product([False, True], repeat=len(universe)):
        I = {a for a, b in zip(universe, bits) if b}
        r, f = sat("reference", I), sat("formal", I)
        fwd &= (not r) or f
        bwd &= (not f) or r
        if not fwd and not bwd:
            break
    return {"fwd": "ENTAILS" if fwd else "SEPARATED", "bwd": "ENTAILS" if bwd else "SEPARATED", "atoms": len(universe)}


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, truth(json.loads(Path(p).read_text())))
