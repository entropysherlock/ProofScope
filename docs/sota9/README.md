# SOTA-9 (first deliverable): one honest entry point, a researcher UI, and a Colab launcher

Branch: `research/sota9-usable-auditor`, created from `8f0be6719c5fc210d62134f7f54c3637edd86212` (the verified SOTA-8 commit, which is left unchanged).
The SOTA-8 engine, the frozen baselines and the Pilot-25 inputs are not modified. This change adds a layer on top of the engine. It does not add new mathematics.

## 1. Forensic assessment (state at `8f0be67`)

- `proofscope/` has about 7,300 lines of Python across 30 modules. There are eight generations of comparison engines (`adelta`, `adelta11`, `adelta12`, `cmcd`, `cmcd_v10`, `v12`, `experimental/cjcs`, `cjcs4`, `sota8`). Each exposes its own `run_case(spec, tc, build, work)`, and each is driven by a benchmark harness rather than by a user.
- The current engine is `experimental/sota8.py`. It runs a derivation portfolio for R → C and C → R, and falls back to CJCS4 for refutations. It sits behind a clean verifier: a fresh compile, an axiom allowlist and `leanchecker` replay. Its verdict strings are internal: `CERTIFIED_LOGICAL_EQUIVALENCE`, `CERTIFIED_IMPLICATION`, `ABSTAIN` and `INCONCLUSIVE`, combined with a `direction`.
- Inputs are bare Lean propositions. Source context reaches the engine only through environment variables: `PROOFSCOPE_IMPORTS` is fixed per process, and `PROOFSCOPE_PREAMBLE` accepts only `open` and `universe` lines. Since SOTA-8, `autoImplicit` is false, so a free identifier is an error rather than a silently universally quantified variable.
- Measured coverage on the paired Pilot-25 run: CJCS4 certified 1 relationship and SOTA-8 certified 5, all 5 replayed, with 88 regression tests passing. Most real pairs still end as "no certificate".
- There was no supported way for a researcher to run one comparison. It required the regression command or the benchmark harness, a hand-built extractor directory, and reading raw JSON rows.

## 2. Five largest usability barriers

1. **No entry point.** There is no single function or command that takes two statements and returns a result.
2. **The engine vocabulary can be misread.** For example, `CERTIFIED_LOGICAL_EQUIVALENCE` by mutual derivation is closed-level: `2+2=4` and `∀ n, n+0=n` qualify. Nothing in the output said so, so a reader could take it as "same formalization".
3. **Diagnostics are raw REPL JSON.** A missing `open Nat` and a genuine error look the same, and nothing suggests what to try.
4. **Setup is undocumented and expensive.** The pinned Lean, REPL and Mathlib must match exactly. Mathlib needs several GB, and the memory figures include file-backed `.olean` pages.
5. **Narrow certified coverage.** On real pairs, "unknown" is the most common outcome. This is a research bottleneck (mission C), but it only becomes measurable and safe to show once 1–3 are solved.

## 3. Bottleneck addressed first

The bottleneck is barriers 1–3 together: no entry point and no report layer that cannot overclaim. Every later mission depends on it. The UI (D), the launcher (E) and the independent benchmarks (F) all have to turn engine rows into claims, and if that mapping can upgrade an unknown, every downstream number is suspect. Engine coverage (C) is the larger scientific gap, but improving it first would only produce more results that users can misread.

## 4. Implementation

- **`proofscope/auditor.py`** (a new module; the v0.1 `proofscope/audit.py` behind the one-click workflow is unchanged) provides `audit(reference, candidate, preamble, out)` and a command-line interface: `python -m proofscope.auditor --ref … --cand … [--preamble "open Nat"] --out DIR`. It runs the unchanged SOTA-8 engine and writes `report.json`, `report.md` and `certificate.lean`. The report has exactly one status, chosen from `PROVED_EQUIVALENT`, `PROVED_IMPLICATION`, `DISPROVED_EQUIVALENCE`, `UNKNOWN`, `NOT_EVALUABLE` and `ENGINE_INCONSISTENT`, and these fields:
  - `proved`: each kernel-checked declaration with its statement, its axioms and a plain-language meaning;
  - `unknown`;
  - `not_established`: what the certificates do *not* show, for example that mutual derivation is closed-level;
  - `diagnostics`;
  - `hints`: suggested `open …` lines for unknown identifiers. They always carry `applied: false`, and the input is never rewritten;
  - `resources`: wall time, child CPU and peak child RSS;
  - the engine commit.
