import Mathlib

/-!
# SL-002 — Erdős 1150: transport from the OpenAI statement to the Formal Conjectures statement

Imports Mathlib only; the OpenAI statement is a hypothesis, not imported.

Sources, copied verbatim (checked by `experiments/SL-002/check.py`):
* `littlewoodValue`, `IsRealSigning`, `MainStatement` — openai/math
  `lean/ComparatorChallenges/AsymptoticallyMinimalLittlewood.lean` at
  4eaee87548250b2682affda7d05d947c05554bae.
* `FCStatement` — the statement of `Erdos1150.erdos_1150`, google-deepmind/formal-conjectures
  `FormalConjectures/ErdosProblems/1150.lean` at da703a5f239f734a47ede2f4e99b9ccc9e644cb5.

Differences: OpenAI indexes by the number of coefficients `N` and bounds `‖·‖` at every point of
the circle for *all* large `N`; Formal Conjectures indexes by the degree `n = N - 1`, uses a
`Polynomial`, a supremum over the sphere, and a strict inequality, and only needs *some* large `n`.
-/

open scoped Polynomial

namespace ScopeLedger.SL002.E1150

/-- Verbatim: `OAI.AsymptoticallyMinimalLittlewood.littlewoodValue`. -/
def littlewoodValue {N : ℕ} (ε : Fin N → ℝ) (z : ℂ) : ℂ :=
  ∑ k : Fin N, (ε k : ℂ) * z ^ (k : ℕ)

/-- Verbatim: `OAI.AsymptoticallyMinimalLittlewood.IsRealSigning`. -/
def IsRealSigning {N : ℕ} (ε : Fin N → ℝ) : Prop :=
  ∀ k, ε k = -1 ∨ ε k = 1

/-- Verbatim: `OAI.AsymptoticallyMinimalLittlewood.MainStatement`. -/
def MainStatement : Prop :=
  ∀ η : ℝ, 0 < η → ∃ N₀ : ℕ, 1 ≤ N₀ ∧ ∀ N : ℕ, N₀ ≤ N →
    ∃ ε : Fin N → ℝ, IsRealSigning ε ∧
      ∀ z : ℂ, ‖z‖ = 1 → ‖littlewoodValue ε z‖ ≤ (1 + η) * Real.sqrt N

/-- Verbatim: the statement of `Erdos1150.erdos_1150`. -/
def FCStatement : Prop :=
  ¬ ∃ c > 0, ∀ᶠ n in Filter.atTop,
      ∀ P : ℂ[X],  (∀ i ≤ P.natDegree, P.coeff i = - 1 ∨ P.coeff i = 1) → P.natDegree = n →
        ⨆ z : Metric.sphere (0 : ℂ) 1, ‖P.eval (z : ℂ)‖ > (1 + c) * Real.sqrt n

/-- Coefficient function of the polynomial attached to a signing. -/
noncomputable def coeffFn {N : ℕ} (ε : Fin N → ℝ) (i : ℕ) : ℂ :=
  if h : i < N then (ε ⟨i, h⟩ : ℂ) else 0

/-- The polynomial `∑_{i<N} ε_i X^i`. -/
noncomputable def poly {N : ℕ} (ε : Fin N → ℝ) : ℂ[X] :=
  ∑ i ∈ Finset.range N, Polynomial.C (coeffFn ε i) * Polynomial.X ^ i

