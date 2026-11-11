import ProofScope.ScopeElim
/-!
# MultiOcc: elimination of a function symbol with several occurrences (SOTA-17)

Core Lean 4 only. SOTA-14 Theorem B eliminates a function symbol that occurs once on each side.
This file treats claims in which the symbol occurs at several sites.

Setting. `M : (Z → W) → Prop` is the model class of the reference (`M f` iff the reference holds for
`f`). The formal claim is `∀ y, B y → θ y ((t y).map f)`: it reads `f` at the finite list of sites
`t y`. Sites may coincide and may depend on `y` in any way.

* `two_point_exact` (no hypothesis on `M`): with at most two sites, entailment is exactly a statement
  about the binary projection `E2 M z₁ w₁ z₂ w₂ := ∃ f, M f ∧ f z₁ = w₁ ∧ f z₂ = w₂`.
* `pairwise_insufficient`: with three sites the binary projection is not enough in general.
* `baker_pixley`: if `M` is closed under the pointwise action of a majority operation on `W`, every
  finite set of points that is pairwise extendable inside `M` is jointly extendable inside `M`.
  This is the Baker-Pixley argument (1975) for subalgebras of powers, here for a class of functions
  on an arbitrary (possibly infinite) domain.
* `majority_elim`: consequently, for a majority-closed reference, entailment of a formal claim with
  any number of sites is equivalent to a statement that mentions `M` only through `E2`.
* Instances with a closed form for `E2`:
  - `Step a b` (`f x + a ≤ f (x+1) ≤ f x + b`; two occurrences on the reference side):
    `step_E2`, `step_points`, `step_elim`.
  - `Lower a` (`f x + a ≤ f (x+1)`; `a = 0` is monotone, `a = 1` strictly monotone):
    `lower_E2`, `lower_points`, `lower_elim`.
  - pointwise references of Theorem B (`RefF`): `pointwise_points`, `pointwise_elim`
    (no majority needed; the class is a product).
* `sq_majority_closed`: the reference `Sq` of Theorem C is majority-closed as well. The criterion of
  `majority_elim` is exact for it, but its binary projection is the graph of squaring. Closure under
  a majority operation gives exactness of the pairwise criterion; it does not give definability of
  the projection in linear arithmetic.

Every theorem ends with a `#print axioms` line.
-/
namespace ProofScope.MultiOcc
open ProofScope.ScopeElim

universe u v w

section General
variable {Z : Type u} {W : Type v}

/-- `f` passes through every point of `l`. -/
def Thru (f : Z → W) (l : List (Z × W)) : Prop := ∀ p, p ∈ l → f p.1 = p.2

/-- The binary projection of a class of functions. -/
def E2 (M : (Z → W) → Prop) (z₁ : Z) (w₁ : W) (z₂ : Z) (w₂ : W) : Prop :=
  ∃ f, M f ∧ f z₁ = w₁ ∧ f z₂ = w₂

/-- Every two points of `l` lie on a common member of `M`. -/
def PairExt (M : (Z → W) → Prop) (l : List (Z × W)) : Prop :=
  ∀ p, p ∈ l → ∀ q, q ∈ l → E2 M p.1 p.2 q.1 q.2

/-- A majority operation. -/
structure IsMajority (μ : W → W → W → W) : Prop where
  aab : ∀ a b, μ a a b = a
  aba : ∀ a b, μ a b a = a
  baa : ∀ a b, μ b a a = a

/-- `M` is closed under the pointwise action of `μ`. -/
def Closed (M : (Z → W) → Prop) (μ : W → W → W → W) : Prop :=
  ∀ f g h, M f → M g → M h → M (fun z => μ (f z) (g z) (h z))

theorem thru_zip_map (f : Z → W) : ∀ ts : List Z, Thru f (ts.zip (ts.map f))
  | [] => fun _ h => nomatch h
  | t :: ts => by
    intro p hp
    simp only [List.map_cons, List.zip_cons_cons, List.mem_cons] at hp
    rcases hp with rfl | hp
    · rfl
    · exact thru_zip_map f ts p hp

theorem map_of_thru_zip (f : Z → W) :
    ∀ (ts : List Z) (vs : List W), vs.length = ts.length → Thru f (ts.zip vs) → ts.map f = vs
  | [], [], _, _ => rfl
  | [], _ :: _, h, _ => nomatch h
  | _ :: _, [], h, _ => nomatch h
  | t :: ts, v :: vs, h, ht => by
    have h1 : f t = v := ht (t, v) (by simp)
    have h2 : ts.map f = vs :=
      map_of_thru_zip f ts vs (by simpa using h) (fun p hp => ht p (by simp [hp]))
    simp [h1, h2]

