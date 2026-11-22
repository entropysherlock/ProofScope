"""Seeded generator for the SOTA-17 multi-occurrence evaluation (Track B). Deterministic.

Families
  step       hypothesis `f n + a ≤ f (n+1) ∧ f (n+1) ≤ f n + b` (or an equivalent spelling); formal
             claim with 2-4 sites
  lower      hypothesis `f n + a ≤ f (n+1)` (monotone, strictly monotone, ...); formal with 2-4 sites
  pointwise  hypothesis with one site `k * n + c`; formal with 2-3 sites
  outside    neither side in a supported class (the engine must abstain on both directions)

The spec carries `meta` (class parameters known to the generator). The engine never reads it; the
independent labeller uses it only to justify extending a finite prefix to a total function.
"""
import json
import random
from pathlib import Path

SEED = 20261111
OUT = Path(__file__).resolve().parent / "cases"
SITES = ["n", "(n + 1)", "(n + 2)", "(n + 3)", "(2 * n)", "(2 * n + 1)", "(3 * n)", "0", "5"]


def step_body(rng, a, b):
    forms = [f"f n + {a} ≤ f (n + 1) ∧ f (n + 1) ≤ f n + {b}",
             f"f (n + 1) ≤ f n + {b} ∧ f n + {a} ≤ f (n + 1)"]
    if a == b:
        forms.append(f"f (n + 1) = f n + {a}")
    if a == 0:
        forms.append(f"f n ≤ f (n + 1) ∧ f (n + 1) ≤ f n + {b}")
    return rng.choice(forms)


def lower_body(rng, a):
    forms = [f"f n + {a} ≤ f (n + 1)"]
    if a == 0:
        forms.append("f n ≤ f (n + 1)")
    if a == 1:
        forms.append("f n < f (n + 1)")
    return rng.choice(forms)


def atom(rng, sites, scale):
    i, j = rng.sample(range(len(sites)), 2)
    c = rng.choice([0, 1, 2, 3, scale, scale + 1, 2 * scale, 2 * scale + 1, 3 * scale])
    kind = rng.randrange(8)
    s, t = f"f {sites[i]}", f"f {sites[j]}"
    if kind == 0:
        return f"{s} ≤ {t} + {c}"
    if kind == 1:
        return f"{s} + {c} ≤ {t}"
    if kind == 2:
        return f"{s} < {t} + {c}"
    if kind == 3:
        return f"{s} = {t} + {c}"
    if kind == 4:
        return f"{s} ≠ {t}"
    if kind == 5:
        return f"{c} * n ≤ {s} + {t}"
    if kind == 6:
        return f"{s} % 2 = {t} % 2"
    return f"{s} + {t} ≤ 2 * f {sites[rng.randrange(len(sites))]} + {c}"


def formal(rng, nsites, scale):
    sites = rng.sample(SITES, nsites)
    while True:
        k = rng.choice([1, 1, 2, 2, 3])
        atoms = [atom(rng, sites, scale) for _ in range(k)]
        body = atoms[0]
        for x in atoms[1:]:
            body = f"({body}) {rng.choice(['∧', '∨'])} ({x})"
        if all(f"f {s}" in body for s in sites):
            break
    guard = rng.choice(["True", "True", "1 ≤ n", "3 ≤ n", "n % 2 = 0", "n ≤ 6"])
    return {"var": "n", "guard": guard, "body": body}


def pointwise(rng):
    k, c = rng.choice([(1, 0), (1, 0), (1, 2), (2, 0), (2, 1), (3, 1)])
    arg = "n" if (k, c) == (1, 0) else (f"{k} * n + {c}" if c else f"{k} * n")
    w = f"f ({arg})"
    rel = rng.choice([f"n ≤ {w}", f"{w} ≤ n + 2", f"n ≤ {w} ∧ {w} ≤ 2 * n + 1", f"{w} = n + 1",
                      f"{w} % 2 = 0", f"{w} % 2 = n % 2 ∧ {w} ≤ n + 3", f"{w} < 4", f"n < {w} ∨ {w} = 0",
                      f"{w} = 2 * n", f"{w} + 1 = n"])
    guard = rng.choice(["True", "True", "1 ≤ n", "2 ≤ n", "n % 2 = 1"])
    return {"var": "n", "guard": guard, "body": rel}, {"k": k, "c": c}


