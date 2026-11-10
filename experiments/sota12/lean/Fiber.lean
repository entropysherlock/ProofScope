/-
  WESTFALL SOTA-12.  Fiber lemma for coupled remainders, Lean 4 core only (no Mathlib).
  x is restricted to a residue class r mod B; the lemma gives the exact range of (c*x) % m on that class.
-/

/-- Bézout for naturals (Lean core does not ship it). -/
theorem bezout_nat (m n : Nat) : ∃ u v : Int, (m : Int) * u + (n : Int) * v = ((Nat.gcd m n : Nat) : Int) := by
  induction m, n using Nat.gcd.induction with
  | H0 n => exact ⟨0, 1, by simp⟩
  | H1 m n hm ih =>
    obtain ⟨u, v, h⟩ := ih
    refine ⟨v - ((n / m : Nat) : Int) * u, u, ?_⟩
    have e : (n : Int) = (m : Int) * ((n / m : Nat) : Int) + ((n % m : Nat) : Int) := by
      exact_mod_cast (Nat.div_add_mod n m).symm
    rw [Nat.gcd_rec]
    rw [← h]
    grind

/-- Bézout for non-negative integers, with `Int.gcd`. -/
theorem bezout_int (a b : Int) (ha : 0 ≤ a) (hb : 0 ≤ b) : ∃ u v : Int, a * u + b * v = (Int.gcd a b : Int) := by
  obtain ⟨u, v, h⟩ := bezout_nat a.natAbs b.natAbs
  refine ⟨u, v, ?_⟩
  have e1 : (a.natAbs : Int) = a := Int.natAbs_of_nonneg ha
  have e2 : (b.natAbs : Int) = b := Int.natAbs_of_nonneg hb
  rw [e1, e2] at h
  exact h

theorem emod_fiber (B c d x : Int) (hdc : d ∣ c * B) : (c * x) % d = (c * (x % B)) % d := by
  obtain ⟨k, hk⟩ := hdc
  have hx : B * (x / B) + x % B = x := Int.mul_ediv_add_emod x B
  have e : c * x = c * (x % B) + d * (k * (x / B)) := by grind
  rw [e, Int.add_mul_emod_self_left]

theorem le_top_residue (m d s : Int) (hd : 0 < d) (hdm : d ∣ m) (hs : s < m) : s ≤ m - d + s % d := by
  obtain ⟨k, hk⟩ := hdm
  have es : d * (s / d) + s % d = s := Int.mul_ediv_add_emod s d
  have hq : s / d < k := by
    apply Int.ediv_lt_of_lt_mul hd
    rw [Int.mul_comm, ← hk]; exact hs
  have hmul : d * (s / d) ≤ d * (k - 1) := Int.mul_le_mul_of_nonneg_left (by omega) (Int.le_of_lt hd)
  rw [Int.mul_sub, Int.mul_one] at hmul
  omega

/-- FIBER LEMMA, upper bound. -/
theorem fiber_upper (B c m d x : Int) (hm : 0 < m) (hd : 0 < d) (hdm : d ∣ m) (hdc : d ∣ c * B) :
    (c * x) % m ≤ m - d + (c * (x % B)) % d := by
  have h1 : ((c * x) % m) % d = (c * x) % d := Int.emod_emod_of_dvd (c * x) hdm
  have h2 := emod_fiber B c d x hdc
  have h3 := le_top_residue m d ((c * x) % m) hd hdm (Int.emod_lt_of_pos (c * x) hm)
  omega

/-- FIBER LEMMA, lower bound. -/
theorem fiber_lower (B c m d x : Int) (hm : 0 < m) (hd : 0 < d) (hdm : d ∣ m) (hdc : d ∣ c * B) :
    (c * (x % B)) % d ≤ (c * x) % m := by
  have h1 : ((c * x) % m) % d = (c * x) % d := Int.emod_emod_of_dvd (c * x) hdm
  have h2 := emod_fiber B c d x hdc
  have h0 : 0 ≤ (c * x) % m := Int.emod_nonneg _ (Int.ne_of_gt hm)
  have es : d * (((c * x) % m) / d) + ((c * x) % m) % d = (c * x) % m := Int.mul_ediv_add_emod _ d
  have hq : 0 ≤ ((c * x) % m) / d := Int.ediv_nonneg h0 (Int.le_of_lt hd)
  have : 0 ≤ d * (((c * x) % m) / d) := Int.mul_nonneg (Int.le_of_lt hd) hq
  omega

/-- FIBER LEMMA, the upper bound is attained on every residue class r mod B. -/
theorem fiber_attain_max (B c m d u v r : Int) (hm : 0 < m) (hd : 0 < d) (hdm : d ∣ m)
    (hr : 0 ≤ r) (hrB : r < B) (hbez : c * B * u + m * v = d) :
    ∃ x : Int, x % B = r ∧ (c * x) % m = m - d + (c * r) % d := by
  have hdle : d ≤ m := Int.le_of_dvd hm hdm
  have h0 : 0 ≤ (c * r) % d := Int.emod_nonneg _ (Int.ne_of_gt hd)
  have h1 : (c * r) % d < d := Int.emod_lt_of_pos _ hd
  have hq : d * ((c * r) / d) + (c * r) % d = c * r := Int.mul_ediv_add_emod (c * r) d
  refine ⟨r + (-(1 + (c * r) / d) * u) * B, ?_, ?_⟩
  · rw [Int.add_mul_emod_self_right]; exact Int.emod_eq_of_lt hr hrB
  · have e : c * (r + (-(1 + (c * r) / d) * u) * B)
        = (m - d + (c * r) % d) + m * (v * (1 + (c * r) / d) - 1) := by grind
    rw [e, Int.add_mul_emod_self_left]
    exact Int.emod_eq_of_lt (by omega) (by omega)

