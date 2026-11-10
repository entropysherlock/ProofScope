set_option autoImplicit false
set_option maxHeartbeats 400000

namespace LR_e1_absorption

structure Magma where
  α : Type
  op : α → α → α

inductive Law where
  | assoc
  | comm
  | idem
  deriving DecidableEq

def sat (m : Magma) : Law → Prop
  | .assoc => ∀ x y z : m.α, (m.op (m.op x y) z) = (m.op x (m.op y z))
  | .comm => ∀ x y : m.α, (m.op x y) = (m.op y x)
  | .idem => ∀ x : m.α, (m.op x x) = x

def P (m : Magma) : Prop := ∀ a b : m.α, (m.op a (m.op a b)) = (m.op a b)
def Q (m : Magma) : Prop := ∀ a b : m.α, (m.op (m.op a b) b) = (m.op a b)

def Suffices (S : List Law) : Prop := ∀ m : Magma, (∀ φ ∈ S, sat m φ) → (P m ↔ Q m)

theorem minimal_of_witnesses (S : List Law)
    (wit : ∀ φ ∈ S, ∃ m, (∀ ψ ∈ S, ψ ≠ φ → sat m ψ) ∧ ¬ (P m ↔ Q m))
    (T : List Law) (hT : ∀ ψ ∈ T, ψ ∈ S) (φ : Law) (hφS : φ ∈ S) (hφT : φ ∉ T) : ¬ Suffices T := by
  obtain ⟨m, hm, hne⟩ := wit φ hφS
  intro h
  exact hne (h m (fun ψ hψ => hm ψ (hT ψ hψ) (fun e => hφT (e ▸ hψ))))

theorem necessary_of_witness (φ : Law) (m : Magma) (hm : ∀ ψ, ψ ≠ φ → sat m ψ) (hne : ¬ (P m ↔ Q m))
    (T : List Law) (hT : φ ∉ T) : ¬ Suffices T :=
  fun h => hne (h m (fun ψ hψ => hm ψ (fun e => hT (e ▸ hψ))))

theorem suff_comm : Suffices [Law.comm] := by
  intro m hm
  have h_comm : sat m Law.comm := hm _ (by simp)
  simp only [sat] at h_comm
  unfold P Q
  constructor <;> intro hpq <;> intros <;> grind

theorem suff_assoc_idem : Suffices [Law.assoc, Law.idem] := by
  intro m hm
  have h_assoc : sat m Law.assoc := hm _ (by simp)
  simp only [sat] at h_assoc
  have h_idem : sat m Law.idem := hm _ (by simp)
  simp only [sat] at h_idem
  unfold P Q
  constructor <;> intro hpq <;> intros <;> grind

def t_m0 (a b : Fin 3) : Fin 3 := ([0, 0, 0, 0, 0, 0, 0, 1, 2] : List (Fin 3)).getD (a.val * 3 + b.val) 0
def M_m0 : Magma := ⟨Fin 3, t_m0⟩
theorem M_m0_assoc : sat M_m0 Law.assoc := (by decide : ∀ x y z : Fin 3, (t_m0 (t_m0 x y) z) = (t_m0 x (t_m0 y z)))
theorem M_m0_sep : ¬ (P M_m0 ↔ Q M_m0) := (by decide : ¬ ((∀ a b : Fin 3, (t_m0 a (t_m0 a b)) = (t_m0 a b)) ↔ (∀ a b : Fin 3, (t_m0 (t_m0 a b) b) = (t_m0 a b))))

def t_m1 (a b : Fin 3) : Fin 3 := ([0, 0, 0, 0, 1, 0, 1, 1, 2] : List (Fin 3)).getD (a.val * 3 + b.val) 0
def M_m1 : Magma := ⟨Fin 3, t_m1⟩
theorem M_m1_idem : sat M_m1 Law.idem := (by decide : ∀ x : Fin 3, (t_m1 x x) = x)
theorem M_m1_sep : ¬ (P M_m1 ↔ Q M_m1) := (by decide : ¬ ((∀ a b : Fin 3, (t_m1 a (t_m1 a b)) = (t_m1 a b)) ↔ (∀ a b : Fin 3, (t_m1 (t_m1 a b) b) = (t_m1 a b))))

theorem minimal_comm : Suffices [Law.comm] ∧ ∀ T : List Law, (∀ ψ ∈ T, ψ ∈ [Law.comm]) → ∀ φ ∈ [Law.comm], φ ∉ T → ¬ Suffices T := by
  refine ⟨suff_comm, minimal_of_witnesses [Law.comm] ?_⟩
  intro φ hφ
  simp only [List.mem_cons, List.not_mem_nil, or_false] at hφ
  rcases hφ with rfl
  · exact ⟨M_m0, fun ψ hψ hne => by cases ψ <;> simp_all <;> first  | skip, M_m0_sep⟩

theorem minimal_assoc_idem : Suffices [Law.assoc, Law.idem] ∧ ∀ T : List Law, (∀ ψ ∈ T, ψ ∈ [Law.assoc, Law.idem]) → ∀ φ ∈ [Law.assoc, Law.idem], φ ∉ T → ¬ Suffices T := by
  refine ⟨suff_assoc_idem, minimal_of_witnesses [Law.assoc, Law.idem] ?_⟩
  intro φ hφ
  simp only [List.mem_cons, List.not_mem_nil, or_false] at hφ
  rcases hφ with rfl | rfl
  · exact ⟨M_m1, fun ψ hψ hne => by cases ψ <;> simp_all <;> first | exact M_m1_idem, M_m1_sep⟩
  · exact ⟨M_m0, fun ψ hψ hne => by cases ψ <;> simp_all <;> first | exact M_m0_assoc, M_m0_sep⟩

end LR_e1_absorption

#print axioms LR_e1_absorption.suff_comm
#print axioms LR_e1_absorption.suff_assoc_idem
#print axioms LR_e1_absorption.M_m0_sep
#print axioms LR_e1_absorption.M_m1_sep
#print axioms LR_e1_absorption.minimal_comm
#print axioms LR_e1_absorption.minimal_assoc_idem
