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

## Limits

* Not wired into the ClaimDelta adapter yet: `--scopeelim` still uses the v1.3 portfolio.
* 9 directions remain open; all involve congruence relations with slope 3 or constant arguments.
* Same author for engine, cases and oracle encoding; Z3 is the only independent check.
