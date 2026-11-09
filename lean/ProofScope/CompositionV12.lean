import ProofScope.Composition
/-!
# v1.2 composition: domain changes, instance substitution, interacting changes

Core Lean, building on `Composition.lean` (v1.1).

* **Domain change along an equivalence.** Relations between claims are invariant under transporting
  the interpretation space along an equivalence `e : T ≃ U` (`entails_transport`,
  `strict_transport`). Along a mere function they are not: a non-surjective map can hide a separation
  (`noninjective_domain_loses_strictness`).
* **Instance substitution.** Replacing an instance by a provably equal one changes nothing
  (`instance_congr`); replacing it by a different one can change the truth value of the same text
  (v1.1 `same_text_different_structure`).
* **Interacting assumption and conclusion changes.** Adding an assumption and weakening the conclusion
  both point in the same direction, so the result is implied by the reference (`assumption_and_weaker_conclusion`).
  Adding an assumption and *strengthening* the conclusion can make the statements incomparable
  (`assumption_vs_stronger_conclusion`).
* **Interacting assumption changes.** When the formalization drops `D` and adds `A`, the relation is
  decided by `D → A` / `A → D` under the shared conditions and by joint models (`mixed_strict`,
  `mixed_incomparable`, `mixed_ref_false`); separate classification is unsound
  (`separate_restrictions_not_incomparable`). This corrects ProofScope v1.1.
* **Dependent binders.** A uniform entailment under `∀ y : β x` where the binder's type depends on the
  interpretation composes (`dependent_forall_mono`); strictness does not lift without a separating
  model of the whole statement (`exists_binder_absorbs`, v1.1).
-/

namespace ProofScope.ClaimDelta

universe u v

section Transport
variable {T : Sort u} {U : Sort v}

/-- Equivalence of interpretation spaces as a pair of maps with both round trips. -/
structure Equiv' (T : Sort u) (U : Sort v) where
  toFun : T → U
  invFun : U → T
  left : ∀ x, invFun (toFun x) = x
  right : ∀ y, toFun (invFun y) = y