/-- **Baker-Pixley for function classes.** -/
theorem baker_pixley {M : (Z → W) → Prop} {μ : W → W → W → W} (hμ : IsMajority μ)
    (hM : Closed M μ) :
    ∀ (n : Nat) (l : List (Z × W)), l.length = n → (∃ f, M f) → PairExt M l → ∃ f, M f ∧ Thru f l := by
  intro n
  induction n with
  | zero =>
    intro l hl hne _
    obtain ⟨f, hf⟩ := hne
    have : l = [] := List.length_eq_zero_iff.1 hl
    subst this
    exact ⟨f, hf, fun _ h => nomatch h⟩
  | succ n ih =>
    intro l hl hne hp
    match l, hl, hp with
    | [a], _, hp =>
      obtain ⟨f, hf, e, _⟩ := hp a (by simp) a (by simp)
      exact ⟨f, hf, fun p h => by simp at h; subst h; exact e⟩
    | [a, b], _, hp =>
      obtain ⟨f, hf, e1, e2⟩ := hp a (by simp) b (by simp)
      refine ⟨f, hf, fun p h => ?_⟩
      simp at h
      rcases h with rfl | rfl
      · exact e1
      · exact e2
    | a :: b :: c :: r, hl, hp =>
      have len : (b :: c :: r).length = n := by simpa using hl
      have sa : ∀ p, p ∈ b :: c :: r → p ∈ a :: b :: c :: r := fun p h => List.mem_cons_of_mem _ h
      have sb : ∀ p, p ∈ a :: c :: r → p ∈ a :: b :: c :: r := by
        intro p h
        simp only [List.mem_cons] at h ⊢
        rcases h with h | h | h <;> simp [h]
      have sc : ∀ p, p ∈ a :: b :: r → p ∈ a :: b :: c :: r := by
        intro p h
        simp only [List.mem_cons] at h ⊢
        rcases h with h | h | h <;> simp [h]
      obtain ⟨fa, hfa, ta⟩ := ih (b :: c :: r) len hne
        (fun p h q h' => hp p (sa p h) q (sa q h'))
      obtain ⟨fb, hfb, tb⟩ := ih (a :: c :: r) (by simpa using len) hne
        (fun p h q h' => hp p (sb p h) q (sb q h'))
      obtain ⟨fc, hfc, tc⟩ := ih (a :: b :: r) (by simpa using len) hne
        (fun p h q h' => hp p (sc p h) q (sc q h'))
      refine ⟨_, hM fa fb fc hfa hfb hfc, fun p h => ?_⟩
      simp only [List.mem_cons] at h
      show μ (fa p.1) (fb p.1) (fc p.1) = p.2
      rcases h with rfl | rfl | rfl | h
      · rw [tb p (by simp), tc p (by simp)]; exact hμ.baa _ _
      · rw [ta p (by simp), tc p (by simp)]; exact hμ.aba _ _
      · rw [ta p (by simp), tb p (by simp)]; exact hμ.aab _ _
      · rw [ta p (by simp [h]), tb p (by simp [h])]; exact hμ.aab _ _

/-- The formal claim: `f` is read at the sites `t y`. -/
def Form {Y : Sort w} (B : Y → Prop) (t : Y → List Z) (θ : Y → List W → Prop) (f : Z → W) : Prop :=
  ∀ y, B y → θ y ((t y).map f)

/-- Soundness of any criterion built from a necessary condition `C` on point lists. Axiom-free. -/
theorem elim_sound {M : (Z → W) → Prop} {C : List (Z × W) → Prop}
    (nec : ∀ f, M f → ∀ ts : List Z, C (ts.zip (ts.map f)))
    {Y : Sort w} (B : Y → Prop) (t : Y → List Z) (θ : Y → List W → Prop)
    (h : ∀ y, B y → ∀ vs : List W, vs.length = (t y).length → C ((t y).zip vs) → θ y vs) :
    ∀ f, M f → Form B t θ f :=
  fun f hf y hb => h y hb _ (by simp) (nec f hf (t y))

/-- Exactness of a criterion `C` that is necessary and sufficient for joint extension. -/
theorem elim_exact {M : (Z → W) → Prop} {C : List (Z × W) → Prop}
    (nec : ∀ f, M f → ∀ ts : List Z, C (ts.zip (ts.map f)))
    (suf : ∀ l, C l → ∃ f, M f ∧ Thru f l)
    {Y : Sort w} (B : Y → Prop) (t : Y → List Z) (θ : Y → List W → Prop) :
    (∀ f, M f → Form B t θ f) ↔
      ∀ y, B y → ∀ vs : List W, vs.length = (t y).length → C ((t y).zip vs) → θ y vs := by
  constructor
  · intro h y hb vs hlen hc
    obtain ⟨f, hf, ht⟩ := suf _ hc
    have := h f hf y hb
    rwa [map_of_thru_zip f (t y) vs hlen ht] at this
  · exact elim_sound nec B t θ

