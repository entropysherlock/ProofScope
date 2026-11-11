import ProofScope.Adversarial
/-!
# Two pairs on which ProofScope v1.2 ClaimDelta returns INCONCLUSIVE, decided (SOTA-14)

Statements are in ClaimDelta's own obligation shapes (`fwd`, `bwd`, `sepW`), with the shared symbol
abstracted as a binary operation `g : Nat → Nat → Nat`, exactly as `Abstract.lean` abstracts
`Nat.gcd` and `HPow.hPow`. Core Lean only.
-/
namespace ProofScope.ScopeElim.Cases
open ProofScope.ScopeElim ProofScope.ScopeElim.Adversarial

/-! ### `cd_s14_twice`: reference `gcd n 6 = 1 → gcd (n+1) 6 = 1`, formal `… → gcd (n+2) 6 = 1`. -/
def TwiceRef (g : Nat → Nat → Nat) : Prop := ∀ n, g n 6 = 1 → g (n + 1) 6 = 1
def TwiceLean (g : Nat → Nat → Nat) : Prop := ∀ n, g n 6 = 1 → g (n + 2) 6 = 1

/-- `fwd`, obtained from Theorem A (`t1_entails`) at `σ z := g z 6 = 1`. -/
theorem twice_fwd : ∀ g, TwiceRef g → TwiceLean g :=
  fun g h n hn => t1_entails (fun z => g z 6 = 1) (fun x _ hp => h x (hp ())) n trivial (fun _ => hn)

/-- `sepW`: the canonical model (closure of `{0}` under `+2`) as an operation. -/
theorem twice_sepW : ∃ g, TwiceLean g ∧ ¬ TwiceRef g :=
  ⟨fun a _ => if a % 2 = 0 then 1 else 0,
   fun n hn => by
     have h0 : n % 2 = 0 := Classical.byContradiction fun h => by simp [h] at hn
     have : (n + 2) % 2 = 0 := by omega
     simp [this],
   fun h => absurd (h 0 (by decide)) (by decide)⟩

/-! ### `cd_s14_shift`: reference `1 ≤ n → n < 2 ^ n`, formal `n + 1 < 2 ^ (n + 1)`. -/
def ShiftRef (g : Nat → Nat → Nat) : Prop := ∀ n, 1 ≤ n → n < g 2 n
def ShiftLean (g : Nat → Nat → Nat) : Prop := ∀ n, True → n + 1 < g 2 (n + 1)

/-- `fwd`, from the sufficiency half of Theorem B at `f := g 2`. -/
theorem shift_fwd : ∀ g, ShiftRef g → ShiftLean g :=
  fun g h => fun_schematic_sound (fun n : Nat => 1 ≤ n) id (fun n w => n < w)
    (fun _ : Nat => True) (fun n => n + 1) (fun n w => n + 1 < w)
    (Or.inr fun y _ _ hadm => hadm (y + 1) (by omega) rfl) (g 2) h

/-- `bwd`, likewise. -/
theorem shift_bwd : ∀ g, ShiftLean g → ShiftRef g :=
  fun g h => fun_schematic_sound (fun _ : Nat => True) (fun n => n + 1) (fun n w => n + 1 < w)
    (fun n : Nat => 1 ≤ n) id (fun n w => n < w)
    (Or.inr fun y w hy hadm => by
      have := hadm (y - 1) trivial (by show y - 1 + 1 = y; omega)
      show y < w; omega) (g 2) h

end ProofScope.ScopeElim.Cases

#print axioms ProofScope.ScopeElim.Cases.twice_fwd
#print axioms ProofScope.ScopeElim.Cases.twice_sepW
#print axioms ProofScope.ScopeElim.Cases.shift_fwd
#print axioms ProofScope.ScopeElim.Cases.shift_bwd