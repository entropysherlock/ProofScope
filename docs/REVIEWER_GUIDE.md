# ProofScope — Technical Reviewer Guide

**Project:** ProofScope — *Verify the proof. Validate the claim.*  
**Research lead:** Caleb J. Westfall  
**Repository:** https://github.com/entropysherlock/ProofScope  
**License:** MIT (see repository LICENSE and notices for third-party material).

## Start here: use the advanced engine, not default `main`

**The most advanced merged and GitHub Actions-validated version at the time of this guide is on [`v1.2-review`](https://github.com/entropysherlock/ProofScope/tree/v1.2-review), commit [`198e17c`](https://github.com/entropysherlock/ProofScope/commit/198e17c313e0752e948ce2f2bc32d74aa7c7cdc5).**

The default branch (`main`) contains an earlier public prototype and workflow launchers. **Do not evaluate the current research engine from `main` alone.** The default branch has not been promoted to the advanced release, pending repository integration decisions. Branch and evidence links below are pinned to documented work; check the latest commits before relying on this guide as a current status report.

## What is ProofScope?

ProofScope is an experimental, open-source system for auditing Lean theorems and comparing the **mathematical strength** of a stated reference claim with a formal claim. Unlike a check of whether a Lean proof is accepted, it investigates whether a formally valid statement has been strengthened, weakened, or changed in other ways *under explicitly stated semantic/abstraction policies*.

The project supports:

- Lean declaration/dependency/axiom inspection, proof checks, and theorem dossiers.
- Comparison certificates for equivalence, strict weakening/strengthening, and incomparability within supported fragments, with countermodels where available.
- ClaimDelta, Assumption Delta, and compositional claim-drift analyses.
- Finite definite-Horn inference and restricted function-symbol scope elimination.
- Lean-checked Presburger witness/instantiation certificates for supported one-occurrence affine function arguments.
- A fail-closed certificate pipeline: untrusted search (including Z3 where used) proposes candidates; Lean compilation, axiom checks, and kernel replay determine acceptance.

**Not supported as a general claim:** automatically verifying a mathematical paper's *intended meaning* against arbitrary Lean code, completeness of the Python implementation for every supported mathematical theorem, or end-to-end analysis of unrestricted Mathlib declarations.

## Direct verification evidence

| Evidence | Outcome / scope |
| --- | --- |
| [SOTA-16 CI reproduction](https://github.com/entropysherlock/ProofScope/actions/runs/42950230302) | Four benchmark/evaluation jobs completed successfully on GitHub Actions. |
| [SOTA-16 validation](https://github.com/entropysherlock/ProofScope/actions/runs/42950230245) | Lean compilation and fresh kernel replay for seven modules; Python regression workflow successful. |
| [SOTA-16 research report](https://github.com/entropysherlock/ProofScope/blob/v1.2-review/docs/sota16_presburger.md) | Exact mathematical fragment, theorem names, evaluation design, nine open directions, known limitations. |
| [v1.3 release report](https://github.com/entropysherlock/ProofScope/blob/v1.2-review/docs/v1.3_release.md) | Earlier SOTA-14/15 integration, soundness fixes and benchmark provenance. |
| [SOTA-16 integration PR #6](https://github.com/entropysherlock/ProofScope/pull/6) | Merged into `v1.2-review`; history and changes are reviewable. |

### Reported and reproduced benchmark (restricted, author-generated)

The SOTA-16 frozen set contains **120 cases, 240 directed comparisons**. GitHub Actions reproduced:

| Metric | Previous v1.3 portfolio | SOTA-16 |
| --- | ---: | ---: |
| Directions certified | 178 / 240 | **231 / 240** |
| Decisive case verdicts | 68 / 120 | **111 / 120** |

An additional labelling procedure using Z3, cvc5 and explicit function witnesses labelled 237/240 directions; **230 of SOTA-16's 231 certified directions received a label and all 230 agreed.** One certified result (`fl105` forward) lacked an independent label. The case generator, engine, and labeller share an author; this is *methodological cross-checking, not an externally authored blind evaluation*. Nine directions remain inconclusive.

**Do not infer state-of-the-art performance or broad real-world Mathlib coverage from these figures.**

## Reproduce from the source

Prerequisites: Git, Python 3.12 (or a supported tested version), Lean **4.34.1**, and any optional dependencies required by the experiment; GitHub Actions gives the most directly reproducible environment.

```bash
git clone https://github.com/entropysherlock/ProofScope.git
cd ProofScope
git switch v1.2-review
git rev-parse HEAD
lean --version
python3 -m unittest discover -s tests/v02 -v
python3 -m proofscope.claimdelta --help
```

For full Lean module kernel replay and benchmark regeneration, use the **successful pinned GitHub Actions workflow runs linked above** and inspect their exact workflow YAML, tool versions, source hashes, job logs, and artifacts. Some tests require optional dependencies and may skip without them. This quickstart runs a regression suite and prints CLI help; it is **not** an end-to-end fidelity proof.

## Trust model and open problems

- A kernel-checked certificate proves its **formal Lean proposition**, not automatically that an informal paper was transcribed faithfully.
- Verdicts are relative to a stated abstraction policy. A separating interpretation need not be the concrete mathematical interpretation.
- Python grounding-to-Lean finite-Horn rule-list correspondence has not been fully formalized end to end.
- SOTA-16 completeness depends on search/tactic limits; the implementation is not a full Presburger decision procedure.
- No independently authored, large-scale external Mathlib or head-to-head competitor benchmark has yet established superiority.
- Research on multi-occurrence symbols (SOTA-17) is experimental and must not be described as a verified release until source and evidence are published.

## Where to look next

- [Advanced engine README](https://github.com/entropysherlock/ProofScope/blob/v1.2-review/README.md)
- [ClaimDelta overview](https://github.com/entropysherlock/ProofScope/blob/v1.2-review/docs/v0.8_claimdelta.md)
- [Assumption Delta](https://github.com/entropysherlock/ProofScope/blob/v1.2-review/docs/v1.0_assumption_delta.md)
- [SOTA-16 Lean formalization](https://github.com/entropysherlock/ProofScope/blob/v1.2-review/lean/ProofScope/PresElim.lean)
- [SOTA-16 adversarial tests](https://github.com/entropysherlock/ProofScope/blob/v1.2-review/tests/v02/test_sota16_adversarial.py)

**Reviewer recommendation:** Inspect the scope and claims first, then the linked successful CI runs and exact Lean statements. The primary contribution to assess is *certified, explainable directional statement-drift analysis*, not unrestricted automated theorem proving.
