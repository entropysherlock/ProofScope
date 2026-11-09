# ProofScope engine (v0.5 slice of the v1.0 roadmap)

Status as of November 8, 2026. This page says what is implemented and tested, what each output means, and what is
not done. Nothing here claims state-of-the-art performance or a mathematical discovery.

## Architecture as implemented

```
Lean project @ pinned commit ──► [1] Theorem intelligence      proofscope/dossier.py + lean/ProofScope/Dossier.lean
                                      │  JSON + Markdown dossiers from the elaborated environment
reference statement (typed) ───► [2] Theorem comparison        proofscope/compare.py
                                      │  obligations: covers, back, gaps, strictness, vacuity
                                 [3] Certificate gate          proofscope/certify.py
                                      │  elaborate → clean module → #print axioms → leanchecker replay
                                 [4] Audit engine              proofscope/project.py (stages S0–S8)
                                      │  provenance, closure, hazards, catalog, worksheets, build, dossiers
                                 [5] Benchmark                 proofscope/bench.py + proofscope/benchmark/
                                      │  dev / held-out / adversarial certificates, metrics with 95% CIs
                                 [6] Viewer                    proofscope/viewer.py → one offline HTML file
```

Workflows: **ProofScope Engine** (subsystems 1, 2, 3, 5, 6, core Lean only) and **ProofScope Project Audit**
(subsystem 4, now with `dossiers` when `build` is on). The v0.1–v0.4 workflows are unchanged.

## 1. Theorem intelligence (`#proofscope_dossier`, `#proofscope_dossier_module`)

Computed inside Lean from the elaborated declaration, not from source text:

| Field | Source |
|---|---|
| `elaborated_type`, `conclusion` | `ppExpr` of the declaration type and of its body under `forallTelescope` |
| `binders[].role` | `instance` (instance-implicit or a class), `hypothesis` (`isProp`), `parameter` (data) |
| `conclusion_shape` | head symbols after `whnfR` (∀ → ∃ ∧ ∨ ↔ ¬ = ≤ < …), depth-limited |
| `statement_dependencies[].role` | `logic`, `machinery` (instances, class projections, Lean's reducible notation such as `GE.ge`), `definition`, `type`, `theorem`, `axiom` |
| `proof_dependencies` | constants in the value that are not in the type (**direct only**) |
| `axioms` | `Lean.collectAxioms` (transitive) → `axiom_status` NONE / STANDARD / NONSTANDARD / SORRY |
| `kernel_status` | driver: `leanchecker` replay of the declaring module → REPLAYED / REPLAY_FAILED; Lean's own library → TOOLCHAIN_LIBRARY; else NOT_RUN |
| `source_locations` | `findDeclarationRanges?` |

A `sorry` theorem **passes** kernel replay (the kernel accepts `sorryAx` as an axiom); `axiom_status = SORRY` is what
catches it. Both are reported.

**Measured:** 180 dossiers from Lean core (`Init.Data.Nat.Lemmas`, `Init.Data.List.Lemmas`) and `Std`
(`Std.Data.HashMap.Lemmas`) in 2.6 s, 0 incomplete extractions; 4 dossiers from the fixture Lake project, all four
kernel-replayed, axiom statuses NONE / STANDARD / NONSTANDARD / SORRY as planted.

## 2–3. Theorem comparison and certificates

Formal `∀ x, H_L x → C_L x` against reference `∀ x, H_R x → C_R x`. Each label is issued only when the listed
propositions are **certificates** (elaborated, recompiled cleanly, only propext / Classical.choice / Quot.sound,
replayed by `leanchecker`):

| Label | Certified propositions | What it establishes | What it does not |
|---|---|---|---|
| VACUOUS | `¬ ∃ x, H_L x` | the formal theorem has no instances | anything about the reference |
| APPLICABILITY_GAP | `∃ x, H_R x ∧ ¬ H_L x` | the formal theorem cannot be applied to an object the reference covers | that the reference claim is false |
| CONCLUSION_GAP | `∃ x, H_R x ∧ H_L x ∧ C_L x ∧ ¬ C_R x` | at that object the formal conclusion does not give the reference's | that the reference claim is false |
| EQUIVALENT | `∀x, H_R→H_L`, `∀x, H_R→C_L→C_R`, `∀x, H_L→H_R`, `∀x, H_L→C_R→C_L`, and the transfer implication | each theorem implies the other uniformly in x | that both match a paper |
| LEAN_STRONGER | transfer + `∃x, H_L ∧ ¬H_R` or `∃x, H_L ∧ H_R ∧ C_R ∧ ¬C_L` | the formal theorem implies the reference and covers strictly more | — |
| COVERS | transfer `(∀x, H_L→C_L) → (∀x, H_R→C_R)` | the formal theorem implies the reference | strictness |
| INCONCLUSIVE | none | nothing | — |

Pairs that cannot both hold (e.g. `hyp_cover` and `app_gap`) are checked; if both were certified the run is labelled
INCONSISTENT. This has not happened in any run.

Witness search: tactic portfolio, small concrete witnesses for `Nat`, `Int` and `List Nat` binders, and, for
natural-number binders with bounds, `decide +kernel` on the boxed existential (a boxed witness is a full certificate
of the unbounded existential). Bounded *agreement* is never reported as a general proof.

**Known limitation (measured):** uniform comparison cannot distinguish two unrelated statements that are both always
true (cases `mislinked_true_true`, `h_mislinked2` are labelled EQUIVALENT and counted as misses). Universal statements
over infinite domains in a conclusion gap are not decidable by finite search (`h_quant_exists_weak` → INCONCLUSIVE).

## 5. Benchmark (project-authored)

| Split | Cases | Exact labels | Detection precision | Recall (95% CI) | FPR | Coverage | Naive baseline precision / FPR |
|---|---|---|---|---|---|---|---|
| dev | 33 | 33/33 | 1.0 | 0.941 [0.73, 0.99] | 0.0 | 1.0 | 0.531 / 0.938 |
| held-out | 20 | 18/20 [0.70, 0.97] | 1.0 | 0.833 [0.55, 0.95] | 0.0 | 0.95 | 0.60 / 1.0 |

Adversarial certificate cases: 20/20 handled correctly, 0 false acceptances (sorry, admit, custom axioms, `False`
axiom, `native_decide`, `decide +native`, sorried lemma and definition, a forged declaration added with kernel checking
off, which only replay caught, false statements, partial progress, `unsafeCast`, statement swap, plus 5 honest
controls that must be accepted).

Held-out cases were written after the engine files were frozen (hashes in `proofscope/benchmark/ENGINE_FREEZE.txt`,
checked by the workflow) and run once. They were written by the same author as the engine, so they are held out from
tuning, not independent. **Competitors were not run:** SemantEq, FormalRx and FormalRx-CC address statement
equivalence or natural-language-to-Lean diagnosis on their own datasets with models not available here; LeanTrail was
not located. No competitor numbers are reported.

## Not done (exact continuation point)

1. **Dossiers on Mathlib projects** have not been executed: the sandbox cannot reach the Mathlib cache. Next: run
   Project Audit with `build` and `dossiers` on a small Mathlib-dependent repository, then on openai/math targets.
2. **Transitive proof dependencies** are not enumerated (direct only).
3. **Comparison specs from real papers**: the engine compares formal statements; turning a paper theorem into a typed
   reference is AI_PRELIMINARY and needs human confirmation. No real-paper comparison has been certified.
4. **Benchmark size**: 53 comparison cases + 20 adversarial certificate cases (target was 100+ with independent
   annotation and multiple mathematical domains beyond ℕ/ℤ/lists).
5. **Resumable checkpointed audits** and a **hosted** interface: not implemented. The viewer is a static offline file.
6. **Three independent research repositories audited with build**: not done (only openai/math without build, plus
   Lean core, Std and the fixture project for dossiers).

## Honest classification

Engineering: solid Level 2 moving toward Level 3. The subsystems are connected, tested, reproducible and fail safely
(no false acceptance in any adversarial case, no contradictory certificates). Research novelty: not established. The
certificate shapes are classical specification refinement; the contribution is a sound, tested, integrated
implementation on Lean 4, not a new method.
