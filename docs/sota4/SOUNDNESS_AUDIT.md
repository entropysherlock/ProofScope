# CJCS soundness audit (SOTA-4 Task M)

`research/cjcs/CJCS.lean` (sha256 `0083afd9…`), compiled with Lean 4.34.1 and replayed with
`leanchecker --fresh`: 15 declarations, no `sorryAx`.

| declaration | proposition (abridged) | axioms | kind | used by a verdict? |
|---|---|---|---|---|
| `cjcs_sound` | `Y → ¬X → ¬(X ↔ Y)` | none | concrete logical | pattern of `diff_RL` |
| `cjcs_sound'` | `X → ¬Y → ¬(X ↔ Y)` | none | concrete logical | pattern of `diff_LR` |
| `difference_needs_a_proof` | `¬(X ↔ Y) → X ∨ Y` | propext, choice, Quot.sound | concrete logical | design argument only |
| `nonequiv_iff` | `¬(X ↔ Y) ↔ (X ∧ ¬Y) ∨ (Y ∧ ¬X)` | classical | concrete logical | no |
| `both_false_equiv` | `¬X → ¬Y → (X ↔ Y)` | none | concrete logical | pattern of `equiv_both_false` |
| `both_true_equiv` | `X → Y → (X ↔ Y)` | none | concrete logical | pattern of `equiv_both_true` |
| `refuted_unprovable` | `¬X → ¬Nonempty X` | none | concrete logical | justifies refute-first pruning |
| `vacuous_logical_equiv` | vacuous reference ↔ any true formalization | none | schema-level | caveat (Track A ≠ fidelity) |
| `disagreement_partition` | pointwise partition into two regions | classical | schema-level | explanation only |
| `regions_disjoint` | the two regions are disjoint | none | schema-level | explanation only |
| `region_refutes_lean` | a region point refutes `Stmt H A Q` | none | schema-level | explanation only |
| `ref_excluded_refutes_ref` | a `ref_excluded` point refutes `Stmt H D P` | none | schema-level | explanation only |
| `joint_failure_iff` | single changes harmless ⇒ (combined fails ↔ joint region inhabited) | classical | schema-level | explanation only |
| `joint_disjoint_harmless` | empty joint region ⇒ combination harmless | classical | schema-level | no |
| `joint_example` | the development example | propext, Quot.sound | concrete (ℕ) | no |

## Verdict-level check
Every decisive verdict is read off a **directly certified declaration whose statement is the verdict**:
`CERTIFIED_LOGICAL_DIFFERENCE` ⇐ certified `diff_RL : ¬((R) ↔ (L))` or `diff_LR`; `CERTIFIED_LOGICAL_EQUIVALENCE`
⇐ certified `equiv_defeq`, `equiv_both_false` or `equiv_both_true : (R) ↔ (L)`. `R` and `L` are the
statement strings themselves, elaborated in the certificate module, so the certificate is about the
statements as Lean elaborates them. The theorem names in the row (`CJCS.cjcs_sound` …) are citations of
the pattern; the certificate module does not import CJCS.lean and does not need to. The mapping is
justified for Track A. Source-to-canonical links (`link_X`) are used inside `false_X` and are certified
whenever a refutation is.

## Unjustified or weaker jumps found
* **J1 — drift regions are not linked to R and L.** Region witnesses are built from `extract(R, L)`, the
  extractor's aligned telescope (H, D, A, P, Q). No certificate links that joint telescope to R or L (the
  certified links are the self-extractions `extract(R,R)`, `extract(L,L)`). A certified `region_*` proves
  that a point exists in a region of the extractor's *reading* of the pair. It is explanatory and no verdict
  depends on it, but the documentation's "complete, non-overlapping explanation of every pointwise
  disagreement" holds only under that unlinked alignment. Wording must say so; a link certificate for the
  joint telescope is future work.
* **J2 — "native" outcome for abstentions.** `bench/outcomes.cjcs` reports `native = NONEQUIV` for ABSTAIN
  and INCONCLUSIVE. Native figures for CJCS must not be read as predictions. Not changed (scoring
  definitions are frozen); reported here and in every summary.
* **J3 — auto-bound implicits.** Statements are elaborated with Lean's default `autoImplicit true`; an
  unbound identifier becomes a universally quantified implicit (`x11_auto_bound_free_variable` is certified
  equivalent to itself). Logically sound for the elaborated statement, but the elaborated statement may
  not be what the text meant. Input validation, not the engine, must reject such inputs.
* **J4 — Track B mapping.** A certified logical difference is mapped to NONEQUIV in Track B as well.
  This is justified only under the interpretation policy that a faithful formalization is logically
  equivalent to the reference *as a Lean statement*; if the reference is itself a mistranslation of the
  paper, Track B needs a human label.
* **F3 — SOTA-3 probe accepted dependents of failed obligations (soundness-preserving, availability bug).**
  Lean keeps a failed declaration (with `sorryAx`) in the environment, so in the SOTA-3 certify probe an
  obligation such as `equiv_both_true` that uses a failed `true_R` elaborated, passed the probe, and then
  broke the clean module: every certificate of the pair was rejected (observed on h01, h04, h12: zero
  certificates; the verdicts stayed ABSTAIN). Fail-closed, so not unsound. SOTA-4 restores state after a
  failed attempt and checks dependencies explicitly; on those three pairs it certifies the valid partial
  results (still ABSTAIN).
* **F2 — SOTA-3 point pools leak across cases** in one worker process (`with_literal_points` mutates a
  module global). Affects search completeness and reproducibility of multi-case runs, not soundness.
  SOTA-4 restores the pools per case (tested).

No jump from a Lean theorem to a decisive Python verdict was found to be unjustified.
