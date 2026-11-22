# SOTA-1: the competitor benchmark, the research candidate, and where things stand

ProofScope by Caleb J. Westfall. Prepared with Claude (Anthropic), 2026-11-09.

**Status: infrastructure built and tested locally; no comparative result exists.** No benchmark has run,
no gold labels exist, and no claim of superiority is made. This document is the executable companion of
`docs/competitor_benchmark_protocol.md`; amendments proposed here (A1–A6) must be accepted and frozen
before the blind corpus is sealed.

## 1. Competitor availability matrix

Evidence levels follow the protocol's gate: SOURCE_ONLY < INSTALLABLE < SMOKE_PASSED < BENCHMARK_PASSED.

| System | Pinned source | License | Native environment | Native evaluation entry point (verified in source) | Level reached | Evidence |
|---|---|---|---|---|---|---|
| ProofScope v1.2 | this repo, V12_FREEZE.txt (hashes re-verified on this branch) | repo license | Lean 4.34.1 + Mathlib `d13f23b` | `python -m proofscope.v12 run` | BENCHMARK_PASSED on its own 80-case split only (developer-authored, not independent) | v1.2 Mathlib run (85 rows, 0 must-not-be violations) |
| SemantEq | `hlxr89/SemantEq@f92767000e14` | Apache-2.0 | Lean v4.30.0-rc1 + its own Mathlib pin (~9 GB RAM per process with `import Mathlib`) | `lake exe semanteq --raw [--timeout N] pairs.jsonl out.jsonl` | SMOKE_PASSED (one identical pair; run 42682197696) | competitor-smoke.yml |
| BEq+ | `augustepoiroux/LeanInteract@768e18ebcb5c` `examples/beq_plus.py` | MIT | LeanInteract REPL, `TempRequireProject(lean_version="v4.8.0", require="mathlib")` as in upstream's own ProofNetVerif driver | `beq_plus(f1, f2, src_header, server, timeout_per_proof)` | INSTALLABLE (import + callable only; **no pair evaluated yet**) | competitor-smoke.yml |
| ASSESS / TransTED (new) | `XiaoyangLiu-sjtu/ASSESS@bc7933547d8a` | Apache-2.0 | Lean REPL; paths hard-coded in `main.py`, `transted.py`, `src/verifier.py` | `python main.py --benchmark ... --ted_similarity`, `transted.py` | SOURCE_ONLY. Its TransTED output is a **similarity score**, not a certified verdict: a separate, non-certified track if added | this document |
| ACE / SAE (arXiv 2610.25018) | not located | unknown | unknown | unknown | UNAVAILABLE (`NOT_PUBLICLY_RUNNABLE_VERIFIED`) | searches on 2026-11-09 found no release |
| FormalRx-CC (ICML 2026) | no code link on the conference page | unknown | LLM-generated witnesses | n/a | UNAVAILABLE; closest prior art (see §7) | icml.cc/virtual/2026/82532 |
| MachineChecked (track C) | `cgarryZA/MachineChecked@47276b53` | Apache-2.0 | Lean v4.32.0 (toy), TeX Live, Poppler | `machinechecked check --json` | SMOKE_PASSED (native toy-paper audit, run 42682197696) | competitor-smoke.yml |
| PaperFormalizer (track C) | `Jiyuan-Tan/PaperFormalizer@5e1f269b` | MIT-derived responsible-use license | Node 22; external model calls; human checkpoints | its agentic pipeline | INSTALLABLE (typecheck only) | competitor-smoke.yml |

The smoke run proved that the four tools install and start. It did not show that any of them evaluates
a mathematical pair correctly, and the four checks are not equivalent in depth.

## 2. The runner (built; unit-tested; not yet run on GitHub)

Code is in `bench/` and the workflow is `.github/workflows/competitor-benchmark.yml`.

