/-!
# ScopeElim: exact elimination criteria for schematic claim comparison (SOTA-14)

Core Lean 4 only (no Mathlib, no imports). Every theorem ends with a `#print axioms` line.

ProofScope certifies relations of the form `∀ σ, R σ → F σ` (uniform entailment over an abstracted
symbol `σ`) and `∃ σ, F σ ∧ ¬ R σ` (separation). Up to v1.2 it does so with *sufficient* rules and a
finite witness registry. This file proves *necessary and sufficient* criteria in which the abstracted
symbol has been eliminated, for three shapes, and proves where elimination stops.

* **Theorem A (`horn_complete`)**: `σ` a predicate, reference and formal claim definite clauses with
  arbitrary (dependent, possibly infinite) premise families. Uniform entailment holds iff the formal
  conclusion is *derivable* from the formal premises by the reference rule. The inductive closure is
  the canonical countermodel. Axiom-free.
* **Theorem A₀ (`concl_schematic`)**: premise-free case; entailment iff image coverage. Axiom-free.
* **Theorem B (`fun_schematic`)**: `σ` a *function* symbol occurring once in each claim. Uniform
  entailment holds iff the reference schema is unsatisfiable (vacuity) or a fibrewise refinement
  holds. Uses choice; `choice_of_fun_schematic` shows choice is necessary.
* **Theorem C (`entails_iff_at_square`)**: with *two* occurrences of a function symbol, a linear
  telescope pins the symbol to `n ↦ n * n`, so entailment out of it is truth of an arbitrary
  statement about squaring. No elimination to linear arithmetic can exist (see the report).

All statements are about the *schematic* relation at the declared abstraction. None of them says
anything about the concrete statements unless specialised (`entails_specializes` in ClaimDelta.lean).
-/

namespace ProofScope.ScopeElim

universe u v w v' w'

/-! ## Theorem A: definite clauses over an abstracted predicate -/
section Horn
variable {Z : Sort u}
variable {X : Sort v} {I : X → Sort w} (A : X → Prop) (prem : (x : X) → I x → Z) (s : X → Z)
variable {Y : Sort v'} {J : Y → Sort w'} (B : Y → Prop) (premF : (y : Y) → J y → Z) (t : Y → Z)

/-- The claim `∀ x, A x → (∀ i, σ (prem x i)) → σ (s x)` as a schema over the predicate `σ`. -/
def Clause (σ : Z → Prop) : Prop := ∀ x, A x → (∀ i, σ (prem x i)) → σ (s x)

/-- Closure of a set of facts `E` under the reference rule. -/
inductive Der (E : Z → Prop) : Z → Prop
  | base {z : Z} : E z → Der E z
  | step (x : X) : A x → (∀ i, Der E (prem x i)) → Der E (s x)

/-- The closure is a model of the reference clause (the canonical model). -/
theorem der_model (E : Z → Prop) : Clause A prem s (Der A prem s E) :=
  fun x ha hp => Der.step x ha hp

/-- The closure is the least model containing `E`. -/
theorem der_least {E σ : Z → Prop} (hE : ∀ z, E z → σ z) (hσ : Clause A prem s σ) :
    ∀ z, Der A prem s E z → σ z := by
  intro z d
  induction d with
  | base e => exact hE _ e
  | step x ha _ ih => exact hσ x ha ih

/-- **Theorem A.** Uniform entailment between definite clauses is exactly derivability of the formal
conclusion from the formal premises under the reference rule. -/
theorem horn_complete :
    (∀ σ : Z → Prop, Clause A prem s σ → Clause B premF t σ) ↔
      ∀ y, B y → Der A prem s (fun z => ∃ j, premF y j = z) (t y) := by
  constructor
  · intro h y hb
    exact h _ (der_model A prem s _) y hb (fun j => Der.base ⟨j, rfl⟩)
  · intro h σ hσ y hb hj
    exact der_least A prem s (fun z ⟨j, e⟩ => e ▸ hj j) hσ _ (h y hb)

/-- Canonical countermodel: if some formal instance is not derivable, the closure itself separates. -/
theorem horn_canonical_separation {y : Y} (hb : B y)
    (hn : ¬ Der A prem s (fun z => ∃ j, premF y j = z) (t y)) :
    ∃ σ : Z → Prop, Clause A prem s σ ∧ ¬ Clause B premF t σ :=
  ⟨_, der_model A prem s _, fun h => hn (h y hb (fun j => Der.base ⟨j, rfl⟩))⟩

end Horn

/-! ## Theorem A₀: premise-free case (conclusion-schematic telescopes) -/
section Concl
variable {Z : Sort u} {X : Sort v} {Y : Sort w}
variable (A : X → Prop) (s : X → Z) (B : Y → Prop) (t : Y → Z)

