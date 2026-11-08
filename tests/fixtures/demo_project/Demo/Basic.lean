/-! Honest results: should audit as standard axioms only. -/
namespace Demo

theorem add_comm' (a b : Nat) : a + b = b + a := Nat.add_comm a b

theorem sum_formula (n : Nat) : 2 * (List.range (n + 1)).sum = n * (n + 1) := by
  induction n with
  | zero => rfl
  | succ k ih =>
    rw [List.range_succ, List.sum_append, List.sum_singleton, Nat.mul_add, ih]
    simp only [Nat.mul_add, Nat.add_mul, Nat.mul_one, Nat.one_mul]
    omega

end Demo
