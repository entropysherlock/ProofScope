# SOTA-19: the true pivot

Research director: Caleb J. Westfall. Written by Claude (Anthropic), 2026-11-11, from the SOTA-18 records,
a new pre-registered ablation (pilot A0) and a literature check. Branch `research/sota19-strategic-pivot`.

## The seven answers

1. **Verdict.** ProofScope should become a **certified explainer of hypothesis drift between two
   formalizations of the same problem**: it says which hypothesis differs, whether that difference is
   harmless, and, when it is not, where the weaker statement fails, each claim backed by a Lean proof.
   It should run behind an equivalence checker, not compete with one. Everything else in the repository
   is either infrastructure for that or should stop.
2. **Thesis.** Hypothesis drift is decided on the *gap region*, the instances one statement covers and the
   other does not. Evaluating the conclusion there turns an undecidable whole-statement question into small,
   local, often finite obligations: either the conclusion holds on the gap (the change is harmless) or a
   counterexample sits in the gap (the weaker formalization is false, and we can say where). The open
   empirical question is how often the gap is small enough to decide on authentic data.
3. **Advantage.** Not equivalence (SemantEq and BEq+ are better, SOTA-18). The difference is the output:
   a localized, certified explanation, and certified refutations located by the reference. SemantEq and
   BEq+ certify only "equivalent"; ACE certifies structure-level inequivalence without localising a
   counterexample and has no released code; Lean Disprove refutes statements without a reference to
   guide it.
4. **Breakthrough experiment.** SOTA-19A: gap certification on ProofNet → ProofNet-Verified (366 pairs with
   independent directional labels, Lean proofs of every corrected statement and Lean disproofs of every
   false original), against SemantEq, BEq+, the A0 baseline, and the same refutation budget *without*
   gap guidance. Kill condition fixed in advance (`experiments/sota19/SOTA-19A.md`).
5. **Grant case.** Faithfulness is the bottleneck of autoformalization: 56 % of ProofNet's reference
   statements are unfaithful (An, Min, Si, Bastani 2026), and equivalence-to-reference metrics penalize
   faithful models. Tools that say *how* two statements differ, with proofs, do not exist as open
   infrastructure. $70,000 buys a fail-closed Lean-native comparison core, an open directional-fidelity
   benchmark built on independent labels, and a decisive, pre-registered test of whether gap
   certification works, with a clear kill condition.
6. **Roadmap.** Section 9: months 1–3 correctness and Lean-native input; 4–6 gap certification; 7–9
   independent evaluation on two labelled sources plus a fresh held-out set; 10–12 release, benchmark,
   paper. Budget section 9.5.
7. **Next mission.** SOTA-19A, specified in `experiments/sota19/SOTA-19A.md`.

## 1. What SOTA-18 actually found (re-verified from the raw records)

| Reported | Verified | Note |
|---|---|---|
| Track A correct certified, H1 | 31 / 300 | confirmed |
| Track B correct certified, H1 | 50 / 200 | confirmed |
| unique wins vs both competitors | 4 | confirmed, all EPLA/miniF2F, all `ASSUMPTION_EQUIVALENT` |
| kernel-certified equivalences | **37, not 69** | 32 of the 69 are CMCD `IDENTICAL` (elaborated terms equal; correct but no certificate). Erratum added to the SOTA-18 report (commit `900a889`). Plus 6 structural `NO_ASSUMPTION_DELTA` |
| non-equivalence verdicts | 3, 1 matching the label | confirmed; 0 concrete counterexamples |
| F1 unsound outputs | 47 (17 wrong) | confirmed |
| universe-polymorphic failures | 189 / 477 | confirmed |

## 2. Why ProofScope won the four cases

All four certificates have the same shape. ProofScope aligned the binder telescopes, saw that the
conclusions were identical, and proved the **hypothesis sets** equivalent (`a_implies_d`,
`d_implies_a`, with kernel `link_R`/`link_L` tying them to the elaborated statements). The conclusion
never enters the proof.

