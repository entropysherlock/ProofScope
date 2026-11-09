# SOTA-3: certified non-equivalence (CJCS), process-tree budgets, and a timeout audit

ProofScope by Caleb J. Westfall. Prepared with Claude (Anthropic), 2026-11-09.
Branch: `research/sota3-cjcs`, created from `competitor-benchmark-audit` @ `5769208`.

**Status.** Everything in this document was run locally in core Lean 4.34.1 unless it is marked PENDING.
Mathlib runs need the workflow `sota3-research.yml`, because Mathlib cannot be loaded in this sandbox.
No benchmark claim is made: all suites here are developer-written development data.

## 1. Why the negative fixture timed out (Challenge A)

The fixture is `∀ x : ℝ, √(x²) = x` against `∀ x : ℝ, 0 ≤ x → √(x²) = x`. The reference is false (x = −1)
and the formalization is true (`Real.sqrt_sq`). The two statements are therefore logically different, and
a certificate of that must contain a **proof of the formalization** (`CJCS.difference_needs_a_proof`).

| System | Cause | Classification | Evidence |
|---|---|---|---|
| BEq+ (3.654 s overshoot) | LeanInteract starts its Lean REPL with `start_new_session=True` (`lean_interact/server.py`). SOTA-2's limiter tracked the session only, so the REPL escaped. Its CPU was counted only when the driver reaped it, all in one step, and it was not killed at the limit. | (5)/(6): an accounting and subprocess interaction, **in our harness** | Reproduced. With the SOTA-2 limiter, a session-escaping child doing 2 s of work under a 1 s limit ran to completion (overshoot 1.019 s). Fixed (§4). |
| BEq+ (TIMEOUT itself) | BEq+ certifies only equivalence. A non-equivalent pair ends in `False` only after its proof search (`exact?`, `apply`, `convert` up to depth 4, per-proof timeout 60 s) is exhausted. | (1): intrinsic to the method | Its upstream code; 72 CPU-s for a native `False` in run 42689439284 |
| SemantEq | It searches for audited proofs of both directions. For a non-equivalent pair it can only finish with a "Likely…" verdict or its own 20 s wall `Timeout`, and statement compilation is not interrupted by that timer (README). | (1): intrinsic, since it has no certified negatives | README at the pin |
| ProofScope v1.2 | **Hypothesis**, measured in core Lean, not yet with Mathlib. The pipeline for an assumption pair starts 6 Lean processes, and 5 of them load the full import environment: extract, certify probe, certify compile, `leanchecker` replay, witness read. The calibration pair, which only extracts, pays for one load. The failing redundancy obligation (`∀ x, 0 ≤ x`) also runs the whole Mathlib portfolio (`nlinarith`, `aesop`, …) at `maxHeartbeats 4000000` before the countermodel is used. | (2) avoidable initialization, plus (4) search order | Core trace (`bench/diagnose.py`): 6 processes, 4.89 CPU-s, import baseline 0.27 s. **PENDING:** the Mathlib trace (`diagnose` job, 2 repeats, v1.2 and CJCS) |

**One fixture does not show an algorithmic weakness.** The v1.2 diagnosis is a hypothesis until the
Mathlib trace confirms it.

## 2. CJCS: definition

For closed statements R (reference) and L (formalization):

1. **Telescopes (1 Lean process).** The frozen v1.1 extractor runs on (R, R), (L, L) and (R, L) in one
   file. Each side gets a canonical form `∀ m, H m → C m` and a certified link `X ↔ canonical`.
2. **Refute first (1 process, search only).** For each side, CJCS searches for `∃ m, ¬C m ∧ H m` over the
   frozen v1.2 carrier registry and point pools. It adds the statements' numerals and their successors,
   plus quantifier-exchange refutations (`∃y ∀x` is instantiated at its own witness or its successor).
   A witness gives `false_X : ¬ X`.
3. **Prove only what was not refuted (final certification, with the frozen `certify` gate).**
   - `true_Y` for each unrefuted side: the v1.2 sufficiency portfolio, existential introduction from
     in-scope terms, then `exact?`.
   - Also attempted: `equiv_defeq` (`Iff.rfl`), the `diff`/`equiv` combinations, and the drift-region
     witnesses.
   - Every alternative runs under `maxHeartbeats 200000`.
4. **Verdict:**
   - `CERTIFIED_LOGICAL_DIFFERENCE` (`diff_RL` or `diff_LR`), with a direction;
   - `CERTIFIED_LOGICAL_EQUIVALENCE` (definitional, both false, or both true);
   - `ABSTAIN` otherwise. A failed search is never a negative.
