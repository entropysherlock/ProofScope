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

## Novelty, still to be checked per finding

- **Prior audit.** Ammanamanchi, Bhat and Biderman (ICML 2026) certified issues in FormalMath using `decide`, Plausible random testing and omega/grind. Their per-item list is not in their public repository ([atp-checkers](https://github.com/Shashi456/atp-checkers)), so overlap cannot yet be ruled out. Integer-witness findings may well overlap.
- **FormalMATH's own issue tracker** has no defect reports (one issue, about the Mathlib version, as of 2026-11-17).

## Not yet done

- Hand review of the other 103 findings.
- Reporting upstream. Nothing has been posted publicly.
