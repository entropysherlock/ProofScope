/-!
# MonoElim: elimination of a function symbol under the monotonicity law (SOTA-15, Challenge D)

Core Lean 4 only. SOTA-14 Theorem B eliminates a function symbol that occurs once and is otherwise
unconstrained. Monotonicity `a ≤ b → f a ≤ f b` uses the symbol twice, so Theorem B does not apply.
This file shows that elimination survives the law when the reference constraints are *convex*
(a lower bound `l z ≤ f z` and an optional upper bound `f z ≤ u z` at each argument):

* `mono_extension`: a monotone function meeting all bounds and passing through `(z₀, w₀)` exists
  iff three *two-point* conditions hold. The witness is canonical (the least such function).
* `mono_elim`: for a feasible reference, uniform entailment over monotone functions of a claim in
  which the symbol occurs once is equivalent to a residual obligation without the symbol.
* `nonconvex_two_point_fails`: with non-convex value sets the two-point conditions do not suffice,
  so convexity is a real hypothesis.

All three are axiom-free or use only `propext`/`Quot.sound` (see the `#print axioms` lines).
-/
namespace ProofScope.MonoElim

def Mono (f : Nat → Nat) : Prop := ∀ a b, a ≤ b → f a ≤ f b

/-- `w` respects an optional upper bound. -/
def LeOpt (w : Nat) (o : Option Nat) : Prop := ∀ k, o = some k → w ≤ k

/-- Convex reference constraints: `l z ≤ f z` and, where given, `f z ≤ u z`. -/
def Box (l : Nat → Nat) (u : Nat → Option Nat) (f : Nat → Nat) : Prop :=
  ∀ z, l z ≤ f z ∧ LeOpt (f z) (u z)

/-- Running maximum of the lower bounds. -/
def L (l : Nat → Nat) : Nat → Nat
  | 0 => l 0
  | z + 1 => max (L l z) (l (z + 1))

theorem L_ge (l : Nat → Nat) : ∀ z, l z ≤ L l z
  | 0 => Nat.le_refl _
  | _ + 1 => Nat.le_max_right _ _

theorem L_step (l : Nat → Nat) (z : Nat) : L l z ≤ L l (z + 1) := Nat.le_max_left _ _

