import SL002.E1150
import OAI.Analysis.Littlewood.Main

/-!
# SL-002 — Erdős 1150 as stated in Formal Conjectures, from OpenAI's proof

The statement below is the Formal Conjectures statement of `Erdos1150.erdos_1150`, character for
character (checked by `check.py`). The proof is OpenAI's `OAI.AsymptoticallyMinimalLittlewood.main`
composed with the Mathlib-only transport `main_implies_fc`.
-/

open scoped Polynomial

namespace ScopeLedger.SL002.E1150

theorem erdos_1150 :
    ¬ ∃ c > 0, ∀ᶠ n in Filter.atTop,
      ∀ P : ℂ[X],  (∀ i ≤ P.natDegree, P.coeff i = - 1 ∨ P.coeff i = 1) → P.natDegree = n →
        ⨆ z : Metric.sphere (0 : ℂ) 1, ‖P.eval (z : ℂ)‖ > (1 + c) * Real.sqrt n :=
  main_implies_fc OAI.AsymptoticallyMinimalLittlewood.main

end ScopeLedger.SL002.E1150
