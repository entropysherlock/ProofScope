# SOTA-18: competitive evaluation of ProofScope against SemantEq and BEq+

Research director: Caleb J. Westfall. Executed by Claude (Anthropic), 2026-11-11.
Branch `research/sota18-independent-evaluation`. Pre-registration: `experiments/sota18/PROTOCOL.md`
(commit `b766001`, before any case was selected). Raw data, scripts and summaries: `experiments/sota18/`.

> **Erratum (2026-11-11, SOTA-19 audit).** The pre-registered mapping listed CMCD `IDENTICAL` among
> kernel-certified verdicts, but `IDENTICAL` is an elaborator identity check with no certificate. Of the 75
> fail-closed (H1) "equivalent" verdicts, **37 are backed by kernel certificates** (ASSUMPTION_EQUIVALENT
> and/or SCHEMA_EQUIVALENT), **32 are `IDENTICAL`** (statements elaborate to the same term: correct, but not
> a certificate) and **6 are structural `NO_ASSUMPTION_DELTA`**. Every "69 kernel" figure below should read
> "37 certificate-backed + 32 identical-after-elaboration". No verdict, label or gate value changes.

## 1. Executive verdict

**Decision: PIVOT** (the pre-registered gate, applied mechanically, gives PIVOT under both readings).

* ProofScope's distinguishing capability, *certified* directional difference, almost never fires on
  real pairs: **3 "not equivalent" verdicts in 477 pairs, 1 matching the label, 0 concrete
  counterexamples**. SemantEq's and BEq+'s uncertified rejections do the same job on these data.
