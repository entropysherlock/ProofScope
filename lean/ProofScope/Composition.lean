import ProofScope.AssumptionDelta
/-!
# v1.1 foundations: linking, polarity-aware composition, assumption minimality

## 1. Linking judgment
`Link R A := R ↔ A`, kernel-checked, where `A` is the canonical form whose parts (shared conditions,
assumptions, conclusion) are the statements certificates are elaborated against, **in the same
context**. Every certificate about `A`'s parts transports to `R` (`linked_assumption_delta`). The
linker may be incomplete (unsupported elaboration → no link → INCONCLUSIVE); it cannot be unsound,
because nothing is concluded about `R` without the checked `↔`. Textual identity is not linking:
`same_text_different_structure` shows one notation with two meanings on one carrier.

## 2. Polarity-aware composition
A *context* is `k : Prop → Prop`. Monotone contexts preserve the direction of a uniform entailment,
antitone contexts reverse it (`mono_lift`, `anti_lift`); contexts compose with the sign rule
(`mono_comp`, `anti_anti`). **Strictness is subtler:** a strict local weakening survives a monotone
context exactly when the context is non-degenerate, `k True ∧ ¬ k False` (`strict_lift_iff`).
Under a *binder* even that is not enough: an `∃` absorbs a pointwise separation
(`exists_binder_absorbs`), and a binder over an empty type absorbs every difference
(`empty_binder_absorbs`). So a global strict verdict needs a separating model **of the global
statement**, which is what `monotone_strict` (v0.9) provides when every edit points one way.

## 3. Assumption minimality (inclusion-minimal, not minimum cardinality)
For assumptions `A i` (`i : Fin n`) selected by `σ`, `Sufficient σ` says the conclusion follows. If `σ`
is sufficient and every `i ∈ σ` has a *removal witness* (a model of the shared conditions and the
other selected assumptions where the conclusion fails), then **no proper subset of `σ` is sufficient**
(`inclusion_minimal`). A redundant assumption (implied by the others) can be dropped without losing
sufficiency (`redundant_drop`). Individual redundancy does not compose: two copies of one assumption
are each redundant but jointly necessary, and the inclusion-minimal sets are not unique
(`substitutable_example`).
-/

namespace ProofScope.ClaimDelta

universe u

/-! ### 1. Linking -/

/-- What a linked Assumption Delta certificate says about the original statements `R` and `L`. -/
theorem linked_assumption_delta {M : Sort u} {R L : Prop} {C A P : M → Prop}
    (hR : R ↔ RefS C P) (hL : L ↔ FormS C A P) (m : M) (hc : C m) (ha : ¬ A m) :
    (R → L) ∧ (R → P m) ∧ ¬ (∀ Q : M → Prop, FormS C A Q → RefS C Q) :=
  ⟨fun r => hL.2 fun m c _ => hR.1 r m c, fun r => hR.1 r m hc,
   fun h => ha (h A (fun _ _ a => a) m hc)⟩

/-- Two structures on one carrier. -/
def mulAnd : Mul Bool := ⟨fun a b => a && b⟩
def mulLeft : Mul Bool := ⟨fun a _ => a⟩

/-- The same notation `a * b` on the same carrier denotes two structures with different properties, so
linking must compare elaborated terms (with their instances), never printed text. -/
theorem same_text_different_structure :
    (∀ a b : Bool, @HMul.hMul Bool Bool Bool (@instHMul Bool mulAnd) a b =
        @HMul.hMul Bool Bool Bool (@instHMul Bool mulAnd) b a) ∧
    ¬ (∀ a b : Bool, @HMul.hMul Bool Bool Bool (@instHMul Bool mulLeft) a b =
        @HMul.hMul Bool Bool Bool (@instHMul Bool mulLeft) b a) :=
  ⟨fun a b => by cases a <;> cases b <;> rfl, fun h => absurd (h true false) (by decide)⟩

/-! ### 2. Polarity-aware composition -/

def Mono (k : Prop → Prop) : Prop := ∀ p q : Prop, (p → q) → k p → k q
def Anti (k : Prop → Prop) : Prop := ∀ p q : Prop, (p → q) → k q → k p

