# FormalMATH triage, part 2: the 31 findings not in the ICML 2026 audit

Part 1 (`TRIAGE.md`) hand-checked 8 of the 39 certified findings that have no entry in the ICML 2026 audit's released per-item results. This file covers the other 31. Every one is already certified in Lean: the negation (or vacuity) of the unchanged statement is kernel-checked. This pass explains *why* each statement is false and checks the witness with exact arithmetic where the reason is arithmetic. Reproduce with `python3 triage_31.py`, which asserts all 31 checks and writes `triage_31.json`.

## Summary

| Category | Count |
|---|---:|
| Source problem or stated answer is wrong | 2 |
| Typo in the statement | 1 |
| Incorrect formalization (meaning changed) | 8 |
| Undeclared identifier became a variable (autoImplicit) | 2 |
| Binder / precedence scope error | 8 |
| Domain edge case not excluded (n = 0) | 2 |
| Lean-semantics artifact (missing side condition or wrong type) | 8 |
| **Total** | **31** |

**Headline.** Combined with part 1, **7** of the 39 findings outside the ICML audit show an error in the source problem or its stated answer, not only in the Lean encoding. Part 1 found 4 (three wrong or incomplete stated answers and one typo). Here are the other 3: `theorem_proving_zh_blue_1183` (the strict inequality is false at n = 1; the reference proof gives only ≥), `olymid-ref-base_9798` (the stated answer {1, 3, 6} contradicts the reference solution, which proves *every* n works), and `theorem_proving_zh_blue_1269` (a typo in part (2) present in both statements).

**Two new systematic patterns** worth reporting as classes, not one by one:

- **`%` on ℝ.** In Mathlib a field's remainder is `a % b = a − a·b/b = 0`, so any statement using `%` for a real fractional part or residue has left side 0 (3 findings).
- **`I` without `open Complex`.** autoImplicit turns `I` into a real variable, so a complex-number statement silently becomes a statement about every real `I` (2 findings).

**Caveat.** The reasons tagged *precedence*, *autoImplicit* and *`%` on ℝ* rest on how Lean elaborated the statement (the elaborated goals are recorded in `findings.jsonl`). The Lean certificates prove the statements false. The explanation of *why* is our reading of the elaborated goal and has not been separately certified.

## Source problem or stated answer is wrong (2)

| Row | Reason |
|---|---|
| `olymid-ref-base_9798` | The stated answer n ∈ {1, 3, 6} is wrong: the reference solution shows a suitable N exists for every n (N = (n+1)!² + 1). For n = 2, N = 13 already works: 14 and 15 are not prime powers. The Lean statement also has the → / ↔ scope error, which gives the n = 0 certificate. |
| `theorem_proving_zh_blue_1183` | The problem asks for a strict inequality, but at n = 1 both sides equal 3. The reference solution's AM-GM argument proves only ≥ (equality when n = 1). Separately, the Lean exponent 2 / n is natural-number division, so for n ≥ 3 the right side is 0. |

## Typo in the statement (1)

| Row | Reason |
|---|---|
| `theorem_proving_zh_blue_1269` | Part (2)'s first term is written 1/(1 + 1/(a+b)) in both the informal and Lean statements; the reference solution bounds 1/(1 + a + b). At a = b = c = 1 the typed version gives 4/3 > 1; the intended one gives 1. |

## Incorrect formalization (meaning changed) (8)

| Row | Reason |
|---|---|
| `aime_all_2007_II_4` | Production is modelled as separate per-product rates, so h1 forces a = 3 and h2 forces a = 2: the hypotheses contradict each other (VACUOUS). The problem shares worker-hours between widgets and whoosits in one equation. |
| `olymid-ref-base_506` | 'The number of these divisors' means the divisors other than n, but Lean counts n.divisors.card (n included). n = 1 then satisfies the hypothesis (0 + 1 = 1) but is not 2m². Under the informal reading n = 1 fails it. |
| `olymid-ref-base_6296` | Irrationality is encoded as ¬ ∃ x : ℚ, x = ∏' k, …, with the product itself computed in ℚ. '∃ x, x = t' is true for every t, so the statement is false regardless of the product. Needs the product in ℝ and ∃ q : ℚ, (q : ℝ) = …. |
| `olymid-ref-base_9952` | p(x) is defined as the least prime y with ¬ x ∣ y; the problem says the least prime NOT DIVIDING x (¬ y ∣ x). For x = 1 the Lean set is empty (1 divides everything), so sInf gives p 1 = 0, contradicting hp1 : p 1 = 2. The hypotheses are inconsistent (VACUOUS). |
| `omni_theorem_4152` | 'Largest k such that the property holds' is encoded as 'the property holds ↔ k = 1'. The property is downward closed, so k = 0 holds trivially (the empty index set) while 0 ≠ 1. Needs IsGreatest. |
| `omni_theorem_4254` | n is not bound inside the set; it became a theorem-level variable. At n = 0 both sums are empty, every C qualifies, and the set has no least element. (The C binder is also unused.) |
| `theorem_proving_zh_blue_679` | The problem asks for which n a 5-way equal-sum partition exists (answer: n = 5k or 5k − 1, k ≥ 2), but the Lean statement has no answer at all: it asserts every n works. False at n = 0, and also at n = 1 (sets summing to 1, 0, 0, 0, 0). |
| `theorem_proving_zh_blue_81` | The problem asks for which n a 5-way equal-sum partition exists (answer: n = 5k or 5k − 1, k ≥ 2), but the Lean statement has no answer at all: it asserts every n works. False at n = 0, and also at n = 1 (sets summing to 1, 0, 0, 0, 0). |

