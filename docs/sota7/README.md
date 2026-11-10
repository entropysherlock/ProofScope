# WESTFALL PROOFSCOPE — SOTA-7 IMPLEMENTATION AND INDEPENDENT EVALUATION READINESS

Caleb J. Westfall · branch `research/sota7-independent-evaluation` from `26eee2bd36b29c895c3f783f33b97a48e4e816a8`.

**Evidence labels:**
- [T] verified by software tests (executed);
- [K] kernel verified;
- [E] observed experimentally;
- [I] independently adjudicated (**nothing**);
- [P] proposed but not implemented;
- [N] not tested;
- [F] failed.

## 1. Executive verdict
**Infrastructure validated: yes [T][E]. Independent mathematical evaluation completed: NO (NOT RUN).**

The harness goes: external cases → frozen manifest → blinded, sandboxed execution of the frozen SOTA-6
engines → sealed records → independent certificate replay → scoring against withheld labels → report.
It works end to end on 11 synthetic development cases.

Acceptance criteria 1–15 (`LIMITATIONS.md`, section 17 of the brief):
- **Met by tests:** 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15.
- **12 (competitor failures classified honestly):** met only for availability. No competitor was run [N].

## 2. SOTA-6 baseline
* `26eee2b` has a tree identical to the delivered SOTA-6 patch, verified with git [E].
* Run 42744838394 and its artifacts are not verified here: no API access. The brief's 10 tests and the
  d11 axioms/leanchecker results match what SOTA-6 shipped, but are taken as reported.
* No protected path changed. The `integrity` job asserts a zero-line diff on all SOTA-1…6 paths [T].

## 3. Benchmarks and competitors
See `BENCHMARK_PROVENANCE.md` and `COMPETITOR_MATRIX.md`. The relevant external sources are:
- **ProofNetVerif** (3,752 pairs, MIT);
- **ProofNet-Verified** (an audit finding 56% of ProofNet ground truths unfaithful);
- **RLM25** (619 research-level pairs);
- **DriftBench** (2,183 pairs with controlled drift labels, κ = 0.81).

None were downloaded: the sandbox network blocks them.

## 4. Architecture (`bench/sota7/`)
| module | role |
|---|---|
| `schema.py` | `proofscope-eval/1` public-case and gold formats; label-leak and opaque-id checks; independence rules for labels |
| `blind.py` | freeze and verify manifests (canonical digests of inputs and gold, protocols, engine commit, budgets); per-case sandbox |
| `runner.py` | run the unchanged SOTA-6 engines under `bench.limits`; normalize claims; seal records and certificates read-only |
| `replay.py` | fresh-directory recompile, axiom audit, `leanchecker`, source identity rebuilt from the public strings |
| `scoring.py` | outcome classes, Clopper-Pearson intervals, zero-error upper bounds, coverage, percentiles; refuses unsealed or modified records |
| `competitors.py` | capability matrix and availability probe |
| `report.py` | summary and readiness report |
| `make_synthetic.py`, `dryrun_freeze.py` | the labelled synthetic fixtures and their manifest |

## 5. Source changes
**New files only, 49 in total** (including fixtures and local evidence):
- `bench/sota7/*` (10 modules);
- `bench/sota7/synthetic/` (11 public cases, `gold.jsonl`, `expected_classes.json`);
- `tests/sota7/*` (3 test files);
- `docs/sota7/*` (7 docs plus local evidence);
- `.github/workflows/sota7-research.yml`.

No existing file is modified.

## 6. Blinding and contamination
See `INDEPENDENCE_PROTOCOL.md`. Each of these was tested [T]:
- the sandbox contains only `case.json` and `spec.json`;
- gold environment variables are dropped;
- a gold canary never appears in any output;
- metadata containing label words is rejected, and so are revealing ids and extra public fields;
- in CI the gold file is deleted before execution.

## 7. Certificate replay
**Rejected by replay [T][K]:**
- a `sorry` proof, rejected with `sorryAx`;
- an added axiom `cheat : False`, rejected because `cheat` is in the axiom set;
- a substituted source statement, rejected for source identity;
- a missing certificate, reported as NO_CERTIFICATE;
- an abstention with only partial certificates, reported as NO_DECISIVE_DECLARATION, not "VERIFIED".

**Genuine certificates replay** [K].

**What replay does not establish:** interpretation of the source mathematics.

## 8. Scoring
- **Mutually exclusive classes.** See `scoring.py`: timeouts, abstentions and missing certificates are never
  negatives, and unresolved gold labels are scored apart.
- **Closed-only equivalence is never counted as correct** against a non-equivalent gold label.
- **Denominators** are all manifest cases.
- **Confidence intervals:** Clopper-Pearson at 95%. With zero errors, the upper bound is reported.
- **Paired competitor tests:** McNemar, available in `bench/score.py` [P for SOTA-7 integration].

## 9. Executed tests [T]
| suite | tests | result |
|---|---|---|
| `test_schema_integrity` | 12 | OK |
| `test_scoring_adversarial` (rules, statistics, 20-category taxonomy) | 10 | OK |
| `test_blinding_replay` (sandbox, canary, seal, tamper, replay, malicious certificates) | 10 | OK |

**Two test bugs of my own, fixed and recorded:**
- a CRLF test that produced invalid JSON;
- my first replay labelled abstentions "VERIFIED" (a misleading label, fixed to NO_DECISIVE_DECLARATION).

## 10. Synthetic dry run [E] (`docs/sota7/evidence-local/`; SYNTHETIC_DEVELOPMENT, not independent)
The 11 cases (6 relation, 5 repair) were run with the gold file withheld; 9 had certificates replayed and
verified, and 2 abstained.

| outcome class | count |
|---|---|
| CORRECT | 7 |
| CLOSED_ONLY_AGREEMENT (unrelated both-true pair) | 1 |
| REPAIR_MISMATCH (the planted wrong label, correctly exposed) | 1 |
| ABSTAIN (division case, which is a known engine gap; unresolved open pair) | 2 |

- **Decisive errors:** 0 of 9, 95% upper bound 0.336.
- **CPU per case:** median 3.4 s, p95 7.3 s, max 7.3 s.

## 11–12. External pilot readiness and what is still needed
**Ready:**
- the case format;
- intake;
- the frozen pilot protocol (`docs/sota5/PILOT_PROTOCOL_v1.md`);
- the reviewer protocol;
- adjudication tooling (`bench/pilot/labels.py`);
- the harness itself.

**Missing:**
- an external custodian;
- two Lean-literate reviewers and an adjudicator;
- 50 selected pairs with provenance;
- Mathlib-mode runs in CI for those pairs, which use the same commands with `environment.imports = ["Mathlib"]`.

## 13–14. Reproducibility and patch
`REPRODUCIBILITY.md` gives the commands. The patch is `proofscope-sota7-independent-evaluation.patch`: one
commit, new files only.

## 15. Limitations
See `LIMITATIONS.md`.

## 16. Most consequential next challenge
Recruit the custodian and two reviewers, and label 50 externally sourced pairs drawn from ProofNet-Verified,
RLM25 and DriftBench.

- **Pass:**
  - Cohen's κ_A ≥ 0.6;
  - 0 incorrect decisive verdicts, with an upper bound reported;
  - at least 30% of adjudicated non-equivalent pairs certified as different;
  - every decisive verdict replays.
- **Fail:** any incorrect decisive verdict.