| Part | What it does |
|---|---|
| `canonical.py` | Defines the case format. A case is two complete Lean declarations with their headers, exactly as published. Label-like fields are rejected in case records. Also provides normalization and near-duplicate grouping. |
| `ingest.py` | Builds the candidate pool from EPLA (pinned ASSESS commit) and ProofNetVerif (Hugging Face, on the runner). Source labels go to a separate file and are never treated as gold. |
| `seal.py` | Builds the custodian's split: the pilot and primary are group-disjoint, case ids are opaque, and the labels are covered by a salted SHA-256 commitment that can be verified later (`seal verify`). |
| `limits.py` | Applies a hard external CPU limit (`prlimit`) to every tool alike, plus a resident-memory watchdog over the whole process group. Per-child CPU and peak RSS come from `wait4`. A process killed at the limit is a TIMEOUT, never an abstention. |
| `adapters/` | Adapters for ProofScope, SemantEq and BEq+; details below. |
| `outcomes.py` | Maps each tool's verdicts to the shared outcomes, with a pre-registered certified (3-way) reading and native (binary) reading. Infrastructure outcomes are kept as they are. |
| `score.py` | Computes the protocol's metrics per track and per reading, with exact Clopper–Pearson intervals, a group-clustered bootstrap, exact McNemar tests with Holm correction, a disputed-case sensitivity analysis, and per-source breakdowns. |

**Adapters:**
- **ProofScope:** ProofScope compares two closed propositions, so the adapter prints each declaration's
  type outside the header's `open`s. It then proves the printed type equal to the original by
  `with_reducible rfl`, which is a meaning-preservation certificate for the adapter (A2).
- **SemantEq:** uses SemantEq's own pair format, one pair per process.
- **BEq+:** runs the unmodified upstream `beq_plus`, with the two headers merged (A4).

**Tested locally (core Lean 4.34.1, no Mathlib):**
- 11 unit tests pass.
- The statistics match reference values: Clopper–Pearson (5/10) = (0.1871, 0.8129), (0/30) upper bound = 0.1157, and McNemar exact (1, 9) = 0.02148.
- The limiter correctly classifies CPU timeouts, OOM and wall timeouts.
- The ProofScope adapter ran end to end on 5 core-Lean plumbing pairs: the printed propositions round-tripped and the frozen engine returned verdicts.

None of this is a benchmark result.

## 3. Frozen manifests

Pins are in the workflow `env:` block: Mathlib, SemantEq, LeanInteract and ASSESS commits, plus the
ProofScope freeze check. Each run writes a `manifest*.json` with:
- the CPU limit, startup allowance and memory cap;
- the SHA-256 of the cases file;
- host, CPU, Python version and the `prlimit` path;
- the cache state.

**Toolchain mismatch.** The three systems natively use Lean 4.34.1, Lean v4.30.0-rc1 and Lean v4.8.0,
each with a different Mathlib. Per the protocol, no tool is forced onto another's version. A case that
does not elaborate in a tool's native environment is NON_ELABORATING for that tool. It is reported, and
it is not counted as a wrong answer.

## 4. Corpus specification and contamination controls

These are facts measured on the pinned EPLA data.

**EPLA** (ASSESS@bc79335, Apache-2.0):
- 1,247 (reference, prediction) pairs: 831 miniF2F and 416 ProofNet.
- Only 430 distinct reference statements.
- 409 near-duplicate groups at Jaccard 0.9.
- 77 exact duplicate pairs.
- Source labels ("likeness after transformation"): 1,096 positive and 151 negative.

**Consequence: EPLA alone cannot supply a balanced 240/240 primary sample by whole groups.** On a test
seal (seed 7), the 120 negative slots reached only 40/120. The seal reports the shortfall instead of
padding it.

**ProofNetVerif:**
- It is the home benchmark of BEq+ (Poiroux et al.).
- SemantEq ships its own re-adjudicated labels for the 1,303-pair test split, plus its own verdicts
  (`test/pnv_test_adjudicated_labels.jsonl`).
- It is therefore **vendor-home for two competitors**. Results on it are reported as a vendor-home
  stratum and are never pooled with independent slices.

**EPLA** is likewise vendor-home for ASSESS/TransTED.

**Exposure declaration.** While building this infrastructure, the developer:
- printed EPLA's first record of each split;
- computed EPLA's aggregate label counts;
- read SemantEq's ProofNetVerif label format.

No other individual labels were examined. All public slices are, in any case, unsealed by nature.

**Primary blind holdout (A3).** The only slice that can support an independence claim is new pairs:
- curated by someone who is neither a ProofScope nor a competitor developer;
- drawn from Lean projects and papers not used by any tool;
- sealed with `bench.seal` before any run.

