"""Triage of the certified FormalMATH findings (run 44002011370).

1. Automatic split: does the statement use an operation Lean totalizes (division, inverse, log, sqrt, floor, %, tan, ...)
   or natural-number subtraction? Those findings may be Lean-semantics artifacts (e.g. x / 0 = 0), which are still real
   defects of the formal benchmark (the theorem is false as written) but often mean a missing side condition rather than
   a wrong mathematical answer.
2. Hand-picked findings re-checked here with exact rational arithmetic, independently of Lean.
"""
import json, math, re
from fractions import Fraction as Q
from pathlib import Path

D = Path(__file__).parent
F = [json.loads(l) for l in (D / "findings.jsonl").read_text().splitlines() if l.strip()]
TOTALIZED = re.compile(r"/|⁻¹|log|√|sqrt|⌊|⌈|%|tan|Real\.cos θ|Nat\.sub|\bdiv\b|logb")
rows = []
for f in F:
    text = " ".join(f["hypotheses"]) + " " + f["formal_goal"]
    cat = "TOTALIZED_OP" if TOTALIZED.search(text) else "PURE"
    rows.append((f["id"], f["kind"], cat, f["novelty"].split(" — ")[0]))


def check():
    out = {}
    x, y, z = 0, -1, -1
    out["fm_theorem_proving_zh_blue_988"] = (
        x*y + y*z + z*x == 1
        and x*(1-y)*(1-z**2) + y*(1-z)*(1-x**2) + z*(1-x**2)*(1-y**2) != 4*x*y*z
        and x*(1-y**2)*(1-z**2) + y*(1-z**2)*(1-x**2) + z*(1-x**2)*(1-y**2) == 4*x*y*z,
        "typo: (1 - y) where the textbook identity has (1 - y²); at (0, -1, -1) the hypothesis holds and the formal "
        "equation fails, while the correct identity holds")
    a, b, c = 0, 0, 1
    out["fm_theorem_proving_zh_blue_1245"] = (
        a**3 + b**3 + c**3 - 2*(a*a*(b+c) + b*b*(c+a) + c*c*(a+b)) + 9*a*b*c > 0,
        "the triangle condition on a, b, c is missing; (0, 0, 1) violates the inequality")
    x, y, z = 0, 1, 1
    out["fm_theorem_proving_zh_blue_1350"] = (
        x*(y+z-x)**2 + y*(z+x-y)**2 + z*(x+y-z)**2 == 3*x*y*z and not (x == y == z),
        "equality also holds at (0, 1, 1), so 'equality iff x = y = z' is wrong")
    x = 0
    out["fm_olymid-ref-base_2124"] = (1 + x**2 + x**6 + x**8 != 4*x**4,
        "x = 0 is listed as an equality case, but 1 ≠ 0 there")
    a, b, c = 0, 1, 1
    out["fm_olymid-ref-base_1859"] = (a*b + b*c + c*a == 1 and a*a*b + c == b*b*c + a == c*c*a + b,
        "the stated answer is 'no solution', but (0, 1, 1) solves the system")
    x = Q(0)
    out["fm_olymid-ref-base_918"] = (math.floor(x) * (x - math.floor(x)) == 1991 * x,
        "x = 0 also solves [x]·{x} = 1991x; the stated answer gives only -1/1992")
    a, b, c = Q(1), Q(-1), Q(1)
    out["fm_olymid-ref-base_10553"] = (
        a+b+c == 1/a + 1/b + 1/c and a*a + b*b + c*c == 1/a**2 + 1/b**2 + 1/c**2
        and not ((c == 1 or c == -1) and b == 1/a),
        "(1, -1, 1) solves the system but is not in the stated families (the answer fixes an order)")
    out["fm_omni_theorem_3461"] = (3*0 + 6 == Q(1, 3)*(3*0) + Q(2, 3)*9,
        "'not equivalent' is formalized as ∀ x; the expressions agree at x = 0 (needs ∃ x / function inequality)")
    return out


if __name__ == "__main__":
    import collections
    print(len(rows), "certified findings;", dict(collections.Counter((k, c) for _, k, c, _ in rows)))
    for k, (ok, why) in check().items():
        assert any(r[0] == k for r in rows), k
        print(("CONFIRMED " if ok else "NOT CONFIRMED ") + k + ": " + why)
    (D / "triage.json").write_text(json.dumps([dict(zip(("id", "kind", "operations", "witness"), r)) for r in rows], indent=1, ensure_ascii=False))
