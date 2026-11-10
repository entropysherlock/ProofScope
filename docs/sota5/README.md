# WESTFALL PROOFSCOPE SOTA-5 — SEMANTIC INTEGRITY AND CERTIFIED STATEMENT RELATIONS

Caleb J. Westfall · ProofScope · branch `research/sota5-semantic-integrity` from
`b7f6cf8d3da950e8cefbbd33a50b91a4d25e0933` · all local results: Lean 4.34.1, core Lean (no Mathlib in the
development sandbox), leanprover-community/repl `193cf4bb`.

## A. Executive verdict

**Level reached: 1 (d03 resolved), with partial Level-2 evidence. Not Level 3 or 4.**

* **d03 is a translation error in the SOTA-4 measurement harness, not an unsound proof and not a wrong
  label.**
  - The reference is false at n = 0 and the candidate is true, so they differ. Both facts are kernel-checked.
  - The engines never saw that statement. The SOTA-4 measurement tool printed the cast without its target
    type, as `↑(n - 1) = ↑n - 1`, and did not run the adapter's round-trip check.
  - Re-elaborated on its own, that text means `∀ n : ℕ, n - 1 = n - 1`, which is trivially true.
  - The engines correctly certified a both-true equivalence about the wrong statements. This is reproduced
    exactly, with the same certificate family, in core Lean.
  - The fix is an adapter v2 that keeps cast targets and checks the printed text on its own. With it, CJCS
    certifies the correct difference with witness n = 0.
* **Statement relations are now precise and kernel-checked** (`research/sota5/Relations.lean`, 14
  declarations, no `sorry`, standard axioms only, `leanchecker --fresh`).
  - Closed equivalence, open equivalence, strict strength and incomparability are defined.
  - The exact gap between them is proved: for universal closures, closed and open equivalence can differ
    only when both closures are false. Dev case d22 is a both-false pair that hides a strict strength
    relation.
  - Every CJCS verdict now carries a relation record stating what it does not establish.
* **The law-relative prototype works on a small fragment and is certified, but it is not novel.**
  - The fragment is universal equations over one binary operation.
  - The prototype outputs inclusion-minimal sufficient law sets, each with a minimality certificate, and the
    laws necessary within the family.
  - In example e1 it finds two incomparable minimal sets, {comm} and {assoc, idem}.
  - For d11 it proves that, inside group theory, the candidate is *equivalent to commutativity*, and
    separates it from the reference with a kernel-verified S₃ table.
  - This is axiom pinpointing (minimal axiom sets, MinAs, with hitting-set duality to diagnoses) applied
    to equivalence of statement pairs. The new part is only certification, inside Lean, of each
    minimality claim.
* **Performance:** no new optimization was achieved or measured. Mathlib is unreachable here, so I did not
  measure anything with it. The CI job reruns the extended measurement with the round-trip check enforced.
* **The SOTA-4 acceptance record needs one correction.** Its single must-not violation (d03) was a harness
  error. The engines did not make it. But it also means the extended measurement counted one decisive
  outcome that was about the wrong statements. Other cases may be affected the same way; the CI adapter
  audit lists every case where unchecked printing changes meaning.

## B. Verified repository baseline
* Verified with git: `b7f6cf8d3da950e8cefbbd33a50b91a4d25e0933` is the head of `research/sota4-oneprocess`,
  with parent `26d425a` ("Add files via upload") and grandparent `3791511`.
* Compared with the SOTA-4 patch as I delivered it, the applied commit differs in two ways:
  - the patch file itself was committed;
  - the 13 evidence JSON files gained a trailing newline. That is the same transit normalization as in
    SOTA-3, it is harmless, and the canonical manifests are unaffected.
* **Not verified in this environment:** the run's job list, its conclusions and its artifacts. This session
  has git read access only; the GitHub API and artifact downloads are refused. The SOTA-4 numbers in the
  brief are used as reported, and labelled as such. Nothing on the protected branches was touched, and the
  `baseline` job asserts the protected paths are byte-identical.

## C. d03 forensic investigation
| | text | elaborated proposition | truth |
|---|---|---|---|
| fixture reference | `∀ (n : ℕ), ((n - 1 : ℕ) : ℤ) = (n : ℤ) - 1` | as written | **false** (n = 0: 0 ≠ −1) |
| fixture candidate | `∀ (n : ℕ), 1 ≤ n → ((n - 1 : ℕ) : ℤ) = (n : ℤ) - 1` | as written | true |
| adapter v1 print (ref) | `∀ (n : Nat), ↑(n - 1) = ↑n - 1` | `∀ n : ℕ, n - 1 = n - 1` (checked with `pp.all`) | true |
| adapter v1 print (cand) | `∀ (n : Nat), 1 ≤ n → ↑(n - 1) = ↑n - 1` | `∀ n : ℕ, 1 ≤ n → n - 1 = n - 1` | true |
| adapter v2 print (ref) | `∀ (n : Nat), (↑(n - 1) : Int) = (↑n : Int) - 1` | the intended reference | false |

