# Changelog

## 0.3.0 (unreleased)

- `python3 -m proofscope.review` and Project Audit stage S7 (`--worksheets`, workflow input `worksheets`, default on):
  scope-fidelity worksheets pairing each scope document with Lean comparator sources, junk-value exposure flags,
  and a typed review ledger (`HUMAN` vs `AI_PRELIMINARY`) that applies only to the commit it names.
- `reviews/openai_math_4eaee875.json`: 10 AI-preliminary statement reviews.
- `tests/v02/test_review.py`.


## 0.2.0 (unreleased)

Added, without changing any v0.1 file:

- `python3 -m proofscope.project` and the **ProofScope Project Audit** workflow: audit a pinned commit of a public
  Lean project (provenance, dependency pins, hashed import closure, trust-hazard scan, `formalization.yaml`
  catalog checks; opt-in build, `#print axioms` and `leanchecker` replay).
- `python3 -m proofscope.fidelity` and the **ProofScope Fidelity** workflow: Lean-checked certificates that two
  definitions agree or disagree on the domain a theorem uses, with 13 bundled cases (controls, mutants and two
  real definitions from the OpenAI comparator corpus) and a static scanner.
- `evidence/`: archived, unmodified outputs of the WESTFALL V23, V0.8 and V0.9-R Colab runs and the v0.2 local runs, with SHA-256 checksums.
- `tests/v02/`: unit, end-to-end (Lean fixture project) and opt-in network tests.

## 0.1.0

- **ProofScope Audit** workflow: honest/forged kernel controls with `leanchecker --fresh`.