/-- A separating function from one failing instance. -/
theorem sep_of_points {M : (Z → W) → Prop} {Y : Sort w} (B : Y → Prop) (t : Y → List Z)
    (θ : Y → List W → Prop) (y : Y) (vs : List W) (hb : B y) (hlen : vs.length = (t y).length)
    (hext : ∃ f, M f ∧ Thru f ((t y).zip vs)) (hθ : ¬ θ y vs) :
    ∃ f, M f ∧ ¬ Form B t θ f := by
  obtain ⟨f, hf, ht⟩ := hext
  refine ⟨f, hf, fun h => hθ ?_⟩
  have := h y hb
  rwa [map_of_thru_zip f (t y) vs hlen ht] at this

/-- **Majority elimination.** For a reference whose model class is closed under a majority operation,
entailment of a claim with any finite number of sites is a statement about the binary projection. -/
theorem majority_elim {M : (Z → W) → Prop} {μ : W → W → W → W} (hμ : IsMajority μ)
    (hM : Closed M μ) {Y : Sort w} (B : Y → Prop) (t : Y → List Z) (θ : Y → List W → Prop) :
    (∀ f, M f → Form B t θ f) ↔
      ∀ y, B y → ∀ vs : List W, vs.length = (t y).length →
        ((∃ f, M f) ∧ PairExt M ((t y).zip vs)) → θ y vs :=
  elim_exact (C := fun l => (∃ f, M f) ∧ PairExt M l)
    (fun f hf ts => ⟨⟨f, hf⟩, fun p hp q hq =>
      ⟨f, hf, thru_zip_map f ts p hp, thru_zip_map f ts q hq⟩⟩)
    (fun l hc => baker_pixley hμ hM l.length l rfl hc.1 hc.2) B t θ

/-- With at most two sites no hypothesis on the class is needed. -/
theorem two_point_exact (M : (Z → W) → Prop) {Y : Sort w} (B : Y → Prop) (t₁ t₂ : Y → Z)
    (θ : Y → W → W → Prop) :
    (∀ f, M f → ∀ y, B y → θ y (f (t₁ y)) (f (t₂ y))) ↔
      ∀ y w₁ w₂, B y → E2 M (t₁ y) w₁ (t₂ y) w₂ → θ y w₁ w₂ :=
  ⟨fun h y _ _ hb ⟨f, hf, e1, e2⟩ => e1 ▸ e2 ▸ h f hf y hb,
   fun h f hf y hb => h y _ _ hb ⟨f, hf, rfl, rfl⟩⟩

end General

/-! ## Three sites: the binary projection is not enough without a closure hypothesis -/

/-- The reference `f 0 + f 1 = f 2` (three occurrences). -/
def Sum3 (f : Nat → Nat) : Prop := f 0 + f 1 = f 2

theorem pairwise_insufficient :
    PairExt Sum3 [(0, 0), (1, 0), (2, 1)] ∧ ¬ ∃ f, Sum3 f ∧ Thru f [(0, 0), (1, 0), (2, 1)] := by
  constructor
  · have m1 : Sum3 (fun z => if z = 0 then 0 else if z = 1 then 0 else 0) := by simp [Sum3]
    have m2 : Sum3 (fun z => if z = 0 then 0 else if z = 1 then 1 else 1) := by simp [Sum3]
    have m3 : Sum3 (fun z => if z = 0 then 1 else if z = 1 then 0 else 1) := by simp [Sum3]
    intro p hp q hq
    simp only [List.mem_cons, List.not_mem_nil, or_false] at hp hq
    rcases hp with rfl | rfl | rfl <;> rcases hq with rfl | rfl | rfl
    · exact ⟨_, m1, by simp, by simp⟩
    · exact ⟨_, m1, by simp, by simp⟩
    · exact ⟨_, m2, by simp, by simp⟩
    · exact ⟨_, m1, by simp, by simp⟩
    · exact ⟨_, m1, by simp, by simp⟩
    · exact ⟨_, m3, by simp, by simp⟩
    · exact ⟨_, m2, by simp, by simp⟩
    · exact ⟨_, m3, by simp, by simp⟩
    · exact ⟨_, m2, by simp, by simp⟩
  · intro ⟨f, hf, ht⟩
    have e0 : f 0 = 0 := ht (0, 0) (by simp)
    have e1 : f 1 = 0 := ht (1, 0) (by simp)
    have e2 : f 2 = 1 := ht (2, 1) (by simp)
    unfold Sum3 at hf
    omega

