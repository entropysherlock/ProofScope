import ProofScope.ClaimDelta
/-!
# Certified drift localization: composition theorems

A reference `A` and a formal statement `D` differ at edit sites `e₁ … eₙ` of their elaborated
terms. Applying the edits one at a time gives a chain `A = S₀, S₁, …, Sₙ = D` of hybrid statements,
all abstracted over the same shared symbols (one interpretation space `T`), so every certificate
below talks about the same `x : T`.

**Localization theorem (`monotone_strict`, `localize_*`).** If every step of the chain is a certified
forward entailment and at least one step `k` is certified strictly weakening (forward entailment plus a
countermodel), then the whole formalization is strictly weaker than the reference, and the
countermodel of step `k` **is** a countermodel for the global pair. So the explanation "edit `k`
weakens the claim, and here is an interpretation that shows it" is itself a checked global fact,
and every other edit is certified not to lose anything in that direction.

**Limit (`cancellation`).** Per-edit verdicts do not compose in general: a weakening edit followed by
a strengthening edit can give a globally equivalent statement. ProofScope therefore only reports a
localized global verdict when the hypotheses of these theorems hold (all steps in one direction),
and otherwise reports the per-edit relations together with the separately certified global relation.
-/

namespace ProofScope.ClaimDelta

universe u
variable {T : Sort u}

theorem equiv_symm {P Q : T → Prop} (h : SchemaEquiv P Q) : SchemaEquiv Q P := ⟨h.2, h.1⟩

theorem equiv_trans {P Q R : T → Prop} (h₁ : SchemaEquiv P Q) (h₂ : SchemaEquiv Q R) : SchemaEquiv P R :=
  ⟨entails_trans h₁.1 h₂.1, entails_trans h₂.2 h₁.2⟩

/-- Steps `S₀ → S₁ → …` that each entail the next. -/
def ChainEntails {T : Type u} : List (T → Prop) → Prop
  | [] => True
  | [_] => True
  | P :: Q :: rest => SchemaEntails P Q ∧ ChainEntails (Q :: rest)

theorem chain_entails_last {T : Type u} : ∀ (P : T → Prop) (rest : List (T → Prop)),
    ChainEntails (P :: rest) → SchemaEntails P ((P :: rest).getLast (List.cons_ne_nil _ _))
  | P, [], _ => entails_refl P
  | P, Q :: rest, ⟨h, hr⟩ => entails_trans h (chain_entails_last Q rest hr)

/-- One strictly weakening step inside a forward-entailing chain makes the whole chain strict,
and the step's countermodel is a global countermodel. -/
theorem monotone_strict {A B C D : T → Prop} (hAB : SchemaEntails A B) (hBC : StrictlyWeaker C B)
    (hCD : SchemaEntails C D) : StrictlyWeaker D A ∧ ∀ x, Separates B C x → Separates A D x :=
  ⟨⟨entails_trans hAB (entails_trans hBC.1 hCD),
    let ⟨x, hx⟩ := hBC.2; ⟨x, hCD x hx.1, fun hA => hx.2 (hAB x hA)⟩⟩,
   fun x hx => ⟨hCD x hx.1, fun hA => hx.2 (hAB x hA)⟩⟩

/-- Localization with all other edits harmless (schema-equivalent). -/
theorem localize_weaker {A B C D : T → Prop} (hAB : SchemaEquiv A B) (hBC : StrictlyWeaker C B)
    (hCD : SchemaEquiv C D) : StrictlyWeaker D A ∧ ∀ x, Separates B C x → Separates A D x :=
  monotone_strict hAB.1 hBC hCD.1

theorem localize_stronger {A B C D : T → Prop} (hAB : SchemaEquiv A B) (hBC : StrictlyWeaker B C)
    (hCD : SchemaEquiv C D) : StrictlyWeaker A D ∧ ∀ x, Separates C B x → Separates D A x :=
  monotone_strict (equiv_symm hCD).1 hBC (equiv_symm hAB).1

/-- A harmless edit can be undone without changing any relation to the reference. -/
theorem harmless_edit {A B C : T → Prop} (h : SchemaEquiv B C) :
    (StrictlyWeaker B A ↔ StrictlyWeaker C A) ∧ (SchemaEquiv A B ↔ SchemaEquiv A C) :=
  ⟨⟨fun ⟨e, x, hx⟩ => ⟨entails_trans e h.1, x, h.1 x hx.1, hx.2⟩,
    fun ⟨e, x, hx⟩ => ⟨entails_trans e h.2, x, h.2 x hx.1, hx.2⟩⟩,
   ⟨fun e => equiv_trans e h, fun e => equiv_trans e (equiv_symm h)⟩⟩

section Cancellation
/-! Counterexample to composing mixed-direction edits: `x ≤ 1` → `x ≤ 2` weakens, `x ≤ 2` →
`x ≤ 2 ∧ x ≠ 2` strengthens, and the end points are equivalent. -/
def CA (x : Nat) : Prop := x ≤ 1
def CB (x : Nat) : Prop := x ≤ 2
def CC (x : Nat) : Prop := x ≤ 2 ∧ x ≠ 2

theorem cancellation : StrictlyWeaker CB CA ∧ StrictlyWeaker CB CC ∧ SchemaEquiv CA CC := by
  refine ⟨⟨fun x h => ?_, 2, ?_, ?_⟩, ⟨fun x h => h.1, 2, ?_, ?_⟩, fun x h => ?_, fun x h => ?_⟩ <;>
    simp only [CA, CB, CC] at * <;> omega

end Cancellation

end ProofScope.ClaimDelta

#print axioms ProofScope.ClaimDelta.equiv_symm
#print axioms ProofScope.ClaimDelta.equiv_trans
#print axioms ProofScope.ClaimDelta.chain_entails_last
#print axioms ProofScope.ClaimDelta.monotone_strict
#print axioms ProofScope.ClaimDelta.localize_weaker
#print axioms ProofScope.ClaimDelta.localize_stronger
#print axioms ProofScope.ClaimDelta.harmless_edit
#print axioms ProofScope.ClaimDelta.cancellation
