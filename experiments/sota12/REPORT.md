# SOTA-12 report: the fiber lemma behind coupled remainders

Caleb J. Westfall / WESTFALL program, 10 November 2026. Lean 4.34.1 core (no Mathlib). Every "Lean-checked" claim below
was accepted by the real checker in this session with exit code 0 and no `sorry`.

## 1. Your reduction is proved (Lean-checked, all positive a, b)
`lean/Fiber.lean`, theorem `westfall_reduction`: with `d = gcd(a, b*b)`,
`L(x) = a*(x % b) + b*((b*x) % a)` and `R(r) = b*(a-d) + a*r + b*((b*r) % d)`:
- for every x there is `0 <= r < b` with `L(x) <= R(r)` (take r = x % b), and
- for every `0 <= r < b` there is x with `L(x) = R(r)`.

So `max_x L = max_r R`. It is unconditional: Bezout's identity is proved in the same file (`bezout_nat`, `bezout_int`)
because Lean core lacks it. Axioms: propext, Classical.choice, Quot.sound.

## 2. The common structure: one lemma
**Fiber lemma (Lean-checked).** Let `m > 0`, `d > 0`, `d | m`, `d | c*B`. Then for every x
`(c*(x % B)) % d  <=  (c*x) % m  <=  m - d + (c*(x % B)) % d`  (`fiber_lower`, `fiber_upper`),
and if `c*B*u + m*v = d` (true for `d = gcd(m, c*B)`), both ends are attained on every residue class r mod B
(`fiber_attain_min`, `fiber_attain_max`).
In words: once x mod B is fixed, a multiplied remainder `(c*x) % m` is free to move only in steps of `gcd(m, c*B)`.
Your reduction is the case `c = B = b, m = a`. The SOTA-11 residue-gap law is the case `c = 1`.
**This is a statement about cosets of a cyclic subgroup; the mathematics is classical.**

## 3. Eliminating the linear search for M(a,b)
Let `d = gcd(a, b^2)`, `e = gcd(b, d)`, `n = d/e`.
- **Structure lemma (paper proof; checked on all 4,900 pairs a,b <= 70):** `n | e`, hence `d | e^2` and `n <= sqrt(d)`.
  Proof: `gcd(n, b/e) = 1` and `n | b*(b/e)`, so `n | b`; also `n | d`; so `n | gcd(b,d) = e`.
- **Reduced form:** with `C = -(b/e) mod n`,
  `M(a,b) = b*(a-d) + a*(b-1) + max over 1 <= t <= n of [ b*e*((C*t) mod n) - a*(t-1) ]`.
  The search drops from b values to at most `sqrt(gcd(a, b^2))`.
- **Closed forms:** if `d | b` (equivalently `gcd(a,b^2) = gcd(a,b)`): `M = 2ab - a - b*gcd(a,b)`. This is exactly the
  formula SOTA-11 fitted and then saw refuted: it is right on 4,350 of 4,900 pairs and wrong precisely when `gcd(a,b^2) > gcd(a,b)`.
  If `a >= b*(d - e)`: `M = b*(a-d) + a*(b-1) + b*((-b) mod d)`.
- **Euclidean algorithm:** `max_lin_mod` in `mfast.py` maximises `B*((C*t) mod n) - A*t` in O(log n) steps by walking
  the successive-maximum records of `C*t mod n` (subtractive Euclid on the two gaps). `M_fast` uses it.

Evidence (not Lean-checked; exhaustive or randomized comparison with brute force):
all 4,900 pairs `1 <= a,b <= 70`: 0 mismatches for your reduction, the sqrt form, `M_fast`, and both closed forms;
200,000 random tests of `max_lin_mod`: 0 mismatches; 20-digit inputs with n = 14,348,907 evaluate instantly.
The record technique itself is a known continued-fraction method.

## 4. The 17 unexplained families
All 17 (the 16 unfitted plus the refuted one) reduce by the fiber lemma. They fall into three types:
- single residue (no coupling at all; the fitter failed only because the answer is piecewise): 6 families;
- weighted CRT with parameter-dependent weights: 4 families;
- genuinely fiber-coupled, including nested `(x % a) % b` against `x % b`: 7 families.

## 5. SHARPEN-REDUCE: reductions generated and proved automatically
`reduce.py` takes a family expression, picks a base modulus per variable, rewrites r-determined terms, replaces the one
coupled term by its fiber extremum, checks the result against brute force on 121 parameter pairs, and writes a Lean
theorem for **all** positive a, b by instantiating `Fiber.lean`.

| Input set | Reduced | Numeric check (max and min) | Lean theorems accepted |
| --- | --- | --- | --- |
| 17 unexplained families | 17 | 17 | 34 of 34 |
| all 74 bounded SOTA-11 families | 72 (2 use division) | 72 | 144 of 144 |
| 300 fresh random remainder families | 297 | 297 | 594 of 594 |

For your family the tool chose the other base and produced a second, different reduction on its own:
`max_x L = max over 0 <= r < a of [ b*((b*r) % a) + a*(b - g + r % g) ]`, `g = gcd(a,b)` (Lean-checked as a bound, numerically exact).

What the generated Lean theorems state: the pointwise bounds `E(x) <= Rmax(x % B)` and `Rmin(x % B) <= E(x)` for all a, b.
Attainment is covered by the general `fiber_attain_*` theorems but is **not** instantiated per family; exactness per
family rests on the numeric check.

## 6. Refuted generalizations and limits
- **Two coupled terms do not add** (Lean-checked, `lean/Refuted.lean`): on the class x even, `x % 3` and `(2x) % 3`
  each reach 2, but `x % 3 + (2x) % 3 <= 3` always. The true statement needs a 2-dimensional lattice, not two fiber lemmas.
- The reducer fails on 3 of 300 fresh families, all containing both `(y % a) % b` and `(y % b) % a`.
- The O(log) algorithm covers M(a,b) and the homogeneous single-residue case only. For the general inhomogeneous
  single-residue problem the tool still scans one modulus.
- No closed form for M(a,b) in the generic regime (470 of 4,900 pairs); I believe none exists short of the Euclid recursion, but have not proved that.
- Division families and anything outside remainders: untouched.
- Mission item 7 (beyond modular arithmetic): not executed. The pattern "fix part of the input so most of the expression is constant, replace the rest by its exact extremum on that fiber, certify both directions" is general, but I have no evidence for it outside this domain.

## 7. Assessment: Level 3 at most for the method, Level 2 for the mathematics
Solid: a formally verified general lemma, an unconditional proof of your reduction, an exact fast algorithm with a new-to-us
structure lemma, and a tool that produced 772 general-parameter Lean theorems without human-written proofs.
Not Level 4: the fiber lemma is elementary group theory, the record algorithm is a known technique, and I ran no literature search,
so nothing here is established as novel.

## 8. Next frontier
Two or more coupled terms: maximise a linear form over a coset of a cyclic subgroup of `Z_m1 x Z_m2`. That is a
2-dimensional lattice problem, the first case where one fiber lemma is provably not enough, and the natural place to look for
mathematics that is not a corollary of CRT.

## Reproduce
`lean lean/Fiber.lean`; `python3 mfast.py`; `python3 reduce.py unexplained17.json out.json` (set `LEAN=` to your binary; needs only Python 3 and Lean 4).