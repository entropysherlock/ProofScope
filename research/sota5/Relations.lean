set_option autoImplicit false

/-!
# SOTA-5: statement relations, the d03 forensic certificates, and law-relative comparison

Core Lean 4.34.1 only (no Mathlib). Every declaration is checked by the kernel and by `leanchecker --fresh`
in CI (`.github/workflows/sota5-research.yml`); `#print axioms` output is part of the evidence.

Sections
1. d03: the intended statements, the statement the SOTA-3/SOTA-4 engines actually received, and why the
   certified "equivalence" was about the wrong statement.
2. Relations between statements (closed equivalence, open equivalence over an aligned context, strength,
   incomparability) and the exact gaps between them.
3. Law-relative comparison: an abstract interpretation theorem for inclusion-minimal sufficient law sets.
4. A certified law-relative explanation: inside group theory, the d11 candidate `(a*b)⁻¹ = a⁻¹*b⁻¹` is
   *equivalent to commutativity*; the symmetric group S₃ (as a verified table) separates it from the
   reference `(a*b)⁻¹ = b⁻¹*a⁻¹`.
-/

namespace SOTA5

/-! ## 1. d03 -/

/-- The intended reference: `((n - 1 : ℕ) : ℤ) = (n : ℤ) - 1` for every natural `n`. -/
def d03_ref : Prop := ∀ n : Nat, ((n - 1 : Nat) : Int) = (n : Int) - 1
/-- The intended candidate: the same equation under `1 ≤ n`. -/
def d03_cand : Prop := ∀ n : Nat, 1 ≤ n → ((n - 1 : Nat) : Int) = (n : Int) - 1

theorem d03_ref_false : ¬ d03_ref := fun h => by
  have h0 := h 0
  simp at h0

theorem d03_cand_true : d03_cand := fun n hn => by
  simp only [Int.ofNat_sub hn, Int.natCast_one]

/-- The provisional label is right: the intended pair is a certified logical difference. -/
theorem d03_intended_differ : ¬ (d03_ref ↔ d03_cand) := fun h => d03_ref_false (h.mpr d03_cand_true)

/-- What `pp` printed (without `pp.coercions.types`) was `∀ (n : ℕ), ↑(n - 1) = ↑n - 1`. Elaborated on
its own, with no target type for `↑`, it is the following statement over ℕ (checked with `pp.all`). -/
def d03_printed_ref : Prop := ∀ n : Nat, n - 1 = n - 1
def d03_printed_cand : Prop := ∀ n : Nat, 1 ≤ n → n - 1 = n - 1

theorem d03_printed_ref_true : d03_printed_ref := fun _ => rfl
theorem d03_printed_cand_true : d03_printed_cand := fun _ _ => rfl

/-- The relation the engines certified (`equiv_both_true`) holds, but between the printed statements. -/
theorem d03_printed_equiv : d03_printed_ref ↔ d03_printed_cand :=
  ⟨fun _ => d03_printed_cand_true, fun _ => d03_printed_ref_true⟩

/-- The printed reference is not the intended reference: the translation changed a false statement into a
true one. Any kernel-accepted proof of the "reference" is therefore a proof about a different statement. -/
theorem d03_printing_changed_meaning : ¬ (d03_printed_ref ↔ d03_ref) :=
  fun h => d03_ref_false (h.mp d03_printed_ref_true)

/-- With `pp.coercions.types true` the printer emits `(↑(n - 1) : Int) = (↑n : Int) - 1`, which
elaborates back to the intended statement (the adapter check `with_reducible rfl` passes, see CI). -/
theorem d03_annotated_is_intended :
    (∀ n : Nat, (↑(n - 1) : Int) = (↑n : Int) - 1) ↔ d03_ref := Iff.rfl

/-! ## 2. Relations between statements -/

section Relations
variable {α : Type} (P Q : α → Prop)

/-- Open equivalence over an aligned context `x : α`. -/
def OpenEquiv : Prop := ∀ x, P x ↔ Q x
/-- Closed equivalence of the universal closures. -/
def ClosedEquiv : Prop := (∀ x, P x) ↔ (∀ x, Q x)
/-- Strict strength: `P` implies `Q` pointwise and not conversely (a certified separating point). -/
def StrictlyStronger : Prop := (∀ x, P x → Q x) ∧ ∃ x, Q x ∧ ¬ P x
/-- Incomparability: separating points in both directions. -/
def Incomparable : Prop := (∃ x, P x ∧ ¬ Q x) ∧ (∃ x, Q x ∧ ¬ P x)

theorem open_imp_closed : OpenEquiv P Q → ClosedEquiv P Q :=
  fun h => ⟨fun hp x => (h x).mp (hp x), fun hq x => (h x).mpr (hq x)⟩

