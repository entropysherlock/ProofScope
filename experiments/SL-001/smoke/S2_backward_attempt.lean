namespace SL001.Smoke

/-- Statement A on the class of natural numbers n. -/
def A (n : Nat) : Prop := 4 ∣ n
/-- Statement B on the same class. -/
def B (n : Nat) : Prop := 2 ∣ n

/-- A target, as a schema over every predicate `p` on the naturals. -/
def Target (p : Nat → Prop) : Prop := ∀ n, p n
/-- What a (hypothetical) certificate actually proves: the target only for positive `n`. -/
def Proved (p : Nat → Prop) : Prop := ∀ n, 0 < n → p n

end SL001.Smoke

theorem SL001.Smoke.bwd : ∀ n, SL001.Smoke.B n → SL001.Smoke.A n := by
  intro n h
  obtain ⟨k, hk⟩ := h
  exact ⟨k, by omega⟩
