# SOTA-18 soundness finding F1: `NO_ASSUMPTION_DELTA` on statements that did not elaborate

Found 2026-11-11 during the synthetic Track C smoke stage, **before** the headline evaluation started.
Frozen engine `v1.2-review` @ `b0519f8`, `proofscope/adelta12.py` (SHA-256 in `ENGINE_HASHES.txt`).

## Minimal counterexamples (core Lean 4.34.1, no Mathlib)

    PROOFSCOPE_IMPORTS= python3 -m proofscope.adelta12 experiments/sota18/soundness/universe_sorry_u3.json \
        experiments/sota18/soundness/universe_sorry_u4.json --out OUT

| Case | Reference | Candidate | Frozen verdict | Truth |
|---|---|---|---|---|
| u3 | `∀ {G : Type u_1} [Inhabited G] (a b : G), a = b` | `∀ {G : Type u_1} [Inhabited G] (a b : G) (h : a = b), a = b` | `NO_ASSUMPTION_DELTA` | an assumption was added; the reference is false (take `Bool`), the candidate true |
| u4 | `∀ {G : Type u_1} (a b : G), a = b` | `∀ {G : Type u_1} (a : G), a = a` | `NO_ASSUMPTION_DELTA` | different statements; reference false, candidate true |

The same pairs with `Type` instead of `Type u_1` are handled correctly (an added assumption is found).

## Cause

The undeclared universe name `u_1` is an elaboration error that Lean recovers from by elaborating the
statement as `sorry`. `#proofscope_assumptions11` still prints a result, with both conclusions equal to
`sorry` and empty telescopes. `run_case` takes the early `not added and not dropped` branch and returns
`NO_ASSUMPTION_DELTA` with **no certificate**: unlike every other verdict, this branch never checks the
`link_R` / `link_L` obligations that tie the extracted telescope to the elaborated statement.
(Unknown identifiers are caught: they make extraction fail and the verdict is `INCONCLUSIVE`.)

CMCD (`cmcd_v10`) is **not** affected: on the same inputs it reports `INCONCLUSIVE`, "abstraction not
linked to the elaborated statements", because its kernel `link` certificate fails.

## Consequences for SOTA-18

* Universe-polymorphic statements (`{G : Type*}`) are common in ProofNetVerif; the adapter prints them
  with their level names (`Type u_1`), so they reach this branch.
* `NO_ASSUMPTION_DELTA` is pre-registered as EQUIV (structural). Under the frozen engine these outputs
  are decisive and unsupported by any evidence; they count as unsound outputs `S` in the decision gate
  (conservative reading: the gate's wording says "certificates"; this verdict is not a kernel certificate,
  and both readings are reported).
* Per the protocol the frozen engine stays the headline condition **H0**. A repaired reading **H1** is
  reported separately (PROTOCOL amendment 2).

## Repair (not applied to the evaluated engine)

Fail closed: treat an extraction whose telescope or conclusions contain `sorry` (or any elaboration
error) as `INCONCLUSIVE`, and certify `link_R`/`link_L` before reporting `NO_ASSUMPTION_DELTA`.
