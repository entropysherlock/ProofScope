# ProofScope SOTA-14 — Exact schematic scope elimination

**Status:** Research source archived; **not yet wired into the Python engine**; reproduction pending fresh CI.

**Base:** `v1.2-review`, branch `research/sota14-scope-elimination`.

## Source
- `lean/ProofScope/ScopeElim.lean`: exact criteria for a definite-clause predicate schema, premise-free coverage, and once-occurring function schemas; choice dependency; illustrative multiple-occurrence boundary.
- `lean/ProofScope/Adversarial.lean`: adversarial examples, including chaining, cancellation, vacuity, interpretation-class changes.
- `lean/ProofScope/Cases.lean`: two manually proved schematic verdicts previously reported INCONCLUSIVE by v1.2.
- `experiments/sota14/REPRODUCE_ORIGINAL.md`: original Fable instructions and claims, preserved unaltered.

## Reproduction (from repository root)

Use the repository's pinned Lean 4.34.1 toolchain with the three modules compiled in import order. For example:

```bash
mkdir -p build/ProofScope
lean -o build/ProofScope/ScopeElim.olean lean/ProofScope/ScopeElim.lean
LEAN_PATH=build lean -o build/ProofScope/Adversarial.olean lean/ProofScope/Adversarial.lean
LEAN_PATH=build lean -o build/ProofScope/Cases.olean lean/ProofScope/Cases.lean
LEAN_PATH=build leanchecker --fresh ProofScope.ScopeElim
LEAN_PATH=build leanchecker --fresh ProofScope.Adversarial
LEAN_PATH=build leanchecker --fresh ProofScope.Cases
```

These are proposed reproduction commands; this import has **not** independently run them in a Lean environment. The original Fable report states that Lean 4.34.1 compiled and replayed the source. Verify actual toolchain setup and adjust paths if needed before treating the statements as rechecked.

## Interpretation limitations

- The exact theorems concern **uniform schematic entailment over explicitly abstracted symbols**, not automatic faithfulness to a paper's intended theorem.
- Classical antecedents (Horn least models and second-order elimination) mean mathematical novelty is **not established**; provisional Level 2.
- The undecidability consequence associated with repeated occurrences was **informal** in SOTA-14 and requires an independently checked reduction and precise decision-problem statement.
- Two cases are manually authored proofs, **not** evidence of an automatic new decision procedure or a blind benchmark.
- SOTA-15 goal: implement a proof-producing decision procedure for a specified decidable fragment, emit Lean certificates, connect it to the Python engine, and evaluate on unseen cases.

## Merge gate

1. Run Lean compilation, `#print axioms`, `leanchecker --fresh` on all modules.
2. Add CI / regression checks without weakening v1.2.
3. Integrate into the engine only after certified automation exists.
4. Keep claims qualified, and disclose all abstentions and incomplete obligations.

Keep all SOTA-14 source and subsequent engine code in this same ProofScope repository. Avoid standalone forks as the source of truth.