| Pair | Hypothesis change | Side goal that decides it | Mathematical reason | SemantEq | BEq+ |
|---|---|---|---|---|---|
| miniF2F 68 | drops `x ≠ -1` | `(x-9)/(x+1) = 2 ⊢ x ≠ -1` | Lean's `x / 0 = 0`: at `x = -1` the left side is `0` | proved one direction in 4.6 s, stopped at 26 s | rejected, 12.7 s |
| miniF2F 430 | drops `0 < m ∧ 0 < n` from additivity | `(∀ m n > 0, Δ ∈ {0,1}) ⊢ ∀ m n, Δ ∈ {0,1}` | truncated subtraction: `f n - f 0 - f n = 0` | inconclusive, 101 s | rejected, 7.2 s |
| miniF2F 237 | drops `0 < a ∧ 0 < b` | `a % 10 = 2, b % 10 = 4 ⊢ 0 < a ∧ 0 < b` | units digits exclude 0 | one direction, 33 s | rejected, 6.1 s |
| miniF2F 298 | adds positivity of `i, m, o` | `i * m * o = 2001 ⊢ 0 < i ∧ 0 < m ∧ 0 < o` | a zero factor makes the product 0 | one direction, 29 s | rejected, 11.0 s |

The budget was not the limit: SemantEq stopped after 26–101 s of its 300 s. In three of the four it
proved the easy direction and failed exactly on the side goal ProofScope isolated.

**Is the advantage robust?** Pilot A0 (`experiments/sota19/ABLATION_PROTOCOL.md`, pre-registered) removes
ProofScope's extraction and alignment and keeps only its tactic portfolio:
`intro hR; intros; apply hR <;> first | assumption | T`.

{{A0_RESULT}}

Three of the four wins also rest on Lean encoding hazards (division by zero, truncated subtraction,
zero factors) that are catalogued as a defect class, with static checkers, by Ammanamanchi, Bhat and
Biderman (ICML 2026, `Shashi456/atp-checkers`). The phenomenon is known; certifying it *relative to a
reference statement* is what ProofScope adds.

## 3. A conceptual constraint every pivot must respect

Two true closed statements are logically equivalent. So no sound tool can certify that two correct
formalizations are "logically inequivalent"; a certified *difference* can only be

