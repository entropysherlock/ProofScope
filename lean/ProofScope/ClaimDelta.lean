/-!
# ClaimDelta: abstraction-relative statement strength

Two true theorems are logically equivalent (`P ↔ Q` is provable by proving each side), so logical
equivalence cannot tell a faithful formalization from a weaker true one. ClaimDelta compares the
two statements *schematically*: chosen symbols (an operator such as `fun n => 2 ^ n`, a constant,
a user definition) are replaced by a variable `x : T`, giving predicates `P Q : T → Prop` with
`P t` and `Q t` definitionally the original statements for the actual symbols `t`.

* `SchemaEntails P Q` — `Q` follows from `P` for **every** interpretation of the abstracted symbols,
  so the step from `P` to `Q` uses nothing particular about them (only the interpreted theory).
* `Separates P Q x` — the interpretation `x` satisfies `Q` but not `P`: a countermodel showing that
  `Q → P` can only be recovered by using specific facts about the abstracted symbols.

Separate proofs of `P t` and `Q t` cannot produce a `SchemaEntails` certificate, because it must
hold at every `x`, which is how the relation blocks "prove both independently".

What the relation is NOT (proved below by counterexample):
* a separation is not a concrete difference: both statements can be true and concretely
  equivalent (`two_pow_concretely_equivalent`);
* the verdict depends on the abstraction policy: abstracting a symbol whose laws a reviewer would
  accept as harmless rewriting (`n + 0 = n`) produces a separation (`add_zero_policy_artifact`),
  which disappears when the law is retained (`add_zero_with_law`).
-/

namespace ProofScope.ClaimDelta

universe u v

section Relation
variable {T : Sort u}

/-- `Q` follows from `P` at every interpretation of the abstracted symbols. -/
def SchemaEntails (P Q : T → Prop) : Prop := ∀ x, P x → Q x

/-- Interpretation `x` satisfies `Q` but not `P`. -/
def Separates (P Q : T → Prop) (x : T) : Prop := Q x ∧ ¬ P x

def SchemaEquiv (P Q : T → Prop) : Prop := SchemaEntails P Q ∧ SchemaEntails Q P

/-- `Q` is strictly weaker than `P` relative to the abstraction: uniformly implied, and separated. -/
def StrictlyWeaker (Q P : T → Prop) : Prop := SchemaEntails P Q ∧ ∃ x, Separates P Q x

/-- Soundness of a countermodel: no uniform derivation of `P` from `Q` exists. -/
theorem separation_refutes_entailment {P Q : T → Prop} {x : T} (h : Separates P Q x) :
    ¬ SchemaEntails Q P :=
  fun e => h.2 (e x h.1)

/-- A uniform entailment specializes to the actual symbols: it is a proof about the real statements. -/
theorem entails_specializes {P Q : T → Prop} (h : SchemaEntails P Q) (t : T) : P t → Q t := h t

theorem strictlyWeaker_not_equiv {P Q : T → Prop} (h : StrictlyWeaker Q P) : ¬ SchemaEquiv P Q :=
  fun e => let ⟨_, x, hx⟩ := h; separation_refutes_entailment hx e.2

/-- The labels cannot contradict each other: strict weakness is asymmetric. -/
theorem strictlyWeaker_asymm {P Q : T → Prop} (h : StrictlyWeaker Q P) : ¬ StrictlyWeaker P Q :=
  fun h' => let ⟨_, x, hx⟩ := h; separation_refutes_entailment hx h'.1

/-! `SchemaEntails` is a preorder; `SchemaEquiv` is its equivalence and `StrictlyWeaker` its strict
part, so statement strength is a partial order on equivalence classes (for a fixed abstraction),
not a total one: two statements can be incomparable (`incomparable_example`). -/
theorem entails_refl (P : T → Prop) : SchemaEntails P P := fun _ h => h

theorem entails_trans {P Q R : T → Prop} (h₁ : SchemaEntails P Q) (h₂ : SchemaEntails Q R) :
    SchemaEntails P R := fun x h => h₂ x (h₁ x h)

theorem strictlyWeaker_trans {P Q R : T → Prop} (h₁ : StrictlyWeaker Q P) (h₂ : StrictlyWeaker R Q) :
    StrictlyWeaker R P :=
  let ⟨e₁, _⟩ := h₁
  let ⟨e₂, x, hR, hQ⟩ := h₂
  ⟨entails_trans e₁ e₂, x, hR, fun hP => hQ (e₁ x hP)⟩

/-- Concrete truth cannot be separated at the actual symbols (the v0.6 observability theorem). -/
theorem no_concrete_separation {P Q : T → Prop} {t : T} (hP : P t) : ¬ Separates P Q t :=
  fun h => h.2 hP

