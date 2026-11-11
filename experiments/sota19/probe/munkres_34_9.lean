import Mathlib

universe u_1

set_option maxHeartbeats 100000 in
theorem p_fwd_0 : (∀ (X : Type u_1) [inst : TopologicalSpace X] [CompactSpace X] [T2Space X] (X1 X2 : Set X),   IsClosed X1 →     IsClosed X2 →       X1 ∪ X2 = Set.univ →         TopologicalSpace.MetrizableSpace ↑X1 → TopologicalSpace.MetrizableSpace ↑X2 → TopologicalSpace.MetrizableSpace X) → (∀ {X : Type u_1} [inst : TopologicalSpace X] [CompactSpace X] [T2Space X] {X1 X2 : Set X},   IsClosed X1 →     IsClosed X2 →       TopologicalSpace.MetrizableSpace ↑X1 → TopologicalSpace.MetrizableSpace ↑X2 → TopologicalSpace.MetrizableSpace X) := by
  intro hR; intros; apply hR <;> first | assumption | (intros; simp_all)

set_option maxHeartbeats 100000 in
theorem p_fwd_1 : (∀ (X : Type u_1) [inst : TopologicalSpace X] [CompactSpace X] [T2Space X] (X1 X2 : Set X),   IsClosed X1 →     IsClosed X2 →       X1 ∪ X2 = Set.univ →         TopologicalSpace.MetrizableSpace ↑X1 → TopologicalSpace.MetrizableSpace ↑X2 → TopologicalSpace.MetrizableSpace X) → (∀ {X : Type u_1} [inst : TopologicalSpace X] [CompactSpace X] [T2Space X] {X1 X2 : Set X},   IsClosed X1 →     IsClosed X2 →       TopologicalSpace.MetrizableSpace ↑X1 → TopologicalSpace.MetrizableSpace ↑X2 → TopologicalSpace.MetrizableSpace X) := by
  intro hR; intros; apply hR <;> first | assumption | (intros; aesop)

set_option maxHeartbeats 100000 in
theorem p_fwd_2 : (∀ (X : Type u_1) [inst : TopologicalSpace X] [CompactSpace X] [T2Space X] (X1 X2 : Set X),   IsClosed X1 →     IsClosed X2 →       X1 ∪ X2 = Set.univ →         TopologicalSpace.MetrizableSpace ↑X1 → TopologicalSpace.MetrizableSpace ↑X2 → TopologicalSpace.MetrizableSpace X) → (∀ {X : Type u_1} [inst : TopologicalSpace X] [CompactSpace X] [T2Space X] {X1 X2 : Set X},   IsClosed X1 →     IsClosed X2 →       TopologicalSpace.MetrizableSpace ↑X1 → TopologicalSpace.MetrizableSpace ↑X2 → TopologicalSpace.MetrizableSpace X) := by
  intro hR; intros; apply hR <;> first | assumption | (intros; continuity)


-- the candidate on its own, with the empty sets: if the above are genuine, this is provable from R
#print axioms p_fwd_0
#print axioms p_fwd_1
#print axioms p_fwd_2
set_option pp.proofs true in
#print p_fwd_0
