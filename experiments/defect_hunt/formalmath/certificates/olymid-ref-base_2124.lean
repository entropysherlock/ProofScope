/-
FormalMATH-All row `olymid-ref-base_2124` (dataset revision 8eea2550f174ce8b95444334da18a7473c2d169c).
Lines below up to the marker are the dataset's `autoformalization` field, byte-for-byte
(SHA-256 a7205ae9154e2da14504c2fee00ab68de35bb25712edf19237ae3f835496943e); only the proof placeholder `sorry` is appended.
Category: INCORRECT_FORMALIZATION. Counterexample: x = 0.
-/
import Mathlib

open Real Set

theorem olymid_ref_base_2124 (x : ℝ) (hx : 0 ≤ x) :
    1 + x^2 + x^6 + x^8 ≥ 4 * x^4 ∧
    (1 + x^2 + x^6 + x^8 = 4 * x^4 ↔ x = 1 ∨ x = 0) := by
  sorry

-- ===== ProofScope certificate: the statement above is false =====
theorem olymid_ref_base_2124_is_false : ¬ (type_of% @olymid_ref_base_2124) := by
  intro h
  have h0 := (h 0 le_rfl).2
  norm_num at h0

-- expected: depends only on standard axioms (no sorryAx)
#print axioms olymid_ref_base_2124_is_false