/-- FIBER LEMMA, the lower bound is attained on every residue class r mod B. -/
theorem fiber_attain_min (B c m d u v r : Int) (hm : 0 < m) (hd : 0 < d) (hdm : d ∣ m)
    (hr : 0 ≤ r) (hrB : r < B) (hbez : c * B * u + m * v = d) :
    ∃ x : Int, x % B = r ∧ (c * x) % m = (c * r) % d := by
  have hdle : d ≤ m := Int.le_of_dvd hm hdm
  have h0 : 0 ≤ (c * r) % d := Int.emod_nonneg _ (Int.ne_of_gt hd)
  have h1 : (c * r) % d < d := Int.emod_lt_of_pos _ hd
  have hq : d * ((c * r) / d) + (c * r) % d = c * r := Int.mul_ediv_add_emod (c * r) d
  refine ⟨r + (-((c * r) / d) * u) * B, ?_, ?_⟩
  · rw [Int.add_mul_emod_self_right]; exact Int.emod_eq_of_lt hr hrB
  · have e : c * (r + (-((c * r) / d) * u) * B) = (c * r) % d + m * (v * ((c * r) / d)) := by grind
    rw [e, Int.add_mul_emod_self_left]
    exact Int.emod_eq_of_lt h0 (by omega)

/-! ## The Westfall reduction for  a*(x % b) + b*((b*x) % a),  d = gcd(a, b*b) -/

def L (a b x : Int) : Int := a * (x % b) + b * ((b * x) % a)
def R (a b d r : Int) : Int := b * (a - d) + (a * r + b * ((b * r) % d))

/-- Every value of the left side is bounded by the reduced expression at r = x % b. -/
theorem westfall_upper (a b d x : Int) (ha : 0 < a) (hb : 0 < b) (hd : 0 < d) (hda : d ∣ a) (hdb : d ∣ b * b) :
    L a b x ≤ R a b d (x % b) := by
  have h := fiber_upper b b a d x ha hd hda hdb
  have h' := Int.mul_le_mul_of_nonneg_left h (Int.le_of_lt hb)
  unfold L R
  rw [Int.mul_add] at h'
  omega

/-- Every value of the reduced expression is attained. -/
theorem westfall_attain (a b d u v r : Int) (ha : 0 < a) (hd : 0 < d) (hda : d ∣ a)
    (hr : 0 ≤ r) (hrb : r < b) (hbez : b * b * u + a * v = d) : ∃ x : Int, L a b x = R a b d r := by
  obtain ⟨x, hx1, hx2⟩ := fiber_attain_max b b a d u v r ha hd hda hr hrb hbez
  refine ⟨x, ?_⟩
  unfold L R
  rw [hx1, hx2, Int.mul_add]
  omega

/-- THE REDUCTION, unconditional, with d = gcd(a, b*b):
    max over x of L equals max over 0 ≤ r < b of R, stated as mutual domination. -/
theorem westfall_reduction (a b : Int) (ha : 0 < a) (hb : 0 < b) :
    (∀ x : Int, ∃ r : Int, 0 ≤ r ∧ r < b ∧ L a b x ≤ R a b (Int.gcd a (b * b)) r) ∧
    (∀ r : Int, 0 ≤ r → r < b → ∃ x : Int, L a b x = R a b (Int.gcd a (b * b)) r) := by
  have hbb : 0 < b * b := Int.mul_pos hb hb
  have hdpos : 0 < (Int.gcd a (b * b) : Int) := by
    have : 0 < Int.gcd a (b * b) := Int.gcd_pos_of_ne_zero_left _ (Int.ne_of_gt ha)
    exact_mod_cast this
  have hda : (Int.gcd a (b * b) : Int) ∣ a := Int.gcd_dvd_left a (b * b)
  have hdb : (Int.gcd a (b * b) : Int) ∣ b * b := Int.gcd_dvd_right a (b * b)
  constructor
  · intro x
    exact ⟨x % b, Int.emod_nonneg x (Int.ne_of_gt hb), Int.emod_lt_of_pos x hb,
      westfall_upper a b _ x ha hb hdpos hda hdb⟩
  · intro r hr hrb
    obtain ⟨u, v, h⟩ := bezout_int a (b * b) (Int.le_of_lt ha) (Int.le_of_lt hbb)
    exact westfall_attain a b _ v u r ha hdpos hda hr hrb (by omega)

#print axioms bezout_int
#print axioms fiber_upper
#print axioms fiber_lower
#print axioms fiber_attain_max
#print axioms fiber_attain_min
#print axioms westfall_reduction