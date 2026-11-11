/-!
# HornFin: a verified decision procedure for ground definite-clause entailment (SOTA-15)

Core Lean 4 only. Atoms are elements of a type with decidable equality; a rule is a finite body and
a head. `closure rules prem` saturates `prem` under `rules`. Proved here:

* **termination**: `sat` is structurally recursive on its fuel, and `closure` supplies fuel
  `rules.length`, which `sat_closed` shows is enough (each productive round retires a rule);
* **soundness** (`closure_sound`): everything in the closure is derivable;
* **completeness** (`closure_complete`): everything derivable is in the closure;
* **exactness** (`entails_iff`): uniform entailment over *all* predicates `σ : α → Prop` holds iff
  the goal is in the closure, so the relation is decidable (`instDecidableEntails`).
-/
namespace ProofScope.HornFin

variable {α : Type} [DecidableEq α]

/-- A ground definite clause: body atoms and head atom. -/
abbrev Rule (α : Type) := List α × α

/-- Derivability from premises `prem` under `rules`. -/
inductive Der (rules : List (Rule α)) (prem : List α) : α → Prop
  | base {a : α} : a ∈ prem → Der rules prem a
  | step {r : Rule α} : r ∈ rules → (∀ b, b ∈ r.1 → Der rules prem b) → Der rules prem r.2

/-- The rule's body is contained in `S`. -/
def app (S : List α) (r : Rule α) : Bool := r.1.all (fun b => decide (b ∈ S))

theorem app_iff {S : List α} {r : Rule α} : app S r = true ↔ ∀ b, b ∈ r.1 → b ∈ S := by
  simp [app]

/-- Saturation: fire every applicable rule, retire the fired rules, repeat. -/
def sat : Nat → List (Rule α) → List α → List α
  | 0, _, S => S
  | fuel + 1, rules, S =>
    if (rules.filter (app S)).isEmpty then S
    else sat fuel (rules.filter (fun r => !app S r)) (S ++ (rules.filter (app S)).map Prod.snd)

/-- The least model of `rules` containing `prem`, as a list. -/
def closure (rules : List (Rule α)) (prem : List α) : List α := sat rules.length rules prem

theorem sat_mono (fuel : Nat) (rules : List (Rule α)) (S : List α) :
    ∀ a, a ∈ S → a ∈ sat fuel rules S := by
  induction fuel generalizing rules S with
  | zero => intro a h; exact h
  | succ n ih =>
    intro a h
    unfold sat
    split
    · exact h
    · exact ih _ _ a (List.mem_append_left _ h)

theorem sat_sound (all : List (Rule α)) (prem : List α) (fuel : Nat) (rules : List (Rule α))
    (S : List α) (hr : ∀ r, r ∈ rules → r ∈ all) (hS : ∀ a, a ∈ S → Der all prem a) :
    ∀ a, a ∈ sat fuel rules S → Der all prem a := by
  induction fuel generalizing rules S with
  | zero => intro a h; exact hS a h
  | succ n ih =>
    intro a h
    unfold sat at h
    split at h
    · exact hS a h
    · refine ih _ _ (fun r hr' => hr r (List.mem_filter.1 hr').1) ?_ a h
      intro b hb
      rcases List.mem_append.1 hb with hb | hb
      · exact hS b hb
      · obtain ⟨r, hrf, rfl⟩ := List.mem_map.1 hb
        have hf := List.mem_filter.1 hrf
        exact Der.step (hr r hf.1) (fun c hc => hS c (app_iff.1 hf.2 c hc))

theorem filter_length_lt {β : Type} (p : β → Bool) (l : List β) {x : β} (hx : x ∈ l)
    (hp : p x = false) : (l.filter p).length < l.length := by
  induction l with
  | nil => cases hx
  | cons y ys ih =>
    rcases List.mem_cons.1 hx with rfl | h
    · rw [List.filter_cons_of_neg (by simp [hp])]
      exact Nat.lt_succ_of_le (List.length_filter_le _ _)
    · by_cases hy : p y = true
      · rw [List.filter_cons_of_pos hy]; exact Nat.succ_lt_succ (ih h)
      · rw [List.filter_cons_of_neg hy]; exact Nat.lt_succ_of_lt (ih h)

