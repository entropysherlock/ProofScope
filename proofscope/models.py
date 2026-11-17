"""Countermodel-family registry and Mathlib proof portfolio (v1.2).

A *family* is a concrete Mathlib carrier with sample elements. The engine never assumes a carrier has
a structure: instance binders are filled with `inferInstance`, so a carrier lacking the required class
simply fails to elaborate inside `first` and the next family is tried. Which carrier, instance and
elements a certificate uses is read back from the kernel-checked proof term (`#proofscope_witness11`).

Families (all with decidable equality, so element-wise refutations reduce by `decide`):
  nonabelian groups   DihedralGroup 3, Equiv.Perm (Fin 3)
  abelian groups      Multiplicative (ZMod 4)
  non-total orders    Finset (Fin 2) (subset order), Bool × Bool (product order)
  rings               ZMod 4 (zero divisors), ZMod 3 (field)
  points              ℝ, ℤ, ℕ, sets of ℕ and ℝ, functions ℕ → ℕ, ℝ → ℝ, Empty → ℕ
"""

MATHLIB_CARRIERS = {
    "DihedralGroup 3": {"vals": ["(DihedralGroup.r 1 : DihedralGroup 3)", "(DihedralGroup.sr 0 : DihedralGroup 3)",
                                 "(1 : DihedralGroup 3)"],
                        "op2": ["fun a b => a * b"], "op1": ["fun a => a⁻¹"], "rel": ["fun a b => a = b"]},
    "Multiplicative (ZMod 4)": {"vals": ["(Multiplicative.ofAdd 1 : Multiplicative (ZMod 4))",
                                         "(Multiplicative.ofAdd 2 : Multiplicative (ZMod 4))"],
                                "op2": ["fun a b => a * b"], "op1": ["fun a => a⁻¹"], "rel": ["fun a b => a = b"]},
    "Finset (Fin 2)": {"vals": ["(∅ : Finset (Fin 2))", "({0} : Finset (Fin 2))", "({1} : Finset (Fin 2))",
                                "(Finset.univ : Finset (Fin 2))"],
                       "op2": ["fun a b => a ∪ b"], "op1": ["fun a => a"], "rel": ["fun a b => a ⊆ b"]},
    "ZMod 4": {"vals": ["(2 : ZMod 4)", "(0 : ZMod 4)", "(1 : ZMod 4)", "(3 : ZMod 4)"],
               "op2": ["fun a b => a * b"], "op1": ["fun a => a"], "rel": ["fun a b => a = b"]},
    "ZMod 3": {"vals": ["(0 : ZMod 3)", "(1 : ZMod 3)", "(2 : ZMod 3)"],
               "op2": ["fun a b => a * b"], "op1": ["fun a => a"], "rel": ["fun a b => a = b"]},
}

MATHLIB_POINTS = {
    "Set ℝ": ["({0} : Set ℝ)", "(∅ : Set ℝ)", "(Set.univ : Set ℝ)", "(Set.Icc 0 1 : Set ℝ)", "(Set.Ioo 0 1 : Set ℝ)"],
    "ℕ → ℕ": ["fun _ => 0", "fun n => n", "fun n => n + 1", "fun n => n / 2"],
    "ℝ → ℝ": ["fun _ => (-1 : ℝ)", "fun x => x", "fun _ => (0 : ℝ)", "fun x => x ^ 2"],
    "Empty → ℕ": ["Empty.elim"],
}

# bounded proof portfolio for sufficiency / redundancy / unneeded assumptions (every alternative is
# wrapped `(...; done)` by the caller and checked by the certify gate)
MATHLIB_PROOF_PORTFOLIO = [
    "(intros; positivity)", "(intros; nlinarith [sq_nonneg _])", "(intros; nlinarith)", "(intros; linarith)",
    "(intros; norm_num)", "(intros; simp_all)", "(intros; omega)", "(intros; fun_prop)", "(intros; continuity)",
    "(intros; exact Eq.symm ‹_›)", "(intros; exact mul_comm _ _)", "(intros; exact le_total _ _)",
    "(intros; exact inf_sup_left _ _ _)", "(intros; exact ⟨1⟩)", "(intros; exact isOpen_univ)",
    "(intros; exact Set.subset_univ _)", "(intros; exact Set.Subset.trans ‹_› ‹_›)", "(intros; exact Nat.dvd_trans ‹_› ‹_›)",
    "(intros; exact Nat.Prime.two_le ‹_›)", "(intros; exact Function.Injective.comp ‹_› ‹_›)",
    "(intros; exact Continuous.comp ‹_› ‹_›)", "(intros; exact Set.image_subset _ ‹_›)", "(intros; aesop)",
    "(intros; group)", "(intros; ring_nf)", "(intros; exact le_trans ‹_› ‹_›)", "(intros; exact not_lt.mp ‹_›)",
    "(intros; exact pow_pos ‹_› _)", "(intros; nlinarith [sq_nonneg (‹ℝ› - 1), sq_nonneg (‹ℝ› + 1), sq_nonneg ‹ℝ›])",
    "(intros; exact le_antisymm ‹_› ‹_›)", "(intros; exact lt_asymm ‹_›)",
]


def MATHLIB_REFUTE(vals: list[str]) -> list[str]:
    """Element-wise refutations of a universal claim and Mathlib-specific negations."""
    out = ["(intro h; obtain ⟨x, hx⟩ := h 1; simp at hx)", "(intro h; obtain ⟨x, _⟩ := h 0; cases x)",
           "(simp [Set.Nonempty])", "(exact not_isOpen_singleton 0)", "(exact isClosed_singleton)",
           "(exact isCompact_empty)", "(exact continuous_const)", "(fun_prop)", "(exact Nat.prime_two)", "norm_num", "decide"]
    for a in vals:
        out += [f"(intro h; have := h {a}; norm_num at this)", f"(intro h; have := h {a}; simp at this)"]
        for b in vals:
            out += [f"(intro h; rcases h {a} {b} with h | h <;> revert h <;> decide)",
                    f"(intro h; rcases h {a} {b} with h | h <;> simp [Finset.subset_iff] at h)",
                    f"(intro h; have := h {a} {b}; revert this; decide)", f"(intro h; have := h {a} {b}; simp at this)",
                    f"(intro h; have := h {a} {b}; norm_num at this)"]
    return out
