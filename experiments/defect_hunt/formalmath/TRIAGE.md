# FormalMATH certified-defect triage

The run is [44002011370](https://github.com/entropysherlock/ProofScope/actions/runs/44002011370), engine commit `4548c41`, on the Lean 4.34.1 and Mathlib `d13f23b` setup. Planted-defect controls **PASS**: two planted FALSE statements and one planted VACUOUS statement were certified, and a true statement was not flagged.

## Counts

| | Count |
|---|---:|
| FormalMATH-All statements checked | 5,560 |
| Searched, no defect found (not evidence of correctness) | 5,325 |
| **Certified defects** | **111** |
| — FALSE: Lean proves the negation of the statement as written | 106 |
| — VACUOUS: the hypotheses contradict each other | 5 |
| — counterexample uses real or rational values | 29 |
| — counterexample uses integer or natural-number values | 77 |
| — uses an operation Lean totalizes (`/`, log, √, floor, …) | 60 |
| — uses no such operation | 51 |
| Did not compile on our Mathlib version (version drift) | 74 |
| Search cut short (resource limit) | 4 |
| Skipped (no theorem, placeholder, universe-polymorphic) | 46 |

**What "certified" means.** For every defect, a clean Lean module re-proves the negation (or vacuity) of the **unchanged** benchmark statement. `#print axioms` shows only the standard axioms, and `leanchecker` replays the module. The proofs are in `findings.jsonl`.

**Caveat on Lean semantics.** A finding that uses an operation Lean totalizes (for example `x / 0 = 0`) is still a real defect of the formal benchmark: the theorem cannot be proved. It often reflects a missing side condition rather than a wrong mathematical answer.

## Hand-checked findings

Each of these was re-checked independently of Lean with exact arithmetic (`triage.py`). Several show that the **benchmark's stated answer is wrong or incomplete**, not just its Lean encoding.

| Finding | What is wrong |
|---|---|
| `fm_olymid-ref-base_1859` | The stated answer is "no solution", but (a, b, c) = (0, 1, 1) satisfies ab + bc + ca = 1 and a²b + c = b²c + a = c²a + b. |
| `fm_olymid-ref-base_918` | x = 0 also solves [x]·{x} = 1991x; the stated answer gives only −1/1992. |
| `fm_olymid-ref-base_10553` | (1, −1, 1) solves the system but is not in the stated solution families, because the answer fixes an order. |
| `fm_theorem_proving_zh_blue_1350` | Equality also holds at (0, 1, 1), so "equality iff x = y = z" is wrong. |
| `fm_olymid-ref-base_2124` | x = 0 is claimed as an equality case of 1 + x² + x⁶ + x⁸ ≥ 4x⁴, but there 1 ≠ 0. |
| `fm_theorem_proving_zh_blue_988` | Typo: (1 − y) where the textbook identity has (1 − y²). The formal equation fails at (0, −1, −1); the correct identity holds there. |
| `fm_theorem_proving_zh_blue_1245` | The triangle condition on a, b, c is missing; (0, 0, 1) violates the inequality. |
| `fm_omni_theorem_3461` | "Not equivalent" is formalized as ∀ x, but the two expressions agree at x = 0. |

## Overlap with the ICML 2026 audit (checked against its released per-item results)

The audit by Ammanamanchi, Bhat and Biderman (ICML 2026) published per-item FormalMATH-All results: [atp-checkers](https://github.com/Shashi456/atp-checkers), branch `v4.28_icml_review`, file `results/formalmath@all/results.jsonl`. Each of our 111 findings was matched to that file by problem id. The full table is in `icml2026_overlap.json`.

| ICML 2026 status of the row | Our certified findings |
|---|---:|
| Certified ("proven") by the ICML audit | 43 |
| Flagged by the ICML audit as "maybe" (not certified) | 29 |
| No finding in the ICML audit's results | 39 |

None of the 8 hand-checked findings has a finding in that file, and none appears in the audit's annotation files. This is evidence about one audit's released results only. It does not show that nobody else has reported these items.

## Classification of the 8 hand-checked findings

The witnesses were checked against the informal statement (`refined_statement`), the intended domain, and the dataset's own reference solution (`solution`). Certificates are in `certificates/` and verified in [run 44006962915](https://github.com/entropysherlock/ProofScope/actions/runs/44006962915) on Lean 4.11.0 with Mathlib `8edf04f` (FormalMATH's environment) and on Lean 4.34.1 with Mathlib `d13f23b`, where `leanchecker` also replays them.

| Row | Category | Evidence |
|---|---|---|
| olymid-ref-base_1859 | Wrong stated answer | The answer "None" is contradicted by (0, 1, 1) and by the reference solution, which lists the solutions. |
| olymid-ref-base_918 | Wrong stated answer (incomplete) | The reference solution says "Obviously, x = 0 is a solution"; the stated answer gives only −1/1992. |
| olymid-ref-base_10553 | Wrong stated answer (incomplete) | The reference solution ends "and all permutations"; the stated answer and the Lean statement drop the permutations. |
| theorem_proving_zh_blue_988 | Incorrect statement (typo) | The statement has (1 − y)(1 − z²) and (1 − z)(1 − x²); the reference solution proves the (1 − y²)(1 − z²) form. |
| theorem_proving_zh_blue_1350 | Incorrect formalization | The informal problem asks for the equality cases; the Lean statement asserts "iff x = y = z", which fails at (0, 1, 1). |
| olymid-ref-base_2124 | Incorrect formalization | The Lean statement adds x = 0 as an equality case; the reference solution says x = 1 only. |
| omni_theorem_3461 | Incorrect formalization (quantifier) | "Not equivalent as expressions" is encoded as ∀ x, ¬(…), which fails at x = 0. |
| theorem_proving_zh_blue_1245 | Missing domain assumption | The informal statement is about a triangle's sides; the Lean statement has no triangle or positivity conditions. |
| — | Lean totalization artifact | None among these 8. Examples among the other 103: `omni_theorem_515` (x = y = 0 makes a hypothesis hold through division by zero) and `olymid-ref-base_7209` (log base 1). |

## Not yet done

- Hand review of the other 103 findings.
- Reporting upstream. Nothing has been posted to FormalMATH or contacted its maintainers.
