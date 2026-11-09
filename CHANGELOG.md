# Changelog

## 0.6.0 (unreleased)

- `lean/ProofScope/Soundness.lean`: nine axiom-free soundness/observability theorems (fresh replay in CI).
- `lean/ProofScope/Tactics.lean` (`ps_arith`) and instantiation-based quantifier closers in `compare.py`; both v0.5
  held-out misses fixed; that split renamed `dev_v05_heldout`; engine re-frozen.
- `proofscope/benchmark/gen_oracle.py` + `heldout_oracle/` (175 oracle-labelled cases); `bench.py`: split discovery,
  `--jobs`, per-family metrics, inconclusive rate, p90 runtime, oracle cross-check.
- `proofscope/research.py` + **ProofScope Research Audit** workflow (network/env isolation); dossier `--replay-limit`
  and NOT_REPLAYED status.
- `proofscope/competitors/semanteq.py` + **ProofScope Competitor Comparison** workflow.
- Viewer: paper trace, separate proof-certification and semantic-review status, comparison table.
- `tests/v02/test_v06.py`; `docs/v0.6_report.md`.

## 0.5.0 (unreleased): engine slice of the v1.0 roadmap

- `lean/ProofScope/Dossier.lean` + `proofscope/dossier.py`: elaborator-based theorem dossiers (Project Audit S8).
- `proofscope/certify.py`: generic certificate gate (clean module, axiom policy, leanchecker replay).
- `proofscope/compare.py`: theorem-level comparison with certified gap / vacuity / equivalence / coverage labels.
- `proofscope/bench.py` + `proofscope/benchmark/`: 33 dev, 20 held-out (post-freeze) cases, 20 adversarial
  certificate cases; metrics with Wilson 95% intervals; naive baseline.
- `proofscope/viewer.py`: offline HTML report.
- Workflow **ProofScope Engine**; Project Audit input `dossiers`.
- `tests/v02/test_engine.py`; `docs/engine.md`.

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