theorem ifT {α : Sort u} {c : Prop} [Decidable c] (h : c) {a b : α} : (if c then a else b) = a := by
  simp [h]

theorem ifF {α : Sort u} {c : Prop} [Decidable c] (h : ¬ c) {a b : α} : (if c then a else b) = b := by
  simp [h]

/-! ## The median on `Nat` -/

/-- The median of three naturals. -/
def med (a b c : Nat) : Nat := max (min a b) (min (max a b) c)

theorem med_majority : IsMajority med :=
  ⟨fun a b => by unfold med; omega, fun a b => by unfold med; omega, fun a b => by unfold med; omega⟩

/-! ## Step references: `f x + a ≤ f (x + 1) ≤ f x + b` -/

/-- Increments between `a` and `b`. The symbol occurs twice. -/
def Step (a b : Nat) (f : Nat → Nat) : Prop := ∀ x, f x + a ≤ f (x + 1) ∧ f (x + 1) ≤ f x + b

theorem step_closed (a b : Nat) : Closed (Step a b) med := by
  intro f g h hf hg hh x
  have := hf x; have := hg x; have := hh x
  show med (f x) (g x) (h x) + a ≤ med (f (x + 1)) (g (x + 1)) (h (x + 1)) ∧
    med (f (x + 1)) (g (x + 1)) (h (x + 1)) ≤ med (f x) (g x) (h x) + b
  unfold med
  omega

theorem step_between {a b : Nat} {f : Nat → Nat} (h : Step a b f) (z : Nat) :
    ∀ d, f z + a * d ≤ f (z + d) ∧ f (z + d) ≤ f z + b * d
  | 0 => by simp
  | d + 1 => by
    have ih := step_between h z d
    have s := h (z + d)
    rw [Nat.mul_succ, Nat.mul_succ, ← Nat.add_assoc z d 1]
    omega

theorem step_base {a b : Nat} {f : Nat → Nat} (h : Step a b f) (z : Nat) : a * z ≤ f z := by
  have := (step_between h 0 z).1
  rw [Nat.zero_add] at this
  omega

/-- Two-point consistency for `Step a b`, for points in either order. -/
def StepCons (a b : Nat) (p q : Nat × Nat) : Prop :=
  a * p.1 ≤ p.2 ∧ (p.1 ≤ q.1 → p.2 + a * (q.1 - p.1) ≤ q.2 ∧ q.2 ≤ p.2 + b * (q.1 - p.1))

instance (a b : Nat) (p q : Nat × Nat) : Decidable (StepCons a b p q) := by
  unfold StepCons; exact inferInstance

theorem step_cons_of {a b : Nat} {f : Nat → Nat} (h : Step a b f) (z₁ z₂ : Nat) :
    StepCons a b (z₁, f z₁) (z₂, f z₂) := by
  refine ⟨step_base h z₁, fun hle => ?_⟩
  have := step_between h z₁ (z₂ - z₁)
  have e : z₁ + (z₂ - z₁) = z₂ := by simp at hle; omega
  rw [e] at this
  exact this

/-- The canonical member of `Step a b` through two points. -/
def stepFun (a b z₁ w₁ z₂ w₂ : Nat) (x : Nat) : Nat :=
  if x ≤ z₁ then w₁ - a * (z₁ - x)
  else if x ≤ z₂ then max (w₁ + a * (x - z₁)) (w₂ - b * (z₂ - x))
  else w₂ + a * (x - z₂)