theorem mono_id : Mono id := fun _ _ h => h
theorem mono_and (c : Prop) : Mono (fun p => c ∧ p) := fun _ _ h ⟨hc, hp⟩ => ⟨hc, h hp⟩
theorem mono_or (c : Prop) : Mono (fun p => c ∨ p) := fun _ _ h o => o.imp id h
theorem mono_imp_right (c : Prop) : Mono (fun p => c → p) := fun _ _ h f x => h (f x)
theorem anti_imp_left (c : Prop) : Anti (fun p => p → c) := fun _ _ h f x => f (h x)
theorem anti_not : Anti Not := fun _ _ h nq p => nq (h p)
theorem mono_comp {k₁ k₂ : Prop → Prop} (h₁ : Mono k₁) (h₂ : Mono k₂) : Mono (k₁ ∘ k₂) :=
  fun p q h => h₁ _ _ (h₂ p q h)
theorem anti_anti {k₁ k₂ : Prop → Prop} (h₁ : Anti k₁) (h₂ : Anti k₂) : Mono (k₁ ∘ k₂) :=
  fun p q h => h₁ _ _ (h₂ p q h)
theorem mono_anti {k₁ k₂ : Prop → Prop} (h₁ : Mono k₁) (h₂ : Anti k₂) : Anti (k₁ ∘ k₂) :=
  fun p q h => h₁ _ _ (h₂ p q h)
theorem mono_forall {β : Sort u} {P Q : β → Prop} (h : ∀ y, P y → Q y) : (∀ y, P y) → ∀ y, Q y :=
  fun f y => h y (f y)
theorem mono_exists {β : Sort u} {P Q : β → Prop} (h : ∀ y, P y → Q y) : (∃ y, P y) → ∃ y, Q y :=
  fun ⟨y, p⟩ => ⟨y, h y p⟩

section Lift
variable {T : Sort u}

theorem mono_lift {k : Prop → Prop} (hk : Mono k) {P Q : T → Prop} (h : SchemaEntails P Q) :
    SchemaEntails (fun x => k (P x)) (fun x => k (Q x)) := fun x => hk _ _ (h x)

theorem anti_lift {k : Prop → Prop} (hk : Anti k) {P Q : T → Prop} (h : SchemaEntails P Q) :
    SchemaEntails (fun x => k (Q x)) (fun x => k (P x)) := fun x => hk _ _ (h x)

/-- Strictness survives a monotone, non-degenerate context, with the same separating model. -/
theorem strict_lift {k : Prop → Prop} (hk : Mono k) (h1 : k True) (h0 : ¬ k False) {P Q : T → Prop}
    (h : StrictlyWeaker Q P) : StrictlyWeaker (fun x => k (Q x)) (fun x => k (P x)) :=
  let ⟨e, x, hq, hp⟩ := h
  ⟨mono_lift hk e, x, hk _ _ (fun _ => hq) h1, fun kp => h0 (hk _ _ (fun p => hp p) kp)⟩

end Lift

/-- Exactly the non-degenerate monotone contexts preserve every strict weakening. -/
theorem strict_lift_iff {k : Prop → Prop} (hk : Mono k) :
    (∀ (T : Type) (P Q : T → Prop), StrictlyWeaker Q P →
        StrictlyWeaker (fun x => k (Q x)) (fun x => k (P x))) ↔ (k True ∧ ¬ k False) := by
  constructor
  · intro h
    have s : StrictlyWeaker (fun _ : Unit => True) (fun _ : Unit => False) :=
      ⟨fun _ f => f.elim, (), trivial, id⟩
    obtain ⟨_, x, hq, hp⟩ := h Unit _ _ s
    exact ⟨hq, hp⟩
  · intro ⟨h1, h0⟩ T P Q s
    exact strict_lift hk h1 h0 s

/-- A degenerate context (`fun _ => True`) erases every difference. -/
theorem degenerate_context :
    StrictlyWeaker (fun _ : Unit => True) (fun _ : Unit => False) ∧
      SchemaEquiv (fun _ : Unit => (fun _ : Prop => True) True) (fun _ : Unit => (fun _ : Prop => True) False) :=
  ⟨⟨fun _ f => f.elim, (), trivial, id⟩, fun _ h => h, fun _ h => h⟩

