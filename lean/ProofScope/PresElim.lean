import ProofScope.ScopeElim
/-!
# PresElim: quantifier-free residuals for an injective argument (SOTA-16)

Core Lean 4 only. In SOTA-14 Theorem B the admissibility predicate
`Adm z w := ∀ x, A x → s x = z → ρ x w` still quantifies over `x`. When the argument map `s` has a
solving function `g` (`s x = z → x = g z`), the quantifier collapses to one instance, and for
`s x = k * x + c` with `k ≥ 1` the solving function is `(z - c) / k`. The residual obligations of
Theorem B then contain no quantifier over reference instances: with linear `A`, `ρ`, `B`, `t`, `θ`
they are Presburger sentences of the shapes `∃ z ∀ w, QF` and `∀ y w, QF`.
-/
namespace ProofScope.PresElim
open ProofScope.ScopeElim

universe u v w w'

section Solve
variable {Z : Sort u} {W : Sort v} {X : Sort w} {Y : Sort w'}
variable (A : X → Prop) (s : X → Z) (ρ : X → W → Prop) (g : Z → X)

/-- With a solving function, admissibility is a single instance. -/
theorem adm_iff_instance (hg : ∀ x z, s x = z → x = g z) (z : Z) (w : W) :
    Adm A s ρ z w ↔ (A (g z) → s (g z) = z → ρ (g z) w) := by
  constructor
  · intro h; exact h (g z)
  · intro h x hA hs
    have e := hg x z hs
    subst e
    exact h hA hs

/-- **Theorem B without the inner quantifier.** -/
theorem fun_schematic_solved (hg : ∀ x z, s x = z → x = g z)
    (B : Y → Prop) (t : Y → Z) (θ : Y → W → Prop) :
    (∀ f, RefF A s ρ f → FormF B t θ f) ↔
      ((∃ z, ∀ w, ¬ (A (g z) → s (g z) = z → ρ (g z) w)) ∨
        ∀ y w, B y → (A (g (t y)) → s (g (t y)) = t y → ρ (g (t y)) w) → θ y w) := by
  rw [fun_schematic]
  constructor
  · rintro (⟨z, hz⟩ | h)
    · exact Or.inl ⟨z, fun w hw => hz w ((adm_iff_instance A s ρ g hg z w).2 hw)⟩
    · exact Or.inr fun y w hB hi => h y w hB ((adm_iff_instance A s ρ g hg (t y) w).2 hi)
  · rintro (⟨z, hz⟩ | h)
    · exact Or.inl ⟨z, fun w hw => hz w ((adm_iff_instance A s ρ g hg z w).1 hw)⟩
    · exact Or.inr fun y w hB hadm => h y w hB ((adm_iff_instance A s ρ g hg (t y) w).1 hadm)

end Solve

/-- The solving function of an affine argument with positive slope. -/
theorem affine_solve (k c : Nat) (hk : 1 ≤ k) : ∀ x z : Nat, k * x + c = z → x = (z - c) / k := by
  intro x z h
  subst h
  rw [Nat.add_sub_cancel, Nat.mul_div_cancel_left x hk]

/-- Theorem B for `f (k * x + c)`: the residuals mention `x` only through `(z - c) / k`. -/
theorem fun_schematic_affine (k c : Nat) (hk : 1 ≤ k) (A : Nat → Prop) (ρ : Nat → Nat → Prop)
    {Y : Sort u} (B : Y → Prop) (t : Y → Nat) (θ : Y → Nat → Prop) :
    (∀ f : Nat → Nat, RefF A (fun x => k * x + c) ρ f → FormF B t θ f) ↔
      ((∃ z, ∀ w, ¬ (A ((z - c) / k) → k * ((z - c) / k) + c = z → ρ ((z - c) / k) w)) ∨
        ∀ y w, B y → (A ((t y - c) / k) → k * ((t y - c) / k) + c = t y → ρ ((t y - c) / k) w) → θ y w) :=
  fun_schematic_solved A (fun x => k * x + c) ρ (fun z => (z - c) / k) (affine_solve k c hk) B t θ

end ProofScope.PresElim

#print axioms ProofScope.PresElim.adm_iff_instance
#print axioms ProofScope.PresElim.fun_schematic_solved
#print axioms ProofScope.PresElim.affine_solve
#print axioms ProofScope.PresElim.fun_schematic_affine
