# ProofScope SOTA-8 — certified directional derivation

Caleb J. Westfall · branch `research/proofscope-sota8` from `a7bd9bb` (PS-25R + source headers).

**Evidence labels:**
- [L] observed in the development sandbox, in core Lean;
- [T] verified by tests;
- [CI] produced by `.github/workflows/sota8-research.yml`, not yet run;
- [U] not verified here.

## 1. Verdict
**More capable than PS-25R on development cases [L][T]; not SOTA on any defined task.**

The Pilot-25 effect is [CI]. PS-25R's artifacts (run 42763495825) could not be downloaded here, so its
counts (1 certified, 9 inconclusive, 13 not evaluable) are used as reported [U].

## 2. Deepest cause of low coverage, and the change
**The CJCS engine never derives one statement from the other.** It certifies equivalence in only three ways:
- by definitional equality;
- by proving both statements outright;
- by refuting both.

For real theorems (Baire, Tietze, solvable subgroups and the like), proving the theorem itself is out of
reach. Deriving one formulation from the other is often routine: reordered binders, implicit versus explicit
binders, split hypotheses, `Fintype` versus `Finite`.

**SOTA-8 adds directional derivation obligations**:
- `impl_RC : (R) → (C)`;
- `impl_CR : (C) → (R)`.

They are searched with a bounded portfolio in which the other statement is available as a hypothesis:
`exact h ..`, `apply h` + `assumption`/`infer_instance`, `solve_by_elim`, `simp_all`, `simpa using h`, `omega`,
`exact?`, and with Mathlib also `aesop` and `tauto`.

**Prior art, stated plainly:** BEq+ (Poiroux et al., EMNLP 2025) proves each statement from the other with
restricted tactics. The derivation idea is theirs. **SOTA-8 does not claim novelty for it.**

What SOTA-8 adds:
- the two directions are kept separate, and a single certified direction is reported as one-way, with the
  converse UNKNOWN unless CJCS certifies a difference;
- it is combined with CJCS's certified refutations;
- every result goes through the clean verifier, the axiom audit, `leanchecker`, and SOTA-7's blinded,
  sealed replay.

## 3. Soundness fixes found on the way [L][T]
* **`autoImplicit` was on in every engine session and certificate** (Lean's default). A misspelled or
  undefined name silently became a universally quantified variable, so the engine could certify a different
  statement: development case g4 `n + zeroish = n` produced a one-way certificate before the fix.
  - `set_option autoImplicit false` is now in the search session and in every certificate header (both
    engines), so such inputs are INPUT_NOT_EVALUABLE.
  - This is the J3 risk from the SOTA-4 audit; it had now produced an actual certificate.
* **Well-formedness check.** `(S) → True` is used instead of `(S) → (S)`: two copies of a `Type _` / `Type*`
  statement get different universe parameters and need not unify.
* **Scoring correction, found by the synthetic run.** `2 + 2 = 4` and `∀ n, n + 0 = n` were "derived" from
  each other by proving each side outright.
  - Mutual derivation is therefore scored as **closed-level** evidence (CLOSED_ONLY_* unless the gold is
    EQUIVALENT), never as formulation-level correctness.
  - A one-way certificate scores at most CORRECT_PARTIAL.

## 4. Development results [L] (developer-written; not independent)
| case | CJCS (PS-25R engine) | SOTA-8 |
|---|---|---|
| g1: two formulations of a Goldbach-type statement (binder order, implicit `{n}`, `>` vs `<`) | ABSTAIN (truth unknown) | **certified equivalence by derivation**; neither side proved |
| g3: candidate adds `n % 8 = 1` | ABSTAIN | **certified reference ⇒ candidate**; converse UNKNOWN |
| g4: free identifier | certified one-way (before the `autoImplicit` fix) | INPUT_NOT_EVALUABLE |
| g5: shared declared universe | ABSTAIN | certified equivalence |

**SOTA-7 synthetic set** (11 cases, gold withheld, sealed, replayed):

| engine | correct | correct, partial | closed-only agreement | repair mismatch | abstain | decisive errors |
|---|---|---|---|---|---|---|
| cjcs4 | 7 | 0 | 1 | 1 | 2 | 0 |
| SOTA-8 | 7 | 1 | 1 | 1 | 1 | 0 |

SOTA-8's median CPU was 3.7 s, the same as cjcs4. In the SOTA-8 column, `division_nonzero` became a certified
one-way implication.

## 5. Regressions [T]
- **Tests:** 82 prior tests plus 6 SOTA-8 tests pass.
- **24 core pairs:** the same verdicts and certificates as the SOTA-4 record, with `autoImplicit` off.

## 6. Pilot-25 paired rerun [CI]
The `pilot` job runs the same 23 cases (same strings and hashes, source headers from `a7bd9bb`) under both
engines. Both get the same budget: 12000 MB and 900 CPU-s, the PILOT_PROTOCOL_v1 measurement policy. Each run
is sealed and replayed.

`compare` writes a per-case table with certified counts, CPU, peak memory and certified results per CPU-hour.
It **fails** if any decisive claim lacks a verified certificate. There are no gold labels, so no accuracy is
reported.

## 7. Performance
- **Development (core Lean):** about 4 s per case; each delta stage is one REPL session, then verification.
- **Memory:** no architectural change. Peak memory on Mathlib is set by the Mathlib-mapped baseline, which
  PS-25R reported at about 10.7 GB. When derivation fails, SOTA-8 runs CJCS afterwards in a *second* session,
  sequentially, so peak memory does not rise but CPU does on those cases. [CI] measures the effect.

## 8. Certificates
Every accepted result needs:
- a clean compile;
- an axiom set within {propext, Classical.choice, Quot.sound};
- `leanchecker` replay;
- SOTA-7 source identity, rebuilt from the public strings, which now covers `impl_RC`, `impl_CR` and `equiv`.

A forged derivation is rejected by the verifier [T].

## 9. Remaining weaknesses
* **Closed-level only.** Derivation certifies relations between closed propositions. When both sides are
  provable, a derivation can ignore its hypothesis. The engine does not yet check whether the proof term
  uses the hypothesis, which would separate "genuine derivation" from "both true".
* **Universes.** Statements with independent universe parameters are compared at independent universes.
  That is sound, but stronger than needed, so some true equivalences will be missed.
* **Strictness.** No certified *strict* one-way relation without a CJCS refutation. Refutation still covers
  only decidable small domains, with no Mathlib-structure countermodels.
* **Inputs.** 13 Pilot-25 inputs were not evaluable in PS-25R; several have genuine source defects (missing
  `open` context, `...`, free variables) that no engine should "fix".
* **No independent labels** and no competitor run on shared cases. BEq+ is the natural paired baseline,
  using the same derivation idea.

## 10. Publication potential
- **Not yet.** A credible paper needs a paired, blinded comparison against BEq+ on independently labelled
  pairs, measuring certified one-way implications and certified refutations that BEq+ does not report.
- **Possible contribution:** a sound three-way relation classifier with replayed certificates and honest
  abstention. The derivation idea itself is BEq+'s.
