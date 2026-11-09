/-!
# Joint assumption–conclusion drift (SOTA-1 research candidate; core Lean, no imports)

Setting (telescope normal form). A reference and a formalization share conditions `C`; the reference
has its own assumptions `D` and conclusion `P`, the formalization its own assumptions `A` and
conclusion `Q`:

    R = ∀ m, C m → D m → P m        L = ∀ m, C m → A m → Q m

ProofScope v1.2 decides only the cases where one of the two parts is unchanged; for a change in both it
answers INCONCLUSIVE. This file gives the inference rules a joint decision procedure needs and the
negative result that rules out deciding from the two parts separately.

* `joint_entails`: `D → A` and `Q → P` on the region `C ∧ D` give `L → R` (the conclusion comparison
  is needed only where the reference's own assumptions hold).
* `joint_refutes_ref`, `joint_refutes_lean`: a model of `C ∧ D ∧ ¬P` (resp. `C ∧ A ∧ ¬Q`) refutes `R`
  (resp. `L`).
* `certified_logical_difference`: a proof of one side plus a refuting model of the other certifies that
  the two closed statements are **logically** inequivalent (`¬ (L ↔ R)`), the negative verdict that
  proof-search-only checkers (BEq+, SemantEq) cannot certify, since a failed search is not evidence.
* `components_do_not_determine_joint`: two instances with the same per-part signature (an added
  restrictive assumption and a pointwise-stronger conclusion) where `L → R` holds in one and fails in
  the other. Any procedure that decides the direction from the parts separately is therefore unsound.
* `vacuous_reference_equiv_true`: a vacuous reference is logically equivalent to every true
  formalization, so logical equivalence (Track A) never certifies a faithful translation (Track B).
-/

namespace ProofScope.JointDrift

universe u

/-- A statement in telescope normal form. -/
def Stmt {M : Sort u} (C H P : M → Prop) : Prop := ∀ m, C m → H m → P m

section
variable {M : Sort u} {C D A P Q : M → Prop}

theorem joint_entails (hA : ∀ m, C m → D m → A m) (hQ : ∀ m, C m → D m → Q m → P m) :
    Stmt C A Q → Stmt C D P :=
  fun hl m hc hd => hQ m hc hd (hl m hc (hA m hc hd))

theorem joint_refutes_ref {m0 : M} (hc : C m0) (hd : D m0) (hp : ¬ P m0) : ¬ Stmt C D P :=
  fun h => hp (h m0 hc hd)

theorem joint_refutes_lean {m0 : M} (hc : C m0) (ha : A m0) (hq : ¬ Q m0) : ¬ Stmt C A Q :=
  fun h => hq (h m0 hc ha)

/-- Proof of the formalization plus a model refuting the reference: certified logical inequivalence. -/
theorem certified_logical_difference (hL : Stmt C A Q) {m0 : M} (hc : C m0) (hd : D m0) (hp : ¬ P m0) :
    ¬ (Stmt C A Q ↔ Stmt C D P) :=
  fun h => joint_refutes_ref hc hd hp (h.mp hL)

/-- Symmetric form: proof of the reference plus a model refuting the formalization. -/
theorem certified_logical_difference' (hR : Stmt C D P) {m0 : M} (hc : C m0) (ha : A m0) (hq : ¬ Q m0) :
    ¬ (Stmt C A Q ↔ Stmt C D P) :=
  fun h => joint_refutes_lean hc ha hq (h.mpr hR)

/-- A vacuous reference is logically equivalent to any true formalization. -/
theorem vacuous_reference_equiv_true (hv : ∀ m, C m → ¬ D m) (hL : Stmt C A Q) :
    Stmt C A Q ↔ Stmt C D P :=
  ⟨fun _ m hc hd => absurd hd (hv m hc), fun _ => hL⟩

end

/-- The per-part signature both instances share: the formalization adds a restrictive assumption
(`∃ m, C m ∧ D m ∧ ¬ A m`) and strengthens the conclusion pointwise (`∀ m, Q m → P m`). -/
def Signature {M : Sort u} (C D A P Q : M → Prop) : Prop :=
  (∃ m, C m ∧ D m ∧ ¬ A m) ∧ (∀ m, Q m → P m)

/-- Deciding the direction from the two parts separately is unsound: the same signature occurs with
`L → R` true and with `L → R` false. -/
theorem components_do_not_determine_joint :
    (∃ C D A P Q : Nat → Prop, Signature C D A P Q ∧ (Stmt C A Q → Stmt C D P)) ∧
    (∃ C D A P Q : Nat → Prop, Signature C D A P Q ∧ ¬ (Stmt C A Q → Stmt C D P)) := by
  refine ⟨⟨fun _ => True, fun _ => True, fun n => n ≤ 5, fun _ => True, fun n => n ≤ 3, ?_, ?_⟩,
          ⟨fun _ => True, fun _ => True, fun n => n ≤ 2, fun n => n ≤ 5, fun n => n ≤ 3, ?_, ?_⟩⟩
  · exact ⟨⟨6, trivial, trivial, by decide⟩, fun _ _ => trivial⟩
  · intro _ _ _ _
    trivial
  · exact ⟨⟨3, trivial, trivial, by decide⟩, fun n h => by simp only at h ⊢; omega⟩
  · intro h
    have hL : Stmt (fun _ => True) (fun n => n ≤ 2) (fun n => n ≤ 3) := fun n _ hn => by simp only at hn ⊢; omega
    have := h hL 6 trivial trivial
    simp only at this
    omega

end ProofScope.JointDrift

#print axioms ProofScope.JointDrift.joint_entails
#print axioms ProofScope.JointDrift.joint_refutes_ref
#print axioms ProofScope.JointDrift.joint_refutes_lean
#print axioms ProofScope.JointDrift.certified_logical_difference
#print axioms ProofScope.JointDrift.certified_logical_difference'
#print axioms ProofScope.JointDrift.vacuous_reference_equiv_true
#print axioms ProofScope.JointDrift.components_do_not_determine_joint
