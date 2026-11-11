# SOTA-18 pre-registration: competitive evaluation of ProofScope

Research director: Caleb J. Westfall. Written by Claude (Anthropic) on 2026-11-11, **before** any case
was selected, before any tool was run on any case, and before any label of a selected case was read.
Committed to `research/sota18-independent-evaluation`; its git commit time is the registration time.
Any later change to this file is listed in section 10 with its reason.

## 0. Exposure declaration

Before writing this file the author had seen: the first ~20 lines of SemantEq's
`test/pnv_test_adjudicated_labels.jsonl` (ids and `correct` flags), the first record of each EPLA split,
SemantEq's published aggregate numbers, the SOTA-1 aggregate EPLA label counts (1,096 positive,
151 negative), and the v0.6 ProofScope/SemantEq comparison on ProofScope's own 208 pairs. No ProofScope
output on any public pair has ever been seen.

## 1. Systems

| System | Version evaluated | Native environment | Role |
|---|---|---|---|
| ProofScope | `v1.2-review` @ `b0519f8` (v1.3 + SOTA-16), Mathlib pipeline `adelta12` + `cmcd_v10`; engine hashes in `ENGINE_HASHES.txt` | Lean 4.34.1, Mathlib `v4.34.1` (`d13f23b`) | system under test |
| ProofScope SOTA-17 `multiocc` | PR #7 head `4bdd369` | none (Nat claim grammar) | fragment-entry count only (no Lean run): its grammar cannot express Mathlib statements, and this is measured, not assumed |
| SemantEq | `hlxr89/SemantEq@f92767000e14` (v1.4.0) | Lean v4.30.0-rc1 + its pinned Mathlib | primary competitor, run |
| BEq+ | `augustepoiroux/LeanInteract@768e18ebcb5c`, `examples/beq_plus.py`, unmodified | Lean v4.8.0 + Mathlib via `TempRequireProject`, as in upstream's own ProofNetVerif driver | primary competitor, run |
| ACE / SAE | arXiv 2610.25018 v3 | no code released | published numbers only, context |
| ShadowBench SA-PASS, FormalAlign, LeanScorer (Mathesis), ASSESS/TransTED | see `competitors.json` | different task or not runnable | not run; reasons recorded |

No system is moved off its native toolchain. A pair that does not elaborate in a system's native
environment is `NON_ELABORATING` for that system: counted in the denominator, never as a verdict.

## 2. Data

* **PNV**: ProofNetVerif (`PAug/ProofNetVerif`, Hugging Face), **test** split, all rows, as downloaded on
  the runner; the dataset revision (commit sha) and card license are recorded by `make_selection.py`.
  Gold label **G1** = the published `correct` field (human labels, Poiroux et al. 2025). Gold label
  **G2** = SemantEq's adjudicated label (`pnv_test_adjudicated_labels.jsonl` at the pinned commit) where
  present. G1 is authored by the BEq+ authors and G2 by the SemantEq authors: PNV is *vendor-home* for
  both competitors and neutral for ProofScope. This is stated with every PNV number.
* **EPLA**: `XiaoyangLiu-sjtu/ASSESS@bc7933547d8a`, `benchmark/EPLA-*.json`, one row per
  (label, prediction) sub-question with `compiler_check == "success"`. Gold label **G3** =
  `likeness after transformation`. Neutral for all three systems run here (vendor-home for ASSESS, not run).

## 3. Tracks and selection (all done by `make_selection.py` on the runner, text only)

* **Track A** (unfiltered): 200 PNV test rows drawn uniformly without replacement with
  `random.Random(20261118)` from all rows, plus 100 EPLA rows drawn the same way with seed 20261119.
  No filtering of any kind.
* **Track B** (capability-relevant, chosen by text only, from all PNV test rows and all EPLA rows):
  a pair qualifies when its two declarations, after whitespace normalisation, satisfy either
  * **B1 assumption drift**: the conclusions (text after the first `:` at bracket depth 0 following
    the declaration name; see amendment 1) are identical and the binder lists differ; or
  * **B2 single-token conclusion drift**: the binder lists are identical and the conclusions differ in
    exactly one token, that token being a relation (`< ≤ > ≥ = ≠ ∣`), a quantifier (`∀ ∃ ∃!`), a
    connective (`∧ ∨ → ↔ ¬`) or a numeral.
  All qualifying pairs are used if there are at most 200; otherwise a seeded sample (20261120) of 200.
  If fewer than 30 qualify, the scarcity is reported and no padding is done.
