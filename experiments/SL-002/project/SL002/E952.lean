import Mathlib

/-!
# SL-002 — Erdős 952: transport between the OpenAI and Formal Conjectures statements

Imports Mathlib only. Nothing here uses, or could use, a proof of either statement:
the theorem `fc_iff_main` relates the two *propositions*, so it is not the trivial
equivalence of two already-proved closed statements.

Sources, copied verbatim (checked by `experiments/SL-002/check.py`):
* `MainEndpoint` — openai/math `lean/ComparatorChallenges/GaussianMoat.lean`
  at 4eaee87548250b2682affda7d05d947c05554bae.
* `FCStatement` — the statement of `Erdos952.erdos_952`, google-deepmind/formal-conjectures
  `FormalConjectures/ErdosProblems/952.lean` at da703a5f239f734a47ede2f4e99b9ccc9e644cb5.

The two differ in two ways: `Irreducible` versus `Prime`, and complex distance `≤ D`
(real `D`) versus Gaussian-integer norm `< C` (integer `C`).
-/

namespace ScopeLedger.SL002.E952

/-- Verbatim: `OAI.GaussianMoat.MainEndpoint`. -/
def MainEndpoint : Prop :=
  ∀ (D : ℝ) (z : ℕ → GaussianInt),
    (∀ t, Irreducible (z t)) → Function.Injective z →
    (∀ t, dist (z (t + 1) : ℂ) (z t : ℂ) ≤ D) → False

/-- Verbatim: the statement of `Erdos952.erdos_952`. -/
def FCStatement : Prop :=
  ¬ ∃ (x : ℕ → GaussianInt) (C : ℤ),
    Function.Injective x ∧
      ∀ n, Prime (x n) ∧ (x (n + 1) - x n).norm < C

/-- The squared complex distance between two Gaussian integers is the norm of their difference. -/
theorem dist_sq_eq_norm (a b : GaussianInt) :
    dist (a : ℂ) (b : ℂ) ^ 2 = ((a - b).norm : ℝ) := by
  rw [dist_eq_norm, ← GaussianInt.toComplex_sub, GaussianInt.intCast_real_norm]
  first
    | exact (Complex.normSq_eq_norm_sq _).symm
    | exact (Complex.sq_norm _)
    | simp [Complex.normSq_eq_norm_sq]

theorem dist_eq_sqrt_norm (a b : GaussianInt) :
    dist (a : ℂ) (b : ℂ) = Real.sqrt ((a - b).norm : ℝ) := by
  rw [← dist_sq_eq_norm, Real.sqrt_sq dist_nonneg]

/-- In `ℤ[i]` (a principal ideal domain) prime and irreducible elements coincide. -/
theorem prime_iff_irreducible (p : GaussianInt) : Prime p ↔ Irreducible p := by
  first
    | exact PrincipalIdealRing.irreducible_iff_prime.symm
    | exact irreducible_iff_prime.symm
    | exact ⟨Prime.irreducible, Irreducible.prime⟩

/-- OpenAI's statement implies the Formal Conjectures statement. -/
theorem main_implies_fc (h : MainEndpoint) : FCStatement := by
  rintro ⟨x, C, hinj, hx⟩
  refine h (Real.sqrt (C : ℝ)) x (fun t => (prime_iff_irreducible _).mp (hx t).1) hinj ?_
  intro t
  rw [dist_eq_sqrt_norm]
  exact Real.sqrt_le_sqrt (by exact_mod_cast (hx t).2.le)

/-- The Formal Conjectures statement implies OpenAI's statement. -/
theorem fc_implies_main (h : FCStatement) : MainEndpoint := by
  intro D z hz hinj hD
  apply h
  refine ⟨z, ⌊D ^ 2⌋ + 1, hinj, fun t => ⟨(prime_iff_irreducible _).mpr (hz t), ?_⟩⟩
  have h1 : ((z (t + 1) - z t).norm : ℝ) ≤ D ^ 2 := by
    rw [← dist_sq_eq_norm]
    first
      | exact pow_le_pow_left₀ dist_nonneg (hD t) 2
      | nlinarith [dist_nonneg (x := (z (t + 1) : ℂ)) (y := (z t : ℂ)), hD t]
  have h2 : (z (t + 1) - z t).norm ≤ ⌊D ^ 2⌋ := Int.le_floor.mpr h1
  first
    | omega
    | linarith

/-- The two formal statements are equivalent, proved without either side's proof. -/
theorem fc_iff_main : FCStatement ↔ MainEndpoint :=
  ⟨fc_implies_main, main_implies_fc⟩

end ScopeLedger.SL002.E952