/-- **Theorem A₀.** `∀ P, (∀ x, A x → P (s x)) → (∀ y, B y → P (t y))` iff every formal instance is
a reference instance. The witness predicate is the image of `A` under `s`. -/
theorem concl_schematic :
    (∀ P : Z → Prop, (∀ x, A x → P (s x)) → (∀ y, B y → P (t y))) ↔
      ∀ y, B y → ∃ x, A x ∧ s x = t y :=
  ⟨fun h y hb => h (fun z => ∃ x, A x ∧ s x = z) (fun x ha => ⟨x, ha, rfl⟩) y hb,
   fun h _ hP y hb => let ⟨x, ha, e⟩ := h y hb; e ▸ hP x ha⟩

/-- Dual: the *hypothesis* predicate is abstracted, conclusions are interpreted. -/
theorem hyp_schematic (P : X → Prop) (Q : Y → Prop) :
    (∀ H : Z → Prop, (∀ x, H (s x) → P x) → (∀ y, H (t y) → Q y)) ↔
      ∀ y, (∀ x, s x = t y → P x) → Q y :=
  ⟨fun h y hy => h (fun z => z = t y) hy y rfl,
   fun h _ hH y hy => h y (fun x e => hH x (e ▸ hy))⟩

end Concl

/-- ProofScope v1.2 `mixed_entails` is an equivalence, constructively: with the conclusion abstracted,
replacing assumption `D` by `A` gives a uniformly implied claim iff `D → A` under the shared `C`. -/
theorem mixed_iff {M : Sort u} (C D A : M → Prop) :
    (∀ P : M → Prop, (∀ m, C m → A m → P m) → (∀ m, C m → D m → P m)) ↔ ∀ m, C m → D m → A m := by
  constructor
  · intro h m hc hd
    exact h (fun m => A m) (fun _ _ a => a) m hc hd
  · intro h P hP m hc hd
    exact hP m hc (h m hc hd)

