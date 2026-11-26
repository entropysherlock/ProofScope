/-
FormalMATH-All row `olymid-ref-base_918` (dataset revision 8eea2550f174ce8b95444334da18a7473c2d169c).
Lines below up to the marker are the dataset's `autoformalization` field, byte-for-byte
(SHA-256 425d4293dcfc1ce8435dbf26b0f829c58cdc8a3409ff829a6dd385a4c07b6adf); only the proof placeholder `sorry` is appended.
Category: WRONG_STATED_ANSWER. Counterexample: x = 0.
-/
import Mathlib

open scoped BigOperators

theorem olymid_ref_base_918 {x : ℝ} (hx : ⌊x⌋ * (x - ⌊x⌋) = 1991 * x) : x = -1/1992 := by
  sorry

-- ===== ProofScope certificate: the statement above is false =====
theorem olymid_ref_base_918_is_false : ¬ (type_of% @olymid_ref_base_918) := by
  intro h
  have h0 := @h 0 (by simp)
  norm_num at h0

-- expected: depends only on standard axioms (no sorryAx)
#print axioms olymid_ref_base_918_is_false
