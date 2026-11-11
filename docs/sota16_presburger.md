# SOTA-16: Presburger instantiation certificates (branch `research/sota16-presburger`)

Base: v1.3 (`v1.2-review` @ `502db13`). Lean 4.34.1, core only.

## Hypothesis

For a once-occurring function symbol whose reference argument is `k * n + c`, the residual
obligations of SOTA-14 Theorem B are Presburger sentences with at most one quantifier alternation,
so they can be certified by integer witnesses plus quantifier-free linear arithmetic.

## Theorem (Lean, `lean/ProofScope/PresElim.lean`, kernel-replayed)

* `adm_iff_instance`: with a solving function `g` (`s x = z → x = g z`), admissibility
  `∀ x, A x → s x = z → ρ x w` is the single instance at `g z`. Axiom-free.
* `fun_schematic_solved`, `fun_schematic_affine`: Theorem B with the inner quantifier removed; for
  `s x = k * x + c`, `k ≥ 1`, the solving function is `(z - c) / k`. Uses choice (inherited).

Consequence (informal, by decidability of Presburger arithmetic): schematic comparison in the
fragment **F-lin** (argument `k * n + c` with `k ≥ 1`; guards and relations quantifier-free linear
with literal `/` and `%`) is decidable.

## Algorithm (`proofscope/scopeelim.py: presburger_tactics`, `proofscope/scope_smt.py`)

| Obligation | Certificate |
|---|---|
| fibre `∀ y w, …` | instantiate the hypothesis at `(t y - c) / k`, then `omega` |
| no fibre `∃ y w, …` | integers from Z3 (untrusted), each conjunct by `omega` |
| vacuous `∃ z ∀ w, …` | `z` from Z3, instance `(z - c) / k`, `omega` |
| not vacuous `∀ z ∃ w, …` | candidate values for `w` (bound terms of `ρ` plus residues); assume none works, extract one failing `x` per candidate, `omega` |

The certificates run as a second pass in a separate Lean process, only for directions the v1.3
portfolio left open. Constant arguments (`k = 0`) are handled by the same scheme with bound terms
for `x`; completeness is **not** claimed there.