* a refutation: one statement is false (concrete counterexample), or
* a relation finer than logical equivalence (ACE's structure-aware equivalence, SemantEq's audited
  equivalence, ProofScope's abstraction-relative and per-hypothesis relations).

This explains SOTA-18's zero concrete counterexamples, and it is why the pivot below targets
*explanations* (where does coverage differ, and does the conclusion hold there) rather than a
"non-equivalent" bit.

## 4. The options, ranked

| | Novelty | Usefulness | Differentiation | Difficulty | Fit for $70k | Rank |
|---|---|---|---|---|---|---|
| **A. Certified drift explainer (with gap certification)** | moderate: method, not theorem | high for autoformalization pipelines and benchmark audits | clear: localized, certified, directional | moderate | good | **1** |
| D. Directional-fidelity benchmark | low–moderate (Ground False, ShadowBench, ProofNetVerif exist) | high | moderate | low | good | 2 (as A's evaluation vehicle) |
| C. Regression / theorem-drift auditor (Mathlib versions, manuscripts) | low | uncertain: no user evidence yet; Mathlib already tracks deprecations | low | moderate | poor (needs users first) | 3 |
| B. General certified equivalence engine | low | high in principle | none: SemantEq, BEq+, ACE already, and better (p < 10⁻⁶) | high | poor | 4 |
| E. Reference-free certified refutation | low: Lean Disprove (ICML 2026) exists | high | none on its own | moderate | poor | merged into A as the guided-refutation half |

**Primary: A.** D is its evaluation instrument, not a second project. C waits for evidence of users.

**Stop developing:** the Nat-only ScopeElim / Presburger / multi-occurrence line (SOTA-14–17; 5 of 477
real statements parse in its grammar); SHARPEN; CMCD's abstraction-relative separations as a fidelity
signal (3 NONEQUIV outputs in 477, one disputed); the printed-text round-trip adapter; WESTFALL
Level-3 chasing as a goal in itself; synthetic benchmarks as headline evidence.

## 5. Technical analysis

| Item | Category | Assessment |
|---|---|---|
| Lean-native `Expr` input (no text round trip) | engineering, known technique | removes the 189 universe failures and 45 adapter failures; prerequisite |
| universe- and typeclass-aware alignment | engineering | `forallTelescope` + instance-aware `isDefEq`; binder permutation search is the only non-trivial part |
| fail-closed elaboration, certificate replay | engineering, known | fixes F1; tests in section 9.1 |
| assumption-redundancy proofs | known (implication between hypothesis sets); A0 measures what ProofScope adds | |
| directional entailment certificates | known (apply + side goals) | |
| sound counterexamples | known (Lean Disprove, `decide`, Plausible-style search) | |
| **reference-guided gap certification** | **candidate method contribution** | uses the other formalization to (i) choose where to look for a counterexample (`¬A`) and (ii) prove harmlessness only on the gap; testable against unguided search at equal budget (SOTA-19A) |
| human-readable explanations | engineering | the gap witness *is* the explanation ("drops `n > 0`; at `n = 0` the claim fails: `1 - p` is a nonzero constant") |
| a Level-3 theorem | speculative | **no credible path visible now.** The gap principle is elementary logic (case split on `A`). The best realistic outcome is a solid method + benchmark paper, not a new theorem |

## 6. The four wins as a research program

General principle: **conclusion-relative redundancy** — a hypothesis `A` is harmless for a claim `P`
under shared context `C` iff `∀ x, C x → ¬A x → P x`. ProofScope today checks only the stronger
`∀ x, C x → A x` (empty gap) and never evaluates `P` on the gap. Two of SOTA-18's three "not
equivalent" outputs are explained by exactly that omission:

* miniF2F 425 drops `0 < n`; the gap is `{n = 0}` and `gcd 4 3 = 1` holds there: harmless, so ProofScope's
  "stronger" verdict was the wrong *kind* of answer.
* Rudin 1.18b drops `x ≠ 0`; the gap is `{x = 0}` and `¬∃ y ≠ 0, 0 * y = 0` fails there: the candidate is
  false, a certified refutation ProofScope did not produce.

Independently sourced tests of the principle: the 60 hypothesis-only pairs of ProofNet → ProofNet-Verified
(21 of them are missing-premise errors with a false original), the ProofNet# → ProofNet-Verified labels, and
SOTA-18 Track B (development only). The benchmark must include pairs where the gap is infinite or
undecidable (most `incomparable` pairs), where it is expected to fail.

## 7. Grant reviewer challenge

1. *Why fund it?* Faithfulness checking is the weak link of autoformalization and of formal benchmarks
   (56 % unfaithful ProofNet references; benchmark-defect audits at ICML 2026). Certified, localized
   explanations are missing infrastructure; the code and data would be open.
2. *Obstacle addressed.* Equivalence checkers return "equivalent" or nothing. Builders of
   autoformalization pipelines and benchmark maintainers need to know *how* a statement is wrong.
3. *Evidence of execution.* Public, pre-registered, CI-reproduced evaluations, including negative results
   (SOTA-18), a self-found soundness bug reported openly, a working Lean 4 / Mathlib pipeline. The
   honest weakness: the PI is not a mathematician and the work so far is AI-executed. A named Lean
   collaborator or advisor would strengthen this more than anything else.
4. *Scientific interest.* Whether reference-guided search makes certified refutation and harmlessness
   proofs tractable on real misformalizations, measured against unguided search.
5. *Not just a new interface?* Only if SOTA-19A shows guided gap certification beats both the checkers'
   certified output and unguided refutation. If it does not, it *is* just an interface, and the kill
   condition says so.
6. *What $70k buys.* Section 9.
7. *Reasons to reject.* SOTA-18 shows ProofScope losing to existing tools; the niche (hypothesis-only
   drift) is 60 of 214 non-identical ProofNet → ProofNet-Verified pairs (28 %); strong groups (ACE, Ground False, Lean Disprove) work
   nearby; single-person, non-specialist team; no external users yet.
8. *Most credibility-raising new evidence.* SOTA-19A passing its pre-registered success condition on
   the held-out labels; an external Lean expert's review of the certificates; one external user
   (a benchmark maintainer) adopting the tool.
9. *Valuable without a new theorem?* Yes, if the released tool produces certified explanations on a
   measurable share of real misformalizations and the directional benchmark is reused.
10. *Better framing.* "Certified explanations for formalization drift" (what changed, does it matter,
    where does it fail), not "a state-of-the-art statement auditor" or "a new equivalence checker".

**On the submitted application:** the fund's page lists seed grants up to $100,000, reviewed on a rolling
basis, in four categories including early-stage prototypes, datasets and benchmarks, and tools or
infrastructure experiments, and requires open-access outputs. It does not state whether applicants may
send updates after submission. Do not send unsolicited revisions; if an update seems warranted (for
example SOTA-19A's result), first ask the fund's listed contact whether updates are accepted. Evidence
producible during review: the public SOTA-18 report and SOTA-19A results on GitHub. Longer-term: a
preprint and an external collaborator for any future, larger application.

## 8. Success and failure, defined in advance (12-month targets)

| Quantity | SUCCESS | PIVOT AGAIN | STOP |
|---|---|---|---|
| unsound certified outputs (any held-out set) | 0 | 0 | any unrepaired |
| correct certified directional verdicts on non-identical ProofNet → PN-V pairs | ≥ 25 % of 214 | 10–25 % | < 10 % |
| correct certified verdicts SemantEq's certified output lacks | ≥ 30 | 10–29 | < 10 |
| guided vs unguided refutations (equal budget) | ≥ 1.5× | 1.1–1.5× | ≤ 1.1× |
| same ordering on a fresh held-out set (built in months 7–9) | yes | partly | no |
| median time per pair | ≤ 60 s | ≤ 300 s | > 300 s |
| certificate replay (`leanchecker`) of every verdict | 100 % | – | < 100 % |
| external use | ≥ 1 external user or benchmark maintainer runs it | interest only | none |

SUCCESS permits a narrow claim: "first open tool producing certified, localized explanations of hypothesis
drift, better than X on Y". Never a general SOTA claim.

## 9. Twelve-month roadmap

### 9.1 Months 1–3: foundations
* Lean-native comparison core (metaprogram: elaborate once, telescope, align, emit obligations as `Expr`).
* Fail-closed: abort on any elaboration error, `sorry`, or unlinked extraction; `NO_ASSUMPTION_DELTA`
  only with a link certificate.
* **F1 regression tests:** `experiments/sota18/soundness/universe_sorry_u3.json`, `u4.json` and the
  Mathlib probe `synth:c05` must return INCONCLUSIVE / abstain; a property test that injects elaboration
  errors into 100 random SOTA-18 statements and requires zero decisive outputs.
* Re-run SOTA-18 on the new core (same frozen pairs): target ≥ 150 of the 189 universe failures elaborated.
* Milestone M1: SOTA-18 rerun with 0 unsound outputs and the universe failures resolved.

### 9.2 Months 4–6: gap certification
* Gap obligations (harmlessness on the gap, guided refutation from `¬A`), certificate assembly, explanations.
* SOTA-19A on ProofNet → ProofNet-Verified with its kill condition.
* Milestone M2: SOTA-19A decision (continue / kill).

### 9.3 Months 7–9: independent evaluation
* Held-out: ProofNet# → ProofNet-Verified labels; a fresh set of autoformalizer outputs on held-out
  problems, labelled by two independent annotators blind to all tool outputs, frozen before running.
* Competitors: SemantEq, BEq+ native; ACE and Lean Disprove if code becomes runnable.
* Milestone M3: frozen, CI-reproduced report with denominators and failure taxonomy.

### 9.4 Months 10–12: public deliverables
* Open-source tool (Lean package + CLI), directional-fidelity benchmark with provenance and licenses,
  preprint (workshop or D&B track), documentation, demonstration on a public benchmark audit.

### 9.5 Illustrative budget ($70,000)

| Item | Amount | Note |
|---|---|---|
| Researcher support (PI, 12 months, part-time) | $46,000 | eligibility of individual stipends to confirm |
| Lean / Mathlib expert advisor or contractor (code and certificate review, ~100 h) | $10,000 | confirm allowed |
| Independent annotation of the held-out set (2 annotators, ~400 pairs) | $6,000 | confirm allowed |
| Compute and API (LLM-generated candidate formalizations, occasional large runners) | $4,000 | GitHub Actions is free for public repos |
| Dissemination (workshop registration, travel, open-access fees) | $3,000 | confirm travel eligibility |
| Contingency / fiscal-sponsor fees | $1,000 | if a fiscal sponsor is required for an individual |

## 10. GitHub implementation plan

* Branch `research/sota19-strategic-pivot` (this document, A0, the SOTA-19A specification). No change to
  `main`, no merges, no history rewrites.
* SOTA-19A goes in `experiments/sota19a/` with a new `lean/ProofScope/Compare.lean` metaprogram; the
  existing engines stay untouched as the baseline. The metaprogram is the smallest piece that makes the
  experiment possible; the full architecture change waits for SOTA-19A's verdict.
* CI: one workflow per experiment, records committed by the workflow, pre-registration committed first.

## Sources

An, Min, Si, Bastani, *Ground False*, NeurIPS 2026 D&B (ProofNet-Verified); Ammanamanchi, Bhat, Biderman,
*Faults in Our Formal Benchmarking*, ICML 2026; *Lean Disprove: Certified Counterexample Search*, ICML 2026;
Yu et al., *Structure-Aware Equivalence*, arXiv 2610.25018; SemantEq v1.4.0; Poiroux et al., EMNLP 2025;
Renaissance Philanthropy, AI for Math Fund page (seed grants), accessed 2026-11-11.
