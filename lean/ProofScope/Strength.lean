/-!
Schematic strength of Nat comparisons over *arbitrary operand values*.
These theorems do not establish strictness for two specific true theorems.
-/
namespace ProofScope.Strength
theorem lt_implies_le (a b : Nat) (h : a < b) : a ≤ b := Nat.le_of_lt h
theorem le_not_implies_lt : ¬ (∀ a b : Nat, a ≤ b → a < b) := by
  intro h
  exact (Nat.lt_irrefl 0) (h 0 0 (Nat.le_refl 0))
theorem gt_implies_ge (a b : Nat) (h : a > b) : a ≥ b := Nat.le_of_lt h
theorem ge_not_implies_gt : ¬ (∀ a b : Nat, a ≥ b → a > b) := by
  intro h
  exact (Nat.lt_irrefl 0) (h 0 0 (Nat.le_refl 0))
end ProofScope.Strength
#print axioms ProofScope.Strength.lt_implies_le
#print axioms ProofScope.Strength.le_not_implies_lt
#print axioms ProofScope.Strength.gt_implies_ge
#print axioms ProofScope.Strength.ge_not_implies_gt