theorem entails_transport (e : Equiv' T U) {P Q : U → Prop} :
    SchemaEntails P Q ↔ SchemaEntails (fun x => P (e.toFun x)) (fun x => Q (e.toFun x)) :=
  ⟨fun h x => h (e.toFun x), fun h y hp => by
    have h' : P (e.toFun (e.invFun y)) → Q (e.toFun (e.invFun y)) := h (e.invFun y)
    rw [e.right] at h'; exact h' hp⟩

theorem strict_transport (e : Equiv' T U) {P Q : U → Prop} :
    StrictlyWeaker Q P ↔ StrictlyWeaker (fun x => Q (e.toFun x)) (fun x => P (e.toFun x)) := by
  constructor
  · intro ⟨h, y, hq, hp⟩
    refine ⟨(entails_transport e).1 h, e.invFun y, ?_, ?_⟩
    · show Q (e.toFun (e.invFun y)); rw [e.right]; exact hq
    · show ¬ P (e.toFun (e.invFun y)); rw [e.right]; exact hp
  · intro ⟨h, x, hq, hp⟩
    exact ⟨(entails_transport e).2 h, e.toFun x, hq, hp⟩

/-- Along a non-surjective map a separation can disappear: the reference differs from the
formalization only at the point the map misses. -/
theorem noninjective_domain_loses_strictness :
    StrictlyWeaker (fun _ : Bool => True) (fun b : Bool => b = true) ∧
      SchemaEquiv (fun _ : Unit => (fun _ : Bool => True) true) (fun _ : Unit => (fun b : Bool => b = true) true) :=
  ⟨⟨fun _ _ => trivial, false, trivial, Bool.false_ne_true⟩, fun _ _ => rfl, fun _ _ => trivial⟩

end Transport

/-- Replacing an instance (or any structure argument) by an equal one changes nothing. -/
theorem instance_congr {I : Sort u} (S : I → Prop) {i j : I} (h : i = j) : S i ↔ S j := h ▸ Iff.rfl

section Interacting
variable {M : Sort u} (C A : M → Prop)

/-- Adding an assumption and weakening the conclusion both weaken the claim. -/
theorem assumption_and_weaker_conclusion {P Q : M → Prop} (hpq : ∀ m, C m → P m → Q m) :
    RefS C P → FormS C A Q := fun r m c _ => hpq m c (r m c)

/-- Adding an assumption while strengthening the conclusion can make the claims incomparable. -/
theorem assumption_vs_stronger_conclusion :
    let C : Nat → Prop := fun _ => True
    let A : Nat → Prop := fun n => 1 ≤ n
    let P : Nat → Prop := fun n => n ≤ n
    let Q : Nat → Prop := fun n => n < 2 * n
    RefS C P ∧ FormS C A Q ∧ ¬ (∀ m, C m → Q m) ∧ ¬ (∀ m, C m → A m) := by
  refine ⟨fun n _ => Nat.le_refl n, fun n _ h => by omega, fun h => absurd (h 0 trivial) (by decide),
    fun h => absurd (h 0 trivial) (by decide)⟩

end Interacting

/-- Uniform entailment under a binder whose type depends on the interpretation. -/
theorem dependent_forall_mono {T : Sort u} {β : T → Sort v} {P Q : (x : T) → β x → Prop}
    (h : ∀ x y, P x y → Q x y) : SchemaEntails (fun x => ∀ y, P x y) (fun x => ∀ y, Q x y) :=
  fun x f y => h x y (f y)

/-- A vacuous hypothesis absorbs any conclusion change: from contradictory assumptions, any two
conclusions are interchangeable (so vacuity must be detected before comparing conclusions). -/
theorem vacuous_absorbs {M : Sort u} (C : M → Prop) (hv : ∀ m, ¬ C m) (P Q : M → Prop) :
    RefS C P ↔ RefS C Q := ⟨fun _ m c => (hv m c).elim, fun _ m c => (hv m c).elim⟩

section Mixed
variable {M : Sort u}

/-! ### Interacting assumption changes (v1.2; corrects a v1.1 classification defect)

Reference `∀ m, C m → D m → P m` (it has `D`), formalization `∀ m, C m → A m → P m` (it has `A`
instead). Classifying `A` and `D` *separately* against `C` is unsound: both can be restrictive while
the formalization is still uniformly stronger (`separate_restrictions_not_incomparable`), and a model
with `C ∧ ¬ A ∧ ¬ P` does not refute the reference unless `D` also holds there (`mixed_ref_false`). -/

/-- The mixed-change telescope. -/
def MixS (C H : M → Prop) (P : M → Prop) : Prop := ∀ m, C m → H m → P m

theorem mixed_entails {C D A : M → Prop} (h : ∀ m, C m → D m → A m) (P : M → Prop) :
    MixS C A P → MixS C D P :=
  fun hl m hc hd => hl m hc (h m hc hd)

/-- `D → A` under `C`, plus a model with `C ∧ A ∧ ¬ D`: the formalization is strictly stronger. -/
theorem mixed_strict {C D A : M → Prop} (h : ∀ m, C m → D m → A m) {m0 : M}
    (hc : C m0) (ha : A m0) (hd : ¬ D m0) :
    StrictlyWeaker (fun P => MixS C D P) (fun P => MixS C A P) :=
  ⟨fun P hl => mixed_entails h P hl, ⟨D, fun _ _ x => x, fun hl => hd (hl m0 hc ha)⟩⟩

/-- Models with `C ∧ A ∧ ¬ D` and with `C ∧ D ∧ ¬ A` make the two schemas incomparable. -/
theorem mixed_incomparable {C D A : M → Prop} {m1 m2 : M}
    (h1 : C m1 ∧ A m1 ∧ ¬ D m1) (h2 : C m2 ∧ D m2 ∧ ¬ A m2) :
    (∃ P, MixS C D P ∧ ¬ MixS C A P) ∧ (∃ P, MixS C A P ∧ ¬ MixS C D P) :=
  ⟨⟨D, fun _ _ x => x, fun hl => h1.2.2 (hl m1 h1.1 h1.2.1)⟩,
   ⟨A, fun _ _ x => x, fun hl => h2.2.2 (hl m2 h2.1 h2.2.1)⟩⟩

/-- Refuting the reference in the mixed case needs a model where its own assumption `D` holds. -/
theorem mixed_ref_false {C D P : M → Prop} {m0 : M} (hc : C m0) (hd : D m0) (hp : ¬ P m0) :
    ¬ MixS C D P :=
  fun h => hp (h m0 hc hd)

end Mixed

/-- The v1.1 defect, as a theorem: both changed assumptions are restrictive on their own, yet the
formalization (`1 ≤ n`) is uniformly stronger than the reference (`2 ≤ n`), not incomparable. -/
theorem separate_restrictions_not_incomparable :
    ∃ C D A : Nat → Prop, (∃ m, C m ∧ ¬ A m) ∧ (∃ m, C m ∧ ¬ D m) ∧ ∀ P, MixS C A P → MixS C D P :=
  ⟨fun _ => True, fun n => 2 ≤ n, fun n => 1 ≤ n, ⟨0, trivial, by decide⟩, ⟨0, trivial, by decide⟩,
   mixed_entails (fun n _ h => by omega)⟩

end ProofScope.ClaimDelta

#print axioms ProofScope.ClaimDelta.entails_transport
#print axioms ProofScope.ClaimDelta.strict_transport
#print axioms ProofScope.ClaimDelta.noninjective_domain_loses_strictness
#print axioms ProofScope.ClaimDelta.instance_congr
#print axioms ProofScope.ClaimDelta.assumption_and_weaker_conclusion
#print axioms ProofScope.ClaimDelta.assumption_vs_stronger_conclusion
#print axioms ProofScope.ClaimDelta.dependent_forall_mono
#print axioms ProofScope.ClaimDelta.vacuous_absorbs
#print axioms ProofScope.ClaimDelta.mixed_entails
#print axioms ProofScope.ClaimDelta.mixed_strict
#print axioms ProofScope.ClaimDelta.mixed_incomparable
#print axioms ProofScope.ClaimDelta.mixed_ref_false
#print axioms ProofScope.ClaimDelta.separate_restrictions_not_incomparable
