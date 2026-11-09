/-!
# ProofScope comparison: soundness and observability theorems

Generic over a type `α` of objects and predicates `HL CL HR CR : α → Prop`:
formal theorem   `TL := ∀ x, HL x → CL x`,   reference claim   `TR := ∀ x, HR x → CR x`.

Every classification ProofScope certifies is justified by one of the theorems below; each is kernel-checked
and uses no axioms beyond Lean's standard ones (`#print axioms` at the end of the file).
-/

namespace ProofScope.Soundness

variable {α : Type} (HL CL HR CR : α → Prop)

/-- COVERS: hypothesis cover + conclusion cover give `TL → TR`. -/
theorem transfer (hc : ∀ x, HR x → HL x) (cc : ∀ x, HR x → CL x → CR x) :
    (∀ x, HL x → CL x) → (∀ x, HR x → CR x) :=
  fun tl x hr => cc x hr (tl x (hc x hr))

/-- EQUIVALENT: covers in both directions give `TL ↔ TR`, uniformly in `x`. -/
theorem equivalent (hc : ∀ x, HR x → HL x) (cc : ∀ x, HR x → CL x → CR x)
    (hb : ∀ x, HL x → HR x) (cb : ∀ x, HL x → CR x → CL x) :
    (∀ x, HL x → CL x) ↔ (∀ x, HR x → CR x) :=
  ⟨transfer HL CL HR CR hc cc, transfer HR CR HL CL hb cb⟩

/-- APPLICABILITY_GAP: a witness shows the hypothesis cover fails, so `TL` cannot be applied at that object. -/
theorem app_gap_blocks_cover (g : ∃ x, HR x ∧ ¬ HL x) : ¬ ∀ x, HR x → HL x :=
  fun hc => let ⟨x, hr, nhl⟩ := g; nhl (hc x hr)

/-- VACUOUS: unsatisfiable formal hypotheses make `TL` hold for *any* conclusion. -/
theorem vacuous_says_nothing (v : ¬ ∃ x, HL x) (C : α → Prop) : ∀ x, HL x → C x :=
  fun x hl => absurd ⟨x, hl⟩ v

/-- CONCLUSION_GAP refutes the reference: if the reference claim were true, no conclusion-gap witness exists.
So a certified conclusion gap against a proved formal theorem means the *reference* (e.g. a transcription of a
paper) is false as written. -/
theorem concl_gap_refutes_reference (g : ∃ x, HR x ∧ HL x ∧ CL x ∧ ¬ CR x) : ¬ ∀ x, HR x → CR x :=
  fun tr => let ⟨x, hr, _, _, ncr⟩ := g; ncr (tr x hr)

/-- A strict-conclusion witness refutes the formal theorem: it can never be certified for a proved `TL`. -/
theorem strict_concl_refutes_formal (g : ∃ x, HL x ∧ HR x ∧ CR x ∧ ¬ CL x) : ¬ ∀ x, HL x → CL x :=
  fun tl => let ⟨x, hl, _, _, ncl⟩ := g; ncl (tl x hl)

/-- Observability: when both theorems are true, conclusion-level witnesses are impossible in both directions.
Any certified semantic difference between two *true* statements is therefore an applicability difference
(hypotheses), vacuity, or strictness of hypotheses: never a pointwise conclusion difference. -/
theorem observability (tl : ∀ x, HL x → CL x) (tr : ∀ x, HR x → CR x) :
    (¬ ∃ x, HR x ∧ HL x ∧ CL x ∧ ¬ CR x) ∧ (¬ ∃ x, HL x ∧ HR x ∧ CR x ∧ ¬ CL x) :=
  ⟨fun g => concl_gap_refutes_reference HL CL HR CR g tr,
   fun g => strict_concl_refutes_formal HL CL HR CR g tl⟩

/-- Contradiction pairs used by the engine's INCONSISTENT check really are contradictory. -/
theorem cover_vs_gap (hc : ∀ x, HR x → HL x) (g : ∃ x, HR x ∧ ¬ HL x) : False :=
  app_gap_blocks_cover HL HR g hc

theorem vacuous_vs_inhabited (v : ¬ ∃ x, HL x) (i : ∃ x, HL x) : False := v i

end ProofScope.Soundness

#print axioms ProofScope.Soundness.transfer
#print axioms ProofScope.Soundness.equivalent
#print axioms ProofScope.Soundness.app_gap_blocks_cover
#print axioms ProofScope.Soundness.vacuous_says_nothing
#print axioms ProofScope.Soundness.concl_gap_refutes_reference
#print axioms ProofScope.Soundness.strict_concl_refutes_formal
#print axioms ProofScope.Soundness.observability
#print axioms ProofScope.Soundness.cover_vs_gap
#print axioms ProofScope.Soundness.vacuous_vs_inhabited
