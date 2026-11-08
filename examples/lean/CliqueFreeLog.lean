-- Challenge statement from the OpenAI comparator corpus (github.com/openai/math, commit
-- 4eaee87548250b2682affda7d05d947c05554bae; (c) OpenAI, Apache License 2.0), copied unmodified for the scan demo.
-- It imports Mathlib and contains `sorry` by design: challenges state theorems, they do not prove them.
import Mathlib

namespace OAI

namespace CliqueFreeLog

noncomputable def averageDegree {V : Type*} [Fintype V] (G : SimpleGraph V) : ℝ := by
  classical
  exact 2 * (G.edgeFinset.card : ℝ) / (Fintype.card V : ℝ)

theorem logarithmic_independence_bound (r : ℕ) (hr : 4 ≤ r) :
    ∃ c : ℝ, 0 < c ∧
      ∀ {V : Type} [Fintype V] (G : SimpleGraph V),
        G.CliqueFree r → 2 ≤ averageDegree G →
        c * (Fintype.card V : ℝ) * Real.log (averageDegree G) / averageDegree G ≤
          (G.indepNum : ℝ) := by
  sorry

end CliqueFreeLog

end OAI
