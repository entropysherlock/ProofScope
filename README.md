# ScopeLedger

*What was claimed. What was proved. What remains uncertain.*

[![tests](https://github.com/entropysherlock/ScopeLedger/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/entropysherlock/ScopeLedger/actions/workflows/tests.yml)
[![SL-001](https://github.com/entropysherlock/ScopeLedger/actions/workflows/sl001-audit.yml/badge.svg?branch=main)](https://github.com/entropysherlock/ScopeLedger/actions/workflows/sl001-audit.yml)
[![SL-002](https://github.com/entropysherlock/ScopeLedger/actions/workflows/sl002-bridges.yml/badge.svg?branch=main)](https://github.com/entropysherlock/ScopeLedger/actions/workflows/sl002-bridges.yml)
![license](https://img.shields.io/badge/license-Apache--2.0-blue)
![maturity](https://img.shields.io/badge/maturity-research%20prototype%2C%20unreviewed-orange)

A Lean proof can be flawless and still prove a different statement from the one that was announced.
ScopeLedger keeps a versioned, machine-readable record of what a claim says, which formal statement
the kernel actually checked, and what evidence, if any, connects the two. It is an overlay on existing
registries and checkers, not a replacement for them.

> **Status.** Research prototype, started 2026-11-11. Nothing here has been reviewed by anyone outside
> the project. Developed first on the branch `scopeledger/staging` of
> [ProofScope](https://github.com/entropysherlock/ProofScope); this repository carries that branch's full
> history. CI runs from before the move are linked where cited and remain in ProofScope's Actions history.

## Why ScopeLedger exists

* AI systems now produce valid formal proofs at scale, including proofs of statements nobody intended.
* A kernel check establishes that a proof matches *its* formal statement. It says nothing about whether
  that statement matches the informal claim.
* That correspondence is currently checked by reading, by an LLM reviewer, or not at all, and the
  outcome is rarely recorded in a form others can audit or contest.
* Existing tools each solve part of this. [Palomar](https://palomar-registry.org) registers Lean proofs
  after a Comparator run and an LLM check of the description, and explicitly leaves human review of
  faithfulness to third parties. [Formal Conjectures](https://github.com/google-deepmind/formal-conjectures)
  maintains reviewed statements and links to external proofs. SemantEq and BEq+ compare two formal
  statements. None of them holds a contestable evidence trail for the *link* between a claim, a target
  statement and a certificate. That link is ScopeLedger's only subject.

## What it does

```
mathematical claim → formal statement → Lean certificate → faithfulness evidence → versioned record
     (asserted)        (identified)        (kernel fact)       (assessed)            (retractable)
```

Kernel facts and assessments are stored as different record types and never merged. A proved formal
statement with an unreviewed link leaves the claim at `supported`, not `verified`.

## Evidence model

Two independent axes ([docs/EVIDENCE_MODEL.md](docs/EVIDENCE_MODEL.md)).

| Proof evidence (about one statement) | Faithfulness evidence (about a claim–statement link) |
|---|---|
| `asserted` | `unassessed` |
| `computational` | `model_suggested` (recorded, never counted) |
| `informal` | `human_reviewed` |
| `reviewed` (named human) | `independently_corroborated` (two humans) |
| `machine_checked` (kernel replay, axioms listed) | `formally_related` (kernel-checked relation to a corroborated reference) |
| `reproduced` (replayed by another party) | `disputed` |
| `suspected_false`, `refuted` | |

Relations between two formal statements are a third record type (`implies`, `equivalent`,
`establishes_target`, `separated`, `asserted_link`, `candidate_similar`). Two proved closed propositions
are always logically equivalent, so ScopeLedger issues equivalence records only for schemas with stated
allowed steps, and never treats formal–formal agreement as proof of faithful formalization.

## Current capabilities

Implemented and tested in this commit:

* Record schema with fail-closed validation (`scopeledger/schema.py`): refuses certificates without
  kernel replay, unapproved axioms, `sorry`, model-authored certification, strictness without a
  separating witness, equivalence without both directions, and any single trust score.
* Append-only ledger in Git with supersede and dispute links (`scopeledger/records.py`).
* Derived status for statements and claims (`scopeledger/certificate.py`).
* `scope-check` CLI: `add`, `check`, `validate`, `status`, `list`.
* A fail-closed kernel checker for core-Lean files (`experiments/SL-001/kernel_check.py`): exit code,
  proposition re-check, axiom inventory, `leanchecker` replay, escape-hatch scan.
* SL-001 Stage 1: a deterministic provenance audit of 18 real statement–proof links, and 68 ledger
  records derived from it (34 statements, 16 source assertions, 18 asserted links; no certificates).

Not implemented: Stage 2 kernel bridges against the OpenAI library, Comparator integration, SemantEq and
BEq+ adapters, any human review, any de-duplication beyond the record types.

## Experimental results

**SL-001, Stage 1 (provenance audit): complete. Stage 2 (kernel bridges): not launched.**
Protocol v1.0 with amendment 1: [experiments/SL-001/PROTOCOL.md](experiments/SL-001/PROTOCOL.md).
Source audit: [experiments/SL-001/SOURCE_AUDIT.md](experiments/SL-001/SOURCE_AUDIT.md).
Per-case data: [experiments/SL-001/results/stage1/](experiments/SL-001/results/stage1/).
The first execution was invalid and is kept in `results/stage1_run0_invalid/`. Two later CI runs failed the
byte-for-byte reproduction check because of a git date-format difference; both are kept in the Actions
history and explained in amendment 2.

Subject: the 18 Erdős-problem theorems in Formal Conjectures that are marked as formally proved by a
declaration in `openai/math` (13 problems). Stage 1 reads pinned commits; it runs no prover and no model.

| Stage 1 observation | Count (of 18) |
|---|---|
| Link resolves to a theorem at the cited OpenAI commit | 18 |
| OpenAI ships a Comparator config naming that theorem (standard axioms only) | 18 |
| OpenAI statement unchanged between the cited commit and the frozen head | 18 |
| Formal Conjectures statement existed before the release and its core is unchanged | 14 |
| Formal Conjectures statement was written after the release (cannot be independent) | 4 |
| Pre-release statement shares a verbatim definition with OpenAI's challenge file | 1 (Erdős 970) |
| OpenAI statement is textually identical to the Formal Conjectures statement | 0 |
| OpenAI statement is a project-local named proposition | 6 |

What this shows: all 18 links are well-formed, and none is a literal match, so every one needs a bridge
argument that, as far as the source audit found, has not been machine-checked for these statements.
The import closure of the linked declarations ranges from 8 to 4,356 library modules.

What this does not show: that any proof compiles, that any link is correct or incorrect, or that any
statement is faithful to Erdős's problem.

| Required reporting line | Value |
|---|---|
| Eligible research claims | 18 linked statements |
| Successfully compiled by ScopeLedger | 0 (not attempted) |
| Certificates replayed | 0 |
| Certified equivalences | 0 |
| Certified one-way implications | 0 |
| Certified separating witnesses | 0 |
| Inconclusive | 0 (Stage 2 not run) |
| Blocked by infrastructure | 0 in Stage 1; Stage 2 build probe failed once, cause unrecorded (relaunched) |
| Independently reviewed | 0 |

Smoke tests 1–4 of the kernel pipeline pass on synthetic statements; they are harness tests, not results.
| CI run | Result |
|---|---|
| [43015699424](https://github.com/entropysherlock/ProofScope/actions/runs/43015699424) | smoke tests passed; Stage 1 ran; build probe failed after 12 min without recording a reason (harness defect, fixed) |
| [43016379474](https://github.com/entropysherlock/ProofScope/actions/runs/43016379474), [43017405870](https://github.com/entropysherlock/ProofScope/actions/runs/43017405870) | reproduction check failed: date-format difference between git versions (amendment 2) |
| [43018353868](https://github.com/entropysherlock/ProofScope/actions/runs/43018353868) | smoke tests passed; **Stage 1 reproduced byte for byte** on a GitHub-hosted runner |

These runs were executed while the project was staged in ProofScope, so their logs live in
[ProofScope's Actions history](https://github.com/entropysherlock/ProofScope/actions). New runs appear in
this repository's Actions tab.

## SL-002: first kernel-checked bridges (Erdős 952 and 1150)

Formal Conjectures marks Erdős 952 and 1150 as solved by OpenAI's Lean proofs, while recording that the
linked theorems differ from its statements by a transport step nobody had machine-checked.
[experiments/SL-002/REPORT.md](experiments/SL-002/REPORT.md) has the details.

| Result | Imports | Status |
|---|---|---|
| Erdős 952: the Formal Conjectures statement **is equivalent to** OpenAI's (`fc_iff_main`) | Mathlib only | kernel-checked, standard axioms, `leanchecker` replay; two build paths ([43024368984](https://github.com/entropysherlock/ProofScope/actions/runs/43024368984), [43024708516](https://github.com/entropysherlock/ProofScope/actions/runs/43024708516)) |
| Erdős 1150: OpenAI's statement **implies** the Formal Conjectures statement (`main_implies_fc`); reverse undecided | Mathlib only | same |
| Erdős 952, Formal Conjectures statement verbatim, **from OpenAI's proof** | Mathlib + 41 OpenAI files | **kernel-checked**: built from verbatim sources, standard axioms, all 69 modules (incl. OpenAI's 65) replayed by `leanchecker` ([43024368984](https://github.com/entropysherlock/ProofScope/actions/runs/43024368984); reproduced by a second build path in [43025657829](https://github.com/entropysherlock/ProofScope/actions/runs/43025657829)) |
| Erdős 1150, Formal Conjectures statement verbatim, **from OpenAI's proof** | Mathlib + 24 OpenAI files | **kernel-checked**: built from verbatim sources, standard axioms, all 69 modules (incl. OpenAI's 65) replayed by `leanchecker` ([43024368984](https://github.com/entropysherlock/ProofScope/actions/runs/43024368984); reproduced by a second build path in [43025657829](https://github.com/entropysherlock/ProofScope/actions/runs/43025657829)) |

These are routine Lean (about 180 lines). What they add is a checked fact where there was an
unchecked assertion. Neither says anything about whether either formal statement is what Erdős asked.

## Reproducibility

```sh
git clone https://github.com/entropysherlock/ScopeLedger scopeledger
cd scopeledger
pip install -e ".[dev]"
pytest -q                 # unit tests
scope-check validate      # every ledger record
```

Smoke tests need Lean 4.34.1 on `PATH` (`lean`, `leanchecker`):

```sh
python experiments/SL-001/smoke_tests.py
```

Stage 1 needs local clones of the two source repositories (commands in
[docs/VALIDATION.md](docs/VALIDATION.md)):

```sh
python experiments/SL-001/sl001.py verify-freeze --fc <formal-conjectures>
python experiments/SL-001/sl001.py stage1 --fc <formal-conjectures> --oai <openai-math>
```

## Roadmap

First 30 days: publish Stage 1; measure whether one OpenAI result can be built on free runners; attempt
Stage 2 bridges for the 18 links under the frozen rules; build MisformBench from repaired Formal
Conjectures statements; ask one qualified person to review one record. First 12 months and the
five-pillar plan with its *proposed, unfunded* budget: [docs/RESEARCH_ROADMAP.md](docs/RESEARCH_ROADMAP.md).

## Research integrity

* A machine-checked proof is not evidence of semantic faithfulness.
* A failed proof search does not establish inequivalence.
* An LLM opinion is not proof and is never stored as one.
* Evidence is versioned and retractable; labels are derived from records.
* Undecided is a legitimate outcome, and is kept apart from infrastructure failure.
* Invalidated experiments stay visible. ProofScope's history, including its negative SOTA-18 result,
  is part of this project's record ([docs/PROOFSCOPE.md](docs/PROOFSCOPE.md)).

## Contributing

Reviews and disputes are the most useful contributions. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

Research director: Caleb J. Westfall (independent researcher, no institutional affiliation).
AI-assisted research and engineering: Claude (Anthropic), which wrote most of the code and text in this
repository under his direction. No funding, endorsement or external collaboration is claimed.
Sources audited: Formal Conjectures (Google DeepMind and contributors) and `openai/math` (OpenAI), both
Apache-2.0. Licence: Apache-2.0.
