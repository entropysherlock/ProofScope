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

## Local use

Install Lean 4.34.1, then run:

```bash
python3 -m unittest discover -s tests -v
python3 -m proofscope.audit --output proofscope-evidence
```

The GitHub workflow handles Lean installation automatically, and publishes reports even when an audit fails.

## Roadmap

- Support arbitrary pinned Lean projects and stronger provenance checks.
- Extract statement, hypothesis, definition, and trust-scope inventories.
- Investigate human-reviewed theorem-relevant semantic discrepancies.
- Publish benchmark comparisons and reproducible audit evidence.

This is an early public prototype, not a peer-reviewed mathematical verifier.

© Caleb J. Westfall. MIT License.
