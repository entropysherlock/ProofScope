/-!
# CJCS: Certified Joint-drift Countermodel Search — soundness theory (core Lean, no imports)

Track A (logical) certificates for two closed statements `X` (reference) and `Y` (formalization), and the
drift-region theory used to explain a difference. Every decisive answer of
`proofscope/experimental/cjcs.py` is an instance of one theorem below.

1. `cjcs_sound`: a refutation of one side and a proof of the other give `¬ (X ↔ Y)`.
2. `difference_needs_a_proof`: conversely, every certificate of `¬ (X ↔ Y)` yields `X ∨ Y`. Certifying a
   logical difference is therefore at least as hard as proving one of the two statements, so a pure
   refuter (countermodel search) and a pure prover (equivalence search) cannot certify differences on their
   own. This is the reason for CJCS's two-stage design.
3. `both_false_equiv`, `both_true_equiv`: the decisive equivalences are logical only (two refuted, or two
   proved, statements), never fidelity (`vacuous_logical_equiv` makes this explicit).
4. Drift regions. Write `R m := H m → D m → P m` and `L m := H m → A m → Q m` pointwise.
   `disagreement_partition`: a point where the reference's instance holds and the formalization's fails
   lies in exactly one of two regions: `lean_excluded` (H ∧ A ∧ ¬D ∧ ¬Q) or `conclusion_lean_stronger`
   (H ∧ D ∧ A ∧ P ∧ ¬Q). The region witnesses CJCS certifies are therefore a complete, non-overlapping
   explanation of every pointwise disagreement in that direction (symmetric statement for the other).
5. `joint_failure_iff`: if each single change is harmless on its own (`Stmt H A P` and `Stmt H D Q` hold),
   the combined statement `Stmt H A Q` fails exactly at points of the joint region
   (H ∧ A ∧ ¬D ∧ P ∧ ¬Q). `joint_disjoint_harmless`: if that region is empty, the combination is harmless.
-/

namespace ProofScope.CJCS

universe u

/-- A statement in telescope normal form. -/
def Stmt {M : Sort u} (H C P : M → Prop) : Prop := ∀ m, H m → C m → P m

section Logical
variable {X Y : Prop}

theorem cjcs_sound (hY : Y) (hX : ¬ X) : ¬ (X ↔ Y) := fun h => hX (h.mpr hY)

theorem cjcs_sound' (hX : X) (hY : ¬ Y) : ¬ (X ↔ Y) := fun h => hY (h.mp hX)

theorem difference_needs_a_proof (h : ¬ (X ↔ Y)) : X ∨ Y :=
  Classical.byCases (fun hx : X => Or.inl hx)
    (fun hx => Classical.byCases (fun hy : Y => Or.inr hy)
      (fun hy => absurd ⟨fun x => absurd x hx, fun y => absurd y hy⟩ h))

theorem nonequiv_iff : ¬ (X ↔ Y) ↔ (X ∧ ¬ Y) ∨ (Y ∧ ¬ X) := by
  constructor
  · intro h
    rcases difference_needs_a_proof h with hx | hy
    · exact Or.inl ⟨hx, fun hy => h ⟨fun _ => hy, fun _ => hx⟩⟩
    · exact Or.inr ⟨hy, fun hx => h ⟨fun _ => hy, fun _ => hx⟩⟩
  · rintro (⟨hx, hy⟩ | ⟨hy, hx⟩)
    · exact cjcs_sound' hx hy
    · exact cjcs_sound hy hx

theorem both_false_equiv (hX : ¬ X) (hY : ¬ Y) : X ↔ Y := ⟨fun x => absurd x hX, fun y => absurd y hY⟩

theorem both_true_equiv (hX : X) (hY : Y) : X ↔ Y := ⟨fun _ => hY, fun _ => hX⟩

/-- A refuted statement is unprovable: refute-first pruning never discards a provable obligation. -/
theorem refuted_unprovable (hX : ¬ X) : ¬ Nonempty X := fun ⟨x⟩ => hX x

end Logical

/-- Logical equivalence is not fidelity: a vacuous reference is logically equivalent to every true
formalization, whatever it says. -/
theorem vacuous_logical_equiv {M : Sort u} {H D P A Q : M → Prop}
    (hv : ∀ m, H m → ¬ D m) (hL : Stmt H A Q) : Stmt H D P ↔ Stmt H A Q :=
  ⟨fun _ => hL, fun _ m hh hd => absurd hd (hv m hh)⟩

section Regions
variable {M : Sort u} {H D P A Q : M → Prop}

