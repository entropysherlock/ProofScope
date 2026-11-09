# CMCD blind structural-drift suite: protocol for an independent author

This suite must be written by someone **other than the engine author** (ChatGPT, or a human
reviewer). It is written **after** the CMCD engine was frozen (`../CMCD_FREEZE.txt`, block 2) and is
run **exactly once**.

1. Write 20–40 cases as `cmcd_blind/<id>.json`:
   ```json
   {"id": "...", "domain": "Nat|Int|List|Logic", "family": "...", "reference": "<closed Lean Prop>",
    "lean": "<closed Lean Prop>", "expected": "<verdict>", "expected_localized_at": [k] or null,
    "must_not_be": ["SCHEMA_EQUIVALENT", "EQUIVALENT_BY_LAWS"] or [], "annotation": "author, date"}
   ```
   - Statements must elaborate in **core Lean 4.34.1** (no Mathlib).
   - Verdicts: `CLAIM_LEAN_WEAKER`, `CLAIM_LEAN_STRONGER`, `CLAIM_INCOMPARABLE`, `SCHEMA_EQUIVALENT`,
     `EQUIVALENT_BY_LAWS`, `NO_SHARED_SYMBOLS`, `IDENTICAL`.
   - Labels follow `docs/v0.9_cmcd.md` §2: they are about the claims **with the shared operators
     abstracted**, not about concrete truth. Two of the engine author's own adversarial labels were wrong
     on exactly this point (`a1`, `a6`), so read §2 carefully.
   - Include harmless reformulations (at least a third of the cases), and include cases expected to be
     `NO_SHARED_SYMBOLS` or hard.
2. Commit `SUITE_HASH.txt`, produced with
   `sha256sum proofscope/benchmark/cmcd_blind/*.json > proofscope/benchmark/cmcd_blind/SUITE_HASH.txt`,
   in the same commit as the cases. Do not look at engine outputs on these statements first.
3. Run the **ProofScope CMCD Drift Localization** workflow once and report its summary verbatim.
   Wrong labels found afterwards are reported as label errors; they are never silently edited.
