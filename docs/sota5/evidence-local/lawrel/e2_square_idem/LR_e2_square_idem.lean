set_option autoImplicit false
set_option maxHeartbeats 400000

namespace LR_e2_square_idem

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

def P (m : Magma) : Prop := ∀ a b : m.α, (m.op (m.op a b) (m.op a b)) = (m.op a b)
def Q (m : Magma) : Prop := ∀ a : m.α, (m.op a a) = a

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

theorem suff_idem : Suffices [Law.idem] := by
  intro m hm
  have h_idem : sat m Law.idem := hm _ (by simp)
  simp only [sat] at h_idem
  unfold P Q
  constructor <;> intro hpq <;> intros <;> grind

def t_m0 (a b : Fin 2) : Fin 2 := ([0, 0, 0, 0] : List (Fin 2)).getD (a.val * 2 + b.val) 0
def M_m0 : Magma := ⟨Fin 2, t_m0⟩
theorem M_m0_assoc : sat M_m0 Law.assoc := (by decide : ∀ x y z : Fin 2, (t_m0 (t_m0 x y) z) = (t_m0 x (t_m0 y z)))
theorem M_m0_comm : sat M_m0 Law.comm := (by decide : ∀ x y : Fin 2, (t_m0 x y) = (t_m0 y x))
theorem M_m0_sep : ¬ (P M_m0 ↔ Q M_m0) := (by decide : ¬ ((∀ a b : Fin 2, (t_m0 (t_m0 a b) (t_m0 a b)) = (t_m0 a b)) ↔ (∀ a : Fin 2, (t_m0 a a) = a)))

theorem minimal_idem : Suffices [Law.idem] ∧ ∀ T : List Law, (∀ ψ ∈ T, ψ ∈ [Law.idem]) → ∀ φ ∈ [Law.idem], φ ∉ T → ¬ Suffices T := by
  refine ⟨suff_idem, minimal_of_witnesses [Law.idem] ?_⟩
  intro φ hφ
  simp only [List.mem_cons, List.not_mem_nil, or_false] at hφ
  rcases hφ with rfl
  · exact ⟨M_m0, fun ψ hψ hne => by cases ψ <;> simp_all <;> first  | skip, M_m0_sep⟩

theorem necessary_idem : ∀ T : List Law, Law.idem ∉ T → ¬ Suffices T :=
  necessary_of_witness Law.idem M_m0 (fun ψ hne => by cases ψ <;> simp_all <;> first | exact M_m0_assoc | exact M_m0_comm | skip) M_m0_sep

end LR_e2_square_idem

#print axioms LR_e2_square_idem.suff_idem
#print axioms LR_e2_square_idem.M_m0_sep
#print axioms LR_e2_square_idem.minimal_idem
#print axioms LR_e2_square_idem.necessary_idem
