/-
FormalMATH-All row `theorem_proving_zh_blue_988` (dataset revision 8eea2550f174ce8b95444334da18a7473c2d169c).
Lines below up to the marker are the dataset's `autoformalization` field, byte-for-byte
(SHA-256 1f6bbfab4c928316a00078d87cba0629f3899a6c61737c857ad8ca44722092a5); only the proof placeholder `sorry` is appended.
Category: INCORRECT_STATEMENT. Counterexample: (x, y, z) = (0, -1, -1).
-/
import Mathlib

theorem algebra_33567 {x y z : ℝ} (h : x * y + y * z + z * x = 1) :
    x * (1 - y) * (1 - z ^ 2) + y * (1 - z) * (1 - x ^ 2) +
    z * (1 - x ^ 2) * (1 - y ^ 2) = 4 * x * y * z := by
  sorry

-- ===== ProofScope certificate: the statement above is false =====
theorem algebra_33567_is_false : ¬ (type_of% @algebra_33567) := by
  intro h
  have h0 := @h 0 (-1) (-1) (by norm_num)
  norm_num at h0

-- expected: depends only on standard axioms (no sorryAx)
#print axioms algebra_33567_is_false