* Where ProofScope decides "equivalent" with kernel certificates, it is always right (precision 1.0
  on 75 decisions under the fail-closed reading, 69 of them kernel-certified), but SemantEq and BEq+ certify more equivalences
  (Track A: 63 and 71 against ProofScope's 31) and are significantly better in paired comparison
  (exact McNemar p < 10⁻⁶ on Tracks A and B).
* The frozen engine has a **soundness bug** (finding F1): 47 uncertified `NO_ASSUMPTION_DELTA`
  ("no difference") outputs on statements it never elaborated; 17 of them are wrong.
* ProofScope does have genuine wins: 4 pairs where it kernel-proved that a changed assumption is
  redundant (e.g. `x ≠ -1` is redundant because Lean defines `x / 0 = 0`) and both competitors failed.
  They are real but few, all on competition arithmetic (EPLA/miniF2F).
* The dominant failure is mechanical, not mathematical: **40 % of pairs (189/477) fail inside the
  engines because the statements are universe-polymorphic (`Type u_1`)**. The pivot target follows.

Answer to the final question: today ProofScope is a narrow, mostly sound application of established
mathematics with a thin real-world advantage. It is not a state-of-the-art statement auditor. The
evidence supports narrowing it to a *certified explanation layer* on top of an equivalence checker,
not continuing it as a standalone competitor.

## 2. GitHub and CI state

| Item | State |
|---|---|
| `v1.2-review` | `b0519f8` (README only since the SOTA-16 merge `198e17c`); evaluated engine = this commit |
| PR #7 (SOTA-17) | open, not merged, head `4bdd369`. CI green after one re-run: *SOTA-16 Reproduce* `Evaluate frozen` failed twice with "runner received a shutdown signal" ~4 min into the frozen engine (no output; job runs no SOTA-17 file) and passed on attempt 2 (run 42961160044). Same pattern earlier on `eadec1a` (run 42959056422, passed on attempt 2). Cause not proven; consistent with runner memory exhaustion by the frozen SOTA-16 engine, which its own report documents. |
| SOTA-18 runs | selection 42965078900 and 42965331884 (identical output); smoke 42965562451, 42966601819, 42968049825 (synthetic only); **headline 42969440169** (48/48 tool jobs succeeded; its `collect` step failed on `ls \| head` under `pipefail`); records re-collected from the same run's artifacts by run 42977127138 |

## 3. Competitor audit (`experiments/sota18/competitors.json`)

| System | Code | License | Native environment | Output | Lean-checked | Certified inequivalence | Run here |
|---|---|---|---|---|---|---|---|
| SemantEq v1.4.0 | hlxr89/SemantEq @`f927670` | Apache-2.0 | Lean v4.30.0-rc1, ~9 GB/process | equivalent / one direction proved / inconclusive | yes (audited proofs) | no | **yes** |
| BEq+ | LeanInteract @`768e18e` `examples/beq_plus.py` | MIT | Lean v4.8.0 REPL | bool | yes for True | no | **yes** |
| ACE / SAE (arXiv 2610.25018 v3) | none in the paper | unknown | Lean + Aesop / LLM backends | certified equivalent / inequivalent / inconclusive | yes | **yes** | no: no code |
| ShadowBench SA-PASS | ldilab/shadowbench @`7d14cba` | none stated | hidden checker theorems (server) | binary per problem | yes | no | no: different task |
| FormalAlign | rookie-joe/FormalAlign @`8de2b43` | none | fine-tuned LLM | score | no | no | no: repo has data only |
| LeanScorer (Mathesis) | not located | unknown | LLM | score | no | no | no |
| ASSESS / TransTED | ASSESS @`bc79335` | Apache-2.0 | Lean REPL | similarity | no | no | no (its EPLA data is used) |

ACE is the closest competitor to ProofScope's claim (certified inequivalence); without code it could
not be compared. Its published numbers are context only.

## 4. Data and provenance (`experiments/sota18/frozen/`)

* ProofNetVerif test split (`PAug/ProofNetVerif` revision `91183e5`, MIT): 1,452 rows. Gold G1 =
  published `correct` (BEq+ authors); G2 = SemantEq's adjudicated labels (1,303 rows). **Vendor-home for
  both competitors.**
* EPLA (ASSESS @`bc79335`, Apache-2.0): 1,247 compiling (reference, prediction) rows; gold G3 =
  `likeness after transformation`. Neutral for all three tools; 88 % positive.
* **Track A** (unfiltered): 200 ProofNetVerif + 100 EPLA, seeded uniform samples.
* **Track B** (text-only criterion, from all 2,699 rows): B1 "conclusions identical, binders differ"
  321 qualified, seeded 200 (85 PNV, 115 EPLA). B2 "binders identical, one-token conclusion change":
  **0 qualified**; reported, not padded.
* 477 distinct pairs; `cases_sha256 a90f00ae…`, committed by the CI runner before any tool ran
  (commit `745e3e2`).

## 5. Tasks and fairness

T1 (scored): is the candidate faithful to the reference? Each output mapped to EQUIV / NONEQUIV /
ABSTAIN / infrastructure. *Certified reading*: only machine-checked outputs count. *Native reading*:
each tool's own accept/reject (SemantEq and BEq+ count every non-accept as "not equivalent", as their
papers do). ProofScope's "not equivalent" verdicts are schema- or assumption-level differences and are
admissible only for faithfulness, never as logical inequivalence. Abstraction-relative separations
were never counted as counterexamples. Every ProofScope input passed a Lean round-trip check
(`printed = type_of% decl` by `with_reducible rfl`), so ProofScope was only ever given the dataset's
propositions. T2 (one-way facts) and T3 (concrete inequivalence) are counted, not ranked.

## 6. Environment

GitHub-hosted `ubuntu-24.04`, 4 vCPU, 16 GB. ProofScope: Lean 4.34.1, Mathlib `v4.34.1` (`d13f23b`),
Python 3.12.16, engine hash-checked against `ENGINE_HASHES.txt` in every job. SemantEq: its pin,
`--timeout 300`. BEq+: upstream method, v4.8.0, 60 s per proof. Same 900 s per-pair cap for all.
Harness hashes: `RUN_FREEZE.txt`.

## 7. Track A (300 pairs, gold G1 for PNV, G3 for EPLA)

| System | Reading | Decisive | Correct | Incorrect | Abstain | Infra | Correct / total | EQUIV precision | NONEQUIV precision | EQUIV recall | median s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ProofScope H0 (frozen) | certified | 56 | 41 | 15 | 173 | 71 | 13.7 % | 0.755 | 0.33 (n=3) | 0.31 | 22.5 |
| ProofScope H1 (fail-closed) | certified | 33 | 31 | 2 | 196 | 71 | **10.3 %** | **1.000** | 0.33 (n=3) | 0.23 | 22.5 |
| SemantEq | certified | 63 | 63 | 0 | 185 | 52 | 21.0 % | 1.000 | – | 0.46 | 20.1 |
| SemantEq | native | 248 | 175 | 73 | 0 | 52 | 58.3 % | 1.000 | 0.605 | 0.46 | 20.1 |
| BEq+ | certified | 71 | 71 | 0 | 225 | 4 | 23.7 % | 1.000 | – | 0.45 | 8.6 |
| BEq+ | native | 296 | 208 | 88 | 0 | 4 | 69.3 % | 1.000 | 0.609 | 0.45 | 8.6 |

