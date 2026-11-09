# ClaimDelta certified evidence and interrupted 208-case evaluation

## Verified in GitHub Actions

Original run: https://github.com/entropysherlock/ProofScope/actions/runs/42625730645
Source commit: `9eae715aa65c4b96be6f1463e3a25871c3908b3f`

The run log established these **completed** checks:
- Exact Lean 4.34.1 installation and frozen SHA checks: PASS.
- All 15 Lean ClaimDelta theorems: PASS, axiom checks and fresh kernel replay.
- Unit and end-to-end tests: 7/7 PASS.
- Internal v0.8 development benchmark: **25/25** exact labels.

Development verdict distribution:
- SCHEMA_EQUIVALENT: 8
- EQUIVALENT_BY_LAWS: 2
- NO_SHARED_SYMBOLS: 4
- CLAIM_LEAN_WEAKER: 8
- CLAIM_INCOMPARABLE: 2
- CLAIM_LEAN_STRONGER: 1

The same run **did not complete** the larger 208-case v0.6 evaluation:
the runner received a shutdown signal (exit 143) before emitting results.
The runner shutdown prevented evidence-artifact upload; the linked
GitHub job logs are the historical evidence.

## Reproducible follow-up

- The unchanged frozen ClaimDelta engine is checked by its original freeze file.
- `ProofScope ClaimDelta Certified` now reports only 15-theorem and
  25-case development certification, without blocking on 208 longer cases.
- `ProofScope ClaimDelta 208 Sharded` splits the previously requested 33 dev
  and 175 oracle cases into eight deterministic shards of 26.
- Every shard uploads its case manifest (including original SHA-256 per file),
  execution log, and complete machine-readable results independently, including
  partial logs if its work fails.
- Aggregation rejects missing shards, missing cases, duplicates, changed
  source hashes, incomplete results and INCONSISTENT verdicts. It publishes
  every inconclusive verdict and any benchmark label disagreements.

These are project-authored research tests. Neither internal-suite success
nor a green CI badge proves state-of-the-art superiority.

**Do not describe the earlier 208-case run as successful. Its test result
was incomplete; the separate sharded workflow must finish first.**
