# SOTA-1 independent adjudication: instructions and records

## Roles

| Role | Who | Responsibilities |
|---|---|---|
| Custodian | Neither a ProofScope developer nor a developer of a tested tool | Runs `python -m bench.seal build`. Publishes `manifest.json` (the case-file SHA-256s and label commitments) before any prediction run. Keeps `custodian/` (salt and labels) offline until the runs are locked. |
| Reviewers R1, R2 | Mathematicians fluent in Lean/Mathlib, not developers of any tested tool | Each reviewer independently receives only `primary.cases.jsonl`: no tool names, no predictions, no source labels. |
| Arbiter R3 | Same restrictions as the reviewers | Resolves disagreements between R1 and R2. |

## Record per case and reviewer (`votes_R1.jsonl`, `votes_R2.jsonl`)

    {"case_id": "...", "reviewer": "R1",
     "track_A": "equivalent|non_equivalent|disputed|unassessable",
     "track_B": "equivalent|non_equivalent|disputed|unassessable",
     "direction": "ref_implies_cand|cand_implies_ref|incomparable|both_false_on_domain|none|unknown",
     "rationale": "required, at least one sentence",
     "lean_evidence": "optional: a checker-replayed lemma or counterexample, as Lean source",
     "minutes": 7}

**Track A** asks whether the two closed statements are logically equivalent in their common context.

**Track B** asks whether the candidate is a faithful formalization of the reference. That means it
preserves:
- the domain;
- the role of each hypothesis;
- the meaning of the conclusion;
- the choice of definitions;
- the strength of the statement.

Approved reformulations are allowed. Two unrelated true theorems are not faithful to each other, even
though they are logically equivalent.

**Hard cases.** Attach Lean evidence that the checker can replay. No sorry, no custom axioms and no
`native_decide`.

## Resolution

1. If R1 and R2 agree, that is the gold label.
2. If they disagree, R3 decides with a written reason. If R3 cannot decide, the case is DISPUTED.
3. DISPUTED cases are excluded from the primary denominator and scored both ways in a sensitivity table.
4. Report Cohen's κ between R1 and R2 for each track.

## Release

After all runs are locked, the custodian publishes:
- the salt;
- `custodian/*.labels.jsonl`;
- the votes;
- `gold.jsonl`.

Anyone can then check the commitment:

    python -m bench.seal verify --labels custodian/primary.labels.jsonl --salt "$(cat salt.txt)" --commitment <published>

The scoring run then uses `gold.jsonl` (workflow input `gold`).

## If no independent reviewers are available

Any labels produced by project members, by an AI, or by both are recorded as `PROVISIONAL_NON_INDEPENDENT`:
- Results scored against them must be titled "provisional".
- AI-generated labels are marked `AI_PRELIMINARY`.
- A second AI does not make a label independent.
