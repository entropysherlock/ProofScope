"""SOTA-16 evaluation cases for the linear one-occurrence function fragment (seeded; frozen before
the first run of the Presburger certificates on them). Harder than the SOTA-15 `func` group:
larger coefficients, congruences, two-sided and disjunctive relations, constant arguments.
The SOTA-15 `func` cases were used while developing SOTA-16 and are development data now."""
import json
import random
from pathlib import Path

SEED = 20261111
OUT = Path(__file__).resolve().parent / "cases" / "func_lin"

G = ["True", "True", "True", "1 ≤ n", "n % 2 = 0", "n % 3 = 1", "n < 4", "3 ≤ n", "2 ≤ n ∧ n % 2 = 1", "n ≠ 2"]
A = ["n", "n", "n + 1", "n + 3", "2 * n", "2 * n + 1", "3 * n", "3 * n + 2", "0", "4"]
R1 = ["n < w", "n ≤ w", "w < n", "w ≤ n", "w ≤ 2 * n + 1", "3 * n ≤ w", "w = n", "w = 2", "w ≠ n", "w % 2 = 0",
      "w % 3 = n % 3", "w + n ≥ 5", "w < 7", "n + 2 < w", "2 * w ≤ n", "n ≤ 2 * w", "w / 2 = n"]


def rel(rng):
    r = rng.random()
    if r < 0.55:
        return rng.choice(R1)
    a, b = rng.sample(R1, 2)
    return f"{a} {'∧' if r < 0.8 else '∨'} {b}"


def main():
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(120):
        side = lambda: {"var": "n", "guard": rng.choice(G), "arg": rng.choice(A), "rel": rel(rng)}
        ref = side()
        if rng.random() < 0.3:                          # adversarial: near-copy of the reference
            frm = dict(ref)
            frm[rng.choice(["guard", "arg", "rel"])] = side()[rng.choice(["guard", "arg", "rel"])] if False else None
            key = rng.choice(["guard", "arg", "rel"])
            frm = dict(ref)
            frm[key] = side()[key]
        else:
            frm = side()
        c = {"id": f"fl{i:03d}", "kind": "func", "reference": ref, "formal": frm}
        (OUT / f"{c['id']}.json").write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