/-- For universal closures the only way closed and open equivalence can come apart is that both closures
are false: if both are true, the open formulas agree everywhere. -/
theorem both_closures_true_open : (∀ x, P x) → (∀ x, Q x) → OpenEquiv P Q :=
  fun hp hq x => ⟨fun _ => hq x, fun _ => hp x⟩

theorem incomparable_not_open : Incomparable P Q → ¬ OpenEquiv P Q :=
  fun ⟨⟨x, hp, hq⟩, _⟩ h => hq ((h x).mp hp)

theorem stronger_not_open : StrictlyStronger P Q → ¬ OpenEquiv P Q :=
  fun ⟨_, x, hq, hp⟩ h => hp ((h x).mpr hq)

end Relations

/-- A concrete gap (dev case d22): `∀ n, n*n = n` and `∀ n, n+n = n` are both false, hence closed-
equivalent, but as open formulas `n+n = n` is strictly stronger (it holds only at 0; `n*n = n` also holds
at 1). Closed equivalence hides a strict strength relation. -/
theorem d22_closed_equiv : ClosedEquiv (fun n : Nat => n * n = n) (fun n => n + n = n) :=
  ⟨fun h => absurd (h 2) (by decide), fun h => absurd (h 1) (by decide)⟩

theorem d22_strictly_stronger : StrictlyStronger (fun n : Nat => n + n = n) (fun n => n * n = n) :=
  ⟨fun n h => by
      have h0 : n = 0 := by omega
      subst h0; rfl,
   ⟨1, by decide, by decide⟩⟩

theorem d22_not_open : ¬ OpenEquiv (fun n : Nat => n * n = n) (fun n => n + n = n) :=
  fun h => absurd ((h 1).mp rfl) (by decide)

/-! ## 3. Law-relative comparison: interpretation theorem -/

section LawRelative
/- `M` is a class of structures, `sat m φ` says structure `m` satisfies law `φ`, `P Q : M → Prop` are the two
statements interpreted in a structure. -/
variable {M L : Type} (sat : M → L → Prop) (P Q : M → Prop)

/-- `S` suffices: every structure satisfying all laws in `S` makes `P` and `Q` agree. -/
def Suffices (S : List L) : Prop := ∀ m, (∀ φ ∈ S, sat m φ) → (P m ↔ Q m)

/-- A separating countermodel for `S`: it satisfies every law of `S` and `P`, `Q` disagree in it. -/
def Separates (S : List L) (m : M) : Prop := (∀ φ ∈ S, sat m φ) ∧ ¬ (P m ↔ Q m)

theorem suffices_mono {S T : List L} (hST : ∀ φ ∈ S, φ ∈ T) : Suffices sat P Q S → Suffices sat P Q T :=
  fun h m hm => h m (fun φ hφ => hm φ (hST φ hφ))

theorem not_suffices_of_separates {S : List L} {m : M} : Separates sat P Q S m → ¬ Suffices sat P Q S :=
  fun ⟨hs, hne⟩ h => hne (h m hs)

/-- **Interpretation theorem for minimality certificates.** If `S` suffices and, for every law `φ ∈ S`, a
structure satisfies all *other* laws of `S` while `P` and `Q` disagree in it, then no subset `T` of `S`
that omits some law of `S` suffices: `S` is inclusion-minimal among sufficient sets (minimal, not
necessarily of minimum size, and other minimal sets may exist). -/
theorem minimal_of_witnesses (S : List L)
    (wit : ∀ φ ∈ S, ∃ m, (∀ ψ ∈ S, ψ ≠ φ → sat m ψ) ∧ ¬ (P m ↔ Q m))
    (T : List L) (hT : ∀ ψ ∈ T, ψ ∈ S) (φ : L) (hφS : φ ∈ S) (hφT : φ ∉ T) :
    ¬ Suffices sat P Q T := by
  obtain ⟨m, hm, hne⟩ := wit φ hφS
  intro h
  apply hne
  apply h m
  intro ψ hψ
  apply hm ψ (hT ψ hψ)
  intro e
  exact hφT (e ▸ hψ)

end LawRelative

/-! ## 4. Certified law-relative explanation of d11 -/

/-- A group, written out (core Lean has no `Group` class). -/
structure Grp where
  G : Type
  mul : G → G → G
  one : G
  inv : G → G
  assoc : ∀ a b c, mul (mul a b) c = mul a (mul b c)
  one_mul : ∀ a, mul one a = a
  inv_mul : ∀ a, mul (inv a) a = one

namespace Grp
variable (g : Grp)

theorem mul_inv (a : g.G) : g.mul a (g.inv a) = g.one := by
  have h1 : g.mul (g.inv (g.inv a)) (g.inv a) = g.one := g.inv_mul _
  calc g.mul a (g.inv a) = g.mul g.one (g.mul a (g.inv a)) := (g.one_mul _).symm
    _ = g.mul (g.mul (g.inv (g.inv a)) (g.inv a)) (g.mul a (g.inv a)) := by rw [h1]
    _ = g.mul (g.inv (g.inv a)) (g.mul (g.mul (g.inv a) a) (g.inv a)) := by simp only [g.assoc]
    _ = g.one := by rw [g.inv_mul, g.one_mul, h1]

