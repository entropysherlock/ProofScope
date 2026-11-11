# Evidence model

## Objects

| Record | Says | Example |
|---|---|---|
| `claim` | what was announced, with an immutable source | "h(k) ≪ k²" in a preprint at a commit |
| `statement` | one exact formal statement: repository, 40-character commit, path, declaration, text hash | `OAI.Erdos970.Erdos970Final.erdos_970_quadratic` |
| `evidence` | proof evidence about one statement | kernel replay with axiom list |
| `relation` | a relation between two formal statements, or between a certificate and a target | "library establishes target B" |
| `review` | faithfulness of a claim–statement link | a named human's review |

## Axis 1: proof evidence

`asserted` → `computational` → `informal` → `reviewed` → `machine_checked` → `reproduced`, with
`suspected_false` and `refuted` on the negative side. `machine_checked`, `reproduced` and `refuted`
require `basis: kernel` and a certificate that records: checker, toolchain, dependencies, artifact hash,
**proposition hash**, replay log, `kernel_replay`, `elaborated_without_error`, `sorry_free`, and an axiom
list inside the allowed set. `reproduced` must name whom the replay is independent of.

## Axis 2: faithfulness

`unassessed`, `model_suggested`, `human_reviewed`, `independently_corroborated`, `formally_related`,
`disputed`. A model can record at most `model_suggested`. `independently_corroborated` needs two
distinct named humans. `formally_related` needs a kernel-checked relation to a reference statement whose
own link is corroborated; a relation to an unreviewed reference transfers nothing.

## Relations and outcomes

Kinds: `candidate_similar`, `asserted_link`, `distinct_text`, `implies`, `equivalent`,
`establishes_target`, `separated`. Outcomes: `certified`, `asserted`, `observed`, `undecided`, `timeout`,
`unsupported_input`, `compile_failure`, `blocked_infrastructure`.

Rules enforced by `scopeledger/schema.py`:

* only `basis: kernel` can be `certified`; similarity, assertions and text differences never can;
* `implies` certified one way leaves the reverse `undecided`; `strict` is refused without a `separated`
  record carrying a witness and the class of structures it lives in;
* `equivalent` needs certificates in both directions **and** a statement of allowed steps, because any
  two proved closed propositions are trivially equivalent;
* a non-certified outcome may not carry a certificate.

## Derived status of a claim

`verified` only if a linked statement is `machine_checked` or better **and** the link is
`independently_corroborated` or `formally_related`. Kernel proof plus a weaker link gives `supported`.
A refuted statement refutes the claim only through a corroborated link; otherwise `undecided`.
There is no numerical score.

## De-duplication

Records are never merged. Identity is expressed by `equivalent` relations with certificates; likeness by
`candidate_similar`. A cluster of "the same statement" is a computed view over certified edges, so
withdrawing an edge never requires un-merging anything.

## Retraction

Records are immutable. `supersedes` replaces a record for the purpose of derived status; `disputes`
flags it. Both the old and new records stay in Git history.
