# SOTA-19 pilot A0: is ProofScope's equivalence advantage replicable without ProofScope?

Pre-registered 2026-11-11 by Claude for Caleb J. Westfall, before the experiment ran.

## Question

SOTA-18 found four pairs where ProofScope certified equivalence and neither SemantEq nor BEq+ did. All four
are `ASSUMPTION_EQUIVALENT`: the conclusions coincide and ProofScope proved the two hypothesis sets
equivalent with a fixed tactic portfolio. Is the advantage ProofScope's extraction and alignment, or just
"apply the other statement, then close the side goals with a stronger portfolio" — something any equivalence
checker can add in a few lines?

## Baseline G (no ProofScope machinery)

For each of the 399 SOTA-18 pairs whose statements reached the engines (printed, round-tripped
propositions R and L from `experiments/sota18/results/full/run_42969440169_1/proofscope/`), and each
direction, a separate theorem per closer `T` in ProofScope's own portfolio (`adelta12.REDUNDANT`, plus
`assumption`):

    theorem g_fwd_k : (R) → (L) := by intro hR; intros; apply hR <;> first | assumption | T

(`g_bwd_k` symmetrically). A direction is proved if some theorem has no error and its axioms are within
`propext, Classical.choice, Quot.sound`. G certifies equivalence when both directions are proved.
Same Lean 4.34.1 / Mathlib v4.34.1, 100,000 heartbeats per theorem, 600 s per pair.

## Pre-registered reading

* **H_rep (replicable)** holds if G certifies all 4 SOTA-18 wins **and** at least 90 % of ProofScope's
  H1 certified equivalences (75 pairs). Then ProofScope's equivalence-side advantage is a portfolio
  effect; its remaining value must come from what G cannot give (localising *which* hypothesis changed,
  directional facts when one side fails, certificates that explain).
* **H_struct** holds if G misses at least 2 of the 4 wins or fewer than 75 % of the 75. Then alignment and
  extraction carry real weight.
* In between: reported as mixed.

Also reported: pairs G certifies that none of ProofScope, SemantEq or BEq+ certified.

## Amendment 1 (2026-11-11, after run 43001388917; protocol unchanged, harness repaired)

Run 43001388917 is **invalid**. Its harness accepted a direction when `#print axioms` listed only standard
axioms. For Munkres 34.9 it reported a proof of `R → L` although `L` is false (both sets empty) and `R` is
a theorem. Probe run 43006408019 showed why: the statement's elaboration hit `maxHeartbeats`, Lean added
`theorem p_fwd_0 : sorry := sorry`, and `#print axioms` printed "does not depend on any axioms".
Repair: a theorem counts only if no error is reported on any of its lines; heartbeats raised from 100,000
to 400,000 so statements elaborate. Closers, pairs and the pre-registered reading are unchanged. The
invalid records are kept in `results/a0_run_43001388917/` and marked invalid there.