5. **Explanation.** Certified region witnesses over the aligned telescope:
   - `ref_excluded`: the reference fails at a point the formalization's own assumption excludes;
   - `lean_excluded`;
   - `conclusion_lean_stronger` and `conclusion_ref_stronger`;
   - `joint`.

   Witness values are read back from the kernel-checked proof terms.

Every certificate passes the unchanged gate: clean recompile, standard axioms only, and a `leanchecker`
replay.

## 3. Theory (`research/cjcs/CJCS.lean`)

The file has 15 theorems: 9 use no axioms, 5 use only the standard classical axioms (propext,
Classical.choice, Quot.sound), and 1 uses propext and Quot.sound. A fresh replay exits 0.

| Theorem | Statement |
|---|---|
| `cjcs_sound`, `cjcs_sound'` | A refutation of one side plus a proof of the other gives `¬ (X ↔ Y)`. |
| `difference_needs_a_proof` | `¬ (X ↔ Y) → X ∨ Y`. **Certifying a logical difference is at least as hard as proving one of the statements.** A pure countermodel search or a pure equivalence prover cannot certify a difference on its own. This explains why all three systems timed out on the negative fixture, and why CJCS needs two halves. |
| `nonequiv_iff` | `¬ (X ↔ Y) ↔ (X ∧ ¬Y) ∨ (Y ∧ ¬X)`: the certificate forms are complete. |
| `both_false_equiv`, `both_true_equiv`, `vacuous_logical_equiv` | These equivalences are logical only. A vacuous reference is logically equivalent to every true formalization. |
| `disagreement_partition`, `regions_disjoint` | A point where the reference's instance holds and the formalization's fails lies in **exactly one** of `lean_excluded` and `conclusion_lean_stronger`. The region explanation is complete and does not overlap. |
| `region_refutes_lean`, `ref_excluded_refutes_ref` | Each region witness refutes the corresponding statement. |
| `joint_failure_iff`, `joint_disjoint_harmless` | If each single change is harmless on its own, the combined statement fails **exactly** on the joint region `H ∧ A ∧ ¬D ∧ P ∧ ¬Q`, and is harmless when that region is empty. This is the precise form of "individually harmless changes that are jointly consequential". |
| `joint_example` | Instance: `n ≤ 5 → n ≤ 10` changed to `n ≤ 7 → n ≤ 6` (each single change is harmless; the pair is not). |

**Honest assessment.** These are elementary logic. Their value is that they **specify** a sound and
complete explanation scheme and justify the algorithm's design. They are not a deep mathematical result.

## 4. Budget audit (Challenge D)

| Mechanism | SOTA-2 | SOTA-3 |
|---|---|---|
| Tree membership | Session (`getsid`) | Ancestry: parent links from the first poll, identity (pid, starttime); orphans adopted through the subreaper |
| Session escape (`setsid`) | CPU counted only at reaping; not killed | Counted live and killed |
| Kill | `killpg` | SIGKILL to every tracked pid, plus `killpg` |
| Overshoot field | Recorded | Recorded, plus `enforcement_ok` against a preregistered tolerance of 0.5 s (amendment A9) |
| Mean poll cost | not recorded | Recorded per run (`mean_poll_ms`; ≈2.5–3.3 ms locally, 2 cores) |

Adversarial measurements with a 2 s limit (1.5 s where marked):

| Case | Status | Tree CPU | Overshoot |
|---|---|---|---|
| child in a new session | TIMEOUT_CPU | 2.036 | 0.036 |
| setsid + double fork grandchild | TIMEOUT_CPU | 2.037 | 0.037 |
| 8 busy children (2 cores) | TIMEOUT_CPU | 2.089 | 0.089 |
| session child that finishes, parent waits | TIMEOUT_CPU | 2.043 | 0.043 |
| SOTA-2 limiter, session child doing 2 s of work, 1 s limit | TIMEOUT_CPU | 2.019 | **1.019** |

After the tests, no test process was still running.

**"Compliant = false" on the three negative cases is correct by definition.** A run that exhausts the
budget is not a compliant completion. What was wrong was the size of BEq+'s overshoot, which was our
limiter's fault, not BEq+'s.

**Residual uncertainty:**
- **CPU charged between two polls:** at most about the number of busy cores × 20 ms.
- **CPU of a child born and reaped within one poll interval:** it reaches its tracked parent's cutime, so
  it is counted, but late. This is bounded by that child's lifetime.
