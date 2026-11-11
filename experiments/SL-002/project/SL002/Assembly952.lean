import SL002.E952
import OAI.NumberTheory.GaussianMoat.Main

/-!
# SL-002 — Erdős 952 as stated in Formal Conjectures, from OpenAI's proof

The statement below is the Formal Conjectures statement of `Erdos952.erdos_952`, character for
character (checked by `check.py`). The proof is OpenAI's `OAI.GaussianMoat.fullMain` (built from
verbatim copies of its source files) composed with the Mathlib-only transport `main_implies_fc`.
The application also checks that OpenAI's library definition of `MainEndpoint` is definitionally
the one in OpenAI's Comparator challenge, of which `E952.MainEndpoint` is a verbatim copy.
-/

namespace ScopeLedger.SL002.E952

theorem erdos_952 :
  ¬ ∃ (x : ℕ → GaussianInt) (C : ℤ),
    Function.Injective x ∧
      ∀ n, Prime (x n) ∧ (x (n + 1) - x n).norm < C :=
  main_implies_fc OAI.GaussianMoat.fullMain.1

end ScopeLedger.SL002.E952