theorem stepFun_step {a b z₁ w₁ z₂ w₂ : Nat} (hab : a ≤ b) (hz : z₁ ≤ z₂) (h0 : a * z₁ ≤ w₁)
    (h1 : w₁ + a * (z₂ - z₁) ≤ w₂) (h2 : w₂ ≤ w₁ + b * (z₂ - z₁)) :
    Step a b (stepFun a b z₁ w₁ z₂ w₂) := by
  intro x
  unfold stepFun
  by_cases c1 : x + 1 ≤ z₁
  · -- both arguments below z₁
    have e : z₁ - x = (z₁ - (x + 1)) + 1 := by omega
    have m : a * (z₁ - x) = a * (z₁ - (x + 1)) + a := by rw [e, Nat.mul_succ]
    have le : a * (z₁ - x) ≤ a * z₁ := Nat.mul_le_mul_left a (Nat.sub_le _ _)
    rw [ifT (by omega : x ≤ z₁), ifT c1]
    omega
  · by_cases c2 : x ≤ z₁
    · -- x = z₁
      have ex : x = z₁ := by omega
      subst ex
      rw [ifT (Nat.le_refl _), ifF (by omega : ¬ x + 1 ≤ x)]
      have z0 : a * (x - x) = 0 := by simp
      have z1 : a * (x + 1 - x) = a := by
        have : x + 1 - x = 1 := by omega
        rw [this, Nat.mul_one]
      by_cases c3 : x + 1 ≤ z₂
      · have e : z₂ - x = (z₂ - (x + 1)) + 1 := by omega
        have m : b * (z₂ - x) = b * (z₂ - (x + 1)) + b := by rw [e, Nat.mul_succ]
        rw [ifT c3]
        omega
      · have ez : z₂ = x := by omega
        subst ez
        have z2 : a * (z₂ - z₂) = 0 := by simp
        have z3 : b * (z₂ - z₂) = 0 := by simp
        rw [ifF c3]
        omega
    · rw [ifF c2, ifF (by omega : ¬ x + 1 ≤ z₁)]
      by_cases c3 : x + 1 ≤ z₂
      · -- both strictly between
        have e : z₂ - x = (z₂ - (x + 1)) + 1 := by omega
        have m : b * (z₂ - x) = b * (z₂ - (x + 1)) + b := by rw [e, Nat.mul_succ]
        have e' : x + 1 - z₁ = (x - z₁) + 1 := by omega
        have m' : a * (x + 1 - z₁) = a * (x - z₁) + a := by rw [e', Nat.mul_succ]
        rw [ifT (by omega : x ≤ z₂), ifT c3]
        omega
      · by_cases c4 : x ≤ z₂
        · -- x = z₂
          have ex : x = z₂ := by omega
          subst ex
          have z3 : b * (x - x) = 0 := by simp
          have z1 : a * (x + 1 - x) = a := by
            have : x + 1 - x = 1 := by omega
            rw [this, Nat.mul_one]
          rw [ifT (Nat.le_refl _), ifF c3]
          omega
        · have e' : x + 1 - z₂ = (x - z₂) + 1 := by omega
          have m' : a * (x + 1 - z₂) = a * (x - z₂) + a := by rw [e', Nat.mul_succ]
          rw [ifF c4, ifF c3]
          omega

theorem stepFun_left (a b z₁ w₁ z₂ w₂ : Nat) : stepFun a b z₁ w₁ z₂ w₂ z₁ = w₁ := by
  unfold stepFun; simp

theorem stepFun_right {a b z₁ w₁ z₂ w₂ : Nat} (hz : z₁ ≤ z₂)
    (h1 : w₁ + a * (z₂ - z₁) ≤ w₂) (h2 : w₂ ≤ w₁ + b * (z₂ - z₁)) :
    stepFun a b z₁ w₁ z₂ w₂ z₂ = w₂ := by
  unfold stepFun
  by_cases c : z₂ ≤ z₁
  · have e : z₂ = z₁ := by omega
    subst e
    have z0 : a * (z₂ - z₂) = 0 := by simp
    have z3 : b * (z₂ - z₂) = 0 := by simp
    rw [ifT c]
    omega
  · have z3 : b * (z₂ - z₂) = 0 := by simp
    rw [ifF c, ifT (Nat.le_refl _)]
    omega

/-- **Closed form of the binary projection of `Step a b`.** -/
theorem step_E2 {a b : Nat} (hab : a ≤ b) (z₁ w₁ z₂ w₂ : Nat) :
    E2 (Step a b) z₁ w₁ z₂ w₂ ↔ (StepCons a b (z₁, w₁) (z₂, w₂) ∧ StepCons a b (z₂, w₂) (z₁, w₁)) := by
  constructor
  · rintro ⟨f, hf, rfl, rfl⟩
    exact ⟨step_cons_of hf z₁ z₂, step_cons_of hf z₂ z₁⟩
  · rintro ⟨⟨h0, h12⟩, ⟨h0', h21⟩⟩
    rcases Nat.le_total z₁ z₂ with hz | hz
    · obtain ⟨h1, h2⟩ := h12 hz
      exact ⟨_, stepFun_step hab hz h0 h1 h2, stepFun_left .., stepFun_right hz h1 h2⟩
    · obtain ⟨h1, h2⟩ := h21 hz
      exact ⟨_, stepFun_step hab hz h0' h1 h2, stepFun_right hz h1 h2, stepFun_left ..⟩

theorem step_sat {a b : Nat} (hab : a ≤ b) : ∃ f, Step a b f :=
  ⟨_, stepFun_step (z₁ := 0) (w₁ := 0) (z₂ := 0) (w₂ := 0) hab (Nat.le_refl _) (by simp) (by simp) (by simp)⟩

