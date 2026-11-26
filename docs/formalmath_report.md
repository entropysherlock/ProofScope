# Certified defects in FormalMATH: a report for the maintainers

> **DRAFT. Not yet sent to the FormalMATH maintainers.** It has not been posted anywhere except this page. Author: Caleb J. Westfall (ProofScope). Prepared with Claude (Anthropic) as the engineering assistant.

## Summary

We ran an automated defect search over all 5,560 statements in `SphereLab/FormalMATH-All` (revision `8eea2550`). It found **111 statements that Lean proves false or vacuous exactly as written**. Each finding was re-proved in a clean module with standard axioms only and replayed by `leanchecker`. A prover can never solve these items.

For **39** of the 111, the ICML 2026 audit of FormalMATH (Ammanamanchi, Bhat and Biderman) has no entry in its released per-item results. We hand-checked all 39. This report covers those 39.

- **7** show an error in the source problem or its stated answer, not only in the Lean encoding.
- **11** change the meaning of the problem in the formalization.
- **2 systematic Lean patterns** that probably affect many more items than we found.

## Method and controls

1. Each statement is loaded unchanged into a Lean REPL with Mathlib (Lean 4.34.1, Mathlib `d13f23b`).
2. The search tries to prove the negation of the statement as written, then tries to prove the hypotheses contradictory.
3. Every candidate is certified in a clean module. `#print axioms` must show only `propext`, `Classical.choice` and `Quot.sound`, and `leanchecker` must replay it.
4. Planted-defect controls run alongside: two planted false statements and one planted vacuous statement were certified, and a true statement was not flagged. All controls passed.
5. The 8 hand-checked findings from the first pass were also verified on FormalMATH's own environment (Lean 4.11.0, Mathlib `8edf04f`).

Result: 111 certified, 5,325 searched with nothing found, 74 did not compile on our Mathlib version, 4 searches were cut short, 46 skipped. **Finding nothing is not evidence that a statement is correct.** The same hunt found 0 defects in PutnamBench (672 statements).

## A. Errors in the source problem or its stated answer (7)

| Row | What is wrong | Evidence |
|---|---|---|
| `olymid-ref-base_1859` | The stated answer is "no solution", but (a, b, c) = (0, 1, 1) satisfies all three equations. | The dataset's reference solution lists solutions. Standalone certificate and reviewer demo included. |
| `olymid-ref-base_918` | The stated answer gives only x = −1/1992. x = 0 is also a solution. | The reference solution says "Obviously, x = 0 is a solution". |
| `olymid-ref-base_10553` | The answer fixes an order. (1, −1, 1) solves the system but is not in the stated families. | The reference solution ends "and all permutations". |
| `olymid-ref-base_9798` | The stated answer {1, 3, 6} is wrong. | The reference solution proves a suitable N exists for every n, with N = (n+1)!² + 1. For n = 2, N = 13 works (14 and 15 are not prime powers). |
| `theorem_proving_zh_blue_1183` | The problem asks for a strict ">" inequality. At n = 1 both sides equal 3. | The reference proof (AM-GM) only establishes "≥". |
| `theorem_proving_zh_blue_988` | Typo: (1 − y) where the identity has (1 − y²). | The reference solution proves the (1 − y²) form. The statement fails at (0, −1, −1). |
| `theorem_proving_zh_blue_1269` | Part (2), first term, is written 1/(1 + 1/(a+b)) instead of 1/(1 + a + b). | At a = b = c = 1 the typed version gives 4/3 > 1. The reference solution bounds 1/(1 + a + b). |

In 1183, the Lean exponent `2 / n` is also natural-number division. That is a second, independent defect.

## B. The formalization changes the problem (11)

