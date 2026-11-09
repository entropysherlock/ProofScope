# 50-case externally reviewed pilot: protocol and infrastructure (SOTA-4 Task K/L)

**Status: infrastructure only. No case has been selected and no label exists. Nothing here may be called
independent until two real reviewers and an adjudicator, none of them a ProofScope developer, have labelled.**

## Composition (bench/pilot/composition.json)
50 pairs: equivalences 9, non-equivalences 9, assumption changes 8, definition changes 6, quantifier/domain
changes 6, joint changes 6, real paper→Lean pairs 6 (each with arXiv id, version, theorem number, page).
Excluded sources: anything written by a ProofScope developer or by an AI system used to build ProofScope
(including all of `research/cjcs`, `bench/dev_sota3`, `proofscope/benchmark`).

## Procedure
1. **Pool and provenance** (`bench/ingest.py`, schema in `bench/canonical.py`): every case records source,
   licence, retrieval date, upstream commit/arXiv version. Exact duplicates by normalized statement hash,
   near-duplicates grouped at token Jaccard ≥ 0.9.
2. **Seal** (`bench/seal.py`, run by a custodian who is not a developer): group-disjoint split, opaque ids,
   salted label commitment published before any tool runs. The sealed set is never opened in development.
3. **Blind packets** (`python -m bench.pilot.labels packets`): case text only (no system outputs, no source
   labels), an independent order per reviewer.
4. **Two independent Lean-literate reviewers** label each case on two tracks, with a written rationale:
   * **Track A** EQUIVALENT / NOT_EQUIVALENT / UNSURE: logical equivalence of the two Lean statements as Lean
     elaborates them (interpretation policy stated per case).
   * **Track B** FAITHFUL / NOT_FAITHFUL / UNASSESSABLE / UNSURE: does the formal statement say what the
     paper claims. Never inferred from Track A.
5. **Agreement** (`… agree`): raw agreement and Cohen's κ per track; every disagreement and every UNSURE goes
   to the adjudication queue. Pre-registered: if κ_A < 0.6 the label guide is revised and the pilot is
   relabelled before any scoring.
6. **Adjudication and finalization** (`… finalize`): a third person decides queued items; participants in
   `bench/pilot/CONFLICTS.txt` are refused; unresolved items are excluded from scoring, never guessed.
7. **Runs and scoring**: systems run on the sealed cases under the SOTA-2/3 resource policy
   (`bench/runner.py`); `bench/score.py` reports Clopper-Pearson intervals, McNemar exact tests with Holm
   correction and cluster bootstrap by group, separately for Track A and Track B, and for native vs
   kernel-certified outcomes. Failure classes are those of `bench.runner.evaluation_class`.
8. **Certificate verification for any decisive certified outcome**: recompile the certificate module with
   Lean 4.34.1 + Mathlib `d13f23b`, `#print axioms` ⊆ {propext, Classical.choice, Quot.sound}, `leanchecker`
   replay; the certificate files are published with the results.

## Reproduction
`python -m bench.pilot.labels --help`; tests in `tests/sota4/test_pilot.py` (synthetic reviewer ids only).
