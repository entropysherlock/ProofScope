/-
FormalMATH-All row `olymid-ref-base_10553` (dataset revision 8eea2550f174ce8b95444334da18a7473c2d169c).
Lines below up to the marker are the dataset's `autoformalization` field, byte-for-byte
(SHA-256 8cee78e16187f8257086901d728c63455bb27a9923e7a79384561ba398f16cd0); only the proof placeholder `sorry` is appended.
Category: WRONG_STATED_ANSWER. Counterexample: (a, b, c) = (1, -1, 1).
-/
import Mathlib

open Polynomial

theorem olymid_ref_base_10553 {a b c : ℝ} (ha : a ≠ 0) (hb : b ≠ 0) (hc : c ≠ 0)
    (h1 : a + b + c = 1 / a + 1 / b + 1 / c) (h2 : a ^ 2 + b ^ 2 + c ^ 2 = 1 / a ^ 2 + 1 / b ^ 2 + 1 / c ^ 2) :
    ∃ t : ℝ, a = t ∧ b = 1 / t ∧ c = 1 ∨ a = t ∧ b = 1 / t ∧ c = -1 := by
  sorry

-- ===== ProofScope certificate: the statement above is false =====
theorem olymid_ref_base_10553_is_false : ¬ (type_of% @olymid_ref_base_10553) := by
  intro h
  obtain ⟨t, ⟨rfl, h2, -⟩ | ⟨rfl, h2, -⟩⟩ := @h 1 (-1) 1 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num)
  all_goals norm_num at h2

-- expected: depends only on standard axioms (no sorryAx)
#print axioms olymid_ref_base_10553_is_false
