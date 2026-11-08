# Scope-fidelity review worksheets (v0.3)

`python3 -m proofscope.review --lean-dir <project>/lean --out DIR [--ledger reviews.json]`, or stage S7 of the
project audit (`--worksheets`, on by default in the **ProofScope Project Audit** workflow).

Projects such as openai/math publish a prose **scope document** for each formalization (`lean/docs/*.md`) that states
what the Lean code claims and links the comparator statements. A worksheet puts, side by side:

1. the papers and the scope document's claims,
2. the Lean comparator file's text, comments stripped, together with its SHA-256,
3. junk-value exposure flags: `sInf`/`sSup`, `tsum`, `limUnder`, real `limsup`/`liminf`, `deriv`, Bochner integrals
   used with no guard (`Nonempty`, `BddBelow`, `Summable`, `Tendsto`, `Integrable`, ...) detected anywhere in the file,
4. the review record from a ledger.

Flags are heuristic string-matching triage; the checker does not resolve Lean elaboration or semantic guard implications.

## Review ledger

`reviews/<corpus>_<commit>.json`. Records apply only to the commit named in the file.

| Field | Values |
|---|---|
| `verdict` | `FAITHFUL`, `FAITHFUL_WITH_NOTE`, `DISCREPANCY`, `NEEDS_EXPERT`, `UNREVIEWED` |
| `reviewer_type` | `HUMAN` (a named person) or `AI_PRELIMINARY` (must be confirmed by a person) |
| `reviewer`, `date`, `notes` | free text; notes should say exactly what was compared |

A `DISCREPANCY` should come with a Lean-checkable witness (for example, an object that satisfies the paper's
hypotheses but not the formal ones) whenever one can be stated.

## What a worksheet is not

It does not certify faithfulness. Junk-value flags are triage: most flagged statements are fine, because the guard
is implied by other hypotheses or the junk value would make the statement false rather than vacuous.
