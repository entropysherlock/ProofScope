"""SOTA-15 evaluation cases: seeded random generator (frozen before the first engine run on them).

Writes native ScopeElim specs (bounded Horn, symbolic Horn, one-occurrence function) and
ClaimDelta-format cases. No expected labels are written here: ground truth comes from
`oracle.py` (exhaustive model enumeration, bounded Horn only) and `z3_check.py` (independent solver).
Terms avoid truncated subtraction so the Z3 encoding over the integers is exact.
"""
import json
import random
from pathlib import Path

SEED = 20261110
OUT = Path(__file__).resolve().parent / "cases"


def bounded(rng, i):
    shape = rng.choices(["S", "ST", "E"], [0.6, 0.25, 0.15])[0]
    if shape == "E":
        syms, n = {"E": 2}, 3
        t = ["x", "y", "0", "1", "2"]
        atom = lambda: ["E", [rng.choice(t), rng.choice(t)]]
        vars_ = lambda: [["x", str(n)], ["y", rng.choice([str(n), "x + 1"])]]
        guards = ["True", "True", "x < y", "x ≠ y", "x = y"]
    else:
        syms = {"S": 1} if shape == "S" else {"S": 1, "T": 1}
        n = rng.choice([3, 4, 5]) if shape == "S" else 3
        t = ["x", "x", "x + 1", "x + 2", "0", "1", "2 * x", "x % 2", "x / 2"]
        atom = lambda: [rng.choice(list(syms)), [rng.choice(t)]]
        vars_ = lambda: [["x", rng.choice([str(n), str(n), str(n - 1), "0"]) if rng.random() < 0.15 else str(n)]]
        guards = ["True", "True", "True", "x % 2 = 0", "1 ≤ x", "x < 2", "x ≠ 1", "False"]

    def clause(local_ok):
        c = {"vars": vars_(), "guard": rng.choice(guards),
             "prems": [atom() for _ in range(rng.choice([0, 1, 1, 1, 2]))], "concl": atom()}
        if local_ok and rng.random() < 0.2:
            c["locals"] = [{"prems": [atom()], "concl": atom()}]
        return c
    ref = [clause(False) for _ in range(rng.choice([1, 1, 2, 3]))]
    if rng.random() < 0.3:                     # adversarial: formal is a re-use or a perturbation of a rule
        base = json.loads(json.dumps(rng.choice(ref)))
        if rng.random() < 0.5 and base["prems"]:
            base["concl"] = atom()
        frm = [base]
    else:
        frm = [clause(True) for _ in range(rng.choice([1, 1, 2]))]
    return {"id": f"hb{i:03d}", "kind": "horn", "symbols": syms, "reference": ref, "formal": frm}


def symbolic(rng, i):
    g = ["True", "True", "True", "1 ≤ x", "x % 2 = 0", "2 ≤ x"]
    t = lambda: rng.choice(["x", "x", "x + 1", "x + 2", "x + 3", "0", "1"])

    def clause():
        return {"vars": [["x", None]], "guard": rng.choice(g),
                "prems": [["S", [t()]] for _ in range(rng.choice([0, 1, 1, 1, 1, 2]))], "concl": ["S", [t()]]}
    return {"id": f"hs{i:03d}", "kind": "horn", "symbols": {"S": 1},
            "reference": [clause() for _ in range(rng.choice([1, 1, 2]))], "formal": [clause()]}


_G = ["True", "True", "True", "1 ≤ n", "n % 2 = 0", "n < 3", "2 ≤ n"]
_A = ["n", "n", "n", "n + 1", "n + 2", "2 * n", "0", "3"]
_R = ["n < w", "n ≤ w", "w < n", "w ≤ n", "w ≤ n + 2", "w = 0", "w = n", "w ≠ n", "n < w ∨ n = 2",
      "w % 2 = 0", "w + n ≥ 3", "w < 5", "n + 1 < w", "2 * n ≤ w"]


def func(rng, i):
    c = lambda: {"var": "n", "guard": rng.choice(_G), "arg": rng.choice(_A), "rel": rng.choice(_R)}
    return {"id": f"fn{i:03d}", "kind": "func", "reference": c(), "formal": c()}


def claimdelta(rng, i):
    if rng.random() < 0.6:                     # once-occurring symbol: 2 ^ (arg)
        def side():
            a = rng.choice(["n", "n", "n + 1", "n + 2", "2 * n"])
            r = rng.choice([x for x in _R if "w" in x])
            return rng.choice(_G), r.replace("w", f"2 ^ ({a})")
    else:                                      # definite clauses over the atom `Nat.gcd t 6 = 1`
        def side():
            at = lambda: f"Nat.gcd ({rng.choice(['n', 'n', 'n + 1', 'n + 2', 'n + 3'])}) 6 = 1"
            h = at() if rng.random() < 0.7 else f"{rng.choice(['1 ≤ n', 'n % 2 = 0'])} ∧ {at()}"
            return h, at()
    (rh, rc), (lh, lc) = side(), side()
    return {"id": f"cd{i:03d}", "family": "sota15", "split": "sota15_eval", "binders": [["n", "Nat"]],
            "ref_hyp": rh, "ref_concl": rc, "lean_hyp": lh, "lean_concl": lc}


def main():
    rng = random.Random(SEED)
    for name, gen, n in [("horn_bounded", bounded, 60), ("horn_symbolic", symbolic, 30), ("func", func, 40),
                         ("claimdelta", claimdelta, 30)]:
        d = OUT / name
        d.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            c = gen(rng, i)
            (d / f"{c['id']}.json").write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