## Undeclared identifier became a variable (autoImplicit) (2)

| Row | Reason |
|---|---|
| `olymid-ref-base_3668` | The file opens Real but not Complex, so `I` is not the imaginary unit: autoImplicit made it a universally quantified real variable (the recorded goal shows a bare `I`). With I = 0 the statement fails. The mathematical answer is correct. (Check: with the true I the value is 1 + e^(−2 ln 2009) = 4036082/4036081.) |
| `quantitative_reasoning_zh_blue_52` | The file opens Real but not Complex, so `I` is not the imaginary unit: autoImplicit made it a universally quantified real variable (the recorded goal shows a bare `I`). With I = 0 the statement fails. The mathematical answer is correct. |

## Binder / precedence scope error (8)

| Row | Reason |
|---|---|
| `olymid-ref-base_10079` | '∀ n, cond → P n ↔ answer' parses as '(cond → P n) ↔ answer'. At n = 0 the left side is vacuously true and the answer is false. |
| `olymid-ref-base_10792` | The ∃ / ∀ binder extends to the end, swallowing the ↔: the statement reads 'cond ∧ ∃ x, (P x ↔ answer)'. At 0 the leading 'n > 0' (or 'k > 0') conjunct is false, so the whole statement is false. |
| `olymid-ref-base_2420` | '∀ n, cond → P n ↔ answer' parses as '(cond → P n) ↔ answer'. At n = 0 the left side is vacuously true and the answer is false. |
| `olymid-ref-base_5988` | The ∃ / ∀ binder extends to the end, swallowing the ↔: the statement reads 'cond ∧ ∃ x, (P x ↔ answer)'. At 0 the leading 'n > 0' (or 'k > 0') conjunct is false, so the whole statement is false. |
| `olymid-ref-base_9813` | '∀ n, cond → P n ↔ answer' parses as '(cond → P n) ↔ answer'. At n = 0 the left side is vacuously true and the answer is false. |
| `omni_theorem_1576` | The ∃ / ∀ binder extends to the end, swallowing the ↔: the statement reads 'cond ∧ ∃ x, (P x ↔ answer)'. At 0 the leading 'n > 0' (or 'k > 0') conjunct is false, so the whole statement is false. |
| `omni_theorem_3647` | The ∃ / ∀ binder extends to the end, swallowing the ↔: the statement reads 'cond ∧ ∃ x, (P x ↔ answer)'. At 0 the leading 'n > 0' (or 'k > 0') conjunct is false, so the whole statement is false. |
| `omni_theorem_4220` | The ∃ / ∀ binder extends to the end, swallowing the ↔: the statement reads 'cond ∧ ∃ x, (P x ↔ answer)'. At 0 the leading 'n > 0' (or 'k > 0') conjunct is false, so the whole statement is false. |

## Domain edge case not excluded (n = 0) (2)

| Row | Reason |
|---|---|
| `olymid-ref-base_2929` | Nothing excludes n = 0: the double sum is empty (0), the right side is 0, but n + 1 = 1 is not prime. The informal problem says 'integers n' and has the same gap; the intended domain is n ≥ 1. |
| `quantitative_reasoning_zh_blue_379` | At n = 0, Fin 0 → ℤ is the empty family: all conditions hold vacuously (0 = 0 · y²), so the right side is true while the left side (n > 0 ∧ …) is false. |

## Lean-semantics artifact (missing side condition or wrong type) (8)

| Row | Reason |
|---|---|
| `aime_all_1995_2` | `%` here is taken in ℝ, where Mathlib's field Euclidean-domain structure gives a % b = a − a·b/b = 0 for b ≠ 0. So the left side is 0. The informal answer is correct; the intended operation is the fractional part / integer remainder. (Check: product of roots is 1995² = 3980025.) |
| `olymid-ref-base_3256` | (3n² + 5)/8 is natural-number division: at n = 2 it truncates 17/8 to 2, which equals φ(1) + φ(2). The informal answer is correct. |
| `olymid-ref-base_7209` | a = b = c = 1 is allowed, and Lean's logb 1 1 = 0/0 = 0, so the hypothesis holds and the sum of cubes is 0. The problem implicitly needs bases ≠ 1. (These two rows are duplicates of the same problem.) |
| `omni_theorem_1467` | `%` here is taken in ℝ, where Mathlib's field Euclidean-domain structure gives a % b = a − a·b/b = 0 for b ≠ 0. So the left side is 0. The informal answer is correct; the intended operation is the fractional part / integer remainder. With k = 1, n = 101 the true fractional part gives exactly 1/2. |
| `omni_theorem_372` | v − e + f is computed in ℕ, where 9 − 16 truncates to 0, giving 9 ≠ 2. Over ℤ both parts hold. |
| `omni_theorem_745` | `%` here is taken in ℝ, where Mathlib's field Euclidean-domain structure gives a % b = a − a·b/b = 0 for b ≠ 0. So the left side is 0. The informal answer is correct; the intended operation is the fractional part / integer remainder. (Check: the integer residues sum to 1816, so 1816/6561 is right.) |
| `omni_theorem_919` | a = b = c = 1 is allowed, and Lean's logb 1 1 = 0/0 = 0, so the hypothesis holds and the sum of cubes is 0. The problem implicitly needs bases ≠ 1. (These two rows are duplicates of the same problem.) |
| `u-math_404` | x defaults to ℕ, so 49 − 77 truncates to 0 and x = 7 gives 28 ≠ 0. Over ℤ (or ℝ), x = 7 is a common root. |

## Not yet done

- The 72 findings that overlap the ICML audit (43 certified there, 29 flagged "maybe") have not been hand-reviewed.
- Nothing has been reported upstream.
