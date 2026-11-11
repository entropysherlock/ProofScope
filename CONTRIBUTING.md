# Contributing to ScopeLedger

ScopeLedger is a research prototype run by one person with AI assistance. Outside review is the thing
it most lacks, so the most valuable contributions are reviews and disputes.

## Ground rules

1. A record never claims more than its evidence. `scope-check check <file>` refuses records that do.
2. Records are immutable. To correct one, add a new record with `"supersedes": "<id>"`. To contest
   one, add a record with `"disputes": "<id>"`. Both stay in history.
3. Only a kernel replay on pinned dependencies can produce `certified`. A model's opinion is recorded
   as `model_suggested` or `candidate_similar` and never counted as evidence.
4. `undecided`, `timeout`, `unsupported_input`, `compile_failure` and `blocked_infrastructure` are
   distinct, legitimate outcomes. Do not merge them.
5. Sign reviews with your real name or a stable public handle. Do not record a review as
   `human_reviewed` on someone else's behalf.

## Ways to contribute

* **Submit a claim.** Open a pull request adding a `claim` record (the announced statement and an
  immutable source) and a `statement` record (repository, full commit, path, declaration name).
* **Review a link.** Add a `review` record with `faithfulness: human_reviewed`, your name, what you
  checked, and what you did not check.
* **Dispute a record.** Add a record with `disputes` and your reasons. A dispute needs no permission.
* **Replay a certificate.** Follow `docs/VALIDATION.md`. A replay by someone other than the original
  author is what turns `machine_checked` into `reproduced`.
* **Improve the code.** `pip install -e ".[dev]" && pytest -q`. New validation rules need a test that
  shows the rule rejecting an overclaim.

## What will be declined

State-of-the-art claims, numerical trust scores, records without immutable sources, and edits to a
frozen experiment protocol other than dated amendments.
