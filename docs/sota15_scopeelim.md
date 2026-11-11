# SOTA-15: ScopeElim engine (development branch `research/sota15-scopeelim`)

Base: `v1.2-review` @ `0824134`. Lean 4.34.1, core only. All numbers are local runs by the author of
the engine on author-generated cases; nothing here is an independent evaluation.

## 1. Supported fragments (exact)

Symbols range over **all** Lean predicates/functions of the stated type (full semantics over the
standard naturals). Terms and guards come from the grammar in `proofscope/scope_expr.py`
(numerals, variables, `+ - * / % ^`, application, `= ≠ < ≤ > ≥`, `∧ ∨ ¬ →`).

| Fragment | Shape | Status of the procedure |
|---|---|---|
| H-bounded | Reference and formal claim are conjunctions of clauses `∀ x̄ (each x < bound), HYP → S t̄`; `HYP` a conjunction of guards and atoms; formal clauses may also contain local rules `(S ā → S b̄)`; predicate arity 1–3 | **Complete**: derivation or least-model separation, for every direction whose rule side is definite |
| H-symbolic | Same without bounds; one variable per clause, unary predicates, terms `v + c` or `c` | Sound, incomplete (offset chaining; periodic/threshold model templates) |
| F-once | `∀ n, guard → rel[n, f (arg n)]` on both sides, `f : Nat → Nat` occurring once | Exact residual obligations (Theorem B); proving them is a tactic portfolio, so incomplete |

A direction is reported only with a certificate accepted by `proofscope.certify` (tactic closes, clean
recompile, axioms ⊆ {propext, Classical.choice, Quot.sound}, `leanchecker` replay). Search results
from Python are never trusted (`test_search_is_not_trusted`).

## 2. Theorems (Lean, `lean/ProofScope/`)

* `HornFin.lean`: `sat` terminates structurally; `closure_sound`, `closure_complete`,
  `entails_iff` (uniform entailment over all `σ : α → Prop` ⇔ membership in the computed closure),
  `instDecidableEntails`, `canonical_separation`, `entails_local` (local rules are extra rules).
  Axioms: propext, Quot.sound.
* `MonoElim.lean` (Challenge D): `mono_extension`, `mono_elim`, `mono_vacuous`,
  `nonconvex_two_point_fails`.
* `ScopeElim.lean` (SOTA-14, unchanged), `ScopeCert.lean` (helper lemmas; `realize_eq`,
  `sep_of_not_entails` use choice).

Not proved in Lean: that the Python grounding of a bounded schema corresponds to the rule list given
to `HornFin`. This affects completeness of the implementation only; each verdict has its own
certificate about the native statement.

**Decidability remark (informal).** For F-once with linear guards, arguments and relations, the four
residual obligations are Presburger sentences, so by Theorem B the comparison problem is decidable.
The engine abstains only because `omega` plus witness pools is not a full Presburger procedure.

## 3. Integration

* `python3 -m proofscope.scopeelim SPEC.json --out DIR` (native specs).
* `python3 -m proofscope.scopeelim CASE.json --claimdelta --out DIR` (ClaimDelta case format;
  fragment detected automatically; obligations are ClaimDelta's own `link*/fwd/bwd/sepW/sepS`).
* `python3 -m proofscope.claimdelta ... --scopeelim`: opt-in fallback, called only when v1.2 returns
  INCONCLUSIVE. v1.2 certificates are merged (contradiction ⇒ INCONSISTENT) and the v1.2 law check
  still applies. Without the flag v1.2 behaviour is unchanged.

Separations produced through the adapter are existence proofs (`sep_of_not_entails`, `realize`), not
explicit operations as in v1.2's registry.

## 4. Evaluation (cases and engine hashed in `experiments/sota15/FREEZE.txt` before the first run)

160 seeded random cases (`gen_cases.py`, seed 20261110). Ground truth: exhaustive enumeration of
interpretations for H-bounded (`oracle.py`); Z3 4.x as an independent tool elsewhere (`z3_check.py`).

First run (frozen engine), per direction:

| Group | Cases | Directions certified | Wrong vs oracle | Disagree with Z3 | Abstained |
|---|---|---|---|---|---|
| H-bounded | 60 | 108 / 120 | 0 / 120 | 0 / 120 | 12 (11 unsupported, 1 defect) |
| H-symbolic | 30 | 57 / 60 | n/a | 0 / 58 | 3 |
| F-once | 40 | 72 / 80 | n/a | 0 / 67 | 8 |

The defect (`hb004`): a correct least model whose certificate tactic could not discharge a rule with
guard `False`. Fixed after the freeze (one closing tactic); post-fix H-bounded is 109 / 120 with the
11 remaining abstentions all outside the definite fragment. On F-once the engine certified 11 directions on which Z3 returned unknown or timed out, and Z3
decided 6 on which the engine abstained (`postfix_native_summary.json`).

ClaimDelta-format cases (30, run after the fix): v1.2 alone decided 13; with `--scopeelim` 30, i.e.
17 new certified decisions; 0 disagreements with Z3 on the 50 directions Z3 decided.

Median wall time per case 1.2 s (Horn) and 3.3 s (F-once); certificate modules 1.6 kB / 18 kB median.

## 5. Finding about v1.2

`cd009`: reference `1 ≤ n → 2 ^ (2 * n) = 0`. The schematic relation is LEAN_STRONGER, and v1.2's law
check then reports EQUIVALENT_BY_LAWS because the (false) reference implies anything once the power
laws are available. The law check should first exclude a reference refutable from the laws.

## 6. Unsupported (abstains)

Several opaque symbols; a symbol with two non-constant argument positions (`a * b`, `gcd a b`);
several binders with a function symbol; `∃`, `∣`, `↔`; non-`Nat` binders; atoms other than
`sym(..) = c`; nested implications on the rule side; non-linear residual obligations.

## 7. Reproduction

    export PATH=<lean-4.34.1>/bin:$PATH
    python3 -m pytest tests/v02 -q                      # existing suite + tests/v02/test_sota15_scopeelim.py
    python3 experiments/sota15/gen_cases.py              # regenerates the frozen cases bit-for-bit
    python3 experiments/sota15/run_eval.py OUT 2         # needs `pip install z3-solver`
    python3 -m proofscope.claimdelta experiments/sota15/cases/claimdelta/*.json --out OUT2 --scopeelim