/-- With enough fuel the result is closed under every rule still pending. -/
theorem sat_closed (fuel : Nat) (rules : List (Rule α)) (S : List α) (hlen : rules.length ≤ fuel) :
    ∀ r, r ∈ rules → (∀ b, b ∈ r.1 → b ∈ sat fuel rules S) → r.2 ∈ sat fuel rules S := by
  induction fuel generalizing rules S with
  | zero =>
    intro r hr
    have : rules = [] := List.eq_nil_of_length_eq_zero (Nat.le_zero.1 hlen)
    subst this; cases hr
  | succ n ih =>
    intro r hr hbody
    unfold sat at hbody ⊢
    split
    · rename_i hemp
      simp only [hemp, ↓reduceIte] at hbody
      have : r ∈ rules.filter (app S) := List.mem_filter.2 ⟨hr, app_iff.2 hbody⟩
      rw [List.isEmpty_iff.1 hemp] at this; cases this
    · rename_i hne
      simp only [hne] at hbody
      by_cases happ : app S r = true
      · apply sat_mono
        exact List.mem_append_right _ (List.mem_map.2 ⟨r, List.mem_filter.2 ⟨hr, happ⟩, rfl⟩)
      · refine ih _ _ ?_ r (List.mem_filter.2 ⟨hr, by simp [happ]⟩) hbody
        have hex : ∃ x, x ∈ rules.filter (app S) := by
          cases hf : rules.filter (app S) with
          | nil => rw [hf] at hne; exact absurd rfl hne
          | cons x _ => exact ⟨x, List.mem_cons_self⟩
        obtain ⟨x, hx⟩ := hex
        have hx' := List.mem_filter.1 hx
        have := filter_length_lt (fun r => !app S r) rules hx'.1 (by simp [hx'.2])
        omega

theorem closure_sound (rules : List (Rule α)) (prem : List α) :
    ∀ a, a ∈ closure rules prem → Der rules prem a :=
  sat_sound rules prem _ rules prem (fun _ h => h) (fun _ h => Der.base h)

theorem closure_complete (rules : List (Rule α)) (prem : List α) :
    ∀ a, Der rules prem a → a ∈ closure rules prem := by
  intro a d
  induction d with
  | base h => exact sat_mono _ _ _ _ h
  | step hr _ ih => exact sat_closed _ rules prem (Nat.le_refl _) _ hr ih

/-- A predicate satisfies every rule. -/
def Models (rules : List (Rule α)) (σ : α → Prop) : Prop :=
  ∀ r, r ∈ rules → (∀ b, b ∈ r.1 → σ b) → σ r.2

/-- Uniform entailment: every model of the rules containing the premises contains the goal. -/
def Entails (rules : List (Rule α)) (prem : List α) (g : α) : Prop :=
  ∀ σ : α → Prop, Models rules σ → (∀ p, p ∈ prem → σ p) → σ g

omit [DecidableEq α] in
theorem der_least {rules : List (Rule α)} {prem : List α} {σ : α → Prop} (hσ : Models rules σ)
    (hp : ∀ p, p ∈ prem → σ p) {a : α} (d : Der rules prem a) : σ a := by
  induction d with
  | base hb => exact hp _ hb
  | step hr _ ih => exact hσ _ hr ih

/-- **Exactness.** Uniform entailment over all predicates is membership in the computed closure. -/
theorem entails_iff (rules : List (Rule α)) (prem : List α) (g : α) :
    Entails rules prem g ↔ g ∈ closure rules prem := by
  constructor
  · intro h
    exact closure_complete rules prem g
      (h (Der rules prem) (fun _ hr hb => Der.step hr hb) (fun _ hp => Der.base hp))
  · intro h σ hσ hp
    exact der_least hσ hp (closure_sound rules prem g h)

instance instDecidableEntails (rules : List (Rule α)) (prem : List α) (g : α) :
    Decidable (Entails rules prem g) :=
  decidable_of_iff _ (entails_iff rules prem g).symm

/-- The closure is itself a separating model whenever the goal is outside it. -/
theorem canonical_separation (rules : List (Rule α)) (prem : List α) (g : α)
    (h : g ∉ closure rules prem) :
    Models rules (· ∈ closure rules prem) ∧ (∀ p, p ∈ prem → p ∈ closure rules prem) ∧
      g ∉ closure rules prem :=
  ⟨fun _ hr hb => sat_closed _ rules prem (Nat.le_refl _) _ hr hb, sat_mono _ _ _, h⟩

/-- Hypothetical premises (a nested implication in the formal claim) are extra rules. -/
theorem entails_local (rules loc : List (Rule α)) (prem : List α) (g : α) :
    (∀ σ : α → Prop, Models rules σ → Models loc σ → (∀ p, p ∈ prem → σ p) → σ g) ↔
      g ∈ closure (rules ++ loc) prem := by
  rw [← entails_iff]
  constructor
  · intro h σ hσ hp
    exact h σ (fun r hr => hσ r (List.mem_append_left _ hr))
      (fun r hr => hσ r (List.mem_append_right _ hr)) hp
  · intro h σ h1 h2 hp
    exact h σ (fun r hr => (List.mem_append.1 hr).elim (h1 r) (h2 r)) hp

/-! Worked instances, decided by evaluation of the verified procedure. -/
example : Entails [([0], 1), ([1], 2)] [0] (2 : Nat) := by decide
example : ¬ Entails [([0], 2), ([2], 4)] [0] (1 : Nat) := by decide
example : Entails [([0, 1], 2), ([], 1)] [0] (2 : Nat) := by decide

end ProofScope.HornFin

#print axioms ProofScope.HornFin.closure_sound
#print axioms ProofScope.HornFin.closure_complete
#print axioms ProofScope.HornFin.sat_closed
#print axioms ProofScope.HornFin.entails_iff
#print axioms ProofScope.HornFin.canonical_separation
#print axioms ProofScope.HornFin.entails_local
