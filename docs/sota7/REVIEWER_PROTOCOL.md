# Reviewer protocol (two independent reviewers + adjudicator)

For every case the reviewer receives the public file only: reference text and Lean, candidate Lean, context,
and, for repair tasks, the edit grammar. They never see any ProofScope output.

Each reviewer records the following, with written reasons:
1. **Reference meaning:** what the reference statement means.
2. **Candidate meaning:** what the elaborated candidate means. Elaborate it, and record `#check` / `pp.all`
   where the meaning is subtle.
3. **Context:** whether the two contexts match (domains, coercion targets, implicit binders, instances).
4. **`relation`:** EQUIVALENT / REF_STRONGER / CAND_STRONGER / INCOMPARABLE / NOT_EQUIVALENT / UNRESOLVED.
5. **`closed_truth`:** for each closed statement, TRUE, FALSE or UNKNOWN, with a proof sketch or countermodel.
6. **`intended_repairs`** (repair tasks): edit-index sets that reconcile the candidate, or NONE_IN_GRAMMAR.
7. **Minimality:** whether a cheaper acceptable repair exists.
8. **Remaining uncertainty.**

Attach proof artifacts or countermodels where possible.

**Agreement and adjudication:**
- Measure agreement (Cohen's κ, `bench/pilot/labels.py agree`) before adjudication.
- Disagreements and UNSURE answers go to the adjudicator, or stay UNRESOLVED.
  UNRESOLVED cases are scored apart (GOLD_UNRESOLVED) and never count as success or as error.
- Reviewer agreement is not a proof, and ProofScope's verdict never sets a label.
- A MINIMALITY_CONFLICT means the gold label lists a repair cheaper than a certified minimum. It is sent
  back to the reviewers, because the certificate and the label cannot both be right.