- **Startup allowance:** measured from the calibration pair, so it only covers the processes that pair
  starts. A tool that starts more processes for other pairs pays for them. That is intended (it is the
  tool's design), and the trace makes it visible.

## 5. Results

| Suite | System | Result |
|---|---|---|
| CJCS core development (10 pairs; used during development) | CJCS | 10/10 after two fixes (§6) |
| CJCS core held-out (14 pairs; hash `bb8628b6…` recorded before the first run) | CJCS | **11/14 exact, 0 must-not-be violations, 3 ABSTAIN** |
| Core analogue of the 3 availability fixtures | CJCS | kernel-certified equivalence ×2 (definitional); certified logical difference ×1 (`ref_excluded`), 6.2 CPU-s, 10 processes |
| Core analogue of the 3 availability fixtures | frozen v1.2 | structural positive ×2; fidelity negative ×1 |
| Mathlib development comparison (27 cases: 3 fixtures + 24 pairs; provisional developer labels) | v1.2, CJCS, SemantEq, BEq+ | **PENDING** (`sota3-research.yml`) |
| Mathlib negative fixture | CJCS | **PENDING** |

**Held-out abstentions, recorded and not tuned on (the set is now exposed):**

| Case | Cause |
|---|---|
| h01 | No core proof of `∀ x : ℤ, x * x ≥ 0` within the heartbeat bound |
| h04 | No List carrier in the registry |
| h12 | Refuting `∃ k, n = 2 * k` under a binder needs the quantifier refuter inside the witness search |

**The negative fixture itself is PENDING.** CJCS will certify it if `exact?` (or the portfolio) proves
`Real.sqrt_sq` within the bound and the extra environment loads fit the 20 s tier. If either fails, the
answer is ABSTAIN or TIMEOUT, never an unsupported negative.

## 6. Failed attempts and corrections (preserved)

| Issue | What happened | Outcome |
|---|---|---|
| Dependency bug (fixed) | `false_X` was kept when `wit_X` had failed: Lean adds an erroring declaration with a `sorry` body, so a dependent lemma still elaborates. Dependencies are now explicit. | Fixed |
| Missing boundary points (fixed) | c08 needed n = 7. Literal-derived point pools were added, as the frozen engine already does. | Fixed |
| Quantifier exchange (fixed) | c05 needed refutation of `∃y ∀x` and proof of `∀x ∃y`. Generic diagonal and successor patterns were added. | Fixed |
| A claim I retracted | I first attributed a miss to a "closer defect" in frozen v1.2 (error recovery inside `first`). Isolated tests showed that every one of those forms fails cleanly. The real cause was the missing pool points. | **No v1.2 defect exists** |

## 7. Novelty

| Prior work | What it does | Overlap with CJCS |
|---|---|---|
| FormalRx-CC (ICML 2026) | LLM-produced, Lean-checkable witnesses that separate a candidate from the intended formalization | The closest prior art |
| Faults in Our Formal Benchmarking (2026); MechGeo (2026) | Counterexample and vacuity checkers for formal statements | Automated counterexamples |
| Lean's Plausible (formerly slim_check) | Property-based testing that finds counterexamples automatically | Finds counterexamples, but does not certify `¬ (R ↔ L)` and does not prove the other side |
| SemantEq, BEq/BEq+, ASSESS | Equivalence side only | None on certified negatives |

Not novel:
- countermodels for formal statements;
- the logic in `CJCS.lean`, which is elementary and folklore-level.

Possibly distinctive (**not established**, since there is no comparison and no independent data):
- LLM-free synthesis of kernel-checked `¬ (R ↔ L)` certificates that pair a refutation with a proof of the
  other side;
- refute-first pruning, justified by `difference_needs_a_proof`;
- a complete, non-overlapping drift-region explanation with certified witnesses (`disagreement_partition`,
  `joint_failure_iff`).

**Level reached:** Level 2 **on core Lean only**: certified non-equivalence in a restricted class
(decidable or omega-closable domains, registry carriers). Level 2 with Mathlib is PENDING. Levels 3 and 4
are not reached.

## 8. Recommendation: **continue, revised**

1. Measure first (the `diagnose` job). If the extra environment loads dominate, move CJCS stages 1–3 into
   one Lean process with a meta-program driver, keeping a separate `leanchecker` replay.
2. Extend the refuters before any blind run: a List carrier, and quantifier refutation inside witness
   search. Develop these on **new** development data, not the exposed held-out set.
3. Only then freeze CJCS v0.1 and evaluate it on the sealed SOTA-1 holdout with independent labels.
   Nothing in this document is evidence of superiority.
