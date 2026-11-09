# Local evidence (sandbox, not CI)

Produced in the development sandbox: Lean 4.34.1 (x86_64 Linux), leanprover-community/repl `193cf4bb`,
**core Lean only (no Mathlib: the Mathlib cache is not reachable from the sandbox)**. Same accounting as the
benchmark (`bench/limits.py`, whole process tree). These numbers are not the Task G measurement, which is
defined on the Mathlib development suite and is produced by the `mathlib-measure` job of the SOTA-4 workflow.

* `core-variantA/`, `core-variantB/`: final engine, 24 core pairs, both engines (records.json is case level).
* `hostile-first-build/`: 12 hostile pairs, both engines (engine build with the compiled search module; the
  verdict logic is unchanged since, and the hostile unit test re-runs the suite on the final engine).
* `theory/`: CJCS.lean axiom report and `leanchecker --fresh` log.
* `core_verdicts.*`: every verdict and certificate of both engines on core_dev and core_heldout (Task C).
* `unit-tests.log`: tests/sota4 (33 tests).
* `superseded/`: earlier SOTA-4 builds, kept as negative results. v1 elaborated each tactic alternative as
  a separate command: same verdicts, **slower than SOTA-3** (median 6.36 vs 5.64 CPU-s, variant A). v2
  compiled the search module per case: still slower in variant A (6.62 vs 5.64).