By source (certified, H1): ProofNetVerif 4/200 correct (2.0 %), EPLA 27/100 (27 %). SemantEq 33/200
and 30/100; BEq+ 33/200 and 38/100. Under SemantEq's adjudicated labels (G2) the PNV picture is the
same (ProofScope H1 4, SemantEq 33, BEq+ 32). ProofScope infrastructure outcomes on Track A:
28 non-elaborating on Lean 4.34.1, 43 adapter round-trip failures, 0 timeouts. SemantEq: 37 compile
errors on v4.30, 15 timeouts. BEq+: 3 non-elaborating, 1 error.

## 8. Track B (200 assumption-drift pairs)

| System | Reading | Decisive | Correct | Incorrect | Correct / total | EQUIV precision |
|---|---|---|---|---|---|---|
| ProofScope H0 | certified | 77 | 73 | 4 | 36.5 % | 0.948 |
| ProofScope H1 | certified | 50 | 50 | 0 | **25.0 %** | 1.000 |
| SemantEq | certified | 85 | 85 | 0 | 42.5 % | 1.000 |
| BEq+ | certified | 93 | 93 | 0 | 46.5 % | 1.000 |

PNV part (85): ProofScope H1 5 correct, SemantEq 30, BEq+ 36. EPLA part (115): 45, 55, 57.
Even on the pairs chosen because only assumptions changed, ProofScope produced **no** certified
"not equivalent" verdict.

## 9. Track C (synthetic, not pooled)

Five pairs (`trackC_smoke.jsonl`). They exposed F1 (c04, c05) and showed CMCD inconclusive on
`n < 2^n` vs `n ≤ 2^n` under Mathlib (forward entailment certified, no separating interpretation found).

## 10. Head to head (certified reading, gold G1/G3)

| Track | Comparison | ProofScope only | Competitor only | exact McNemar p |
|---|---|---|---|---|
| A, H1 | vs SemantEq | 3 | 35 | < 10⁻⁶ |
| A, H1 | vs BEq+ | 3 | 43 | < 10⁻⁶ |
| B, H1 | vs SemantEq | 5 | 40 | < 10⁻⁶ |
| B, H1 | vs BEq+ | 5 | 48 | < 10⁻⁶ |
| A, H0 | vs SemantEq / BEq+ | 7 / 7 | 29 / 37 | 3·10⁻⁴ / 5·10⁻⁶ |

Pairs where ProofScope is correct and certified and **neither** competitor is correct even in its native
reading (gate quantity X): **11 under H0** (7 of them F1 outputs that happen to match a "faithful" label),
**4 under H1**, all EPLA/miniF2F, all `ASSUMPTION_EQUIVALENT` with kernel certificates:

