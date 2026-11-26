/-
FormalMATH-All row `omni_theorem_3461` (dataset revision 8eea2550f174ce8b95444334da18a7473c2d169c).
Lines below up to the marker are the dataset's `autoformalization` field, byte-for-byte
(SHA-256 3210d6130259ba2cd1b93814ecd86b255e8172b00e2c35b421e0461ce5941e0d); only the proof placeholder `sorry` is appended.
Category: INCORRECT_FORMALIZATION. Counterexample: x = 0.
-/
import Mathlib

theorem omni_theorem_3461 (x : ℝ) :
    ¬(3 * x + 6 = (1 / 3) * (3 * x) + (2 / 3) * 9) := by
  sorry

-- ===== ProofScope certificate: the statement above is false =====
theorem omni_theorem_3461_is_false : ¬ (type_of% @omni_theorem_3461) := by
  intro h
  exact h 0 (by norm_num)

-- expected: depends only on standard axioms (no sorryAx)
#print axioms omni_theorem_3461_is_false
