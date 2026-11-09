# ProofScope
### by Caleb J. Westfall
**Verify the proof. Validate the claim.**

ProofScope is an experimental open-source proof-scope auditing project for AI-assisted mathematics.

## One-click live prototype

1. Click **Actions** in this repository.
2. Click **ProofScope Audit** in the left sidebar.
3. Click **Run workflow** → **Run workflow**.
4. Open the completed run and download **proofscope-audit-evidence** under *Artifacts*.
5. Read `REPORT.md`, `report.json`, and the command logs.

**[Open ProofScope Audit](../../actions/workflows/proofscope-audit.yml)**

The workflow runs Lean 4.34.1 on a GitHub runner. It compiles a valid theorem and a deliberately forged declaration, then checks that `leanchecker --fresh` accepts the first and rejects the second for a genuine type mismatch. It saves source hashes and JSON/Markdown evidence.

**Limits:** This lightweight prototype does not verify all 418 OpenAI challenges, establish mathematical statement fidelity to a paper, prove novelty, or use an independent implementation of Lean's kernel. `DEMO_CONTROLS_PASS` refers only to the bundled integrity controls.

## v0.2 (in development): audit a real Lean project

### ProofScope Project Audit

**[Open ProofScope Project Audit](../../actions/workflows/proofscope-project-audit.yml)** → **Run workflow**.
Enter a public GitHub repository, a full 40-character commit and, optionally, target modules. The defaults audit
OpenAI's [openai/math](https://github.com/openai/math) at commit `4eaee875` and its `formalization.yaml` catalog of
208 paper main results.

It fetches exactly that commit, records the Lean toolchain and every dependency pin, hashes the targets' import
closure, scans it for `sorry`, `axiom`, `native_decide` and kernel-check bypasses, and checks each catalog entry
(the declaration exists under its full name, its comparator challenge lists it, the solution module imports it).
With **build** switched on it also compiles the targets, prints their axioms and replays them with `leanchecker`.
Every finding is labelled **VERIFIED**, **WARNING**, **FAIL**, **INCONCLUSIVE**, **HUMAN_REVIEW** or **INFO**.
Paper-to-Lean statement fidelity is always **HUMAN_REVIEW**. Details: [`docs/project_audit.md`](docs/project_audit.md).

Security: only people with write access can start it; the token is read-only and not stored; no secrets are used;
inputs are validated and never pasted into shell code. With build off, no code from the audited project runs.

### ProofScope Fidelity

**[Open ProofScope Fidelity](../../actions/workflows/proofscope-fidelity.yml)** → **Run workflow**. Produces
Lean-checked certificates that a custom definition agrees or disagrees with a reference on the inputs a theorem
actually uses, for 13 bundled cases including two real definitions from the OpenAI comparator corpus. Core Lean
only. Format of a case: [`docs/pair_spec.md`](docs/pair_spec.md).

### Results so far (local runs, November 8, 2026; not yet run on GitHub)

- openai/math @ `4eaee875`, no build: commit verified; 42 dependencies pinned to exact commits; all **208**
  catalog main results mechanically consistent; the Hadwiger counterexample's import closure (374 files) has no
  text-level trust hazards. This says the catalog is internally consistent, not that any statement matches its paper.
- Fixture project with planted flaws (`tests/fixtures/demo_project`), with build: honest theorems VERIFIED,
  `sorry` FAIL, custom axiom WARNING, `leanchecker` replay VERIFIED.
- Fidelity benchmark: 12/12 labelled cases correct, 39 certificates replayed. No theorem-relevant discrepancy has
  been found in a real formalization.

## v0.3: scope-fidelity review worksheets

The Project Audit now also builds a **review worksheet for every scope document** in a project that has them
(stage S7, on by default). For openai/math at `4eaee875`, Claude's local run reported 245 worksheets covering all 418 comparator
challenges through 433 links, none broken. Each worksheet shows the scope document's claims beside Lean
comparator source text, flags junk-value-prone operators used without a detected guard (141 of 433 links
in that run; triage, not errors), and merges attributed review verdicts from [`reviews/`](reviews/).

Ten statements have **AI-preliminary** reviews so far (7 faithful, 1 faithful with a note, 2 needing an expert); none
has a human review yet, and no discrepancy has been found. Details: [`docs/review_worksheets.md`](docs/review_worksheets.md).
These are reported local results pending a GitHub Actions rerun.

## v0.5: theorem intelligence, comparison certificates, benchmark, viewer

**[Open ProofScope Engine](../../actions/workflows/proofscope-engine.yml)** → **Run workflow**. One coherent engine,
documented in [`docs/engine.md`](docs/engine.md):

- **Theorem dossiers** computed inside Lean from the elaborated declaration: binders split into parameters,
  hypotheses and typeclass machinery; statement vs proof dependencies; definitions a reviewer must check; transitive
  axioms; kernel replay status.
- **Theorem comparison** of a formal statement against a typed reference, with Lean-checked certificates for
  applicability gaps, conclusion gaps, vacuity, equivalence, coverage and strict strengthening.
- **Certificate gate**: only declarations that compile cleanly, use standard axioms and pass `leanchecker` replay count.
- **Benchmark** (project-authored): held-out 18/20 exact labels, detection precision 1.0, recall 0.83, 0 false
  positives; 20/20 adversarial certificates handled, 0 false acceptances. No competitor comparison was run.
- **Viewer**: one offline HTML report.

Not done yet: Mathlib-project dossiers, real-paper comparisons, a 100+ case independently annotated benchmark,
resumable audits, a hosted interface. See the continuation point in `docs/engine.md`.