/-- All points of `l` are pairwise consistent for `Step a b`. -/
def StepConsAll (a b : Nat) (l : List (Nat × Nat)) : Prop :=
  ∀ p, p ∈ l → ∀ q, q ∈ l → StepCons a b p q

/-- **Joint extension for `Step a b`**: pairwise consistency of any finite set of points suffices. -/
theorem step_points {a b : Nat} (hab : a ≤ b) (l : List (Nat × Nat)) (h : StepConsAll a b l) :
    ∃ f, Step a b f ∧ Thru f l :=
  baker_pixley med_majority (step_closed a b) l.length l rfl (step_sat hab)
    (fun p hp q hq => (step_E2 hab p.1 p.2 q.1 q.2).2 ⟨h p hp q hq, h q hq p hp⟩)

/-- **Elimination for `Step a b`** (any number of sites on the formal side). -/
theorem step_elim {a b : Nat} (hab : a ≤ b) {Y : Sort w} (B : Y → Prop) (t : Y → List Nat)
    (θ : Y → List Nat → Prop) :
    (∀ f, Step a b f → Form B t θ f) ↔
      ∀ y, B y → ∀ vs : List Nat, vs.length = (t y).length → StepConsAll a b ((t y).zip vs) → θ y vs :=
  elim_exact (C := StepConsAll a b)
    (fun f hf ts p hp q hq => by
      have e1 := thru_zip_map f ts p hp
      have e2 := thru_zip_map f ts q hq
      have := step_cons_of hf p.1 q.1
      rwa [e1, e2] at this)
    (step_points hab) B t θ

/-- With `b < a` the reference has no model. -/
theorem step_unsat {a b : Nat} (hab : b < a) (f : Nat → Nat) : ¬ Step a b f := by
  intro h
  have := h 0
  omega

/-! ## Lower-step references: `f x + a ≤ f (x + 1)` -/

/-- Increments at least `a`. `Lower 0` is monotone, `Lower 1` strictly monotone. -/
def Lower (a : Nat) (f : Nat → Nat) : Prop := ∀ x, f x + a ≤ f (x + 1)

theorem lower_of_step {a b : Nat} {f : Nat → Nat} (h : Step a b f) : Lower a f := fun x => (h x).1

theorem lower_between {a : Nat} {f : Nat → Nat} (h : Lower a f) (z : Nat) :
    ∀ d, f z + a * d ≤ f (z + d)
  | 0 => by simp
  | d + 1 => by
    have ih := lower_between h z d
    have s := h (z + d)
    rw [Nat.mul_succ, ← Nat.add_assoc z d 1]
    omega

def LowerCons (a : Nat) (p q : Nat × Nat) : Prop :=
  a * p.1 ≤ p.2 ∧ (p.1 ≤ q.1 → p.2 + a * (q.1 - p.1) ≤ q.2) ∧ (p.1 = q.1 → p.2 = q.2)

instance (a : Nat) (p q : Nat × Nat) : Decidable (LowerCons a p q) := by
  unfold LowerCons; exact inferInstance

theorem lower_cons_of {a : Nat} {f : Nat → Nat} (h : Lower a f) (z₁ z₂ : Nat) :
    LowerCons a (z₁, f z₁) (z₂, f z₂) := by
  refine ⟨?_, fun hle => ?_, fun e => ?_⟩
  · have := lower_between h 0 z₁
    rw [Nat.zero_add] at this
    show a * z₁ ≤ f z₁
    omega
  · have := lower_between h z₁ (z₂ - z₁)
    have e : z₁ + (z₂ - z₁) = z₂ := by simp at hle; omega
    rwa [e] at this
  · simp at e; subst e; rfl

def LowerConsAll (a : Nat) (l : List (Nat × Nat)) : Prop :=
  ∀ p, p ∈ l → ∀ q, q ∈ l → LowerCons a p q

theorem lower_closed (a : Nat) : Closed (Lower a) med := by
  intro f g h hf hg hh x
  have := hf x; have := hg x; have := hh x
  show med (f x) (g x) (h x) + a ≤ med (f (x + 1)) (g (x + 1)) (h (x + 1))
  unfold med
  omega