theorem mul_one (a : g.G) : g.mul a g.one = a := by
  rw [← g.inv_mul a, ← g.assoc, mul_inv, g.one_mul]

theorem inv_unique {a b : g.G} (h : g.mul a b = g.one) : g.inv a = b := by
  calc g.inv a = g.mul (g.inv a) g.one := (mul_one g _).symm
    _ = b := by rw [← h, ← g.assoc, g.inv_mul, g.one_mul]

/-- d11 reference: true in every group. -/
def ref (g : Grp) : Prop := ∀ a b : g.G, g.inv (g.mul a b) = g.mul (g.inv b) (g.inv a)
/-- d11 candidate. -/
def cand (g : Grp) : Prop := ∀ a b : g.G, g.inv (g.mul a b) = g.mul (g.inv a) (g.inv b)
/-- Law: commutativity. -/
def Comm (g : Grp) : Prop := ∀ a b : g.G, g.mul a b = g.mul b a

theorem ref_holds : ref g := fun a b => inv_unique g (by
  rw [g.assoc, ← g.assoc b, mul_inv, g.one_mul, mul_inv])

/-- **The exact law responsible.** Over the group axioms, the candidate is equivalent to commutativity. -/
theorem cand_iff_comm : cand g ↔ Comm g := by
  have ia : ∀ x : g.G, g.inv (g.inv x) = x := fun x => inv_unique g (g.inv_mul x)
  constructor
  · intro h a b
    -- the candidate and the reference at a⁻¹, b⁻¹ give a⁻¹⁻¹ * b⁻¹⁻¹ = b⁻¹⁻¹ * a⁻¹⁻¹
    have e := (h (g.inv a) (g.inv b)).symm.trans (ref_holds g (g.inv a) (g.inv b))
    rw [ia, ia] at e
    exact e
  · intro hc a b
    rw [ref_holds g a b, hc]

/-- Hence, relative to the group axioms, `{Comm}` suffices for reference ⟺ candidate. -/
theorem comm_suffices : Comm g → (ref g ↔ cand g) := fun hc =>
  ⟨fun _ => (cand_iff_comm g).mpr hc, fun _ => ref_holds g⟩

/-- S₃ as a verified multiplication table on `Fin 6` (index 0 = identity). -/
def s3mul (a b : Fin 6) : Fin 6 :=
  (#[#[0,1,2,3,4,5],#[1,0,4,5,2,3],#[2,3,0,1,5,4],#[3,2,5,4,0,1],#[4,5,1,0,3,2],#[5,4,3,2,1,0]] : Array (Array (Fin 6)))[a]![b]!
def s3inv (a : Fin 6) : Fin 6 := (#[0,1,2,4,3,5] : Array (Fin 6))[a]!

def S3 : Grp where
  G := Fin 6
  mul := s3mul
  one := 0
  inv := s3inv
  assoc := by decide
  one_mul := by decide
  inv_mul := by decide

/-- The separating countermodel: in S₃ the reference holds and the candidate fails, so the empty law set
does not suffice, and `{Comm}` is inclusion-minimal (by `minimal_of_witnesses`). -/
theorem S3_separates : ¬ (ref S3 ↔ cand S3) := fun h =>
  absurd ((h.mp (ref_holds S3)) (1 : Fin 6) (2 : Fin 6))
    (by decide : s3inv (s3mul 1 2) ≠ s3mul (s3inv 1) (s3inv 2))

/-- And S₃ is not commutative (consistent with `cand_iff_comm`). -/
theorem S3_not_comm : ¬ Comm S3 := fun h => absurd (h (1 : Fin 6) (2 : Fin 6)) (by decide : s3mul 1 2 ≠ s3mul 2 1)

end Grp
end SOTA5

#print axioms SOTA5.d03_intended_differ
#print axioms SOTA5.d03_printed_equiv
#print axioms SOTA5.d03_printing_changed_meaning
#print axioms SOTA5.d03_annotated_is_intended
#print axioms SOTA5.both_closures_true_open
#print axioms SOTA5.d22_closed_equiv
#print axioms SOTA5.d22_strictly_stronger
#print axioms SOTA5.d22_not_open
#print axioms SOTA5.minimal_of_witnesses
#print axioms SOTA5.Grp.ref_holds
#print axioms SOTA5.Grp.cand_iff_comm
#print axioms SOTA5.Grp.comm_suffices
#print axioms SOTA5.Grp.S3_separates
#print axioms SOTA5.Grp.S3_not_comm
