# ProofScope competitor benchmark: preregistered protocol (draft v0)

Date: 2026-11-09. Status: **protocol only; NOT a completed blind competitor evaluation**.
Source branch: `v1.2-review`. Do not alter `main` or the frozen v1.2 corpus.
The original 80-case Mathlib split is **not independent**: it was authored by the development team and is NOT the primary blind leaderboard.

## Competitor availability and licensing (verified in source repositories)
- SemantEq: https://github.com/hlxr89/SemantEq ; Apache-2.0; runnable Lean 4; existing ProofScope comparator at pinned `f92767000e14d11744580946980cf874324f5d19`. Repo README specifies Lean 4.30.0-rc1 and 20 seconds default per pair. Preserve its vendor toolchain and Mathlib pin.
- BEq+: https://github.com/augustepoiroux/LeanInteract/blob/main/examples/beq_plus.py ; parent repository MIT; runnable Python + Lean; published in Poiroux et al., EMNLP 2025. The published ProofNetVerif has 3,752 annotated examples. Pin the script's commit, Python dependencies, Lean version and Mathlib before run.
- ACE/SAE: Yi Yu et al., arXiv:2610.25018v3 (2026-10-22). Code repository, commit, license and executable installation path **NOT YET VERIFIED**. Do not score as a failed runner; record unavailable pending audit. Paper's reported performance is external, not our reproduction.
- MachineChecked: https://github.com/cgarryZA/MachineChecked ; Apache-2.0; Python CLI `machinechecked check --json`; test separately on paper/Lean correspondence and audit provenance.
- PaperFormalizer: https://github.com/Jiyuan-Tan/PaperFormalizer ; custom MIT-derived responsible-use license (read entire LICENSE and third-party licenses before reuse), agentic LaTeX-to-Lean pipeline. Requires external model calls, human checkpoints and substantial compute; no direct identical-budget equivalence ranking.
- Also consider papercheck https://github.com/cgarryZA/papercheck and formalize-paper https://github.com/ZRTMRH/formalize-paper as end-to-end auditing comparators. Licensing and toolchain must be pinned independently; formalize-paper includes PolyForm Noncommercial components.

## Defining truth: two separate, non-interchangeable tracks
**Track A: whole-statement logical equivalence**. `E_LOGICAL` iff the two fully elaborated statements are equivalent in a specified common context. A pair of independently provable theorems may be logically equivalent. A proved implication each way is admissible evidence for this track. This is not a faithful-translation metric.

**Track B: statement-fidelity/role-preserving equivalence**. `E_FAITHFUL` iff the candidate preserves the intended quantified domain, hypothesis role, conclusion meaning, definition choices and relevant strength of the reference, allowing explicit approved algebraic/logical reformulations. Independently proving two unrelated statements is *not* enough. True-but-different bounds must be assessed by blinded mathematicians on this track, even if Track A calls them equivalent.

**Track C: paper-to-Lean audit**. Evaluate claim inventory, exact theorem links, assumptions, definitions, kernel replay, paper-faithfulness decisions, reproducible evidence and coverage. This is NOT ranked together with A/B.

For A/B, record `equivalent`, `non_equivalent`, `disputed` or `unassessable`. Separately record directional relations `reference_implies_candidate`, `candidate_implies_reference`, `incomparable`, `both_false_on_specified_domain` only when independently justified. Do not translate every ProofScope diagnosis into a SemantEq verdict; preserve original tool outputs.

## Blind data and adjudication
1. Independent curator (not the ProofScope/competitor implementation authors) selects a preregistered, stratified sample from published **ProofNetVerif** and other permitted publicly released benchmarks, plus genuinely new holdout pairs from Lean/Mathlib projects unexposed to the developers. Document licenses and duplicates. Include real paper-to-Lean mismatches, not only synthetic mutations.
2. Precommit case IDs, exact Lean source strings, imports, Mathlib/toolchain fingerprints, source provenance, split hashes, adjudication rubric, inclusion/exclusion rules, expected compute and primary metrics. Deposit a sealed mapping of anonymized pairs to ground truth with an independent custodian before runs.
3. Two independent mathematical reviewers receive blinded reference/candidate pairs with sources and semantics, **without tool predictions, developer labels or tool names**. They each record A and B with reasoned evidence. A third non-developer resolves disagreement; remaining dispute is excluded from adjudicated primary scoring and counted explicitly. Publish both votes and reasons after results are locked.
4. Oversample adversarial categories but report sampling strata: true-but-different claims, vacuity, inconsistent hypotheses, nontrivial assumptions, binder and domain changes, quantifier reversal, coercions, dependent types, nontrivial structures, local field/ring/number/topology/set cases, missing paper hypotheses, false claims. Include duplicates only in a clearly identified robustness stratum.
5. Avoid performance-driven test removal. Predeclare `non_elaborating` and `unsupported_input` separately. A compiler mismatch is an infrastructure event, not a mathematical abstention. A disclosed adapter may perform only semantics-preserving format conversion, reviewed by an adversarial maintainer. No tuning on blinded labels.
6. Preserve separate data sets: vendor-home benchmark, ProofScope 80-case non-independent evaluation, entirely external heldout, and new independent blind holdout. **Primary leaderboard is the independent blind holdout**, not the ProofScope-authored 80.

