import ProofScope.ScopeElim
/-!
# ScopeCert: helper lemmas and closing tactics for generated ScopeElim certificates (SOTA-15)

Core Lean 4 only. Nothing here is trusted: generated certificates that use these lemmas are still
compiled, axiom-checked and replayed by `proofscope.certify`.
-/
namespace ProofScope.ScopeCert

/-- Close a closed or linear equation between natural-number terms. -/
macro "ps_eq" : tactic => `(tactic| first | rfl | omega | decide)
/-- Close a guard: a trivial, linear or decidable side condition. -/
macro "ps_triv" : tactic => `(tactic| first | trivial | assumption | omega | decide)

theorem cast1 {S : Nat → Prop} {a b : Nat} (h : S a) (e : a = b) : S b := e ▸ h
theorem cast2 {S : Nat → Nat → Prop} {a b a' b' : Nat} (h : S a b) (e₁ : a = a') (e₂ : b = b') :
    S a' b' := e₁ ▸ e₂ ▸ h
theorem cast3 {S : Nat → Nat → Nat → Prop} {a b c a' b' c' : Nat} (h : S a b c) (e₁ : a = a')
    (e₂ : b = b') (e₃ : c = c') : S a' b' c' := e₁ ▸ e₂ ▸ e₃ ▸ h

/-- A failed uniform entailment has a separating interpretation (classically). -/
theorem sep_of_not_entails {T : Sort u} {P Q : T → Prop} (h : ¬ ∀ x, P x → Q x) :
    ∃ x, P x ∧ ¬ Q x :=
  Classical.byContradiction fun hne =>
    h fun x hp => Classical.byContradiction fun hq => hne ⟨x, hp, hq⟩

/-- Every predicate is the solution set of `g · = c` for some function `g`. -/
noncomputable def realize (S : Nat → Prop) (c : Nat) (z : Nat) : Nat :=
  @ite Nat (S z) (Classical.propDecidable _) c (c + 1)

theorem realize_eq (S : Nat → Prop) (c : Nat) : (fun z => realize S c z = c) = S := by
  funext z
  apply propext
  unfold realize
  constructor
  · intro h
    apply Classical.byContradiction
    intro hn
    simp [hn] at h
  · intro h
    simp [h]

end ProofScope.ScopeCert

#print axioms ProofScope.ScopeCert.sep_of_not_entails
#print axioms ProofScope.ScopeCert.realize_eq
