/-
  Residue-gap law, discovered by the SHARPEN law finder from instance data
  (range of x % a - x % b fitted as [-(b - gcd), a - gcd] and confirmed on held-out moduli),
  then proved here for ALL moduli.  Lean 4 core only (no Mathlib).
-/

/-- Upper bound: for any common divisor g of a and b, x % a - x % b ≤ a - g. -/
theorem residue_gap_le (a b g x : Int) (hg : 0 < g) (ha : 0 < a) (hb : 0 < b)
    (hga : g ∣ a) (hgb : g ∣ b) : x % a - x % b ≤ a - g := by
  have h1 : (x % a) % g = x % g := Int.emod_emod_of_dvd x hga
  have h2 : (x % b) % g = x % g := Int.emod_emod_of_dvd x hgb
  have hs0 : 0 ≤ x % a := Int.emod_nonneg x (Int.ne_of_gt ha)
  have hs1 : x % a < a := Int.emod_lt_of_pos x ha
  have ht0 : 0 ≤ x % b := Int.emod_nonneg x (Int.ne_of_gt hb)
  obtain ⟨k, hk⟩ := hga
  have es : g * ((x % a) / g) + (x % a) % g = x % a := Int.mul_ediv_add_emod (x % a) g
  have et : g * ((x % b) / g) + (x % b) % g = x % b := Int.mul_ediv_add_emod (x % b) g
  have hq : (x % a) / g < k := by
    apply Int.ediv_lt_of_lt_mul hg
    rw [Int.mul_comm]; rw [← hk]; exact hs1
  have hp : 0 ≤ (x % b) / g := Int.ediv_nonneg ht0 (Int.le_of_lt hg)
  have hle : (x % a) / g - (x % b) / g ≤ k - 1 := by omega
  have hmul : g * ((x % a) / g - (x % b) / g) ≤ g * (k - 1) :=
    Int.mul_le_mul_of_nonneg_left hle (Int.le_of_lt hg)
  rw [Int.mul_sub, Int.mul_sub, Int.mul_one] at hmul
  omega

/-- Lower bound, by symmetry. -/
theorem residue_gap_ge (a b g x : Int) (hg : 0 < g) (ha : 0 < a) (hb : 0 < b)
    (hga : g ∣ a) (hgb : g ∣ b) : -(b - g) ≤ x % a - x % b := by
  have := residue_gap_le b a g x hg hb ha hgb hga
  omega

/-- Sharpness: whenever g is an integer combination of a and b (true for g = gcd a b by Bézout),
    the bound a - g is attained. -/
theorem residue_gap_sharp (a b g u v : Int) (hg : 0 < g) (ha : 0 < a)
    (hga : g ∣ a) (hbez : a * u + b * v = g) : ∃ x : Int, x % a - x % b = a - g := by
  refine ⟨-(b * v), ?_⟩
  have hgle : g ≤ a := Int.le_of_dvd ha hga
  have hb0 : (-(b * v)) % b = 0 := Int.emod_eq_zero_of_dvd (Int.dvd_neg.mpr (Int.dvd_mul_right b v))
  have hx : -(b * v) = (a - g) + a * (u - 1) := by
    rw [Int.mul_sub, Int.mul_one]; omega
  have ha' : (-(b * v)) % a = a - g := by
    rw [hx, Int.add_mul_emod_self_left]
    exact Int.emod_eq_of_lt (by omega) (by omega)
  rw [ha', hb0]; omega

#print axioms residue_gap_le
#print axioms residue_gap_ge
#print axioms residue_gap_sharp