/-! ## Theorem B: one occurrence of an abstracted function symbol -/
section Fun
variable {Z : Sort u} {W : Sort v} {X : Sort w} {Y : Sort w'}
variable (A : X → Prop) (s : X → Z) (ρ : X → W → Prop)
variable (B : Y → Prop) (t : Y → Z) (θ : Y → W → Prop)

/-- Reference `∀ x, A x → ρ x (f (s x))` as a schema over the function `f`. -/
def RefF (f : Z → W) : Prop := ∀ x, A x → ρ x (f (s x))
/-- Formal claim `∀ y, B y → θ y (f (t y))`. -/
def FormF (f : Z → W) : Prop := ∀ y, B y → θ y (f (t y))

/-- `w` is an admissible value at argument `z`: it satisfies every reference constraint landing on `z`. -/
def Adm (z : Z) (w : W) : Prop := ∀ x, A x → s x = z → ρ x w

theorem adm_of_ref {f : Z → W} (h : RefF A s ρ f) (z : Z) : Adm A s ρ z (f z) :=
  fun x ha e => e ▸ h x ha

/-- Sufficiency of the criterion needs no axioms. -/
theorem fun_schematic_sound
    (h : (∃ z, ∀ w, ¬ Adm A s ρ z w) ∨ ∀ y w, B y → Adm A s ρ (t y) w → θ y w) :
    ∀ f, RefF A s ρ f → FormF B t θ f := by
  intro f hR y hb
  cases h with
  | inl hv => exact let ⟨z, hz⟩ := hv; absurd (adm_of_ref A s ρ hR z) (hz (f z))
  | inr hr => exact hr y (f (t y)) hb (adm_of_ref A s ρ hR (t y))

/-- **Theorem B.** Uniform entailment over a once-occurring function symbol holds iff the reference
schema is vacuous (some argument admits no value) or the fibrewise refinement holds. -/
theorem fun_schematic :
    (∀ f, RefF A s ρ f → FormF B t θ f) ↔
      ((∃ z, ∀ w, ¬ Adm A s ρ z w) ∨ ∀ y w, B y → Adm A s ρ (t y) w → θ y w) := by
  constructor
  · intro h
    apply Classical.byCases (p := ∃ z, ∀ w, ¬ Adm A s ρ z w) Or.inl
    intro hnv
    refine Or.inr fun y w hb hadm => ?_
    have total : ∀ z, ∃ w, Adm A s ρ z w := fun z =>
      Classical.byContradiction fun hne => hnv ⟨z, fun w hw => hne ⟨w, hw⟩⟩
    let f : Z → W := fun z => @ite W (z = t y) (Classical.propDecidable _) w (Classical.choose (total z))
    have hf : f (t y) = w := by simp [f]
    have hR : RefF A s ρ f := by
      intro x ha
      apply Classical.byCases (p := s x = t y)
      · intro e
        have : f (s x) = w := by rw [e]; exact hf
        rw [this]; exact hadm x ha e
      · intro ne
        have : f (s x) = Classical.choose (total (s x)) := by simp [f, ne]
        rw [this]; exact Classical.choose_spec (total (s x)) x ha rfl
    have := h f hR y hb
    rw [hf] at this; exact this
  · exact fun_schematic_sound A s ρ B t θ

/-- The vacuity disjunct is exactly unsatisfiability of the reference schema. -/
theorem ref_satisfiable_iff :
    (∃ f, RefF A s ρ f) ↔ ∀ z, ∃ w, Adm A s ρ z w :=
  ⟨fun ⟨f, hf⟩ z => ⟨f z, adm_of_ref A s ρ hf z⟩,
   fun h => ⟨fun z => Classical.choose (h z), fun x ha => Classical.choose_spec (h (s x)) x ha rfl⟩⟩

end Fun

/-- **Choice is necessary for Theorem B.** From excluded middle and the "only if" direction of
Theorem B (at `X = Z`, `s = id`, a one-point formal claim with conclusion `False`), the axiom of
choice for `ρ` follows. The proof itself uses no axioms. -/
theorem choice_of_fun_schematic {Z : Sort u} {W : Sort v}
    (em : ∀ p : Prop, p ∨ ¬ p)
    (elim : ∀ (ρ : Z → W → Prop) (z₀ : Z),
      (∀ f, RefF (fun _ : Z => True) id ρ f → FormF (fun _ : PUnit => True) (fun _ => z₀) (fun _ _ => False) f) →
        ((∃ z, ∀ w, ¬ Adm (fun _ : Z => True) id ρ z w) ∨
          ∀ (_ : PUnit) w, True → Adm (fun _ : Z => True) id ρ z₀ w → False))
    (ρ : Z → W → Prop) (total : ∀ z, ∃ w, ρ z w) : ∃ f : Z → W, ∀ z, ρ z (f z) := by
  cases em (∃ f : Z → W, ∀ z, ρ z (f z)) with
  | inl h => exact h
  | inr hno =>
    cases em (Nonempty Z) with
    | inr hempty => exact ⟨fun z => absurd ⟨z⟩ hempty, fun z => absurd ⟨z⟩ hempty⟩
    | inl hz =>
      let ⟨z₀⟩ := hz
      have key := elim ρ z₀ (fun f hR _ _ => hno ⟨f, fun z => hR z trivial⟩)
      cases key with
      | inl hv =>
        let ⟨z, hzv⟩ := hv
        let ⟨w, hw⟩ := total z
        exact absurd (fun x _ (e : x = z) => e.symm ▸ hw) (hzv w)
      | inr hr =>
        let ⟨w, hw⟩ := total z₀
        exact absurd (fun x _ (e : x = z₀) => e.symm ▸ hw) (hr PUnit.unit w trivial)

/-! ## Theorem C: two occurrences of a function symbol defeat elimination -/
section Square

/-- A formal claim with two occurrences of `f` (at `y` and `y + 1`) and a linear body. -/
def Sq (f : Nat → Nat) : Prop := ∀ y, f 0 = 0 ∧ f (y + 1) = f y + 2 * y + 1

theorem sq_square : Sq (fun n => n * n) :=
  fun y => ⟨rfl, by show (y + 1) * (y + 1) = y * y + 2 * y + 1; rw [Nat.add_mul, Nat.mul_add]; omega⟩

theorem sq_forces {f : Nat → Nat} (h : Sq f) : ∀ n, f n = n * n := by
  intro n
  induction n with
  | zero => exact (h 0).1
  | succ n ih =>
    rw [(h n).2, ih, Nat.add_mul, Nat.mul_add]; omega

/-- **Theorem C.** Uniform entailment out of `Sq` is truth at the squaring function, for *every*
property `Φ` of the symbol. With `Φ` a linear telescope over `f` this is an arbitrary statement of
the form "a polynomial equation has no solution" (products come from `two_mul_from_squares`). -/
theorem entails_iff_at_square (Φ : (Nat → Nat) → Prop) :
    (∀ f, Sq f → Φ f) ↔ Φ (fun n => n * n) :=
  ⟨fun h => h _ sq_square, fun h f hf => (funext (sq_forces hf) : f = fun n => n * n) ▸ h⟩

/-- Products are linear in squares, so polynomial identities are linear telescopes over `f`. -/
theorem two_mul_from_squares (x y : Nat) : 2 * (x * y) + x * x + y * y = (x + y) * (x + y) := by
  rw [Nat.add_mul, Nat.mul_add, Nat.mul_add, Nat.mul_comm y x]; omega

end Square

end ProofScope.ScopeElim

#print axioms ProofScope.ScopeElim.der_model
#print axioms ProofScope.ScopeElim.der_least
#print axioms ProofScope.ScopeElim.horn_complete
#print axioms ProofScope.ScopeElim.horn_canonical_separation
#print axioms ProofScope.ScopeElim.concl_schematic
#print axioms ProofScope.ScopeElim.hyp_schematic
#print axioms ProofScope.ScopeElim.mixed_iff
#print axioms ProofScope.ScopeElim.fun_schematic_sound
#print axioms ProofScope.ScopeElim.fun_schematic
#print axioms ProofScope.ScopeElim.ref_satisfiable_iff
#print axioms ProofScope.ScopeElim.choice_of_fun_schematic
#print axioms ProofScope.ScopeElim.sq_square
#print axioms ProofScope.ScopeElim.sq_forces
#print axioms ProofScope.ScopeElim.entails_iff_at_square
#print axioms ProofScope.ScopeElim.two_mul_from_squares