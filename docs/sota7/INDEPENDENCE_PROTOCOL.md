# Independence protocol (SOTA-7)

Three roles are kept separate, and the software enforces the separation where it can.

| role | may do | may not do |
|---|---|---|
| A. Tool developers (Caleb J. Westfall; Claude; ChatGPT; any AI used to build ProofScope) | change the engine; build the harness; write SYNTHETIC_DEVELOPMENT fixtures | select held-out cases, write or see held-out gold labels before scoring, or call any label INDEPENDENT |
| B. Evaluation operator (may be a developer) | freeze manifests, run `bench.sota7.runner` and `bench.sota7.replay`, publish sealed records | open the gold file before the records are sealed and published |
| C. Custodian and reviewers (external) | select cases (`PILOT_PROTOCOL_v1`), write labels (`REVIEWER_PROTOCOL.md`), hold the gold file until scoring | run or modify the engine |

**Enforced by software:**
- `schema.validate_public` refuses fields outside the public set. It also refuses non-opaque case ids, and
  metadata that uses label words.
- `blind.sandbox` gives the engine one public file and an environment with no gold variables.
- `blind.freeze` / `verify_manifest` commit the input and gold digests; a mismatch is fatal.
- `runner.seal` makes records read-only and hashes them together with every certificate.
- `scoring.score` refuses unsealed or modified records, and refuses records from a different manifest.
- `validate_gold` refuses an INDEPENDENT label without two distinct reviewers and their rationales.
- In CI, the gold file is deleted before execution, and scoring runs in a later job.

**Enforced only by procedure:**
- the custodian keeps the gold file off any machine the operator controls until the records are published;
- the conflict list (`bench/pilot/CONFLICTS.txt`).

A content hash commits bytes. It does not make a label correct, or independent.
