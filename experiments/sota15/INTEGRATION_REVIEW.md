# SOTA-15 integration audit — November 10, 2026

This is the **single integration branch** for SOTA-14 and SOTA-15. PR #4 (SOTA-14 standalone) has been closed as superseded, not merged. All original SOTA-14 source remains preserved on its original branch and was copied into this branch.

## Change 1: ClaimDelta false-reference law verdict

Root cause: `claimdelta.py` previously promoted a certificate for one missing implication to `EQUIVALENT_BY_LAWS`, and described this as harmless rewriting, without checking whether the concrete reference was even true. False reference statements can make implications true vacuously.

Fix:
- Generate separate Lean obligations for the **positive truth of the concrete reference** (`refValid`) and **refutation** (`refFalse`).
- Both obligations pass through the existing certificate gate (Lean compile, accepted axioms and fresh replay).
- `EQUIVALENT_BY_LAWS` now requires a **positive kernel-checked** `refValid` certificate in addition to the previously required law implication.
- A certified `refFalse` is reported as `REFERENCE_REFUTED`, with the certificate attached.
- An unverified reference stays a schema/claim verdict; a proved missing implication is annotated as `IMPLICATION_PROVED_REFERENCE_UNVERIFIED`. Absence of a refutation is never treated as proof of validity.

This is deliberately conservative: some older equivalence-by-laws labels may now downgrade to claim-relative verdicts or require stronger tactics. Refutation detection remains incomplete, but that cannot fabricate the positive truth gate.

Regression: `tests/v02/test_v08_claimdelta.py::EndToEnd::test_false_reference_is_not_called_harmless_rewriting` uses original SOTA-15 `cd009`. It must yield a `refFalse` Lean certificate and `REFERENCE_REFUTED`, not `EQUIVALENT_BY_LAWS`.

## Change 2: Frozen vs post-fix vs current reproducibility

`.github/workflows/sota15-reproduce.yml` runs three provenance-separated comparisons:

1. `a2592a729d2f0a8686d0d7698a2df238b83873e1` — original frozen SOTA-15 engine (expected bounded Horn certified directions 108/120).
2. `2a215577a7d20a419e8d506498d334d892e30c7f` — Fable's post-freeze certificate correction (expected 109/120).
3. `research/sota15-scopeelim` — current integrated engine (expected native benchmark 109/120; ClaimDelta changes are a separate module).

Each stage records exact checked-out SHA, Lean/Python versions, frozen source hashes, regenerated cases, native result JSON, oracle/Z3 discrepancies, and comparison with the originally archived per-stage summaries. Runtime values are not asserted equal across machines. The historical summary is read from a separate checkout so the original frozen commit is never modified to add a report after the fact.

**Do not label these figures independently reproduced until the GitHub Actions jobs actually finish successfully.** This is still an author-generated benchmark, not a blind externally-authored evaluation.

## Change 3: Reconciliation

Copied unchanged from SOTA-14 standalone branch:
- `lean/ProofScope/Adversarial.lean`
- `lean/ProofScope/Cases.lean`
- `experiments/sota14/README.md`
- `experiments/sota14/REPRODUCE_ORIGINAL.md`

`lean/ProofScope/ScopeElim.lean` already existed in SOTA-15; its contents match SOTA-14 except a final newline. The new PR validation workflow compiles and fresh-replays all six Lean modules: ScopeElim, HornFin, MonoElim, Adversarial, Cases, ScopeCert.

## Merge gate

- [x] New Lean compilation and six fresh kernel replays pass.
- [x] Python regression suite passes, including cd009 false-reference test.
- [x] Frozen/post-fix/current benchmark job logs and artifacts inspected; case generation and original hashes verified.
- [x] No unexpected oracle or Z3 disagreements.
- [x] Evaluate changed label coverage from the conservative reference-validity rule.
- [x] Confirm that PR #5 is mergeable and no existing v1.2 functionality regressed.

**PR #5 remains draft until all relevant gates pass.** No Level 4 or independent state-of-the-art claim follows from this work.

Gate evidence and the two defects found while closing these gates: `docs/v1.3_release.md`.