/-- **Closed form of the binary projection of `Lower a`.** -/
theorem lower_E2 (a z₁ w₁ z₂ w₂ : Nat) :
    E2 (Lower a) z₁ w₁ z₂ w₂ ↔ (LowerCons a (z₁, w₁) (z₂, w₂) ∧ LowerCons a (z₂, w₂) (z₁, w₁)) := by
  constructor
  · rintro ⟨f, hf, rfl, rfl⟩
    exact ⟨lower_cons_of hf z₁ z₂, lower_cons_of hf z₂ z₁⟩
  · rintro ⟨⟨h0, h12, he⟩, ⟨h0', h21, _⟩⟩
    -- choose an upper increment large enough for the two points, then use `Step`
    have key : ∀ z₁ w₁ z₂ w₂ : Nat, z₁ ≤ z₂ → a * z₁ ≤ w₁ → w₁ + a * (z₂ - z₁) ≤ w₂ →
        (z₁ = z₂ → w₁ = w₂) → ∃ f, Step a (a + w₂) f ∧ f z₁ = w₁ ∧ f z₂ = w₂ := by
      intro z₁ w₁ z₂ w₂ hz h0 h1 he
      have h2 : w₂ ≤ w₁ + (a + w₂) * (z₂ - z₁) := by
        rcases Nat.eq_or_lt_of_le hz with e | lt
        · have := he e; omega
        · have : (a + w₂) * 1 ≤ (a + w₂) * (z₂ - z₁) := Nat.mul_le_mul_left _ (by omega)
          omega
      exact ⟨_, stepFun_step (Nat.le_add_right a w₂) hz h0 h1 h2, stepFun_left ..,
        stepFun_right hz h1 h2⟩
    rcases Nat.le_total z₁ z₂ with hz | hz
    · obtain ⟨f, hf, e1, e2⟩ := key z₁ w₁ z₂ w₂ hz h0 (h12 hz) he
      exact ⟨f, lower_of_step hf, e1, e2⟩
    · obtain ⟨f, hf, e1, e2⟩ := key z₂ w₂ z₁ w₁ hz h0' (h21 hz) (fun e => (he e.symm).symm)
      exact ⟨f, lower_of_step hf, e2, e1⟩

theorem lower_points (a : Nat) (l : List (Nat × Nat)) (h : LowerConsAll a l) :
    ∃ f, Lower a f ∧ Thru f l :=
  baker_pixley med_majority (lower_closed a) l.length l rfl
    ⟨_, lower_of_step (Classical.choose_spec (step_sat (Nat.le_refl a)))⟩
    (fun p hp q hq => (lower_E2 a p.1 p.2 q.1 q.2).2 ⟨h p hp q hq, h q hq p hp⟩)

/-- **Elimination for `Lower a`** (monotone at `a = 0`, strictly monotone at `a = 1`). -/
theorem lower_elim (a : Nat) {Y : Sort w} (B : Y → Prop) (t : Y → List Nat)
    (θ : Y → List Nat → Prop) :
    (∀ f, Lower a f → Form B t θ f) ↔
      ∀ y, B y → ∀ vs : List Nat, vs.length = (t y).length → LowerConsAll a ((t y).zip vs) → θ y vs :=
  elim_exact (C := LowerConsAll a)
    (fun f hf ts p hp q hq => by
      have e1 := thru_zip_map f ts p hp
      have e2 := thru_zip_map f ts q hq
      have := lower_cons_of hf p.1 q.1
      rwa [e1, e2] at this)
    (lower_points a) B t θ

/-! ## Pointwise references (the reference shape of Theorem B) with several formal sites -/
section Pointwise
variable {Z : Type u} {W : Type v} {X : Sort w}
variable (A : X → Prop) (s : X → Z) (ρ : X → W → Prop)

/-- Points are admissible and no argument carries two values. -/
def PtCons (l : List (Z × W)) : Prop :=
  (∀ p, p ∈ l → Adm A s ρ p.1 p.2) ∧ (∀ p, p ∈ l → ∀ q, q ∈ l → p.1 = q.1 → p.2 = q.2)

/-- **Joint extension for a pointwise reference.** The class is a product, so admissibility of each
point and functionality of the list suffice. -/
theorem pointwise_points (total : ∀ z, ∃ w, Adm A s ρ z w) (l : List (Z × W))
    (h : PtCons A s ρ l) : ∃ f, RefF A s ρ f ∧ Thru f l := by
  classical
  let f : Z → W := fun z =>
    if hz : ∃ p, p ∈ l ∧ p.1 = z then (Classical.choose hz).2 else Classical.choose (total z)
  have hval : ∀ p, p ∈ l → f p.1 = p.2 := by
    intro p hp
    have hz : ∃ q, q ∈ l ∧ q.1 = p.1 := ⟨p, hp, rfl⟩
    have e : f p.1 = (Classical.choose hz).2 := by simp only [f, hz, ↓reduceDIte]
    rw [e]
    exact h.2 _ (Classical.choose_spec hz).1 p hp (Classical.choose_spec hz).2
  refine ⟨f, fun x ha => ?_, hval⟩
  by_cases hz : ∃ p, p ∈ l ∧ p.1 = s x
  · obtain ⟨p, hp, e⟩ := hz
    rw [← e, hval p hp]
    exact h.1 p hp x ha e.symm
  · have e : f (s x) = Classical.choose (total (s x)) := by simp only [f, hz, ↓reduceDIte]
    rw [e]
    exact Classical.choose_spec (total (s x)) x ha rfl

