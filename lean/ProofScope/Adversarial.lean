import ProofScope.ScopeElim
/-!
# Adversarial tests for ScopeElim (SOTA-14, Phase C)

Each test tries to break a criterion from `ScopeElim.lean` or shows what a weaker rule gets wrong.
Core Lean only.
-/
namespace ProofScope.ScopeElim.Adversarial
open ProofScope.ScopeElim

/-! ### T1. The reference must be used twice: no single-instance (pointwise) rule sees the entailment. -/
def stepR (σ : Nat → Prop) : Prop := Clause (fun _ : Nat => True) (fun n (_ : Unit) => n) (fun n => n + 1) σ
def stepF (σ : Nat → Prop) : Prop := Clause (fun _ : Nat => True) (fun n (_ : Unit) => n) (fun n => n + 2) σ

theorem t1_entails : ∀ σ, stepR σ → stepF σ :=
  (horn_complete _ _ _ _ _ _).2 fun y _ =>
    Der.step (y + 1) trivial fun _ => Der.step y trivial fun _ => Der.base ⟨(), rfl⟩

/-- No single reference instance has the right conclusion and a premise among the formal premises. -/
theorem t1_not_pointwise : ¬ ∃ y x : Nat, x + 1 = y + 2 ∧ x = y := by
  intro ⟨y, x, h1, h2⟩; omega

theorem t1_strict : ¬ ∀ σ, stepF σ → stepR σ := by
  intro h
  have := h (fun k => k % 2 = 0) (fun x _ hp => by have hx : x % 2 = 0 := hp (); show (x + 2) % 2 = 0; omega) 0 trivial (fun _ => rfl)
  exact absurd this (by decide)

/-! ### T2. Two edits that each look like a change cancel exactly. -/
theorem t2_hypothesis_alone_differs : ¬ ∀ n : Nat, 1 ≤ n → 2 ≤ n := fun h => absurd (h 1 (Nat.le_refl 1)) (by decide)

theorem t2_schema_equivalent :
    (∀ P : Nat → Prop, (∀ n, 2 ≤ n → P n) → (∀ n, 1 ≤ n → P (n + 1))) ∧
    (∀ P : Nat → Prop, (∀ n, 1 ≤ n → P (n + 1)) → (∀ n, 2 ≤ n → P n)) :=
  ⟨(concl_schematic _ _ _ _).2 fun y hy => ⟨y + 1, by omega, rfl⟩,
   (concl_schematic _ _ _ _).2 fun y hy => ⟨y - 1, by omega, by show y - 1 + 1 = y; omega⟩⟩

/-! ### T3. Dependent conclusion: `P : (n : Nat) → Fin (n + 1) → Prop`, packed as a predicate on a Σ-type. -/
abbrev DZ := (n : Nat) ×' Fin (n + 1)

theorem t3_forward : ∀ P : DZ → Prop, (∀ x : DZ, True → P x) → (∀ n : Nat, True → P ⟨n, 0⟩) :=
  (concl_schematic (fun _ : DZ => True) id (fun _ : Nat => True) (fun n => (⟨n, 0⟩ : DZ))).2
    fun y _ => ⟨⟨y, 0⟩, trivial, rfl⟩

theorem t3_backward_fails :
    ¬ ∀ P : DZ → Prop, (∀ n : Nat, True → P ⟨n, 0⟩) → (∀ x : DZ, True → P x) := by
  intro h
  have := (concl_schematic (fun _ : Nat => True) (fun n => (⟨n, 0⟩ : DZ)) (fun _ : DZ => True) id).1 h
    ⟨1, 1⟩ trivial
  obtain ⟨n, _, e⟩ := this
  have h1 : n = 1 := congrArg PSigma.fst e
  subst h1
  have h2 : (0 : Fin 2) = 1 := eq_of_heq (PSigma.mk.inj e).2
  exact absurd h2 (by decide)

/-! ### T4. Vacuity: an unsatisfiable reference schema entails everything, and the fibre condition
alone would wrongly deny the entailment. -/
def vacR (f : Nat → Nat) : Prop := RefF (fun _ : Nat => True) id (fun n w => w < n) f
def anyF (f : Nat → Nat) : Prop := FormF (fun _ : Nat => True) id (fun _ _ => False) f

theorem t4_vacuous_entails : ∀ f, vacR f → anyF f :=
  fun_schematic_sound _ _ _ _ _ _ (Or.inl ⟨0, fun w h => absurd (h 0 trivial rfl) (Nat.not_lt_zero w)⟩)

