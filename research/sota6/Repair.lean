set_option autoImplicit false
/-!
# SOTA-6: formulation equivalence and certified minimal repair (core Lean 4.34.1)

A statement in *hypothesis form* over an aligned context `Γ` is `∀ γ : Γ, hyp γ → concl γ`.

* `FormEquiv R F`: same hypothesis region and the same conclusion on that region. Unlike closed or open
  equivalence it is not trivialised when both statements are true (`open_equiv_trivial_for_true`).
* A *repair grammar* is a function `apply : Nat → HForm Γ` on edit masks `e < 2^n` with a cost.
* `minimal_repair_sound`: a proof of `FormEquiv R (apply e₀)` together with a separating point for every
  cheaper mask certifies that `apply e₀` is a repair of minimum cost **within the grammar**.
* `formEquiv_iff_points`: over a finite context listed exhaustively, `FormEquiv` is equivalent to a check
  on the listed points, so the search is complete there (decidable by the kernel).
-/

namespace SOTA6

structure HForm (Γ : Type) where
  hyp : Γ → Prop
  concl : Γ → Prop

variable {Γ : Type}

def HForm.stmt (S : HForm Γ) : Prop := ∀ γ, S.hyp γ → S.concl γ

def FormEquiv (R F : HForm Γ) : Prop :=
  (∀ γ, R.hyp γ ↔ F.hyp γ) ∧ (∀ γ, R.hyp γ → (R.concl γ ↔ F.concl γ))

/-- A point separating `F` from `R` as formulations. -/
def Separates (R F : HForm Γ) (γ : Γ) : Prop :=
  ¬ (R.hyp γ ↔ F.hyp γ) ∨ (R.hyp γ ∧ ¬ (R.concl γ ↔ F.concl γ))

/-- Formulation equivalence implies pointwise (open) equivalence, hence closed equivalence. -/
theorem formEquiv_open {R F : HForm Γ} (h : FormEquiv R F) (γ : Γ) :
    (R.hyp γ → R.concl γ) ↔ (F.hyp γ → F.concl γ) := by
  constructor
  · intro hr hf; exact (h.2 γ ((h.1 γ).mpr hf)).mp (hr ((h.1 γ).mpr hf))
  · intro hf hr; exact (h.2 γ hr).mpr (hf ((h.1 γ).mp hr))

theorem formEquiv_stmt {R F : HForm Γ} (h : FormEquiv R F) : R.stmt ↔ F.stmt :=
  ⟨fun hr γ => (formEquiv_open h γ).mp (hr γ), fun hf γ => (formEquiv_open h γ).mpr (hf γ)⟩

/-- Soundness of separation certificates. -/
theorem not_formEquiv_of_separates {R F : HForm Γ} {γ : Γ} (hs : Separates R F γ) : ¬ FormEquiv R F := by
  intro h
  rcases hs with hs | ⟨hr, hc⟩
  · exact hs (h.1 γ)
  · exact hc (h.2 γ hr)

/-- Why open equivalence is the wrong repair target: when both statements hold, the open formulas agree
everywhere regardless of what they say. -/
theorem open_equiv_trivial_for_true (R F : HForm Γ) (hr : R.stmt) (hf : F.stmt) (γ : Γ) :
    (R.hyp γ → R.concl γ) ↔ (F.hyp γ → F.concl γ) :=
  ⟨fun _ => hf γ, fun _ => hr γ⟩

/-- **Minimal repair soundness.** If `apply e₀` is formulation-equivalent to `R` and every mask of smaller
cost has a separating point, then no mask of smaller cost is a repair. -/
theorem minimal_repair_sound (R : HForm Γ) (apply : Nat → HForm Γ) (cost : Nat → Nat) (n e₀ : Nat)
    (_hrep : FormEquiv R (apply e₀))
    (hsep : ∀ e, e < 2 ^ n → cost e < cost e₀ → ∃ γ, Separates R (apply e) γ) :
    ∀ e, e < 2 ^ n → cost e < cost e₀ → ¬ FormEquiv R (apply e) := by
  intro e he hc
  obtain ⟨γ, hγ⟩ := hsep e he hc
  exact not_formEquiv_of_separates hγ

/-- Completeness over finite contexts: if `pts` lists every point, formulation equivalence is exactly the
check on the listed points (so it is decided by evaluation, and the minimal-repair search is exact). -/
theorem formEquiv_iff_points (R F : HForm Γ) (pts : List Γ) (hall : ∀ γ, γ ∈ pts) :
    FormEquiv R F ↔ ∀ γ ∈ pts, (R.hyp γ ↔ F.hyp γ) ∧ (R.hyp γ → (R.concl γ ↔ F.concl γ)) := by
  constructor
  · intro h γ _; exact ⟨h.1 γ, h.2 γ⟩
  · intro h; exact ⟨fun γ => (h γ (hall γ)).1, fun γ => (h γ (hall γ)).2⟩

/-- Distinct minimal repairs: two repairs of equal cost are both minimal (minimality is not uniqueness). -/
theorem two_minimal_repairs (R : HForm Γ) (apply : Nat → HForm Γ) (cost : Nat → Nat) (n e₁ e₂ : Nat)
    (h₁ : FormEquiv R (apply e₁)) (h₂ : FormEquiv R (apply e₂)) (hc : cost e₁ = cost e₂)
    (hsep : ∀ e, e < 2 ^ n → cost e < cost e₁ → ∃ γ, Separates R (apply e) γ) :
    (∀ e, e < 2 ^ n → cost e < cost e₁ → ¬ FormEquiv R (apply e)) ∧
    (∀ e, e < 2 ^ n → cost e < cost e₂ → ¬ FormEquiv R (apply e)) :=
  ⟨minimal_repair_sound R apply cost n e₁ h₁ hsep,
   minimal_repair_sound R apply cost n e₂ h₂ (hc ▸ hsep)⟩

/-! ### The motivating instance: open equivalence accepts a wrong repair, formulation equivalence does not -/

def divRef : HForm Nat := ⟨fun n => n ≠ 0, fun n => n / n = 1⟩
def divWrong : HForm Nat := ⟨fun n => 2 ≤ n, fun n => n / n = 1⟩

theorem divRef_true : divRef.stmt := fun n (h : n ≠ 0) => Nat.div_self (Nat.pos_of_ne_zero h)
theorem divWrong_true : divWrong.stmt := fun n (h : 2 ≤ n) => Nat.div_self (by omega)

/-- Both statements are true, so they are open-equivalent everywhere ... -/
theorem div_open_equiv (n : Nat) : (divRef.hyp n → divRef.concl n) ↔ (divWrong.hyp n → divWrong.concl n) :=
  open_equiv_trivial_for_true divRef divWrong divRef_true divWrong_true n

/-- ... but `2 ≤ n` is not the reference's hypothesis region: separated at `n = 1`. -/
theorem div_not_formEquiv : ¬ FormEquiv divRef divWrong :=
  not_formEquiv_of_separates (γ := 1) (Or.inl (by show ¬ ((1 : Nat) ≠ 0 ↔ 2 ≤ 1); decide))

end SOTA6

#print axioms SOTA6.formEquiv_open
#print axioms SOTA6.formEquiv_stmt
#print axioms SOTA6.not_formEquiv_of_separates
#print axioms SOTA6.open_equiv_trivial_for_true
#print axioms SOTA6.minimal_repair_sound
#print axioms SOTA6.formEquiv_iff_points
#print axioms SOTA6.two_minimal_repairs
#print axioms SOTA6.div_open_equiv
#print axioms SOTA6.div_not_formEquiv