## v1.0: Assumption Delta, boundary synthesis, Mathlib track

Details: [`docs/v1.0_assumption_delta.md`](docs/v1.0_assumption_delta.md).

- **Assumption Delta:** an added assumption changes the claim exactly when a model of the reference's
  conditions violates it (`restrictive_iff_strictly_weaker`, Lean). ProofScope certifies such models, reads
  them out of the kernel-checked proof term (e.g. `Bool` with `op a b := a` for a hidden commutativity
  assumption), and certifies when a reference is false without an assumption.
- **Boundary witness synthesis** closes the blind-suite strict/non-strict gap (blind suite now development data).
- **Mathlib track** (ℝ, groups, sets): workflow ready, **pending its first run**.
- A soundness bug found by the adversarial suite (model scope) is documented and fixed (v1.0.2).

## v0.9: certified drift localization (CMCD)

Details: [`docs/v0.9_cmcd.md`](docs/v0.9_cmcd.md).

- **Question answered:** *which* edit between a reference and a formal statement changed the claim, in which
  direction, and with what Lean-checked countermodel, even when both statements are true theorems.
- **Localization theorem** (`lean/ProofScope/DriftSoundness.lean`): in a one-direction chain of edits, a
  strictly weakening edit's countermodel is a countermodel for the whole pair; with mixed directions,
  per-edit verdicts provably do not compose (`cancellation`), and ProofScope does not claim localization.
- Four domains in core Lean (ℕ, ℤ, lists, quantifier logic); verified Lean installation (pinned SHA-256,
  retries, fail-closed `INFRASTRUCTURE_ERROR`).
- Development evidence only. An independently authored blind suite and ProofNetVerif are **pending**.

## v0.8: ClaimDelta, certified statement strength beyond logical equivalence

Details: [`docs/v0.8_claimdelta.md`](docs/v0.8_claimdelta.md).

- **The problem:** two *true* theorems are logically equivalent, so no equivalence checker can see a
  formalization that proves a weaker true claim (`n ≤ 2^n` for a paper's `n < 2^n`).
- **ClaimDelta** abstracts the operators both statements share (`^`, nonlinear `*`, `gcd`, `%` by a variable, ...)
  and certifies either a uniform entailment or a **countermodel**: an interpretation of those operators
  where the Lean claim holds and the reference fails. Every certificate is Lean-checked; the
  abstraction is bound to the elaborated statements by `Iff.rfl`.
- **Soundness in Lean** (`lean/ProofScope/ClaimDelta.lean`, 15 axiom-free theorems), including the
  counterexamples that limit what a verdict means.
- **Fixed:** research-audit dossier identity (module-qualified; the 35 overwritten records), fail-closed counts.
- Development evidence only (author-written cases); external benchmark (ProofNetVerif) **pending**.

## v0.6: blind evaluation, soundness theorems, research-statement audit

Details: [`docs/v0.6_report.md`](docs/v0.6_report.md).

- **Soundness theorems** for every comparison label, proved in Lean with no axioms (`lean/ProofScope/Soundness.lean`),
  including an *observability* theorem: when both statements are true, a pointwise conclusion difference can never be
  certified, so a certified conclusion gap against a proved Lean theorem refutes the reference transcription.
- **Both v0.5 held-out misses fixed** by general methods (`ps_arith`, an elaborator-level arithmetic tactic, and
  instantiation-based quantifier refutation); that set is now development data.
- **Blind oracle benchmark** (175 cases, labels from an independent Python model of Lean's ℕ semantics, engine frozen
  first, run once): 154/175 exact, **0 wrong labels** (all misses INCONCLUSIVE), detection precision 1.0 and recall 1.0,
  0 false positives, 0 oracle disagreements.
- **ProofScope Research Audit** workflow: dossiers for up to 150 OpenAI research statements across 20 areas, Mathlib
  pinned to the corpus revision, corpus code compiled without network or credentials. *Not yet run on GitHub.*
- **ProofScope Competitor Comparison** workflow against SemantEq on the shared question "equivalent or not".
  *Not yet run.* State-of-the-art superiority has not been established.

## Local use

Install Lean 4.34.1, then run:

```bash
python3 -m unittest discover -s tests -v                 # v0.1 tests
python3 -m proofscope.audit --output proofscope-evidence  # v0.1 kernel controls
python3 -m unittest discover -s tests/v02 -v             # v0.2 tests (pip install pyyaml for catalog tests)
python3 -m proofscope.fidelity benchmark                 # v0.2 definition-fidelity benchmark
python3 -m proofscope.project --help                     # v0.2 pinned-project audit
python3 -m proofscope.review --help                      # v0.3 review worksheets
python3 -m proofscope.bench --split all                  # v0.5 comparison benchmark
python3 -m proofscope.dossier --help                     # v0.5 theorem dossiers
```

The GitHub workflow handles Lean installation automatically, and publishes reports even when an audit fails.

## Roadmap

- ~~Support arbitrary pinned Lean projects and stronger provenance checks.~~ (v0.2, in development)
- Extract statement, hypothesis, definition, and trust-scope inventories.
- Investigate human-reviewed theorem-relevant semantic discrepancies.
- Publish benchmark comparisons and reproducible audit evidence.

This is an early public prototype, not a peer-reviewed mathematical verifier.

Earlier research evidence (WESTFALL V23, V0.8, V0.9-R) and v0.2 local runs are archived in [`evidence/`](evidence/).

© Caleb J. Westfall. MIT License. Files in `examples/lean/` are (c) OpenAI, Apache License 2.0.
