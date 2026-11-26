/-
FormalMATH-All row `theorem_proving_zh_blue_1245` (dataset revision 8eea2550f174ce8b95444334da18a7473c2d169c).
Lines below up to the marker are the dataset's `autoformalization` field, byte-for-byte
(SHA-256 3d825cb260e2b148f583c6994aa8ccaa4af0f10a4773cb42878db9533adbe2da); only the proof placeholder `sorry` is appended.
Category: MISSING_DOMAIN_ASSUMPTION. Counterexample: (a, b, c) = (0, 0, 1).
-/
import Mathlib

open Real
open scoped BigOperators

theorem algebra_68645 (a b c : ℝ) :
  a^3 + b^3 + c^3 - 2*(a^2*(b+c) + b^2*(c+a) + c^2*(a+b)) +
  9*a*b*c ≤ 0 := by
  sorry

-- ===== ProofScope certificate: the statement above is false =====
theorem algebra_68645_is_false : ¬ (type_of% @algebra_68645) := by
  intro h
  have h0 := h 0 0 1
  norm_num at h0

-- expected: depends only on standard axioms (no sorryAx)
#print axioms algebra_68645_is_false