OUTSIDE = [
    ("f (n + 2) = f n + 2", "f (n + 4) = f n + 4"),
    ("f (n + 1) = f n + n", "f (n + 2) = f n + 2 * n + 1"),
    ("f (f n) = n", "f (f (f n)) = f n"),
    ("f (n + 1) = 2 * f n", "f (n + 2) = 4 * f n"),
    ("f n * f n = f (2 * n)", "f 0 * f 0 = f 0"),
    ("f (n + 1) + f n = 7", "f (n + 2) = f n"),
    ("f (2 * n) = f n", "f (4 * n) = f n"),
    ("f (n + 2) ≤ f n", "f (n + 4) ≤ f n"),
    ("f n + f (n + 1) ≤ f (n + 2)", "f n ≤ f (n + 2)"),
    ("f (n + 1) ≤ f n", "f (n + 2) ≤ f n"),
    ("f (n + 1) = f n + 1 ∨ f (n + 1) = f n + 3", "f (n + 2) ≠ f n + 3"),
    ("f (n + 1) % 2 = f n % 2", "f (n + 2) % 2 = f n % 2"),
    ("f (3 * n) = f n + 1", "f (9 * n) = f n + 2"),
    ("f (n + 3) = f n", "f (n + 6) = f n"),
    ("f n = f 0 + n ∧ f 0 = f 1", "f 2 = f 0 + 2"),
    ("f (n + 1) < f n + n", "f (n + 2) < f n + 2 * n + 1"),
    ("f (n + 1) = f n ∨ f n = 0 ∧ f (n + 2) = 1", "f (n + 3) ≤ f n + 1"),
    ("f (f n + 1) = n", "f (f 0 + 1) = 0"),
    ("f (n * n) = n", "f (4 * (n * n)) = 2 * n"),
    ("f (n + 2) + f n = 2 * f (n + 1)", "f (n + 4) + f n = 2 * f (n + 2)"),
]


def main():
    rng = random.Random(SEED)
    OUT.mkdir(exist_ok=True)
    for p in OUT.glob("*.json"):
        p.unlink()
    cases = []
    for i in range(40):
        a = rng.choice([0, 0, 1, 1, 2, 3])
        b = a + rng.choice([0, 0, 1, 2, 3])
        cases.append(("step", {"var": "n", "guard": "True", "body": step_body(rng, a, b)},
                      formal(rng, rng.choice([2, 2, 3, 3, 4]), max(a, 1)), {"a": a, "b": b}))
    for i in range(30):
        a = rng.choice([0, 0, 1, 1, 2])
        cases.append(("lower", {"var": "n", "guard": "True", "body": lower_body(rng, a)},
                      formal(rng, rng.choice([2, 2, 3, 3, 4]), max(a, 1)), {"a": a, "b": None}))
    for i in range(30):
        ref, meta = pointwise(rng)
        cases.append(("pointwise", ref, formal(rng, rng.choice([2, 2, 3]), 1), meta))
    for r, f in OUTSIDE:
        cases.append(("outside", {"var": "n", "guard": "True", "body": r}, {"var": "n", "guard": "True", "body": f}, {}))
    for i, (fam, ref, frm, meta) in enumerate(cases):
        spec = {"id": f"mo{i:03d}", "kind": "multi", "family": fam, "reference": ref, "formal": frm, "meta": meta}
        (OUT / f"mo{i:03d}.json").write_text(json.dumps(spec, ensure_ascii=False, sort_keys=True) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