theorem L_mono (l : Nat → Nat) : ∀ a b, a ≤ b → L l a ≤ L l b := by
  intro a b h
  induction b with
  | zero => have : a = 0 := Nat.le_zero.1 h; subst this; exact Nat.le_refl _
  | succ n ih =>
    rcases Nat.lt_or_ge a (n + 1) with h' | h'
    · exact Nat.le_trans (ih (Nat.le_of_lt_succ h')) (L_step l n)
    · have : a = n + 1 := Nat.le_antisymm h h'; subst this; exact Nat.le_refl _

theorem L_attained (l : Nat → Nat) : ∀ z, ∃ a, a ≤ z ∧ L l z = l a
  | 0 => ⟨0, Nat.le_refl _, rfl⟩
  | z + 1 => by
    obtain ⟨a, ha, e⟩ := L_attained l z
    rcases Nat.le_total (L l z) (l (z + 1)) with h | h
    · exact ⟨z + 1, Nat.le_refl _, Nat.max_eq_right h⟩
    · exact ⟨a, Nat.le_succ_of_le ha, by show max (L l z) (l (z + 1)) = l a; rw [Nat.max_eq_left h, e]⟩

/-- The canonical monotone solution through `(z₀, w₀)`. -/
def canon (l : Nat → Nat) (z₀ w₀ : Nat) (z : Nat) : Nat :=
  if z < z₀ then L l z else max (L l z) w₀

/-- **Two-point extension.** -/
theorem mono_extension (l : Nat → Nat) (u : Nat → Option Nat) (z₀ w₀ : Nat) :
    (∃ f, Mono f ∧ Box l u f ∧ f z₀ = w₀) ↔
      ((∀ a b, a ≤ b → LeOpt (l a) (u b)) ∧ (∀ a, a ≤ z₀ → l a ≤ w₀) ∧
        (∀ b, z₀ ≤ b → LeOpt w₀ (u b))) := by
  constructor
  · intro ⟨f, hm, hb, e⟩
    refine ⟨fun a b hab k hk => ?_, fun a ha => ?_, fun b hb' k hk => ?_⟩
    · exact Nat.le_trans (hb a).1 (Nat.le_trans (hm a b hab) ((hb b).2 k hk))
    · exact e ▸ Nat.le_trans (hb a).1 (hm a z₀ ha)
    · exact e ▸ Nat.le_trans (hm z₀ b hb') ((hb b).2 k hk)
  · intro ⟨hfeas, hlo, hup⟩
    have hLu : ∀ z k, u z = some k → L l z ≤ k := fun z k hk => by
      obtain ⟨a, ha, e⟩ := L_attained l z
      rw [e]; exact hfeas a z ha k hk
    have hLw : L l z₀ ≤ w₀ := by
      obtain ⟨a, ha, e⟩ := L_attained l z₀
      rw [e]; exact hlo a ha
    refine ⟨canon l z₀ w₀, ?_, ?_, ?_⟩
    · intro a b hab
      unfold canon
      by_cases ha : a < z₀ <;> by_cases hb : b < z₀ <;> simp only [ha, hb, ↓reduceIte]
      · exact L_mono l a b hab
      · exact Nat.le_trans (L_mono l a b hab) (Nat.le_max_left _ _)
      · omega
      · exact Nat.max_le.2 ⟨Nat.le_trans (L_mono l a b hab) (Nat.le_max_left _ _), Nat.le_max_right _ _⟩
    · intro z
      unfold canon
      by_cases hz : z < z₀ <;> simp only [hz, ↓reduceIte]
      · exact ⟨L_ge l z, hLu z⟩
      · exact ⟨Nat.le_trans (L_ge l z) (Nat.le_max_left _ _),
          fun k hk => Nat.max_le.2 ⟨hLu z k hk, hup z (Nat.le_of_not_lt hz) k hk⟩⟩
    · unfold canon
      simp only [Nat.lt_irrefl, ↓reduceIte]
      exact Nat.max_eq_right hLw

/-- **Elimination under monotonicity.** For a feasible convex reference, entailment of a formal
claim `∀ y, B y → θ y (f (t y))` over all monotone `f` is a symbol-free obligation. -/
theorem mono_elim (l : Nat → Nat) (u : Nat → Option Nat) {Y : Sort v} (B : Y → Prop) (t : Y → Nat)
    (θ : Y → Nat → Prop) (hfeas : ∀ a b, a ≤ b → LeOpt (l a) (u b)) :
    (∀ f, Mono f → Box l u f → ∀ y, B y → θ y (f (t y))) ↔
      ∀ y w, B y → (∀ a, a ≤ t y → l a ≤ w) → (∀ b, t y ≤ b → LeOpt w (u b)) → θ y w := by
  constructor
  · intro h y w hB hlo hup
    obtain ⟨f, hm, hb, e⟩ := (mono_extension l u (t y) w).2 ⟨hfeas, hlo, hup⟩
    exact e ▸ h f hm hb y hB
  · intro h f hm hb y hB
    have := (mono_extension l u (t y) (f (t y))).1 ⟨f, hm, hb, rfl⟩
    exact h y _ hB this.2.1 this.2.2

/-- An infeasible reference is vacuous over monotone functions: it entails everything. -/
theorem mono_vacuous (l : Nat → Nat) (u : Nat → Option Nat) {a b k : Nat} (hab : a ≤ b)
    (hk : u b = some k) (hlt : k < l a) : ∀ f, Mono f → ¬ Box l u f :=
  fun _ hm hb => absurd (Nat.le_trans (hb a).1 (Nat.le_trans (hm a b hab) ((hb b).2 k hk)))
    (Nat.not_le.2 hlt)

/-- **Convexity is needed.** Value sets `{1}, {0, 2}, {1}` at arguments `0, 1, 2` are pairwise
compatible with monotonicity, yet no monotone function selects from all three. -/
theorem nonconvex_two_point_fails :
    let C : Nat → Nat → Prop := fun z w => (z = 0 → w = 1) ∧ (z = 1 → w = 0 ∨ w = 2) ∧ (z = 2 → w = 1)
    (∀ a b, a ≤ b → b ≤ 2 → ∃ wa wb, C a wa ∧ C b wb ∧ wa ≤ wb) ∧
      ¬ ∃ f, Mono f ∧ ∀ z, C z (f z) := by
  refine ⟨?_, ?_⟩
  · intro a b hab hb
    have ha : a = 0 ∨ a = 1 ∨ a = 2 := by omega
    have hb' : b = 0 ∨ b = 1 ∨ b = 2 := by omega
    rcases ha with rfl | rfl | rfl <;> rcases hb' with rfl | rfl | rfl <;>
      first
        | omega
        | exact ⟨1, 1, by omega, by omega, by omega⟩
        | exact ⟨1, 2, by omega, by omega, by omega⟩
        | exact ⟨0, 1, by omega, by omega, by omega⟩
        | exact ⟨0, 0, by omega, by omega, by omega⟩
        | exact ⟨0, 2, by omega, by omega, by omega⟩
  · intro ⟨f, hm, hc⟩
    have h0 := (hc 0).1 rfl
    have h1 := (hc 1).2.1 rfl
    have h2 := (hc 2).2.2 rfl
    have m01 := hm 0 1 (by omega)
    have m12 := hm 1 2 (by omega)
    omega

/-- The SOTA-14 test T8, now decided by the criterion: over monotone functions the formal claim
`1 ≤ f 1` gives the reference `∀ n, 1 ≤ f (n + 1)`. -/
example : ∀ f, Mono f → Box (fun z => if z = 1 then 1 else 0) (fun _ => none) f →
    ∀ n : Nat, True → 1 ≤ f (n + 1) :=
  (mono_elim _ _ (fun _ : Nat => True) (fun n => n + 1) (fun _ w => 1 ≤ w)
    (fun _ _ _ _ hk => by cases hk)).2
    (fun y w _ hlo _ => by have := hlo 1 (by omega); simpa using this)

end ProofScope.MonoElim

#print axioms ProofScope.MonoElim.mono_extension
#print axioms ProofScope.MonoElim.mono_elim
#print axioms ProofScope.MonoElim.mono_vacuous
#print axioms ProofScope.MonoElim.nonconvex_two_point_fails
