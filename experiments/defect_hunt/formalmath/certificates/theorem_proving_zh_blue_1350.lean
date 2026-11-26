/-
FormalMATH-All row `theorem_proving_zh_blue_1350` (dataset revision 8eea2550f174ce8b95444334da18a7473c2d169c).
Lines below up to the marker are the dataset's `autoformalization` field, byte-for-byte
(SHA-256 5091056b8b365e2df2f4896cad9fc6cc14a4bd234743441be5538e614eadabf2); only the proof placeholder `sorry` is appended.
Category: INCORRECT_FORMALIZATION. Counterexample: (x, y, z) = (0, 1, 1).
-/
import Mathlib

open Real

theorem inequalities_8712 (x y z : ℝ) (hx : 0 ≤ x) (hy : 0 ≤ y) (hz : 0 ≤ z) :
    3 * x * y * z ≤ x * (y + z - x) ^ 2 + y * (z + x - y) ^ 2 + z * (x + y - z) ^ 2 ∧
    (3 * x * y * z = x * (y + z - x) ^ 2 + y * (z + x - y) ^ 2 + z * (x + y - z) ^ 2 ↔
      (x = y ∧ y = z)) := by
  sorry

-- ===== ProofScope certificate: the statement above is false =====
theorem inequalities_8712_is_false : ¬ (type_of% @inequalities_8712) := by
  intro h
  have h0 := (h 0 1 1 le_rfl zero_le_one zero_le_one).2
  norm_num at h0

-- expected: depends only on standard axioms (no sorryAx)
#print axioms inequalities_8712_is_false
