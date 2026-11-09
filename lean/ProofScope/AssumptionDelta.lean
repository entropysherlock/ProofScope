import ProofScope.ClaimDelta
/-!
# Assumption Delta: certified meaning of an added (or dropped) assumption

Setting. A reference quantifies over *models* `m : M` (a type with operations, a structure, a point)
satisfying shared conditions `C m` and claims `P m`. A formal statement adds an assumption `A m`
(a hypothesis, a Prop-valued typeclass such as `Std.Commutative op`, `Nonempty α`, a decidability or
nonemptiness side condition, a domain restriction):

    R := ∀ m, C m → P m          L := ∀ m, C m → A m → P m

Three certified outcomes, each about the statements, not about a textual difference:

* `Redundant C A` (a proof `∀ m, C m → A m`): the assumption changes nothing (`redundant_equiv`).
* `Restrictive C A` (a model `m` with `C m ∧ ¬ A m`): the formal theorem says nothing about a model
  the reference covers. As claims *about the conclusion*, L is strictly weaker than R
  (`restrictive_iff_strictly_weaker`, with the conclusion `P` as the abstracted symbol). This holds
  even when both theorems are true, where `R ↔ L` is trivially provable.
* `Necessary C A P` (a model with `C m ∧ ¬ A m ∧ ¬ P m`): without the assumption the reference
  claim is **false**; the formalization added a needed hypothesis the reference omitted
  (`necessary_refutes_reference`).

Exactly one of `Redundant` / `Restrictive` holds (`dichotomy`, classical).

Polarity. Adding an assumption weakens the claim only in **positive** position. Under an implication
(negative position) it strengthens it (`negative_position_strengthens`); a compositional checker
must track polarity (`variance_counterexample`).

Domain change. Quantifying over a smaller domain `e : D → M` is the assumption
`A m := ∃ d, e d = m` (`domain_restriction`), so a changed domain is an assumption delta with a
certified outside point.

Dependency limit. If later parts of the statement *use* the assumption (an instance referenced in the
conclusion), there is no well-typed statement "without it", so no separation is defined; the engine
reports INCONCLUSIVE (`docs/v1.0_assumption_delta.md`, test `dependent_instance`).
-/

namespace ProofScope.ClaimDelta

universe u
variable {M : Sort u}

def Redundant (C A : M → Prop) : Prop := ∀ m, C m → A m
def Restrictive (C A : M → Prop) : Prop := ∃ m, C m ∧ ¬ A m
def Necessary (C A P : M → Prop) : Prop := ∃ m, C m ∧ ¬ A m ∧ ¬ P m

/-- The reference and the formal statement as schemas over the conclusion predicate `P`. -/
def RefS (C : M → Prop) (P : M → Prop) : Prop := ∀ m, C m → P m
def FormS (C A : M → Prop) (P : M → Prop) : Prop := ∀ m, C m → A m → P m

theorem redundant_equiv {C A : M → Prop} (h : Redundant C A) (P : M → Prop) :
    FormS C A P ↔ RefS C P :=
  ⟨fun f m c => f m c (h m c), fun r m c _ => r m c⟩

/-- Redundancy makes the schemas equivalent for every conclusion. -/
theorem redundant_schema_equiv {C A : M → Prop} (h : Redundant C A) :
    SchemaEquiv (RefS C) (FormS C A) :=
  ⟨fun P r => (redundant_equiv h P).2 r, fun P f => (redundant_equiv h P).1 f⟩

/-- A restrictive assumption is exactly a strict weakening of the claim, as a schema over the
conclusion; the witness model gives the separating conclusion `P := A`. -/
theorem restrictive_iff_strictly_weaker {C A : M → Prop} :
    Restrictive C A ↔ StrictlyWeaker (FormS C A) (RefS C) := by
  constructor
  · intro ⟨m, hc, ha⟩
    exact ⟨fun P r m c _ => r m c, A, fun _ _ a => a, fun r => ha (r m hc)⟩
  · intro ⟨_, P, hf, hr⟩
    apply Classical.byContradiction
    intro hno
    exact hr fun m c => hf m c (Classical.byContradiction fun ha => hno ⟨m, c, ha⟩)

/-- The witness of a restrictive assumption is a model the reference applies to and the formal
statement does not: the formal statement's instance there is vacuous. -/
theorem restrictive_witness_vacuous {C A P : M → Prop} {m : M} (hc : C m) (ha : ¬ A m) :
    RefS C P → P m ∧ (FormS C A P → True) :=
  fun r => ⟨r m hc, fun _ => trivial⟩

theorem necessary_refutes_reference {C A P : M → Prop} (h : Necessary C A P) : ¬ RefS C P :=
  fun r => let ⟨m, c, _, hp⟩ := h; hp (r m c)

theorem dichotomy (C A : M → Prop) : (Redundant C A ∨ Restrictive C A) ∧ ¬ (Redundant C A ∧ Restrictive C A) := by
  refine ⟨?_, fun ⟨hr, m, c, ha⟩ => ha (hr m c)⟩
  apply Classical.byCases (p := Restrictive C A) (fun h => Or.inr h)
  intro hn
  exact Or.inl fun m c => Classical.byContradiction fun ha => hn ⟨m, c, ha⟩

/-- Polarity: under an implication the comparison flips. If `L` is strictly weaker than `R`, then
`L → Q` is strictly *stronger* than `R → Q` as a schema (for the separating `Q := False`). -/
theorem negative_position_strengthens {T : Sort u} {R L : T → Prop} (h : StrictlyWeaker L R) :
    StrictlyWeaker (fun x => R x → False) (fun x => L x → False) :=
  let ⟨e, x, hl, hr⟩ := h
  ⟨fun y k r => k (e y r), x, hr, fun k => k hl⟩

/-- Counterexample to "adding an assumption always weakens": adding `A n` inside the antecedent of
`(∀ n, n = 0) → False` gives a statement that implies the original for every `A`, but not conversely
(at `A n := n = 0` the original holds and the new one is `False`). So it *strengthens* the claim. -/
theorem variance_counterexample :
    (∀ A : Nat → Prop, ((∀ n, A n → n = 0) → False) → ((∀ n : Nat, n = 0) → False)) ∧
      ¬ (∀ A : Nat → Prop, ((∀ n : Nat, n = 0) → False) → ((∀ n, A n → n = 0) → False)) :=
  ⟨fun _ l h => l fun n _ => h n,
   fun h => h (fun n => n = 0) (fun k => absurd (k 1) (by decide)) (fun _ e => e)⟩

/-- A changed domain `e : D → M` is an added assumption "in the range of `e`". -/
theorem domain_restriction {D : Sort u} (e : D → M) (P : M → Prop) :
    (∀ d, P (e d)) ↔ FormS (fun _ => True) (fun m => ∃ d, e d = m) P :=
  ⟨fun h m _ ⟨d, hd⟩ => hd ▸ h d, fun h d => h (e d) trivial ⟨d, rfl⟩⟩

end ProofScope.ClaimDelta

#print axioms ProofScope.ClaimDelta.redundant_equiv
#print axioms ProofScope.ClaimDelta.redundant_schema_equiv
#print axioms ProofScope.ClaimDelta.restrictive_iff_strictly_weaker
#print axioms ProofScope.ClaimDelta.restrictive_witness_vacuous
#print axioms ProofScope.ClaimDelta.necessary_refutes_reference
#print axioms ProofScope.ClaimDelta.dichotomy
#print axioms ProofScope.ClaimDelta.negative_position_strengthens
#print axioms ProofScope.ClaimDelta.variance_counterexample
#print axioms ProofScope.ClaimDelta.domain_restriction
