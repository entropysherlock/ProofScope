# SOTA-19A: reference-guided gap certification on ProofNet → ProofNet-Verified

Research director: Caleb J. Westfall. Designed by Claude, 2026-11-11. Self-contained mission.

## Hypothesis (falsifiable)

When two formalizations of one problem differ in their hypotheses, the question "how do they differ?"
is decided by the conclusion on the **gap region**: the instances where one statement's hypotheses hold
and the other's do not. Concretely, for aligned statements

    R : ∀ x, C x → A x → P x          L : ∀ x, C x → P x

* if `∀ x, C x → ¬A x → P x` is provable, the dropped `A` is harmless: **R ⇔ L** (certified);
* if `C g ∧ ¬A g ∧ ¬P g` for a concrete `g`, **L is false** (certified counterexample, located by `¬A`);
* if `∀ x, C x → A x` is provable, the gap is empty: **R ⇔ L** (ProofScope's current redundancy check);
* otherwise the certified content is the direction `L ⇒ R` plus an explicit, unresolved gap.

**H19A:** on independently labelled, authentic pairs, gap certification yields more correct certified
directional verdicts than (i) the best competitor's certified output and (ii) the same refutation
budget spent *without* the gap guidance, with zero unsound outputs.

## Data (frozen before any run)

* **Primary:** ProofNet original (`data/proofnet/proofnet-4.28.jsonl`) vs ProofNet-Verified corrected
  (`data/proofnet-verified-latest.jsonl`), `marcusm117/ProofNet-Verified@b7ca411`, Apache-2.0; labels from
  `error_taxonomy/proofnet/results.jsonl` (faithfulness: faithful / stronger / weaker / incomparable;
  provability; error type). Labels are LLM-produced with human review (An, Min, Si, Bastani, NeurIPS 2026
  D&B); every corrected statement has a Lean proof and every false original has a Lean disproof in the
  authors' ground-truth archive.
* **Held-out:** the same pipeline's ProofNet# vs ProofNet-Verified labels (`error_taxonomy/proofnet#/`).
* Text-sized population (computed 2026-11-11): 366 matched pairs; 152 identical; 60 differ only in
  hypotheses (32 stronger, 13 weaker, 9 incomparable, 3 faithful, 3 ambiguous); 21 of those are
  missing-premise errors with a false original.
* Contamination note: ProofNet originals are the ProofNetVerif references used in SOTA-18 (statements
  seen, these pairs and labels not).

## Systems and conditions

| Condition | What |
|---|---|
| G | apply-the-other-statement + portfolio (SOTA-19 pilot A0), both directions |
| G + D | G plus **unguided** refutation of each side: small-instance enumeration over all binders, `decide` / `norm_num` / `simp` (same budget as GAP) |
| G + GAP | G plus gap certification above: redundancy-for-P on the gap, and refutation with instances drawn from `¬A` |
| SemantEq | v1.4.0, native, `--timeout 300` (one-direction verdicts count as directional evidence) |
| BEq+ | native v4.8.0 where the statements elaborate; else reported non-elaborating |
| Lean Disprove (lean4-skills) | if runnable without an LLM agent; otherwise documented as not run |

Input layer (prerequisite, `Months 1–3` item): a Lean metaprogram elaborates both statements once,
telescopes them with `forallTelescope`, aligns binders by type (`isDefEq`, instance-aware), and emits
gap obligations as `Expr`s. Universe parameters are kept as level parameters. Any elaboration error or
`sorry` aborts the pair (fail closed). No printed-text round trip.

## Metrics (fixed before the run)

Per pair, the certified facts are mapped to a direction: `EQUIV` (both implications), `R⇒L only`,
`L⇒R only`, `L false`, `R false`, or nothing. Against the gold label:

* **correct certified direction** = EQUIV on `faithful`; the right single implication on `stronger` /
  `weaker`; a refutation on a pair whose gold provability is `false`;
* **wrong** = any certified fact contradicting the label (e.g. EQUIV on `stronger`), or a refutation of a
  side whose gold provability is `true` (that would be unsound or a label error, and is audited by hand);
* denominators: all 366 pairs, the 214 non-identical pairs, and the 60 hypothesis-only pairs.

## Success condition and kill condition

* **Success:** on the 214 non-identical pairs, G + GAP has (a) zero unsound outputs, (b) at least 20
  correct certified directional verdicts that SemantEq's certified output lacks, and (c) at least 1.5×
  the certified refutations of G + D at equal budget, **and** the same ordering holds on the held-out
  ProofNet# labels.
* **Kill:** G + GAP adds fewer than 5 correct certified verdicts over G + D, or fewer than 10 over
  SemantEq, on the primary set. The gap idea is then not worth a research program.
* Everything in between: report, do not claim an advantage.

## Deliverables

`experiments/sota19a/` with the frozen manifest, the metaprogram, runners, per-pair records,
`SUMMARY.md`; regression tests showing SOTA-18 finding F1 cannot recur (`Type u_1` pairs, `sorry`
extraction → abstain); one CI workflow that reproduces everything on GitHub-hosted runners.