theorem t4_fibre_condition_fails :
    ¬ ∀ (y w : Nat), True → Adm (fun _ : Nat => True) id (fun n v => v < n) y w → False :=
  fun h => h 1 0 trivial (fun x _ e => by subst e; decide)

/-! ### T5. Decoupling two occurrences of one symbol into two symbols is sound for entailment but
not for separation. -/
theorem t5_coupled_entails : ∀ f : Nat → Nat, True → ∀ n, f n ≤ f n := fun _ _ _ => Nat.le_refl _

theorem t5_decoupled_separates : ∃ f₁ f₂ : Nat → Nat, True ∧ ¬ ∀ n, f₁ n ≤ f₂ n :=
  ⟨fun _ => 1, fun _ => 0, trivial, fun h => absurd (h 0) (by decide)⟩

/-! ### T6. The ClaimDelta flagship pair decided by Theorem B, with no witness search. -/
def RefLt (f : Nat → Nat) : Prop := RefF (fun _ : Nat => True) id (fun n w => n < w) f
def FormLe (f : Nat → Nat) : Prop := FormF (fun _ : Nat => True) id (fun n w => n ≤ w) f

theorem t6_forward : ∀ f, RefLt f → FormLe f :=
  fun_schematic_sound _ _ _ _ _ _ (Or.inr fun y _ _ h => Nat.le_of_lt (h y trivial rfl))

theorem t6_backward_fails : ¬ ∀ f, FormLe f → RefLt f := by
  intro h
  have := (fun_schematic (fun _ : Nat => True) id (fun n w => n ≤ w)
    (fun _ : Nat => True) id (fun n w => n < w)).1 h
  cases this with
  | inl hv =>
    obtain ⟨z, hz⟩ := hv
    exact hz z (fun x _ e => by subst e; exact Nat.le_refl _)
  | inr hr => exact Nat.lt_irrefl 0 (hr 0 0 trivial (fun x _ e => by subst e; exact Nat.le_refl _))

/-! ### T7. Empty reference binder: the reference schema is true for every `P`, so it entails only
formal claims with no instances. -/
theorem t7_empty : ¬ ∀ P : Nat → Prop, (∀ x : Empty, True → P (nomatch x)) → (∀ _ : Unit, True → P 0) := by
  intro h
  obtain ⟨x, _⟩ := (concl_schematic (fun _ : Empty => True) (fun x => nomatch x) (fun _ : Unit => True)
    (fun _ => (0 : Nat))).1 h () trivial
  exact nomatch x

/-! ### T8. The verdict depends on the class of interpretations. Over all functions the formal claim
`1 ≤ f 1` does not give the reference `∀ n, 1 ≤ f (n + 1)`; over monotone functions it does.
Monotonicity is a two-occurrence law, outside Theorem B. -/
theorem t8_all_functions : ¬ ∀ f : Nat → Nat, (1 ≤ f 1) → ∀ n, 1 ≤ f (n + 1) :=
  fun h => absurd (h (fun k => if k = 1 then 1 else 0) (by decide) 1) (by decide)

theorem t8_monotone : ∀ f : Nat → Nat, (∀ a b, a ≤ b → f a ≤ f b) → (1 ≤ f 1) → ∀ n, 1 ≤ f (n + 1) :=
  fun f mono h n => Nat.le_trans h (mono 1 (n + 1) (by omega))

end ProofScope.ScopeElim.Adversarial

#print axioms ProofScope.ScopeElim.Adversarial.t1_entails
#print axioms ProofScope.ScopeElim.Adversarial.t1_not_pointwise
#print axioms ProofScope.ScopeElim.Adversarial.t1_strict
#print axioms ProofScope.ScopeElim.Adversarial.t2_hypothesis_alone_differs
#print axioms ProofScope.ScopeElim.Adversarial.t2_schema_equivalent
#print axioms ProofScope.ScopeElim.Adversarial.t3_forward
#print axioms ProofScope.ScopeElim.Adversarial.t3_backward_fails
#print axioms ProofScope.ScopeElim.Adversarial.t4_vacuous_entails
#print axioms ProofScope.ScopeElim.Adversarial.t4_fibre_condition_fails
#print axioms ProofScope.ScopeElim.Adversarial.t5_coupled_entails
#print axioms ProofScope.ScopeElim.Adversarial.t5_decoupled_separates
#print axioms ProofScope.ScopeElim.Adversarial.t6_forward
#print axioms ProofScope.ScopeElim.Adversarial.t6_backward_fails
#print axioms ProofScope.ScopeElim.Adversarial.t7_empty
#print axioms ProofScope.ScopeElim.Adversarial.t8_all_functions
#print axioms ProofScope.ScopeElim.Adversarial.t8_monotone