- **Fail-closed mapping** (`report_from_row`, a pure function):
  - A positive status is shown only if the certificate that justifies it, for that verdict *and direction*, is present. Otherwise the result is downgraded to `UNKNOWN` with a diagnostic.
  - Unrecognised verdicts become `UNKNOWN`.
  - `INCONSISTENT` is surfaced as an engine bug, with no proved claims.
  - In `UNKNOWN` and `NOT_EVALUABLE`, partial facts such as "R is true" stay visible, but no relation certificate is ever listed.
- **`proofscope/ui.py`** is a standard-library HTTP server and a single page with fields for R, C and the preamble. It displays the report and does not compute any verdict itself. It shows the proved, unknown, not-established, hint and diagnostic sections, the collapsible certificate, the resources and a JSON export. It runs one audit at a time, and any exception is shown as `ERROR`, never as a verdict. In Colab it opens through `serve_kernel_port_as_window`.
- **`colab/sota9_cell.py`** is a single Colab cell.
  - It installs:
    - the ProofScope branch, which can be pinned to an exact commit;
    - Lean 4.34.1 from the official archive, verified by SHA-256;
    - the REPL at `193cf4bb`, smoke-tested by elaborating a theorem.
  - It then runs targeted core-Lean regressions and three demo audits, and ends with `VERDICT: PASS/FAIL`, per-step timings and a run-time estimate.
  - Flags:
    - `MATHLIB=True` adds Mathlib at `d13f23b7` from its precompiled cache. It never runs `lake update`, and it checks the lockfile.
    - `DRIVE_CACHE=True` keeps the archive and the REPL in Google Drive. Both are re-verified by hash and commit before reuse.
    - `EXPENSIVE=True` runs the full 88-test suite.
  - If Lean tests are skipped, the run counts as a FAIL.

## 5. Tests (`tests/sota9/test_audit.py`, 16 tests)

- **Unit tests** (no Lean needed):
  - every status;
  - the converse of an implication stays unknown;
  - `ABSTAIN`, `INCONCLUSIVE`, `RESOURCE_EXHAUSTED`, empty and unrecognised verdicts become `UNKNOWN`;
  - four adversarial cases where a verdict arrives without its certificate (missing, wrong direction, no direction), which are downgraded;
  - partial facts are shown without a relation;
  - `INCONSISTENT` is surfaced;
  - hints are never applied;
  - the Markdown output has no `PROVED` line for an unknown.
- **End-to-end tests** in core Lean:
  - division gives one-way implication, with `C → R` unknown;
  - `succ` without `open Nat` is `NOT_EVALUABLE`, with an unapplied hint;
  - with `open Nat` the input is unchanged;
  - an `axiom cheat : False` preamble is rejected;
  - a false statement against a true one is never reported as equivalent.
- **UI test:** an HTTP round trip that checks the page, `PROVED_EQUIVALENT` for `n+0=n` against `m=m+0`, that no raw engine row leaks, and that malformed JSON gives `ERROR`.

## 6. Verification status (honest)

| Item | Status |
|---|---|
| SOTA-9 tests | 16/16 pass locally with Lean 4.34.1 and the REPL at `193cf4bb`, core Lean |
| SOTA-8 regression suite on this branch | 88/88 pass, unchanged |
| Colab cell | Run end to end in a Linux sandbox with a clean `PATH` and a fresh root: `VERDICT: PASS` in 96–106 s fresh and 65 s with a warm cache. **Not yet run on Google Colab.** Colab CPUs are slower; the estimate there is 3–5 min |
| Mathlib mode of the cell, and Mathlib audits through the new entry point | **Not run.** Mathlib is unavailable in this sandbox. Unverified until executed |
| New mathematics | None. Every "proved" line comes from the SOTA-8 certificate pipeline: clean compile, axioms ⊆ {propext, Classical.choice, Quot.sound}, `leanchecker` replay |
| Claims | No state-of-the-art or novelty claim is made. This deliverable is about usability and safety |

## 7. Branch and commit plan

1. `research/sota9-usable-auditor` from `8f0be67`, with this commit only. Do not push to the SOTA-8 branch.
2. Next commit (mission B): source-aware input. Accept a `.lean` file and a declaration name, and recover its imports, namespaces, `variable` binders and universes verbatim. Keep rejecting anything that changes meaning, and show the reconstructed statement in the report.
3. Mission C: widen certified reasoning, for example by instantiating binders for refutations and adding the `simp`/`omega` normal-form bridge. Measure only on the frozen Pilot-25 plus a new, separately frozen set.
4. Mission E: a CI job that runs `colab/sota9_cell.py` headless in core mode, so the launcher is tested on every push.
5. Mission F: an independent benchmark split, frozen before any engine change and with gold labels kept separate. Report with Clopper-Pearson intervals using the SOTA-7 harness.