end Relation

section Refinement
/-! Abstracting more symbols (type `U`) versus fewer (type `T`, where the extra symbols are fixed by
`e : T → U`). Entailment proved with more abstraction survives with less; a countermodel found with
less abstraction survives with more. So the sets of abstracted symbols that separate two statements
are upward closed, and *minimal separating sets* are well defined: they are the explanation. -/
variable {T : Sort u} {U : Sort v} (e : T → U) {P Q : U → Prop}

theorem entails_restrict (h : SchemaEntails P Q) : SchemaEntails (P ∘ e) (Q ∘ e) :=
  fun x => h (e x)

theorem separation_lifts {x : T} (h : Separates (P ∘ e) (Q ∘ e) x) : Separates P Q (e x) := h

end Refinement

section Examples

/-- Reference `∀ n, n < 2 ^ n`, formalization `∀ n, n ≤ 2 ^ n`, with `fun n => 2 ^ n` abstracted. -/
def RefLt (f : Nat → Nat) : Prop := ∀ n, n < f n
def FormLe (f : Nat → Nat) : Prop := ∀ n, n ≤ f n

theorem two_pow_strictly_weaker : StrictlyWeaker FormLe RefLt :=
  ⟨fun _ h n => Nat.le_of_lt (h n), fun n => n, fun n => Nat.le_refl n, fun h => Nat.lt_irrefl 0 (h 0)⟩

/-- Both concrete statements are true, hence concretely equivalent: the separation above is not a
concrete difference, and no pointwise or logical-equivalence check can see it. -/
theorem two_pow_concretely_equivalent : RefLt (fun n => 2 ^ n) ↔ FormLe (fun n => 2 ^ n) :=
  ⟨fun _ n => Nat.le_of_lt Nat.lt_two_pow_self, fun _ _ => Nat.lt_two_pow_self⟩

/-- Policy artifact: `∀ n, n + 0 = n` against `∀ n, n = n` with `+` abstracted and no law kept. -/
def AddZero (g : Nat → Nat → Nat) : Prop := ∀ n, g n 0 = n
def Refl (_ : Nat → Nat → Nat) : Prop := ∀ m : Nat, m = m

theorem add_zero_policy_artifact : StrictlyWeaker Refl AddZero :=
  ⟨fun _ _ _ => rfl, fun _ _ => 0, fun _ => rfl, fun h => Nat.noConfusion (h 1)⟩

/-- Keeping the law `g n 0 = n` in the abstraction (interpretations are lawful) removes the artifact. -/
def Lawful := { g : Nat → Nat → Nat // ∀ n, g n 0 = n }

theorem add_zero_with_law : SchemaEquiv (fun g : Lawful => AddZero g.1) (fun g : Lawful => Refl g.1) :=
  ⟨fun _ _ _ => rfl, fun g _ => g.2⟩

/-- Strength is only a partial order: `∀ n, f n ≤ 1` and `∀ n, 1 ≤ f n` are incomparable. -/
def AtMostOne (f : Nat → Nat) : Prop := ∀ n, f n ≤ 1
def AtLeastOne (f : Nat → Nat) : Prop := ∀ n, 1 ≤ f n

theorem incomparable_example :
    Separates AtMostOne AtLeastOne (fun _ => 2) ∧ Separates AtLeastOne AtMostOne (fun _ => 0) :=
  ⟨⟨fun _ => Nat.le_succ 1, fun h => absurd (h 0) (by decide)⟩,
   ⟨fun _ => Nat.zero_le 1, fun h => absurd (h 0) (by decide)⟩⟩

end Examples

end ProofScope.ClaimDelta

#print axioms ProofScope.ClaimDelta.separation_refutes_entailment
#print axioms ProofScope.ClaimDelta.entails_specializes
#print axioms ProofScope.ClaimDelta.strictlyWeaker_not_equiv
#print axioms ProofScope.ClaimDelta.strictlyWeaker_asymm
#print axioms ProofScope.ClaimDelta.entails_refl
#print axioms ProofScope.ClaimDelta.entails_trans
#print axioms ProofScope.ClaimDelta.strictlyWeaker_trans
#print axioms ProofScope.ClaimDelta.no_concrete_separation
#print axioms ProofScope.ClaimDelta.entails_restrict
#print axioms ProofScope.ClaimDelta.separation_lifts
#print axioms ProofScope.ClaimDelta.two_pow_strictly_weaker
#print axioms ProofScope.ClaimDelta.two_pow_concretely_equivalent
#print axioms ProofScope.ClaimDelta.add_zero_policy_artifact
#print axioms ProofScope.ClaimDelta.add_zero_with_law
#print axioms ProofScope.ClaimDelta.incomparable_example
