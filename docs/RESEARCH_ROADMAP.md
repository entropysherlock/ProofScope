# Research roadmap

## What changed since the selection report

The report that selected this project (2026-11-11) did not know about **Palomar**, a registry of
Lean-verified mathematics incubated by the Lean FRO and ICARM and announced in August 2026. Palomar
already provides the registry, the Comparator replay, the axiom policy and versioned entries. ScopeLedger
therefore does not build a proof registry. It is scoped to what Palomar says it does not do: comparison
against external target statements, human review of faithfulness, and contestable records. The report's
originality and defensibility scores were too high in light of this.

## First 30 days

1. Publish SL-001 Stage 1 for the 18 links (done when the run is recorded in the README).
2. Stage 2 feasibility: can one OpenAI result be built on a free hosted runner? (probe job)
3. Stage 2 under the frozen protocol, starting with the three links whose transport gap Formal
   Conjectures' own PR describes (Erdős 371, 952, 1150).
4. MisformBench v0: wrong and repaired statement pairs from Formal Conjectures history.
5. One external review of one record. Until this happens the project has no independent validation.

## Five pillars, first year

| Pillar | Deliverable | Depends on |
|---|---|---|
| 1. Early-stage research | Test whether claim–certificate links can be audited with kernel witnesses, and at what cost per link (SL-001, then the two-key hypothesis on MisformBench) | Stage 2 feasibility |
| 2. Dataset and benchmark | MisformBench: repaired misformalizations with before and after statements, error class and dates | permissive licences (Formal Conjectures is Apache-2.0) |
| 3. Tool | `scope-check` CLI, a Lean bridge-checking workflow, CI checks other projects can call | Comparator and equivalence-checker adapters |
| 4. Field building | A community audit sprint | **conditional** on finding qualified reviewers and resources; not scheduled |
| 5. Evidence ledger | Versioned records with faithfulness and uncertainty labels; de-duplication by certified relation only, never by text or embedding similarity | upstream interest (Palomar overlays, Formal Conjectures) |

## Twelve-month gates

| Quarter | Gate |
|---|---|
| Q1 | SL-001 decision rule (PROTOCOL.md section 12); MisformBench v0 public |
| Q2 | Two raters agree on relation type (Cohen's kappa ≥ 0.6) or the label set is simplified |
| Q3 | ≥ 10 outside contributors or ≥ 20 upstream-accepted fixes, else finish as a dataset project |
| Q4 | Blind external re-labelling of 100 records; final report states which gates passed |

## Illustrative budget (a proposal; no funding has been secured)

| Line | USD |
|---|---|
| Principal investigator support, 12 months | 36,000 |
| Lean/Mathlib expert, contract (~150 h) | 15,000 |
| Paid expert annotation and blind validation | 7,000 |
| Compute and model APIs | 4,000 |
| Audit sprint (bounties, hosting) | 5,000 |
| Administration and contingency | 3,000 |
| **Total** | **70,000** |

## Main risks

Palomar or Formal Conjectures may absorb this function, which would be a good outcome for the field and
would end the need for a separate ledger. The OpenAI library may be too large to build per result on free
infrastructure. There is no Lean/Mathlib expert on the project. Nothing has been independently reviewed.