/-- Pointwise partition of the disagreement points (reference instance holds, formalization's fails). -/
theorem disagreement_partition (m : M) :
    ((H m → D m → P m) ∧ ¬ (H m → A m → Q m)) ↔
      ((H m ∧ A m ∧ ¬ D m ∧ ¬ Q m) ∨ (H m ∧ D m ∧ A m ∧ P m ∧ ¬ Q m)) := by
  constructor
  · rintro ⟨hr, hl⟩
    have hh : H m := Classical.byContradiction fun hh => hl fun h _ => absurd h hh
    have ha : A m := Classical.byContradiction fun ha => hl fun _ a => absurd a ha
    have hq : ¬ Q m := fun q => hl fun _ _ => q
    by_cases hd : D m
    · exact Or.inr ⟨hh, hd, ha, hr hh hd, hq⟩
    · exact Or.inl ⟨hh, ha, hd, hq⟩
  · rintro (⟨hh, ha, hd, hq⟩ | ⟨hh, hd, ha, _, hq⟩)
    · exact ⟨fun _ d => absurd d hd, fun hl => hq (hl hh ha)⟩
    · exact ⟨fun _ _ => ‹P m›, fun hl => hq (hl hh ha)⟩

/-- The two regions are disjoint. -/
theorem regions_disjoint (m : M) : ¬ ((H m ∧ A m ∧ ¬ D m ∧ ¬ Q m) ∧ (H m ∧ D m ∧ A m ∧ P m ∧ ¬ Q m)) :=
  fun ⟨⟨_, _, hd, _⟩, ⟨_, d, _⟩⟩ => hd d

/-- Each region witness refutes the formalization. -/
theorem region_refutes_lean {m : M} (h : (H m ∧ A m ∧ ¬ D m ∧ ¬ Q m) ∨ (H m ∧ D m ∧ A m ∧ P m ∧ ¬ Q m)) :
    ¬ Stmt H A Q := by
  intro hl
  rcases h with ⟨hh, ha, _, hq⟩ | ⟨hh, _, ha, _, hq⟩
  · exact hq (hl m hh ha)
  · exact hq (hl m hh ha)

/-- A `ref_excluded` witness refutes the reference at a point the formalization's assumption excludes. -/
theorem ref_excluded_refutes_ref {m : M} (h : H m ∧ D m ∧ ¬ A m ∧ ¬ P m) : ¬ Stmt H D P :=
  fun hr => h.2.2.2 (hr m h.1 h.2.1)

/-- Joint drift: when each single change is harmless, the combination fails exactly on the joint region. -/
theorem joint_failure_iff (hA : Stmt H A P) (hQ : Stmt H D Q) :
    ¬ Stmt H A Q ↔ ∃ m, H m ∧ A m ∧ ¬ D m ∧ P m ∧ ¬ Q m := by
  constructor
  · intro hl
    apply Classical.byContradiction
    intro hno
    apply hl
    intro m hh ha
    by_cases hd : D m
    · exact hQ m hh hd
    · exact Classical.byContradiction fun hq => hno ⟨m, hh, ha, hd, hA m hh ha, hq⟩
  · rintro ⟨m, hh, ha, _, _, hq⟩ hl
    exact hq (hl m hh ha)

theorem joint_disjoint_harmless (hA : Stmt H A P) (hQ : Stmt H D Q)
    (hdisj : ∀ m, H m → A m → ¬ D m → P m → Q m) : Stmt H A Q := by
  intro m hh ha
  by_cases hd : D m
  · exact hQ m hh hd
  · exact hdisj m hh ha hd (hA m hh ha)

end Regions

/-- The SOTA-3 development example: both single changes are harmless, the joint change is not. -/
theorem joint_example :
    Stmt (fun _ : Nat => True) (fun n => n ≤ 7) (fun n => n ≤ 10) ∧
    Stmt (fun _ : Nat => True) (fun n => n ≤ 5) (fun n => n ≤ 6) ∧
    ¬ Stmt (fun _ : Nat => True) (fun n => n ≤ 7) (fun n => n ≤ 6) :=
  ⟨fun n _ h => by omega, fun n _ h => by omega, fun h => absurd (h 7 trivial (by decide)) (by decide)⟩

end ProofScope.CJCS

#print axioms ProofScope.CJCS.cjcs_sound
#print axioms ProofScope.CJCS.cjcs_sound'
#print axioms ProofScope.CJCS.difference_needs_a_proof
#print axioms ProofScope.CJCS.nonequiv_iff
#print axioms ProofScope.CJCS.both_false_equiv
#print axioms ProofScope.CJCS.both_true_equiv
#print axioms ProofScope.CJCS.refuted_unprovable
#print axioms ProofScope.CJCS.vacuous_logical_equiv
#print axioms ProofScope.CJCS.disagreement_partition
#print axioms ProofScope.CJCS.regions_disjoint
#print axioms ProofScope.CJCS.region_refutes_lean
#print axioms ProofScope.CJCS.ref_excluded_refutes_ref
#print axioms ProofScope.CJCS.joint_failure_iff
#print axioms ProofScope.CJCS.joint_disjoint_harmless
#print axioms ProofScope.CJCS.joint_example