## Environment and budget
- Freeze exact Git commit, tags, sha256 of source and adapter, OS image, CPU model, RAM limit, number of workers, and each tool's Lean/Mathlib dependencies. **Never force a competitor onto an incompatible Lean/Mathlib version merely for apparent equality.** Instead prove exact same proposition elaborates in each native environment, and disclose any version-dependent mismatch; do not compare incompatible cases as if identical.
- Use a matched fixed CPU-time budget and wall-clock cap per case, plus a generous sensitivity tier (e.g. 20 seconds and 180 seconds, with budget applied to **every** tool, including ProofScope). Count startup, compilation, tactic/proof search and certificate replay separately. Report actual CPU seconds and wall seconds, peak RSS, timeouts and cache warmth; repeat on the same runner image after a cold and warm run. Costly LLM-based alternatives get a separate dollar/token budget and inference-run variance, not a misleading CPU-only comparison.
- Re-run each certified certificate using the pinned Lean checker in a fresh process. Check all imported axioms and `sorryAx`, `native_decide`, unsafe evaluation and external trust assumptions under a published policy. A syntactically emitted proof is not a validated certificate unless replay succeeds.
- GitHub Actions workflows must run an adapter compatibility test, a small pilot, then a fixed complete job matrix with `fail-fast: false`, full artifacts, SHA manifest and an independent verification job. Do not silently downgrade failed runs to abstentions.
- Archive inputs, individual responses, raw logs, certificates, timestamps, metrics code, exact build/install stdout, adjudication votes and dispute resolutions. On tool failure preserve error trace, do not fabricate a result.

## Primary and secondary scoring
For each A/B track separately, define positive=equivalent, negative=non-equivalent:
TP=certified equivalent on gold equivalent; FP=equivalent on gold non-equivalent; TN=certified non-equivalent on gold non-equivalent; FN=non-equivalent on gold equivalent; ABSTAIN=undecided on an elaborated and supported item.
- Precision_equiv = TP/(TP+FP) (undefined if zero positive predictions).
- Recall_equiv = TP / all gold equivalents, **including abstentions**.
- False-equivalence rate = FP / all gold non-equivalents, **including abstentions**.
- False-difference rate = FN / all gold equivalents, **including abstentions**.
- Decisive coverage = (TP+TN+FP+FN)/all eligible cases.
- Selective accuracy = (TP+TN)/(TP+TN+FP+FN), with coverage beside it, never alone.
- Also report non-equivalence precision/recall, abstention rate, timeout/error/elaboration rate, macro-by-domain means, per-case runtime, tail P50/P90/P99, and cost per certified correct decision.
- Report full confusion matrices, bootstrap 95% CIs clustered by original theorem/paper, exact McNemar comparisons on *paired resolved cases*, paired coverage differences, and all subgroup counts. For error rates of zero use nonzero upper confidence bounds; do not conclude a zero true error probability.
- Certificate quality has independent axes: (1) kernel-replayed in both directions, (2) certified counterexample/negative theorem, (3) audited rule restriction, (4) source-to-statement linking, (5) explicit assumptions/axioms, (6) human paper-faithfulness signoff. Do not collapse to one marketing score.
- Treat tools unable to assert certified non-equivalence as `abstain` for negative detection unless they truly return a justified negative; treating absence of proof as evidence of non-equivalence is invalid.

## End-to-end paper audit (track C)
Select at least three papers not written or previously audited by any tested developer, stratified by (short vs long; preexisting Lean vs LaTeX only; seeded and naturally occurring errors). Freeze manuscript source, Lean commit, and claim gold inventory before running. Judge claim recall, false claim links, definition/assumption discrepancies, proved vs `sorry` vs axiom-supported claims, verified counterexamples, repaired statements (with recorded approval), time/cost/human minutes, and audit trail reproducibility. MachineChecked primarily *inspects and links* Lean; PaperFormalizer *generates and revises* Lean. Evaluate each in native intended workflow; show task-coverage matrix before outcome matrix.

## Specific existing confounders and adjudication
- Previous 208-pair ProofScope/SemantEq comparison (`docs/v0.6_competitor_result.md`) is **historical exploratory**, not blind or apples-to-apples. Its 18 disagreements require Track-A/Track-B recoding; do not turn them into a victory count.
- `e_n08_euclid`: reference `∀a b c:ℕ, a∣b*c → a∣b ∨ a∣c` is false at (4,2,2); candidate adds `Nat.Prime a` and is true by Euclid's lemma. Author label `REFERENCE_NEEDS_ASSUMPTION` is mathematically plausible, subject to Lean-level independent proof and structural decision.
- `e_r06_log_mul`: candidate drops `0<y` from the reference `Real.log (x*y)=Real.log x+Real.log y`; for x=2,y=0, candidate claims `0 = Real.log 2`, false. Author label `LEAN_CLAIM_FALSE` is mathematically plausible, subject to a checker-validated counterexample and independent reviewer.
These two are **not yet independently adjudicated** merely because this audit has restated counterexamples.

## Release gate
No title containing 'best', 'SOTA', 'wins', or 'state of the art' until: independent gold labels and votes are published; all runnable licensed competitors are included at frozen commits; identical eligible inputs and balanced budgets are documented; missing runners disclosed; certificate checks replay; significance/uncertainty reported; and an external team reproduces the principal result. Otherwise publish descriptive per-task findings only.
