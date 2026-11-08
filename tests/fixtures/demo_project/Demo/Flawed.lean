import Demo.Basic
/-! Planted problems for the auditor: an unproved theorem and a custom axiom. -/
namespace Demo

theorem unproved_claim (n : Nat) : n * n ≥ n := by
  sorry

axiom convenient : ∀ n : Nat, n < n + 1 → True

theorem uses_axiom : True := convenient 0 (Nat.lt_succ_self 0)

end Demo
