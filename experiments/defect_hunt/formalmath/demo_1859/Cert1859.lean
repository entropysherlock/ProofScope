/-
FormalMATH-All row `olymid-ref-base_1859` (dataset revision 8eea2550f174ce8b95444334da18a7473c2d169c).
Lines below up to the marker are the dataset's `autoformalization` field, byte-for-byte
(SHA-256 f1c7ff79f3e4f688d02776a3ecaee92736bdc5d560f34812d513357369ed7a73); only the proof placeholder `sorry` is appended.
Category: WRONG_STATED_ANSWER. Counterexample: (a, b, c) = (0, 1, 1).
-/
import Mathlib

theorem olymid_ref_base_1859 (a b c : ℝ) (h1 : a * b + b * c + c * a = 1)
(h2 : a^2 * b + c = b^2 * c + a) (h3 : b^2 * c + a = c^2 * a + b) :
False:= by
  sorry

-- ===== ProofScope certificate: the statement above is false =====
theorem olymid_ref_base_1859_is_false : ¬ (type_of% @olymid_ref_base_1859) := by
  intro h
  exact h 0 1 1 (by norm_num) (by norm_num) (by norm_num)

-- expected: depends only on standard axioms (no sorryAx)
#print axioms olymid_ref_base_1859_is_false