| Row | What is wrong |
|---|---|
| `theorem_proving_zh_blue_1350` | The problem asks for the equality cases. The Lean statement asserts "iff x = y = z", which fails at (0, 1, 1). |
| `olymid-ref-base_2124` | The Lean statement adds x = 0 as an equality case. There 1 ≠ 0. The reference solution says x = 1 only. |
| `omni_theorem_3461` | "Not equivalent" is encoded as ∀ x, ¬(…). The two expressions agree at x = 0. |
| `aime_all_2007_II_4` | Production is modelled as separate per-product rates, so h1 forces a = 3 and h2 forces a = 2: the hypotheses contradict each other (VACUOUS). The problem shares worker-hours between widgets and whoosits in one equation. |
| `olymid-ref-base_506` | 'The number of these divisors' means the divisors other than n, but Lean counts n.divisors.card (n included). n = 1 then satisfies the hypothesis (0 + 1 = 1) but is not 2m². Under the informal reading n = 1 fails it. |
| `olymid-ref-base_6296` | Irrationality is encoded as ¬ ∃ x : ℚ, x = ∏' k, …, with the product itself computed in ℚ. '∃ x, x = t' is true for every t, so the statement is false regardless of the product. Needs the product in ℝ and ∃ q : ℚ, (q : ℝ) = …. |
| `olymid-ref-base_9952` | p(x) is defined as the least prime y with ¬ x ∣ y; the problem says the least prime NOT DIVIDING x (¬ y ∣ x). For x = 1 the Lean set is empty (1 divides everything), so sInf gives p 1 = 0, contradicting hp1 : p 1 = 2. The hypotheses are inconsistent (VACUOUS). |
| `omni_theorem_4152` | 'Largest k such that the property holds' is encoded as 'the property holds ↔ k = 1'. The property is downward closed, so k = 0 holds trivially (the empty index set) while 0 ≠ 1. Needs IsGreatest. |
| `omni_theorem_4254` | n is not bound inside the set; it became a theorem-level variable. At n = 0 both sums are empty, every C qualifies, and the set has no least element. (The C binder is also unused.) |
| `theorem_proving_zh_blue_679` | The problem asks for which n a 5-way equal-sum partition exists (answer: n = 5k or 5k − 1, k ≥ 2), but the Lean statement has no answer at all: it asserts every n works. False at n = 0, and also at n = 1 (sets summing to 1, 0, 0, 0, 0). |
| `theorem_proving_zh_blue_81` | The problem asks for which n a 5-way equal-sum partition exists (answer: n = 5k or 5k − 1, k ≥ 2), but the Lean statement has no answer at all: it asserts every n works. False at n = 0, and also at n = 1 (sets summing to 1, 0, 0, 0, 0). |

## C. Missing assumptions and domain edge cases (3)

| Row | What is wrong |
|---|---|
| `theorem_proving_zh_blue_1245` | The informal statement is about a triangle's sides. The Lean statement has no triangle or positivity conditions. (0, 0, 1) violates the inequality. |
| `olymid-ref-base_2929` | Nothing excludes n = 0: the double sum is empty (0), the right side is 0, but n + 1 = 1 is not prime. The informal problem says 'integers n' and has the same gap; the intended domain is n ≥ 1. |
| `quantitative_reasoning_zh_blue_379` | At n = 0, Fin 0 → ℤ is the empty family: all conditions hold vacuously (0 = 0 · y²), so the right side is true while the left side (n > 0 ∧ …) is false. |

## D. Systematic Lean patterns (18 findings, many more items likely)

These are the most useful part for a benchmark maintainer, because each can be searched for across all 5,560 statements.

**D1. Precedence and binder scope (8).** `∀ n, 0 < n → P n ↔ answer` parses as `(0 < n → P n) ↔ answer`. At n = 0 the left side is vacuously true. A trailing `n > 0 ∧ ∃ x, … ↔ answer` binds the `↔` inside the `∃`, so the statement is false at n = 0. A bracketing check would find these.