theorem poly_coeff {N : ℕ} (ε : Fin N → ℝ) (j : ℕ) : (poly ε).coeff j = coeffFn ε j := by
  unfold poly
  rw [Polynomial.finset_sum_coeff]
  simp only [Polynomial.coeff_C_mul_X_pow]
  first
    | rw [Finset.sum_ite_eq]
    | rw [Finset.sum_ite_eq']
  by_cases h : j < N
  · simp [h]
  · simp [h, coeffFn]

theorem poly_natDegree {n : ℕ} (ε : Fin (n + 1) → ℝ) (hε : IsRealSigning ε) :
    (poly ε).natDegree = n := by
  apply le_antisymm
  · rw [Polynomial.natDegree_le_iff_coeff_eq_zero]
    intro j hj
    have hj' : ¬ j < n + 1 := by omega
    rw [poly_coeff]
    simp [coeffFn, hj']
  · apply Polynomial.le_natDegree_of_ne_zero
    rw [poly_coeff]
    rcases hε ⟨n, lt_add_one n⟩ with h | h
    · first
        | simp [coeffFn, h]
        | norm_num [coeffFn, h]
    · first
        | simp [coeffFn, h]
        | norm_num [coeffFn, h]

theorem poly_coeff_sign {n : ℕ} (ε : Fin (n + 1) → ℝ) (hε : IsRealSigning ε) :
    ∀ i ≤ (poly ε).natDegree, (poly ε).coeff i = - 1 ∨ (poly ε).coeff i = 1 := by
  intro i hi
  rw [poly_natDegree ε hε] at hi
  rw [poly_coeff]
  have hi' : i < n + 1 := by omega
  rcases hε ⟨i, hi'⟩ with h | h
  · left
    first
      | simp [coeffFn, hi', h]
      | norm_num [coeffFn, hi', h]
  · right
    first
      | simp [coeffFn, hi', h]
      | norm_num [coeffFn, hi', h]

theorem poly_eval {N : ℕ} (ε : Fin N → ℝ) (z : ℂ) :
    (poly ε).eval z = littlewoodValue ε z := by
  have key : ∀ k : Fin N, (ε k : ℂ) * z ^ (k : ℕ) = coeffFn ε k * z ^ (k : ℕ) := by
    intro k
    simp [coeffFn, k.isLt]
  unfold poly littlewoodValue
  rw [Polynomial.eval_finset_sum]
  simp only [key]
  first
    | (rw [Fin.sum_univ_eq_sum_range (fun i => coeffFn ε i * z ^ i) N]; simp)
    | simp [Finset.sum_range]

/-- For large `n`, `(1 + c/2) √(n+1) ≤ (1 + c) √n`. -/
theorem sqrt_step {c : ℝ} (hc : 0 < c) {n : ℕ} (hcn : (1 + c / 2) ^ 2 ≤ c * n) :
    (1 + c / 2) * Real.sqrt ((n + 1 : ℕ) : ℝ) ≤ (1 + c) * Real.sqrt n := by
  have hn0 : (0 : ℝ) ≤ n := Nat.cast_nonneg n
  have hX : 0 ≤ (1 + c / 2) * Real.sqrt ((n + 1 : ℕ) : ℝ) :=
    mul_nonneg (by linarith) (Real.sqrt_nonneg _)
  have hY : 0 ≤ (1 + c) * Real.sqrt n := mul_nonneg (by linarith) (Real.sqrt_nonneg _)
  have hsq : ((1 + c / 2) * Real.sqrt ((n + 1 : ℕ) : ℝ)) ^ 2 ≤ ((1 + c) * Real.sqrt n) ^ 2 := by
    rw [mul_pow, mul_pow, Real.sq_sqrt (Nat.cast_nonneg _), Real.sq_sqrt hn0]
    push_cast
    nlinarith [mul_nonneg (sq_nonneg c) hn0, mul_nonneg hc.le hn0]
  calc (1 + c / 2) * Real.sqrt ((n + 1 : ℕ) : ℝ)
      = Real.sqrt (((1 + c / 2) * Real.sqrt ((n + 1 : ℕ) : ℝ)) ^ 2) := (Real.sqrt_sq hX).symm
    _ ≤ Real.sqrt (((1 + c) * Real.sqrt n) ^ 2) := Real.sqrt_le_sqrt hsq
    _ = (1 + c) * Real.sqrt n := Real.sqrt_sq hY

/-- OpenAI's statement implies the Formal Conjectures statement. -/
theorem main_implies_fc (hA : MainStatement) : FCStatement := by
  rintro ⟨c, hc, hev⟩
  obtain ⟨N₁, hN₁⟩ := Filter.eventually_atTop.mp hev
  obtain ⟨N₀, -, hN₀⟩ := hA (c / 2) (half_pos hc)
  obtain ⟨m, hm⟩ := exists_nat_ge ((1 + c / 2) ^ 2 / c)
  obtain ⟨n, hn1, hn2, hn3⟩ : ∃ n : ℕ, N₀ ≤ n ∧ N₁ ≤ n ∧ m ≤ n :=
    ⟨max (max N₀ N₁) m, (le_max_left _ _).trans (le_max_left _ _),
      (le_max_right _ _).trans (le_max_left _ _), le_max_right _ _⟩
  obtain ⟨ε, hε, hbound⟩ := hN₀ (n + 1) (by omega)
  have hP := hN₁ n hn2 (poly ε) (poly_coeff_sign ε hε) (poly_natDegree ε hε)
  have hsup : (⨆ z : Metric.sphere (0 : ℂ) 1, ‖(poly ε).eval (z : ℂ)‖)
      ≤ (1 + c / 2) * Real.sqrt ((n + 1 : ℕ) : ℝ) := by
    haveI : Nonempty (Metric.sphere (0 : ℂ) 1) := ⟨⟨1, by simp⟩⟩
    apply ciSup_le
    intro z
    rw [poly_eval]
    apply hbound
    first
      | exact mem_sphere_zero_iff_norm.mp z.2
      | simpa using z.2
  have hcn : (1 + c / 2) ^ 2 ≤ c * n := by
    have hmn : (m : ℝ) ≤ n := by exact_mod_cast hn3
    have h1 : (1 + c / 2) ^ 2 / c ≤ n := hm.trans hmn
    first
      | (have := (div_le_iff₀ hc).mp h1; linarith)
      | (rw [div_le_iff₀ hc] at h1; linarith)
  exact absurd hP (not_lt.mpr (hsup.trans (sqrt_step hc hcn)))

end ScopeLedger.SL002.E1150