theorem ptcons_of {f : Z → W} (hf : RefF A s ρ f) (ts : List Z) :
    PtCons A s ρ (ts.zip (ts.map f)) := by
  refine ⟨fun p hp => ?_, fun p hp q hq e => ?_⟩
  · rw [← thru_zip_map f ts p hp]; exact adm_of_ref A s ρ hf p.1
  · rw [← thru_zip_map f ts p hp, ← thru_zip_map f ts q hq, e]

/-- **Elimination for a pointwise reference and a formal claim with any number of sites.** -/
theorem pointwise_elim (total : ∀ z, ∃ w, Adm A s ρ z w) {Y : Sort u} (B : Y → Prop)
    (t : Y → List Z) (θ : Y → List W → Prop) :
    (∀ f, RefF A s ρ f → Form B t θ f) ↔
      ∀ y, B y → ∀ vs : List W, vs.length = (t y).length → PtCons A s ρ ((t y).zip vs) → θ y vs :=
  elim_exact (C := PtCons A s ρ) (fun _ hf ts => ptcons_of A s ρ hf ts)
    (pointwise_points A s ρ total) B t θ

/-- A reference with an argument that admits no value entails every claim. -/
theorem vacuous_entails (hv : ∃ z, ∀ w, ¬ Adm A s ρ z w) (P : (Z → W) → Prop) :
    ∀ f, RefF A s ρ f → P f :=
  fun f hf => let ⟨z, hz⟩ := hv; absurd (adm_of_ref A s ρ hf z) (hz (f z))

end Pointwise

/-! ## Exactness without definability: Theorem C's reference is majority-closed -/

theorem sq_majority_closed : Closed Sq med := by
  intro f g h hf hg hh
  have ef := funext (sq_forces hf); have eg := funext (sq_forces hg); have eh := funext (sq_forces hh)
  subst ef; subst eg; subst eh
  have : (fun z => med (z * z) (z * z) (z * z)) = fun n : Nat => n * n :=
    funext fun z => med_majority.aab _ _
  rw [this]
  exact sq_square

/-- The binary projection of `Sq` is the graph of squaring. -/
theorem sq_E2 (z₁ w₁ z₂ w₂ : Nat) : E2 Sq z₁ w₁ z₂ w₂ ↔ (w₁ = z₁ * z₁ ∧ w₂ = z₂ * z₂) :=
  ⟨fun ⟨_, hf, e1, e2⟩ => ⟨e1 ▸ sq_forces hf z₁, e2 ▸ sq_forces hf z₂⟩,
   fun ⟨e1, e2⟩ => ⟨_, sq_square, e1.symm, e2.symm⟩⟩

end ProofScope.MultiOcc

#print axioms ProofScope.MultiOcc.baker_pixley
#print axioms ProofScope.MultiOcc.elim_sound
#print axioms ProofScope.MultiOcc.elim_exact
#print axioms ProofScope.MultiOcc.sep_of_points
#print axioms ProofScope.MultiOcc.majority_elim
#print axioms ProofScope.MultiOcc.two_point_exact
#print axioms ProofScope.MultiOcc.pairwise_insufficient
#print axioms ProofScope.MultiOcc.med_majority
#print axioms ProofScope.MultiOcc.step_closed
#print axioms ProofScope.MultiOcc.step_between
#print axioms ProofScope.MultiOcc.step_base
#print axioms ProofScope.MultiOcc.stepFun_step
#print axioms ProofScope.MultiOcc.step_E2
#print axioms ProofScope.MultiOcc.step_points
#print axioms ProofScope.MultiOcc.step_elim
#print axioms ProofScope.MultiOcc.step_unsat
#print axioms ProofScope.MultiOcc.lower_E2
#print axioms ProofScope.MultiOcc.lower_points
#print axioms ProofScope.MultiOcc.lower_elim
#print axioms ProofScope.MultiOcc.pointwise_points
#print axioms ProofScope.MultiOcc.pointwise_elim
#print axioms ProofScope.MultiOcc.vacuous_entails
#print axioms ProofScope.MultiOcc.sq_majority_closed
#print axioms ProofScope.MultiOcc.sq_E2
