import Mathlib
/-!
# d11 against Mathlib's `Group` (SOTA-6). Not compiled in the development sandbox (no Mathlib there);
compiled, axiom-audited and replayed by the `mathlib-d11` job of .github/workflows/sota6-research.yml.
If this file fails in CI, that failure is the result.
-/

/-- The dev-suite reference `ref_d11` is Mathlib's `mul_inv_rev`. -/
theorem d11_ref {G : Type*} [Group G] (a b : G) : (a * b)⁻¹ = b⁻¹ * a⁻¹ := mul_inv_rev a b

/-- The exact law responsible: over the group axioms the candidate is equivalent to commutativity. -/
theorem d11_cand_iff_comm {G : Type*} [Group G] :
    (∀ a b : G, (a * b)⁻¹ = a⁻¹ * b⁻¹) ↔ ∀ a b : G, a * b = b * a := by
  constructor
  · intro h a b
    have e := h b a
    rw [← mul_inv_rev] at e
    exact (inv_injective e).symm
  · intro h a b
    rw [mul_inv_rev, h]

/-- A separating group: the symmetric group on three letters. -/
theorem d11_S3_separates : ¬ ∀ a b : Equiv.Perm (Fin 3), (a * b)⁻¹ = a⁻¹ * b⁻¹ := by
  intro h
  have e := h (Equiv.swap 0 1) (Equiv.swap 1 2)
  revert e
  decide

/-- Hence the dev pair d11 is a certified logical difference over `Type` with `[Group G]`. -/
theorem d11_differ :
    ¬ ((∀ (G : Type) [Group G] (a b : G), (a * b)⁻¹ = b⁻¹ * a⁻¹) ↔
       (∀ (G : Type) [Group G] (a b : G), (a * b)⁻¹ = a⁻¹ * b⁻¹)) := by
  intro h
  exact d11_S3_separates (h.mp (fun G _ a b => mul_inv_rev a b) (Equiv.Perm (Fin 3)))

#print axioms d11_cand_iff_comm
#print axioms d11_S3_separates
#print axioms d11_differ