/-- An `∃` binder absorbs a pointwise strict weakening: `y = true` against `True`, pointwise strict
over `Bool`, become equivalent under `∃ y`. -/
theorem exists_binder_absorbs :
    StrictlyWeaker (fun _ : Bool => True) (fun y : Bool => y = true) ∧
      ((∃ y : Bool, y = true) ↔ (∃ _ : Bool, True)) :=
  ⟨⟨fun _ _ => trivial, false, trivial, Bool.false_ne_true⟩,
   ⟨fun ⟨y, _⟩ => ⟨y, trivial⟩, fun _ => ⟨true, rfl⟩⟩⟩

/-- A binder over an empty type absorbs every difference. -/
theorem empty_binder_absorbs (P Q : Empty → Prop) : (∀ y, P y) ↔ (∀ y, Q y) :=
  ⟨(fun _ y => nomatch y), (fun _ y => nomatch y)⟩

/-! ### 3. Assumption minimality -/

section Minimality
variable {M : Sort u} {n : Nat} (C : M → Prop) (A : Fin n → M → Prop) (P : M → Prop)

def Sufficient (σ : Fin n → Prop) : Prop := ∀ m, C m → (∀ i, σ i → A i m) → P m

def RemovalWitness (σ : Fin n → Prop) (i : Fin n) : Prop :=
  ∃ m, C m ∧ (∀ j, σ j → j ≠ i → A j m) ∧ ¬ P m

/-- Removal witnesses for every selected assumption make a sufficient selection inclusion-minimal. -/
theorem inclusion_minimal {σ : Fin n → Prop} (hw : ∀ i, σ i → RemovalWitness C A P σ i)
    (τ : Fin n → Prop) (hsub : ∀ i, τ i → σ i) (hproper : ∃ i, σ i ∧ ¬ τ i) :
    ¬ Sufficient C A P τ := by
  intro hs
  obtain ⟨i, hσ, hτ⟩ := hproper
  obtain ⟨m, hc, hothers, hp⟩ := hw i hσ
  apply hp
  refine hs m hc fun j hj => hothers j (hsub j hj) ?_
  intro e
  exact hτ (e ▸ hj)

/-- An assumption implied by the other selected ones can be dropped without losing sufficiency. -/
theorem redundant_drop {σ : Fin n → Prop} {i : Fin n}
    (hr : ∀ m, C m → (∀ j, σ j → j ≠ i → A j m) → A i m) :
    Sufficient C A P σ ↔ Sufficient C A P (fun j => σ j ∧ j ≠ i) := by
  constructor
  · intro hs m hc ha
    refine hs m hc fun j hj => ?_
    by_cases e : j = i
    · subst e; exact hr m hc fun k hk hne => ha k ⟨hk, hne⟩
    · exact ha j ⟨hj, e⟩
  · intro hs m hc ha
    exact hs m hc fun j hj => ha j hj.1

end Minimality

/-- Two copies of one assumption: each is redundant given the other, the pair is jointly necessary,
and `{0}` and `{1}` are two different inclusion-minimal sufficient selections. -/
theorem substitutable_example :
    let C : Nat → Prop := fun _ => True
    let A : Fin 2 → Nat → Prop := fun _ x => x ≠ 0
    let P : Nat → Prop := fun x => x ≠ 0
    Sufficient C A P (fun i => i = 0) ∧ Sufficient C A P (fun i => i = 1) ∧
      ¬ Sufficient C A P (fun _ => False) := by
  refine ⟨fun m _ h => h 0 rfl, fun m _ h => h 1 rfl, fun h => h 0 trivial (fun _ f => f.elim) rfl⟩

end ProofScope.ClaimDelta

#print axioms ProofScope.ClaimDelta.linked_assumption_delta
#print axioms ProofScope.ClaimDelta.same_text_different_structure
#print axioms ProofScope.ClaimDelta.mono_comp
#print axioms ProofScope.ClaimDelta.anti_anti
#print axioms ProofScope.ClaimDelta.mono_anti
#print axioms ProofScope.ClaimDelta.mono_lift
#print axioms ProofScope.ClaimDelta.anti_lift
#print axioms ProofScope.ClaimDelta.strict_lift
#print axioms ProofScope.ClaimDelta.strict_lift_iff
#print axioms ProofScope.ClaimDelta.degenerate_context
#print axioms ProofScope.ClaimDelta.exists_binder_absorbs
#print axioms ProofScope.ClaimDelta.empty_binder_absorbs
#print axioms ProofScope.ClaimDelta.inclusion_minimal
#print axioms ProofScope.ClaimDelta.redundant_drop
#print axioms ProofScope.ClaimDelta.substitutable_example