* **Track C** (synthetic, optional, diagnostic only): never pooled with A or B.

Case ids, gold labels and dataset hashes are written to `frozen/manifest.json` and committed before any
system is run on any selected case.

## 4. Tasks and semantics

Let R and L be the closed propositions of the reference and candidate declarations in their headers.

* **Concrete entailment** R ⇒ L: a proof of `R → L` in Lean with the actual Mathlib meanings.
* **Abstraction-relative entailment** (ProofScope's ClaimDelta/CMCD): for every interpretation of the
  shared opaque symbols, R_A ⇒ L_A. It implies concrete entailment (specialise to the actual symbols).
  An abstraction-relative **separation** is a model of the *abstracted* statements; it is **not** a
  counterexample to R or L and is never counted as a concrete inequivalence.
* **Concrete inequivalence certificate**: a Lean proof of ¬(R ↔ L), or of ¬L together with a proof of R.
  A proof of ¬L alone ("the candidate is false") is a *conditional* inequivalence: valid if R is true.
* **Faithfulness** (the question PNV and EPLA labels answer): the candidate formalizes the same
  mathematical statement. Two true but different theorems are logically equivalent and unfaithful.

**T1 (shared binary task, scored for every system):** is the candidate faithful to the reference?
Gold G1 / G2 / G3. Each system's output is mapped to `EQUIV`, `NONEQUIV`, `ABSTAIN`, or an
infrastructure outcome (`NON_ELABORATING`, `UNSUPPORTED_INPUT`, `TIMEOUT`, `ERROR`). Two readings,
both reported, never merged:

* **certified reading**: `EQUIV` / `NONEQUIV` only if backed by a machine-checked artefact for that claim;
* **native reading**: each tool's own accept/reject as its authors score it (abstentions become
  `NONEQUIV` for SemantEq and BEq+, as in their papers).

Mapping (fixed now):

| System | EQUIV (certified) | NONEQUIV (certified) | everything else |
|---|---|---|---|
| ProofScope | `ASSUMPTION_EQUIVALENT`, `IDENTICAL`, `SCHEMA_EQUIVALENT`, `EQUIVALENT_BY_LAWS` (kernel certificates); `NO_ASSUMPTION_DELTA` (structural, reported in its own column) | `LEAN_WEAKER_BY_ASSUMPTION`, `LEAN_STRONGER_BY_ASSUMPTION`, `ASSUMPTION_INCOMPARABLE`, `REFERENCE_NEEDS_ASSUMPTION`, `LEAN_CLAIM_FALSE`, `CLAIM_LEAN_WEAKER`, `CLAIM_LEAN_STRONGER`, `CLAIM_INCOMPARABLE` | ABSTAIN (incl. `BOTH_CLAIMS_FALSE`, `CONCLUSION_ONLY_CHANGE`, `NO_SHARED_SYMBOLS`, `INCONCLUSIVE*`) |
| SemantEq | `ExactMatch`, `DefEq`, `EquivalentRestricted` | none (it does not certify a difference) | ABSTAIN; `Timeout` → TIMEOUT; `*CompileError` → NON_ELABORATING |
| BEq+ | `True` | none | ABSTAIN |

ProofScope's NONEQUIV verdicts are schema- or assumption-level differences: they are admissible for
**faithfulness** (T1) and are **never** counted as logical inequivalence. For the logical task they are
reported only in T3.

ProofScope runs both engines on every pair. Combination: if exactly one engine is decisive, its verdict
is used; if both are decisive and agree in T1 class, that class; if they disagree, the pair is
`INCONSISTENT` and counted as an **incorrect** decisive output.

**T2 (directional information, not scored against a gold label):** count the machine-checked one-way
facts each system produces (ProofScope `fwd`/`bwd` certificates; SemantEq `LikelyTooStrong/Weak`
proved direction). Each is a Lean theorem; the count is reported with a sample re-checked by hand.

