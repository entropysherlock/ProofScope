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

## Local use

Install Lean 4.34.1, then run:

```bash
python3 -m unittest discover -s tests -v                 # v0.1 tests
python3 -m proofscope.audit --output proofscope-evidence  # v0.1 kernel controls
python3 -m unittest discover -s tests/v02 -v             # v0.2 tests (pip install pyyaml for catalog tests)
python3 -m proofscope.fidelity benchmark                 # v0.2 definition-fidelity benchmark
python3 -m proofscope.project --help                     # v0.2 pinned-project audit
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
