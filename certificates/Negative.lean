/-! Negative axiom-policy control. Intentionally uses sorry.
    This must be rejected by ProofScope's certificate policy, even if Lean
    emits an olean. Never distribute as a verified theorem. -/
theorem proofscope_certificate_negative : False := by
  sorry

#print axioms proofscope_certificate_negative
