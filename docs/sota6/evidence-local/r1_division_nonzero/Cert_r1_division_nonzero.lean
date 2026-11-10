set_option autoImplicit false
set_option maxHeartbeats 400000
set_option linter.unusedVariables false

structure HForm (Γ : Type) where
  hyp : Γ → Prop
  concl : Γ → Prop

def FormEquiv {Γ : Type} (R F : HForm Γ) : Prop :=
  (∀ γ, R.hyp γ ↔ F.hyp γ) ∧ (∀ γ, R.hyp γ → (R.concl γ ↔ F.concl γ))
def Separates {Γ : Type} (R F : HForm Γ) (γ : Γ) : Prop :=
  ¬ (R.hyp γ ↔ F.hyp γ) ∨ (R.hyp γ ∧ ¬ (R.concl γ ↔ F.concl γ))
theorem not_formEquiv_of_separates {Γ : Type} {R F : HForm Γ} {γ : Γ} (hs : Separates R F γ) :
    ¬ FormEquiv R F := by
  intro h
  rcases hs with hs | ⟨hr, hc⟩
  · exact hs (h.1 γ)
  · exact hc (h.2 γ hr)

abbrev Γ := Nat
abbrev R : HForm Γ := ⟨fun n => (n ≠ 0), fun n => n / n = 1⟩
abbrev apply (e : Nat) : HForm Γ := ⟨fun n => ((e.testBit 0 = true → (n ≠ 0))) ∧ ((e.testBit 1 = true → (0 < n))) ∧ ((e.testBit 2 = true → (2 ≤ n))) ∧ ((e.testBit 3 = true → (n % 2 = 1))), fun n => n / n = 1⟩
def cost (e : Nat) : Nat := (List.range 4).countP (fun i => e.testBit i)
instance (e : Nat) (γ : Γ) : Decidable (Separates R (apply e) γ) := by
  unfold Separates; rcases γ with n; infer_instance

def pts : List Γ := [(0 : Nat), (1 : Nat), (2 : Nat), (3 : Nat), (4 : Nat), (5 : Nat)]
def wit (e : Nat) : Γ := pts.getD (([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 1, 1, 1, 1] : List Nat).getD e 0) (0 : Nat)

theorem R_source : R.hyp = R.hyp := rfl
/-- source link: the reference statement as written equals the hypothesis form -/
theorem R_source_stmt : (∀ (n : Nat), n ≠ 0 → n / n = 1) ↔ (∀ γ : Γ, R.hyp γ → R.concl γ) := by
  constructor
  · intro h γ; rcases γ with n; simp only [R]; intro hh; simp_all
  · intro h; intros; first | (apply h; simp_all) | simp_all
theorem F_source_stmt : (∀ (n : Nat), n / n = 1) ↔ (∀ γ : Γ, (apply 0).hyp γ → (apply 0).concl γ) := by
  constructor
  · intro h γ; rcases γ with n; simp (config := {decide := true}) only [apply, Nat.testBit_zero, Nat.zero_testBit] at *; intro hh; simp_all
  · intro h; intros; first | (apply h; simp (config := {decide := true}) [Nat.zero_testBit] <;> simp_all) | simp_all

theorem repair_1 : FormEquiv R (apply 1) := by
  refine ⟨fun γ => ?_, fun γ hr => ?_⟩ <;> rcases γ with n <;> simp (config := {decide := true}) [apply, R, HForm.hyp, HForm.concl, Nat.testBit] at * <;> omega

theorem repair_2 : FormEquiv R (apply 2) := by
  refine ⟨fun γ => ?_, fun γ hr => ?_⟩ <;> rcases γ with n <;> simp (config := {decide := true}) [apply, R, Nat.testBit] at * <;> grind

/-- every mask cheaper than the repair is separated at an explicit point (kernel `decide`) -/
theorem cheaper_separated : ∀ e, e < 2 ^ 4 → cost e < cost 1 → Separates R (apply e) (wit e) := by decide
theorem minimal : ∀ e, e < 2 ^ 4 → cost e < cost 1 → ¬ FormEquiv R (apply e) :=
  fun e he hc => not_formEquiv_of_separates (cheaper_separated e he hc)
#print axioms R_source_stmt
#print axioms F_source_stmt
#print axioms repair_1
#print axioms repair_2
#print axioms cheaper_separated
#print axioms minimal