| Pair | Changed assumption | Why it is redundant (proved in Lean) | SemantEq | BEq+ |
|---|---|---|---|---|
| miniF2F 68 (`mathd_algebra_80`) | candidate drops `x ≠ -1` | at `x = -1`, `(x-9)/(x+1) = 0 ≠ 2` (Lean's `x/0 = 0`) | LikelyTooStrong | False |
| miniF2F 430 (`imo_1982_p1`) | candidate drops `0 < m ∧ 0 < n` from the additivity hypothesis | with truncated subtraction the `m = 0` / `n = 0` cases hold trivially | Inconclusive | False |
| miniF2F 237 (`mathd_numbertheory_495`) | candidate drops `0 < a ∧ 0 < b` | units digits 2 and 4 force `a, b ≠ 0` | LikelyTooStrong | False |
| miniF2F 298 (`amc12_2000_p1`) | candidate adds positivity of `i, m, o` | `i * m * o = 2001` forces it | LikelyTooWeak | False |

These are the clearest evidence of what ProofScope's machinery is good for: a checked explanation of
*why* a changed assumption does not matter. On the other side, the competitors were correct-and-decisive
on 235 (H0) / 258 (H1) A ∪ B pairs where ProofScope was not (native reading).

**T2 (one-way facts).** ProofScope produced machine-checked implications on 92 pairs (84 both ways,
8 one way only). SemantEq produced one proved direction (`LikelyTooStrong/Weak`) on 77 pairs.
**T3 (concrete inequivalence).** ProofScope: 0. No system produced one.

## 11. Soundness audit

* **F1 (confirmed, `experiments/sota18/SOUNDNESS.md`).** `adelta12` returns `NO_ASSUMPTION_DELTA`
  without any certificate when a statement fails to elaborate inside the engine (error recovery turns
  it into `sorry`, and `sorry` = `sorry`). Minimal counterexample in core Lean:
  `∀ {G : Type u_1} (a b : G), a = b` vs `∀ {G : Type u_1} (a : G), a = a` → `NO_ASSUMPTION_DELTA`.
  Under Mathlib on CI: `a * b = b * a` in every `Group` vs in every `CommGroup` → `NO_ASSUMPTION_DELTA`.
  Headline run: **47** such outputs (`S = 47`), **17** of them on pairs labelled unfaithful; every
  incorrect H0 "equivalent" verdict is an F1 output. CMCD fails closed on the same inputs (its kernel
  link certificate fails). Repair: certify `link_R/link_L` before `NO_ASSUMPTION_DELTA` and fail
  closed on any `sorry` in the extraction.
* **Kernel certificates.** No incorrect kernel-certified verdict was found: all 69 kernel-backed
  "equivalent" outputs (and the 6 non-F1 structural ones) agree with the labels; all 17 incorrect
  "equivalent" outputs are uncertified F1 outputs. The 4 X-pairs were checked by hand above.
* **Disputed labels (not unsound).** Two of the three "not equivalent" outputs disagree with EPLA's
  "alike" label but describe real differences: miniF2F 54 (candidate adds an existence conjunct,
  `CLAIM_LEAN_STRONGER`) and miniF2F 425 (candidate drops `0 < n`, more general, harmless).
  The third (Rudin 1.18b, candidate drops `x ≠ 0`) is correct but under-reported: the candidate is
  *false* at `x = 0`, and the engine said "stronger" rather than certifying `LEAN_CLAIM_FALSE`.
* **Checklist items with no issue found:** sides never swapped (adapter keeps reference/candidate
  order; direction verified on the four X-pairs); adapter round trip is a Lean proof of meaning
  preservation; schema separations never counted as counterexamples; witnesses of assumption
  verdicts are concrete Mathlib instances; typeclass and implicit binders round-trip.
* **Adapter defects fixed during the synthetic smoke stage only** (no benchmark output seen): universe
  names in the round trip; BEq+ toolchain default; artifact paths.

## 12. Failure and abstention taxonomy (all 477 pairs, H1)

| Category | Pairs | Where it fails |
|---|---|---|
| universe-polymorphic statement fails inside the engines (`Type u_1`: unresolved metavariables 118, `sorry` 50, universe errors 21) | **189 (40 %)** | input representation |
| assumptions equal, conclusion changed (`CONCLUSION_ONLY_CHANGE`; CMCD then inconclusive or no shared symbols) | 82 | conclusion reasoning |
| both engines inconclusive after elaborating | 48 | proof search / abstraction |
| adapter round trip fails (printed text does not re-elaborate) | 45 | adapter |
| does not elaborate on Lean 4.34.1 / Mathlib v4.34.1 (dataset written for older Mathlib) | 33 | version drift |
| other extraction failure | 9 | – |
| decisive | 78 (75 EQUIV, 3 NONEQUIV) | – |

Only 5 of 477 printed statements parse in the ScopeElim / SOTA-17 claim grammar at all; the
multi-occurrence work cannot reach this distribution.

## 13. Results that contradict expectations (pre-registered in PROTOCOL §9)

* Track A coverage was **higher** than predicted (10–14 % vs "below 5 %"), but almost all of it comes
  from EPLA's near-identical pairs; on ProofNetVerif it is 2 % (H1).
* The certified "not equivalent" capability, the project's selling point, fired **3 times**.
  Predicted: rare; observed: almost absent, including on Track B.
* The biggest loss is not mathematics but universe polymorphism, which was not anticipated.
* BEq+ (2024 method, Lean v4.8) was the strongest system on these data under the certified reading.
* The competitors' native rejections are far from precise on EPLA (NONEQUIV precision 0.17–0.19),
  because EPLA is 88 % positive: "reject when unsure" is cheap on PNV, expensive on EPLA.

## 14. Does ProofScope have a genuine competitive advantage?

Narrowly, yes: kernel-certified explanations that a changed assumption is redundant, including cases
both competitors miss (4 pairs), and a pipeline that is sound wherever a kernel certificate is
involved. As a statement-equivalence or fidelity checker, no: it decides fewer pairs, its certified
"difference" output is almost never produced, and it is significantly worse in paired comparison.

## 15. Architectural changes warranted by the evidence

1. **Fix the input layer first (40 % of pairs).** Elaborate statements once, inside Lean, and pass
   `Expr`s (not printed text) to the engines; universe parameters, instances and notation then need no
   re-parsing. This also removes the 45 adapter failures and is the natural home of the F1 repair.
2. **Fail closed everywhere.** No verdict without link certificates; `NO_ASSUMPTION_DELTA` must be
   certified or demoted to "structurally identical (unverified)".
3. **Stop competing on equivalence; compose with a checker.** Run SemantEq or BEq+ first; invoke
   ProofScope only where they abstain or report one direction, to (a) prove assumption redundancy and
   (b) explain the direction with a certificate. That is where all four wins sit.
4. **Conclusion drift needs a different method.** CMCD's abstraction finds no shared symbols or no
   separating interpretation on most real conclusions. Concrete counterexample search (finite models,
   `decide`/`norm_num` instances, as in `adelta12`'s carriers) is the evidence that would make a
   "not equivalent" verdict both certified and meaningful.
5. **Retire the Nat-only fragments as product features** (ScopeElim/SOTA-16/17): 5 of 477 real
   statements enter their grammar.

## 16. Recommendation

**PIVOT**, by the pre-registered rule:

| Quantity | Threshold for CONTINUE | H0 (frozen) | H1 (fail-closed) |
|---|---|---|---|
| S (unsound outputs) | 0 | **47** | 47 in the evaluated engine |
| U_A | ≥ 10 % | 13.7 % | 10.3 % |
| U_B | ≥ 25 % | 36.5 % | 25.0 % |
| P_N (with ≥ 10 outputs) | ≥ 0.90 | 0.33, **n = 3** | 0.33, **n = 3** |
| X | ≥ 5 | 11 | **4** |

STOP requires U_A < 2 % and U_B < 10 % and X = 0: not met. CONTINUE fails on S, P_N and (H1) X.
The pivot: ProofScope becomes a certified *explanation and assumption-redundancy* layer behind an
equivalence checker, built on an `Expr`-level input pipeline. Re-evaluate on these same frozen
pairs: the data and harness are reusable as-is.

## 17a. Independent reproduction (run #5, 43000099441)

A second full run with the fixed workflow ([43000099441](https://github.com/entropysherlock/ProofScope/actions/runs/43000099441),
all 48 tool jobs and its own collect step green; records in `experiments/sota18/results/full/run_43000099441_1/`)
reproduces every gate quantity exactly under both readings (S = 47; H0: U_A 13.7 %, U_B 36.5 %, X = 11;
H1: U_A 10.3 %, U_B 25.0 %, X = 4; P_N 0.33 on 3 outputs). Per pair:

* BEq+: 0 of 478 records differ.
* ProofScope: 1 of 477 differs (CMCD returned no verdict on one pair that adelta12 already decided as
  `ASSUMPTION_EQUIVALENT`); no scored outcome changes.
* SemantEq: 10 of 477 differ, all involving its 300 s timeout (7 Timeout → Inconclusive, one each
  Timeout → EquivalentRestricted, Timeout → LikelyTooStrong, LikelyTooStrong → Timeout). SemantEq's
  certified correct count on Track B moves from 85 to 86; nothing else changes.

The decision (PIVOT) is unchanged.

## 17. Reproduce

See `experiments/sota18/README.md`. Scoring of the committed records:

    python experiments/sota18/score.py experiments/sota18/results/full/run_42969440169_1 --mode H0 --out H0.json
    python experiments/sota18/score.py experiments/sota18/results/full/run_42969440169_1 --mode H1 --out H1.json

Limits: same author for protocol, harness and report; labels are the datasets' own (vendor-home for
the competitors on ProofNetVerif); single run per tool; ACE could not be evaluated.