Answers to the audit questions:
1. **Compared:** two closed propositions over ℕ that contain no casts, not the fixture.
2. **Intended:** the fixture statements.
3. **Closed or open:** both are closed.
4. **Variables:** `n` is universally bound in both, with no auto-binding.
5. **Inserted elements:** the `↑` became the identity coercion ℕ→ℕ, because there was no target type.
6. **Domain:** the ℤ codomain silently became ℕ, which made the equation trivial.
7. **What the certificate proves:** mutual truth of the printed statements, `equiv_both_true` built from
   `true_R` and `true_L`.
8. **Does it match the intended reference:** no. `SOTA5.d03_printing_changed_meaning : ¬ (printed_ref ↔ ref)`.
9. **Independent check:** the certificates pass the kernel and replay, and the same family is reproduced in
   `tests/sota5/test_d03_regression.py`.
10. **The label is mathematically justified:** `SOTA5.d03_intended_differ`.

**Where it entered:**
- The frozen runner's round-trip check rejects the v1 strings, so in the standard harness d03 is
  INPUT_NOT_EVALUABLE. I expect it is one of the two persistent input-not-evaluable cases, but that is
  unverified here (Mathlib CI will confirm).
- `bench/sota4/specs.py`, which I wrote for the SOTA-4 extended measurement, printed the statements and
  skipped that check.

**Classification: incorrect translation and elaboration in the measurement harness, plus misleading verdict
reporting.** The engine's proof is sound for what it received. The provisional label is right and was not
changed.

**Repair:**
- `bench/sota5/adapter2.py` adds `pp.coercions.types` to printing and a standalone check:
  `abbrev ps_printed : Prop := (text)` must be `with_reducible rfl`-equal to the declaration's type.
- `bench/sota5/specs.py` enforces that check and records the v1 and v2 printing for every case.
- The frozen adapter and runner are unchanged.

## D. Mathematical content (definitions and theorems; none claimed new)
These are in `research/sota5/Relations.lean`.

**Definitions:** `OpenEquiv`, `ClosedEquiv`, `StrictlyStronger`, `Incomparable`.

**Theorems:**
- `open_imp_closed`;
- `both_closures_true_open`: for universal closures, both-true closures imply open equivalence, so any gap
  between the two notions needs both closures to be false;
- `incomparable_not_open`, `stronger_not_open`;
- the d22 instances `d22_closed_equiv`, `d22_strictly_stronger` and `d22_not_open`: closed-equivalent, yet
  `n+n=n` is strictly stronger than `n*n=n`;
- `minimal_of_witnesses`, the interpretation theorem for minimality certificates. If S suffices and, for
  each φ ∈ S, some structure satisfies the other laws of S while P and Q disagree in it, then no subset of S
  that omits any law suffices. The result is inclusion-minimality, not minimum size, and is relative to the
  candidate family.

**d11:**
- `Grp.ref_holds`;
- `Grp.cand_iff_comm` (the candidate ⟺ commutativity, over the group axioms);
- `Grp.S3_separates` and `Grp.S3_not_comm`, with S₃ as a kernel-checked table.

**Two corrections to my own SOTA-5 work:**
- My first attempt stated d22 as *incomparable*. That is false: `n+n=n` implies `n*n=n`. The compiler caught
  it, and the statement was corrected to strict strength.
- A first hostile test for the law-relative tool was mis-designed: it patched the evaluator so that no model
  was ever found. It was replaced by a direct kernel-rejection test.

**Prior art:**
- Minimal sufficient law sets are the MinAs / justifications of axiom pinpointing.
- The same reduction appears in MUS/MCS enumeration (MARCO), through hitting-set duality.
- "Equivalent over a base theory" is the reverse-mathematics pattern.
- `(ab)⁻¹ = a⁻¹b⁻¹ ⟺ abelian` is a textbook exercise.

## E. Lean/kernel evidence
- **`Relations.lean`:**
  - 14 `#print axioms`: none use sorryAx, and all are within {propext, Classical.choice, Quot.sound};
  - `autoImplicit false`;
  - `leanchecker --fresh Relations` exit 0;
  - `evidence-local/` holds the logs; the CI `theory` job re-checks the count and axioms.
- **Law-relative modules**, `evidence-local/lawrel/*/LR_*.lean`: compiled, axiom-audited and replayed.
  - Entailment proofs use `grind` (standard classical axioms).
  - Countermodels use `decide` (propext only).
- **Remaining assumptions:**
  - the Lean kernel;
  - `decide` evaluation of finite tables;
  - the adapter's standalone check as the only link from source declaration to statement text.

