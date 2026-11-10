# ProofScope Phase-1 pilot protocol, version 1 (FROZEN at the SOTA-5 commit; changes require v2)

Status: protocol only. No case selected, no label written. If no external reviewers are found, the pilot
must be called *internally adjudicated* and may not be described as independent.

1. **Population.** Pairs (reference statement, formal statement) where both are Lean 4 + Mathlib
   declarations, or a paper statement with a Lean formalization. Sources, in order: published
   formalization errata and review comments; Mathlib/Archive restatements by different authors; recorded
   autoformalization failures with corrections; real paper→Lean pairs with arXiv id, version, theorem
   number and page. Excluded: anything written by a ProofScope developer or an AI used to build ProofScope;
   all of `bench/dev_sota3`, `research/cjcs`, `research/sota5`, `proofscope/benchmark`.
2. **Strata (50).** equivalences 7, non-equivalences 7, domain changes 4, missing hypotheses 4, quantifier
   changes 3, implicit-type/instance differences 3, truncation/coercion mistakes 4, vacuous statements 3,
   both-false pairs 3, dependent binders 3, open claims 3, ambiguous reference 3, assumption-dependent
   equivalences 3.
3. **Sealing.** A custodian (not a developer) samples from the pool, runs `bench/seal.py` (group-disjoint,
   salted label commitment, opaque ids) and publishes the commitment before any tool runs.
4. **Adapter gate.** Every pair goes through adapter v2 (`bench/sota5/specs.py`). Pairs failing the standalone
   round-trip check are reported as INPUT_NOT_EVALUABLE for every system, never dropped silently.
5. **Labels.** Two Lean-literate reviewers, blind packets (`bench/pilot/labels.py packets`), labelling
   Track A (logical relation of the two Lean statements: EQUIVALENT, NOT_EQUIVALENT, ONE_WAY_R_TO_L,
   ONE_WAY_L_TO_R, INCOMPARABLE, UNSURE) and Track B (fidelity to the source: FAITHFUL, NOT_FAITHFUL,
   UNASSESSABLE, UNSURE) with written rationales. Track B is never derived from Track A.
6. **Agreement and adjudication.** Cohen's κ per track (`… agree`). If κ_A < 0.6, revise the guide and
   relabel before scoring. Disagreements and UNSURE go to a third person; conflicts in
   `bench/pilot/CONFLICTS.txt` are refused; unresolved items are excluded from scoring.
7. **Systems and budgets.** ProofScope v1.2, CJCS (SOTA-4 engine), BEq+, SemantEq at their native settings, one
   budget policy for all (tier 20 CPU-s whole-tree + measured startup allowance, 12000 MB), plus one
   900 CPU-s measurement run. Outcomes reported per class: kernel-certified equivalence (with relation
   record: definitional / both-true / both-false), kernel-certified difference, structural-only, abstain,
   input-not-evaluable, resource-exhausted.
8. **Primary endpoint.** Incorrect decisive verdicts (kernel-certified relation contradicting the adjudicated
   Track-A label). Pass: 0 incorrect decisive verdicts. Secondary: certified-difference recall on
   NOT_EQUIVALENT pairs with Clopper-Pearson 95% intervals; paired McNemar (exact) against each competitor on
   decisive-and-correct, Holm-corrected; median CPU. No accuracy is assigned from verdict counts.
9. **Publication.** Commitment, labels, rationales, agreement report, every run record and every certificate
   module are published together.