**T3 (concrete inequivalence):** count pairs where any system produces a concrete or conditional
inequivalence certificate (ProofScope `LEAN_CLAIM_FALSE`, `BOTH_CLAIMS_FALSE`). Reported, not ranked.

## 5. Budgets and execution

* Same external wall-clock cap for every system: **900 s per pair**, all stages included (ProofScope's
  printing/round-trip adapter, SemantEq's compile, BEq+'s proofs). Setup (Mathlib download, builds,
  REPL start) is excluded and timed separately.
* Internal limits: ProofScope unchanged defaults; SemantEq `--timeout 300` (its default of 20 s caused
  101 timeouts in 175 pairs on a GitHub runner in v0.6, which would understate it); BEq+ upstream
  `DEFAULT_TIMEOUT = 60` per proof.
* Runners: GitHub-hosted `ubuntu-24.04` (4 vCPU, 16 GB). One evaluation process per job at a time.
* A timeout is never a verdict. A crash is `ERROR`. Nothing is retried except whole jobs lost to runner
  shutdown, which are re-run unchanged and reported.
* The ProofScope engine files are hash-checked against `ENGINE_HASHES.txt` in every job. No engine file
  is changed in response to any result. If a soundness bug is found, the headline evaluation stops at
  that point, the counterexample is documented, and any repaired engine is a separate condition.

## 6. Metrics (per system, per track, per gold label)

Total cases; eligible (elaborates natively); processed; correct decisive; incorrect decisive;
abstentions; infrastructure failures; timeouts; coverage = decisive / total; precision per decided
class (EQUIV, NONEQUIV); recall of each class where gold exists; median and 90th-percentile wall time.
ProofScope only: counts per native verdict, kernel-certified vs structural, certificates replayed,
cases correct-and-decisive where both competitors are not, and the converse.
Exact 95% Clopper–Pearson intervals on proportions; exact McNemar on paired correct-decisive outcomes.

## 7. Decision gate (fixed now, applied mechanically)

Let `U_A` = ProofScope's correct certified decisive outputs on Track A under G1 / 300 (EPLA under G3),
`U_B` = the same on Track B, `P_N` = precision of ProofScope's NONEQUIV under G1/G3 (pooled A ∪ B),
`X` = number of A ∪ B pairs where ProofScope is correct and certified-decisive and neither SemantEq nor
BEq+ is correct-and-decisive (native reading), and `S` = confirmed unsound ProofScope certificates.

* **CONTINUE** iff `S = 0`, `U_A ≥ 10 %`, `U_B ≥ 25 %`, `P_N ≥ 0.90` (with at least 10 NONEQUIV outputs)
  and `X ≥ 5`.
* **STOP** iff `U_A < 2 %` and `U_B < 10 %` and `X = 0`, **and** no single failure category explains at
  least half of ProofScope's non-decisive Track A outcomes in a way that one named architectural change
  would address.
* **PIVOT** otherwise; the pivot is the change indicated by the dominant failure category.

`S > 0` blocks CONTINUE regardless of the other numbers.

## 8. Adversarial review checklist (executed during the run)

Unsound certificates; adapter round-trip failures; wrong reference binding (sides swapped);
abstraction mismatch (schema separation counted as concrete); existential witnesses; direction labels;
statements already known true; synthesized countermodels misused; typeclass and implicit binders;
printed versus elaborated statement mismatch. Every confirmed issue gets a minimal counterexample.

## 9. What would contradict expectations

Expected before running (stated so it can be checked): ProofScope coverage on Track A below 5 %, mostly
`CONCLUSION_ONLY_CHANGE`, `INCONCLUSIVE` or `NO_SHARED_SYMBOLS`; a measurable number of
`NON_ELABORATING` pairs on Lean 4.34.1 because PNV statements were written for Lean 4.8-era Mathlib;
SemantEq precision near 1.0 with recall near half; BEq+ recall similar with a few false accepts.

## 10. Amendments

1. (2026-11-11, before any data was loaded) Section 3, B1: "last `:` at bracket depth 0" replaced by
   "first `:` at bracket depth 0 following the declaration name". Reason: conclusions such as
   `∀ x : ℝ, P x` contain a depth-0 colon, so the last-colon rule would split inside the conclusion.
   Found while implementing `make_selection.py`.