## F. Law-relative comparison
- **Algorithm (`proofscope/experimental/lawrel.py`):**
  1. Untrusted model search over all magmas on Fin 2 and Fin 3, largest law sets first. A model of S refutes
     every subset of S.
  2. Untrusted proof portfolio (`grind`, `simp_all`) for the remaining subsets, smallest first, closed
     upward by monotonicity.
  3. One Lean module containing every entailment proof, every countermodel (law satisfaction and
     separation, by `decide`), a minimality theorem for each minimal set (an instance of
     `minimal_of_witnesses`), and a necessity theorem for each law whose removal from Φ is separated.
  4. Compile, axiom audit, `leanchecker`.
- **Results:**

| spec | P vs Q | certified minimal sufficient sets | necessary in family | countermodels |
|---|---|---|---|---|
| e1 | `a*(a*b)=a*b` vs `(a*b)*b=a*b` | {comm}, {assoc, idem} | none | Fin 3 tables m0 (assoc only), m1 (idem only) |
| e2 | `(a*b)*(a*b)=a*b` vs `a*a=a` | {idem} | idem | zero magma on Fin 2 |
| d11 (manual, Relations.lean) | `(ab)⁻¹=b⁻¹a⁻¹` vs `(ab)⁻¹=a⁻¹b⁻¹` over groups | {Comm} | — | S₃ |

- **Model scope.** Non-entailment is witnessed by real finite models, so it is absolute. Entailment is
  proved over all Lean types.
- **Completeness.** For equational theories, Birkhoff's completeness theorem holds. Even so, the procedure
  is incomplete:
  - the finite-model search is bounded to size 3;
  - the proof portfolio is bounded;
  - UNKNOWN is reported and never treated as negative (tested).
- **Limitations:**
  - one operation, equational laws only, |Φ| ≤ 4 in practice (2^|Φ| subsets);
  - no link yet from Mathlib statements to this fragment;
  - minimal sets are relative to the declared family.

## G. Performance results
**No optimization was attempted or measured in this mission.** That is the honest result.
- Mathlib cannot be reached from the sandbox, and all four median environment loads that remain are
  Mathlib loads: 1 for search, plus extractor build, compile and leanchecker.
- One explanation can be stated from proved facts: d11's candidate is equivalent to commutativity
  (`cand_iff_comm`). Refuting it therefore needs a non-abelian group carrier, which CJCS's point pools do
  not contain, so the search spends its budget trying to prove a false statement.
- That explanation is a hypothesis for the 422 CPU-s figure, not a measurement.

The CI `mathlib` job reruns the 27-case extended measurement with the round-trip check enforced. It reports
coverage loss as INPUT_NOT_EVALUABLE, the corrected must-not count, and the median CPU.

## H. Benchmark design
`PILOT_PROTOCOL_v1.md` is frozen, sha256 `8c9175dc…` (full hash in the patch description). It extends the
SOTA-4 infrastructure with:
- the adapter v2 gate;
- relation-level Track-A labels;
- a pre-registered primary endpoint: zero incorrect decisive verdicts against adjudicated labels.

No external reviewers exist yet. If none are found, the pilot must be called internally adjudicated.

## I. Hostile-referee assessment
* **Translation.** d03 shows the most dangerous failure point is the step from source text to statement
  text, not the kernel. The repaired check covers the case that occurred. A printer that changes meaning
  in a way that still round-trips is possible in principle.
* **Hostile pairs.**
  - 6 new pairs (`research/cjcs/sota5_hostile`) and 5 relation-record tests.
  - All pass with 0 must-not violations.
  - y05 (missing nonzero divisor) abstains: the portfolio cannot prove `n ≠ 0 → n / n = 1`. That is a
    completeness gap, not a soundness one.
  - Of the 16 hostile items in the brief, item 10 (wrong implicit instance) has no core-Lean test.
* **Novelty.** The law-relative work is known theory with certificates attached. The relation definitions
  are elementary.
* **Evidence quality.** Everything is developer-written. No independent labels exist.

## J. Novelty and publication readiness
* **A defensible short paper** would be an experience report: kernel-certified statement-relation checking,
  including the adapter failure (meaning-changing pretty-printing) and its detection. Missing: the Mathlib
  adapter audit, and an independent pilot.
* **Not yet a paper:** the law-relative explanation. It needs a link from real Mathlib statement pairs to a
  law family, and a comparison against axiom-pinpointing baselines.

## K. Grant relevance
A seed proposal can now point to:
- a documented, reproduced and repaired semantic-integrity failure;
- certified relation semantics with explicit non-claims;
- certified minimal-assumption explanations on a toy fragment;
- a frozen pilot protocol.

It cannot claim accuracy, independence or state-of-the-art status.

## L. Next decisive challenge
**Run the frozen Phase-1 pilot with two external reviewers.**

- **Pass:**
  - Cohen's κ_A ≥ 0.6;
  - zero incorrect decisive verdicts across all pairs that pass the adapter v2 gate;
  - certified-difference recall ≥ 30% on adjudicated NOT_EQUIVALENT pairs;
  - every decisive verdict replays.
- **Fail:** any incorrect decisive verdict, or recall < 15%.