| Row | |
|---|---|
| `olymid-ref-base_10079` | implication scope |
| `olymid-ref-base_10792` | binder swallows the ↔ |
| `olymid-ref-base_2420` | implication scope |
| `olymid-ref-base_5988` | binder swallows the ↔ |
| `olymid-ref-base_9813` | implication scope |
| `omni_theorem_1576` | binder swallows the ↔ |
| `omni_theorem_3647` | binder swallows the ↔ |
| `omni_theorem_4220` | binder swallows the ↔ |

**D2. `%` on ℝ is always 0 (3).** In Mathlib, a field's remainder satisfies `a % b = a − a·b/b = 0` for `b ≠ 0`. Statements that use `%` for a real fractional part or residue therefore have a left side of 0: `aime_all_1995_2`, `omni_theorem_1467`, `omni_theorem_745`.

**D3. `I` without `open Complex` (2).** autoImplicit turns `I` into a universally quantified real variable, so a complex-number statement silently becomes a statement about every real `I`: `olymid-ref-base_3668`, `quantitative_reasoning_zh_blue_52`. The mathematical answers are correct.

**D4. Other Lean-semantics artifacts (5).** Natural-number subtraction or division where the problem needs ℤ or ℝ (`omni_theorem_372`, `u-math_404`, `olymid-ref-base_3256`), and `logb 1 1 = 0` with a missing base ≠ 1 condition (`olymid-ref-base_7209` and `omni_theorem_919`, which are the same problem).

## E. Overlap with the ICML 2026 audit

Each of the 111 findings was matched by problem id against the audit's released per-item file (`results/formalmath@all/results.jsonl`, branch `v4.28_icml_review` of `Shashi456/atp-checkers`).

| ICML 2026 status | Our certified findings |
|---|---:|
| Certified by the audit | 43 |
| Flagged "maybe" by the audit | 29 |
| No entry in the audit's results | **39** |

This is evidence about one audit's released results only. It does not show that nobody else has reported these items. We have not hand-reviewed the 72 overlapping findings.

## F. What we are claiming, and what we are not

- **Claimed:** the 111 statements are false or vacuous as written, certified by Lean. The 39 listed here are not in one prior audit's released results. The 7 errors in section A are supported by the dataset's own reference solutions or by direct arithmetic.
- **Not claimed:** that the explanations in sections B to D are the only reading. They rest on how Lean elaborated each statement (elaborated goals are in `findings.jsonl`). Lean certifies *that* the statements are false, not *why*. We recommend a maintainer confirm D1 to D3 on a few items before bulk-fixing.
- **Not claimed:** that FormalMATH has only these defects. 74 statements did not compile on our Mathlib version.

## Reproduce

Everything is in the repository under [`experiments/defect_hunt/formalmath/`](https://github.com/entropysherlock/ProofScope/tree/main/experiments/defect_hunt/formalmath):

- [`findings.jsonl`](https://github.com/entropysherlock/ProofScope/blob/main/experiments/defect_hunt/formalmath/findings.jsonl): all 111 findings with Lean certificates.
- [`TRIAGE.md`](https://github.com/entropysherlock/ProofScope/blob/main/experiments/defect_hunt/formalmath/TRIAGE.md) and [`TRIAGE_31.md`](https://github.com/entropysherlock/ProofScope/blob/main/experiments/defect_hunt/formalmath/TRIAGE_31.md): the hand checks.
- `triage.py`, `triage_31.py`: exact-arithmetic witness checks.
- [`demo_1859/`](https://github.com/entropysherlock/ProofScope/tree/main/experiments/defect_hunt/formalmath/demo_1859): a reviewer demo with a pinned Lean 4.11.0 project and `reproduce.sh`.
- [`proofscope/defect_hunt.py`](https://github.com/entropysherlock/ProofScope/blob/main/proofscope/defect_hunt.py): the search engine.

## Suggested fixes

For the 7 source errors, correct the stated answer or statement against the reference solution. For D1 to D3, add a linter pass that flags `→ … ↔` without parentheses, `%` on ℝ, and `I` in files that do not open `Complex`.
