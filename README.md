# ProofScope
### Verify the proof. Validate the claim.

**An open-source, Lean-backed research engine for certified mathematical statement comparison and proof-scope auditing.**

Developed by **Caleb J. Westfall** · Experimental research software · MIT licensed

[**Explore the advanced engine**](https://github.com/entropysherlock/ProofScope/tree/v1.2-review) · [**Technical reviewer guide**](docs/REVIEWER_GUIDE.md) · [**Verified CI results**](https://github.com/entropysherlock/ProofScope/actions/runs/42950230245) · [**Benchmark reproduction**](https://github.com/entropysherlock/ProofScope/actions/runs/42950230302)

> **Where is the current engine?** The most recent *merged, verified* research engine is in **[`v1.2-review`](https://github.com/entropysherlock/ProofScope/tree/v1.2-review)**, SOTA-16 merge commit [`198e17c`](https://github.com/entropysherlock/ProofScope/commit/198e17c313e0752e948ce2f2bc32d74aa7c7cdc5). This default `main` branch still contains an earlier prototype. Follow the advanced-engine link for the current code; it has not yet been promoted to the default branch.

## The problem ProofScope addresses

**A Lean proof can be valid while its theorem is different from the mathematical claim someone intended to formalize.** Proof checking establishes formal correctness, but it does not by itself establish that the formal statement captures the intended mathematics.

ProofScope investigates *how* two explicitly supplied formal claims relate. Within supported, precisely specified fragments, it generates machine-checkable evidence to classify statements as:

| Relation | Meaning |
| --- | --- |
| **Equivalent** | The claims match under the defined comparison semantics. |
| **Formal claim weaker** | The formal claim demands less than the reference claim. |
| **Formal claim stronger** | The formal claim demands more than the reference claim. |
| **Incomparable** | Neither uniformly entails the other under the declared abstraction. |
| **Inconclusive / unsupported** | ProofScope cannot certify a decisive conclusion. |

This is **abstraction-relative mathematical statement analysis**. An abstract countermodel is not automatically a real-world counterexample to the concrete mathematics; human review is required when interpreting informal references.

## What is implemented

The merged development engine includes:

- **Proof-scope audit:** Lean declarations, dependencies, axioms, theorem dossiers, and fresh kernel replay.
- **ClaimDelta and Assumption Delta:** certified statement-strength comparisons and hypothesis-change analysis in supported fragments.
- **Certified comparisons:** accepted Lean certificates for applicable implications and separating interpretations where available.
- **ScopeElim:** finite definite-Horn reasoning and restricted single-occurrence function-symbol elimination.
- **SOTA-16 Presburger extension:** automated arithmetic witness/instantiation tactics for supported affine argument forms, with Z3 as *untrusted search* and Lean as the certificate authority.
- **Safety and reproducibility controls:** false-reference protection, conservative abstention, regression tests, pinned toolchains, and archived GitHub Actions results.

**Not yet general-purpose:** unrestricted theorem comparison, automatic interpretation of arbitrary mathematical papers, or fully integrated multi-occurrence function reasoning. The SOTA-17 work on broader fragments is experimental until separately published and validated.

## Verified research milestone: SOTA-16

On a **frozen, author-generated set of 120 cases (240 directed comparisons)**, the corrected SOTA-16 implementation improved over the preceding v1.3 portfolio:

| Reproduced metric | v1.3 | SOTA-16 |
| --- | ---: | ---: |
| Lean-certified directions | 178 / 240 | **231 / 240** |
| Cases receiving decisive verdicts | 68 / 120 | **111 / 120** |

**Independent-method labels:** Solver/explicit-function cross-checking provided labels for 237/240 directions. **All 230 labelled certified directions agreed**; one certified direction (`fl105` forward) had no independent label. Nine directed comparisons remain unresolved. These methods, the engine, and the case generator share an author, so **this is not an externally authored blind evaluation**, and no state-of-the-art claim follows.

| Evidence | Direct link |
| --- | --- |
| GitHub Actions: seven Lean modules and Python regressions | [Successful validation](https://github.com/entropysherlock/ProofScope/actions/runs/42950230245) |
| GitHub Actions: frozen and corrected evaluation + separate labels | [Successful reproduction](https://github.com/entropysherlock/ProofScope/actions/runs/42950230302) |
| Exact hypotheses, theorems, open cases, and limits | [SOTA-16 technical report](https://github.com/entropysherlock/ProofScope/blob/v1.2-review/docs/sota16_presburger.md) |
| Formal soundness and SOTA-15 integration | [v1.3 release report](https://github.com/entropysherlock/ProofScope/blob/v1.2-review/docs/v1.3_release.md) |
| Full integration history | [Merged PR #5](https://github.com/entropysherlock/ProofScope/pull/5) · [Merged PR #6](https://github.com/entropysherlock/ProofScope/pull/6) |

## Reproduce the advanced engine

Lean **4.34.1** is required for the pinned formal checks. Python 3 is required; some suites use optional dependencies. The commands below inspect the latest development branch and run its existing Python regression suite:

```bash
git clone https://github.com/entropysherlock/ProofScope.git
cd ProofScope
git switch v1.2-review
lean --version
python3 -m unittest discover -s tests/v02 -v
python3 -m proofscope.claimdelta --help
```

For the exact Lean kernel replay and experiment reproduction, follow the successful CI links above and inspect the pinned commits, workflow steps, logs, and evidence artifacts. Passing the tests above is **not** an end-to-end assessment of paper-to-Lean fidelity.

## Research directions and open limitations

Our priority is **certified, explainable mathematical statement drift**: identify meaningful claim changes, show why the direction of change matters, and attach formal evidence a reviewer can independently check.

Current limitations include incomplete Python-grounding-to-Lean correspondence proofs, limited scope of function-symbol elimination, search caps and tactic incompleteness, and a lack of large-scale externally authored Mathlib/competitor benchmarks. **A sound certified verdict proves the checked formal proposition; it does not prove the informal paper was faithfully transcribed.**

Ongoing work explores **multi-occurrence symbols, coupled mathematical constraints, and genuine Mathlib-derived evaluations**. Those results will be announced only after repository publication and independent verification.

## Reviewer and project resources

- [Technical reviewer guide — capabilities, evidence, and caveats](docs/REVIEWER_GUIDE.md)
- [Advanced engine source and documentation](https://github.com/entropysherlock/ProofScope/tree/v1.2-review)
- [Project audit methodology](docs/project_audit.md)
- [ClaimDelta background](https://github.com/entropysherlock/ProofScope/blob/v1.2-review/docs/v0.8_claimdelta.md)
- [Historical README and development log](docs/README_HISTORY.md)
- [Full repository history](https://github.com/entropysherlock/ProofScope/commits)

---

**ProofScope is an experimental mathematical research platform, not a peer-reviewed general-purpose verification product.** We welcome reproducible scrutiny, precise counterexamples, and independent evaluation.

© Caleb J. Westfall · MIT License. Third-party code and examples retain their own notices.