Completeness in F-lin is relative to two things that are not proved: `omega` closing every valid
quantifier-free goal it is given (Lean's `omega` omits the dark and grey shadows), and the candidate
set for `w` containing a witness (it is truncated to 8 terms).

## Evaluation (cases and engine hashed in `experiments/sota16/FREEZE.txt` before the first run)

120 seeded cases, 240 directions, harder than the SOTA-15 `func` group. Criteria fixed in advance:
0 disagreements with Z3, 0 disagreements between configurations, more certified directions.

| Configuration | Directions certified | Verdicts decided | Disagree with Z3 | Lean killed |
|---|---|---|---|---|
| v1.3 portfolio | 178 / 240 | 68 / 120 | 0 | 0 |
| SOTA-16, first (frozen) run | 209 / 240 | 103 / 120 | 0 | 13 cases |
| SOTA-16 after fix | 231 / 240 | 111 / 120 | 0 | 0 |

**First-run defect.** In 13 cases Lean was killed for memory (6 GB) inside `omega` on the
"not vacuous" goal with 24 candidates; because all obligations of a case shared one module, 22
directions that v1.3 certifies were lost. Fix after the freeze: second pass in its own process with
the default heartbeat budget, candidates capped at 8. No direction is lost after the fix.

Z3 (2 s per query) decided 165 directions; the engine certified 68 directions Z3 did not decide,
and Z3 decided 2 the engine did not. Median 3.7 s per case, maximum 28 s.

The first evaluation attempt was stopped by the 30-minute job limit during the Z3 stage (8 s per
query) before results were written; the runner was made resumable and rerun. Engine and cases were
not changed between those two attempts.

## Independent labels (`experiments/sota16/labels.py`)

Labels are computed without the engine, Lean or Theorem B: ENTAILS when Z3 or cvc5 refutes
`R(f) ∧ ¬F(f)` with `f` uninterpreted; SEPARATED when a solver returns a model, or when an explicit
function `f z = if z = z0 then v else a * q(z) + b` is found for which Z3 proves, as Presburger
sentences without uninterpreted symbols, that the reference holds and the formal claim fails.

Local run: 237 of 240 directions labelled (97 by Z3 model, 69 by explicit function, 68 by Z3
refutation, 3 by cvc5). Of the 231 directions certified after the fix, 230 carry a label and all
230 agree; one certified direction (`fl105` fwd, SEPARATED) has no independent label. The frozen
first run and the v1.3 configuration also have no contradiction.

## Integration

`compare_claimdelta` (and therefore `python3 -m proofscope.claimdelta --scopeelim`) runs the same
isolated second pass for the once-occurring fragment, only for directions still open after the v1.3
obligations, with ClaimDelta's own statement shapes. The reference guard, the law check and the
INCONSISTENT merge are unchanged.

## Adversarial tests (`tests/v02/test_sota16_adversarial.py`)

Slope-3 congruences (one decided, one open case that must never be wrong); constant arguments
including a jointly unsatisfiable reference; repeated and nested symbols (must abstain); non-affine
arguments (no Presburger tactics); truncated subtraction, division by zero and literals beyond
64 bits; a heavy congruence case that must finish, must not be killed, and must keep every
certificate the v1.3 portfolio finds; the adapter with and without the pass; a false reference
through the fallback (stays `REFERENCE_REFUTED`).

## Open directions after the fix (all 9)

| Case | Direction | Reference (guard; argument; relation) | Formal | Independent label |
|---|---|---|---|---|
| fl026 | fwd | `True`; `3 * n + 2`; `w / 2 = n` | `True`; `n + 3`; `w + n ≥ 5` | SEPARATED (explicit-function) |
| fl028 | bwd | `3 ≤ n`; `4`; `n ≤ w ∧ w % 2 = 0` | `n ≠ 2`; `3 * n + 2`; `w / 2 = n ∨ w % 2 = 0` | ENTAILS (z3) |
| fl047 | fwd | `3 ≤ n`; `n + 3`; `w % 3 = n % 3 ∧ 3 * n ≤ w` | `True`; `3 * n`; `w % 3 = n % 3` | none (-) |
| fl049 | fwd | `2 ≤ n ∧ n % 2 = 1`; `4`; `n + 2 < w ∨ w = n` | `True`; `4`; `n + 2 < w ∨ w = n` | ENTAILS (z3) |
| fl061 | fwd | `3 ≤ n`; `2 * n + 1`; `w ≤ 2 * n + 1 ∧ w % 3 = n % 3` | `True`; `0`; `w = n` | SEPARATED (explicit-function) |
| fl067 | fwd | `n % 3 = 1`; `4`; `w < 7 ∧ 3 * n ≤ w` | `True`; `0`; `w = n ∧ n < w` | ENTAILS (z3) |
| fl070 | fwd | `3 ≤ n`; `3 * n`; `2 * w ≤ n ∧ w % 3 = n % 3` | `3 ≤ n`; `3 * n`; `n < w` | none (-) |
| fl101 | fwd | `2 ≤ n ∧ n % 2 = 1`; `0`; `n ≤ w` | `True`; `4`; `w < n` | ENTAILS (cvc5) |
| fl117 | fwd | `n % 3 = 1`; `n`; `n ≤ 2 * w ∧ 3 * n ≤ w` | `n % 3 = 1`; `n`; `2 * w ≤ n` | SEPARATED (explicit-function) |

Each of these is an abstention, not a wrong answer. By the independent labels four are true
entailments, three are separations and two are unlabelled. They involve modulus-3 or slope-3
relations, or a constant argument, where the instantiation and candidate sets are truncated or not
known to be complete.

## Limits

* 9 directions remain open; all involve congruence relations with slope 3 or constant arguments.
* Same author for engine, cases and labeller. The labels are independent of the engine's method, not of its author.