Target size and balance follow the protocol (480 cases, 240/240, at least 25% real-paper pairs).
Grouping uses three relations: the source theorem group, candidate near-duplicates, and reference
near-duplicates. The pilot (48) and primary splits share no group.

## 5. Independent adjudication

See `docs/sota1/ADJUDICATION.md`: the reviewer packet, the record schema, the dispute rule, and how to
release labels against the commitment. **Two blinded reviewers and a third arbiter are not available to
this project today.** Until they are, any run is reported as PROVISIONAL and never as independent.

## 6. Comparative report

No comparative result exists yet. What does exist:
- **Availability:** all four smoke jobs passed (run 42682197696).
- **Historical exploratory comparison:** the 208-pair ProofScope/SemantEq comparison
  (`docs/v0.6_competitor_result.md`). It is not blind, not matched and not evidence of superiority.
- **ProofScope's own 80-case Mathlib split:**
  - 61 certified decisive verdicts and 60 exact label matches;
  - 0 must-not-be violations (the protocol's unsound-verdict flag);
  - developer-authored, so it is not independent and not comparative.

**Known reasons ProofScope may score poorly on public slices:**
1. ProofScope certifies **logical** non-equivalence (Track A negative) only when one side is refuted
   **and** the other proved; v1.2 never proves a side in pair mode. Its Track A negatives are therefore
   almost all ABSTAIN.
2. Most autoformalization errors in EPLA/ProofNetVerif are conclusion changes. v1.2 answers
   CONCLUSION_ONLY_CHANGE (ABSTAIN) for these by design.
3. Many statements need carriers outside the registry: ℂ, filters, matrices, measure theory.
4. The adapter's round-trip check will refuse some statements whose printed form does not re-elaborate.
   These count as UNSUPPORTED_INPUT.

## 7. Novelty analysis (prior work checked 2026-11-09)

| Prior work | What it does | Overlap with ProofScope |
|---|---|---|
| BEq (Liu et al., ICLR 2025); BEq+ (Poiroux et al., EMNLP 2025) | Bidirectional proof search for equivalence | Positive (equivalence) direction only; no certified negatives |
| SemantEq (Li et al., Oct 2026) | Audited bidirectional equivalence finer than logical equivalence; a proof audit for LLM-written proofs | Positive direction only; one-direction results are labelled "Likely", not certified |
| ASSESS / TransTED (ICLR 2026) | Structural and semantic similarity; the EPLA benchmark | Scores, not certificates |
| FormalRx (ICML 2026) | A 28-category error taxonomy with localization, from a trained LLM | Diagnosis and localization, but not certified |
| **FormalRx-CC (Yang & Osorio, ICML 2026)** | Every misalignment diagnosis must carry a **Lean-checkable witness that separates the candidate from the intended formalization**, produced by LLMs and checked adversarially | **Closest prior art.** "Certified countermodels for non-equivalence" is therefore **not new as an idea** |
| The Faithfulness Gap / BPF (arXiv 2606.16541) | LLM probes; a "drift detection theorem" | Statistical rather than kernel-certified |
| Faults in Our Formal Benchmarking (arXiv 2606.29493); MechGeo (arXiv 2608.02295) | Counterexample and vacuity checkers that find defects in formal statements | Counterexample search for statement defects is established |

**What may still distinguish ProofScope (not established):**
- witnesses synthesized **without an LLM**, by structure-agnostic countermodel search, with a typed,
  assumption-level diagnosis (weaker / stronger / incomparable / needs-assumption / minimality);
- each verdict class tied to a Lean soundness theorem;
- linking certificates from the user's statements to the canonical form.

Whether this beats FormalRx-CC or the others on matched tasks is an empirical question, and it has not
been tested. **No novelty claim is made.**

## 8. Research candidate (Phase 6 material)

The candidate is `research/joint_drift/JointDrift.lean`: 7 theorems, 6 axiom-free and 1 using only
`propext` and `Quot.sound`. A fresh `leanchecker` replay passes locally.

| Theorem | Statement |
|---|---|
| `joint_entails` | `D → A` and `Q → P` on the region `C ∧ D` give `L → R`. The conclusion comparison is needed only where the reference's own assumptions hold. |
| `joint_refutes_ref`, `joint_refutes_lean` | Concrete refutations. |
| `certified_logical_difference` (and its symmetric form) | A proof of one side plus a refuting model of the other certifies `¬ (L ↔ R)`. This is a certified Track A negative, the outcome that proof-search-only checkers cannot produce. |
| `components_do_not_determine_joint` | The same per-part signature (an added restrictive assumption and a pointwise-stronger conclusion) occurs both with `L → R` and with `¬ (L → R)`. Deciding the direction from the parts separately is unsound, so the joint obligations are necessary. |
| `vacuous_reference_equiv_true` | A vacuous reference is logically equivalent to every true formalization. Track A equivalence never certifies fidelity. |

**Honest assessment.** These are elementary lemmas. Their value lies in specifying a sound decision
procedure and in a negative result that constrains any design; they are not a significant mathematical
result.

**Proof obligations for a v1.3 engine** (must be built on a separate development corpus, after the
baseline):
1. Implement the joint path: entailment by the portfolio, refutations by the countermodel registry, and
   certified Track A negatives by "sufficiency proof + refutation". Every verdict must be an instance of
   one of these theorems.
2. Freeze v1.3 and evaluate it on a **new** sealed holdout. Never reuse an exposed slice.
3. Run hostile tests for the `components_do_not_determine_joint` instances, vacuity, and mixed-region
   errors (conclusion compared outside `C ∧ D`).

## 9. Status classification

**Engineering result.**
- **Done:** the runner, adapters, scoring and statistics are implemented and tested, and the availability
  matrix is verified to the levels stated above.
- **Not done:** a new mathematical result of significance; any defensible state-of-the-art claim, which
  needs independent gold and a matched run, neither of which exists.

## 10. Protocol amendments proposed (freeze before sealing)

| Amendment | Proposal |
|---|---|
| A1 | The per-pair CPU limit is the tier plus the tool's startup allowance. The allowance is the median CPU on the calibration pair over three availability runs, frozen in the run manifest before the primary run. Startup is also reported separately. |
| A2 | ProofScope adapter: the printed propositions must pass `with_reducible rfl` against the original declaration. Failures count as UNSUPPORTED_INPUT. |
| A3 | Strata: vendor-home public slices (EPLA for ASSESS; ProofNetVerif for BEq+ and SemantEq) are reported separately. Only the new holdout is "primary blind". |
| A4 | BEq+ gets the de-duplicated union of the two headers as its single `src_header`. |
| A5 | ProofScope Track A mapping: schema-level separations count as ABSTAIN (they do not make the closed statements inequivalent). `NO_ASSUMPTION_DELTA` and `BOTH_CLAIMS_FALSE` count as EQUIV in Track A. `NO_ASSUMPTION_DELTA` rests on meta-level extraction (Lean's elaborated-expression comparison), not on a kernel certificate, and is reported as its own sub-count. |
| A6 | SemantEq `LikelyTooStrong` / `LikelyTooWeak` count as ABSTAIN in the certified reading and NONEQUIV in the native reading. |

## 11. Errata found during this mission

- **v1.2 theorem count.** `docs/v1.2_coverage.md` says CompositionV12 has "14 theorems (12 axiom-free)".
  The correct count is **13 theorems: 11 axiom-free and 2 standard-axiom**. ChatGPT's CI correction
  (`0824134`) is right. The frozen engine files on this branch match the delivered v1.2 byte for byte.
- **The PENDING v1.2 resolution report** in the same document was superseded by the GitHub run, which
  resolved m05, m09, m10, m12 and m13.

## 12. Blockers

| Blocker | Effect |
|---|---|
| No independent reviewers or custodian | Every run is PROVISIONAL |
| No GitHub write access from this session | Patch handed over |
| Hugging Face unreachable from the sandbox | ProofNetVerif is ingested on the runner |
| No Mathlib in the sandbox | No Mathlib-level adapter test here |
| ACE/SAE and FormalRx-CC code not released | Not benchmarked |
| Track C needs three independent papers and human time | Not started |

## 13. SOTA-2 repair (availability run 42689439284)

All three defects reproduced locally before any fix.

| Run 42689439284 result | Root cause | Fix |
|---|---|---|
| ProofScope 3/3 NON_ELABORATING | The workflow passes `--out runs`, so every generated file path was relative (`runs/work/...`). The adapter then started Lean with `cwd=` the work directory, and Lean reported `no such file or directory: runs/work/proofscope/t20/<case>/r0/ref_print.lean`. Nothing reached elaboration, so the label NON_ELABORATING was itself a misclassification. | Every path is absolute (`--out`, `--cases` and `--tool-dir` are resolved). A launch-time check returns LAUNCH_ERROR for a missing or relative input. A Lean failure is NON_ELABORATING only when its error lines fall inside the source declaration; otherwise it is ADAPTER_ERROR. |
| SemantEq 3/3 ERROR | The same relative path, handed to `lake exe semanteq`, which ran with `cwd=` the SemantEq checkout. | Same fix. The adapter also no longer overrides SemantEq's `--timeout`, so its documented default is restored. |
| BEq+ used 72.1 CPU-s at a 20 CPU-s tier | `prlimit --cpu` sets RLIMIT_CPU **per process**. The Lean REPL and other descendants each had their own 20 s. Reproduced: four busy children under a "2 s" limit used 8.04 CPU-s and were reported OK. Separately, the adapter set BEq+'s per-proof timeout to the tier (20 s) instead of upstream's `DEFAULT_TIMEOUT` (60 s). | See amendment A7 below. The BEq+ driver now uses upstream's `DEFAULT_TIMEOUT`. |
| CI green with zero usable evaluations | The collect job only counted records. | See amendment A8 below. |

**Amendment A7: budget semantics.** The budget binds the **whole process tree of one tool invocation**,
measured over a new session plus orphans: the runner is a child subreaper, so orphans return to it and
are counted.
- **Enforcement.** Every 20 ms, the runner sums utime + stime + cutime + cstime over the live session
  processes and kills the session at the limit. This is calibrated, not exact: the overshoot is recorded
  per record. Locally, the four-child test now stops at 2.074 CPU-s (overshoot 0.074 s).
- **Accounting.** `cpu_tree_s = max(wait4 of root + reaped orphans, peak polled sum)`, and peak RSS is
  summed over the tree.
- **Startup allowance.** In the availability phase it is **measured**: the median tree CPU of the
  calibration pair over 3 runs, under a 900 CPU-s measurement ceiling. These runs are never scored. For
  pilot and primary runs, the frozen value from that manifest is passed in.
- **Per record.** Each record stores `chargeable_cpu_s = cpu_tree_s - allowance` and `compliant`.
- **Uncharged conversion.** Adapter conversion (ProofScope's printing and round-trip check) runs under its
  own limit and is not charged.
- **Wall cap.** A wall cap is reported as TIMEOUT_WALL, never as a CPU limit.

**Amendment A8: fail closed.** Every record has an `evaluation_class`:
- EVALUATED_POSITIVE_KERNEL
- EVALUATED_POSITIVE_STRUCTURAL
- EVALUATED_NEGATIVE_LOGICAL
- EVALUATED_NEGATIVE_FIDELITY
- EVALUATED_ABSTAIN
- RESOURCE_EXHAUSTED
- INPUT_NOT_EVALUABLE
- NOT_EVALUATED_INFRA

`bench/gate.py` writes the availability report: infrastructure readiness, native initialization, valid
evaluations, kernel and structural positives, negatives, abstentions and resource exhaustion. Each
system's gate requires a valid, budget-compliant evaluation of **both** equivalent calibration fixtures.
No particular verdict is required. The non-equivalent fixture is reported but does not gate.

The collect job fails when any gate fails, and all evidence is uploaded first. Two upstream checks were
added:
- SemantEq reproduces its own manifest on two pairs from its recall suite.
- ProofScope runs its v1.2 tests and a Mathlib smoke file. (BEq+ already has its native REPL init check.)

**Expected and not fixable in the interoperability layer.** Frozen ProofScope v1.2 answers
`NO_ASSUMPTION_DELTA` for identical or alpha-renamed statements. That comparison is meta-level (Lean's
comparison of the elaborated telescopes) and comes with **no kernel certificate**, so it is classified
EVALUATED_POSITIVE_STRUCTURAL, not EVALUATED_POSITIVE_KERNEL. Producing a kernel certificate for this case
would be an engine change (v1.3 and a new freeze), not an adapter fix. SemantEq's `ExactMatch`/`DefEq` are
classified the same way, for symmetry.
