# SOTA-11 report: SHARPEN, a certified theorem-sharpening and law-finding prototype

Caleb J. Westfall / WESTFALL program. Work session of 10 November 2026. Lean 4.34.1 (core, no Mathlib), Z3 for search.
Everything below marked "Lean-checked" was accepted by the real Lean checker in this session; the files are in `out/` and `lean/`.

## 1. Directions investigated
- **A + C (chosen core):** given a statement in a fixed language, push every constant to its exact limit, delete every
  removable hypothesis, and certify that no single further step is possible. For false statements, synthesize the
  weakest single missing hypothesis from a template language.
- **D:** random conjecture generation over floor/mod expressions, with refutation and sharpening.
- **E:** run the sharpener across a two-parameter family, fit a closed-form law for the exact constants, test the law on
  held-out parameters, then prove it for all parameters.
- **B (lemma invention):** not attempted.

## 2. Strongest result
A working pipeline, instance data -> closed-form law -> held-out test -> general Lean proof, demonstrated once end to end:
the law finder produced `-(b - gcd(a,b)) <= x % a - x % b <= a - gcd(a,b)` from data without gcd being suggested for that
family, and `lean/ResidueGap.lean` proves it for all moduli (three theorems, axioms: propext, Quot.sound only).
**The mathematics of this law is classical** (it is a corollary of the Chinese remainder theorem for non-coprime moduli).
What is new here is the tool, not the theorem.

## 3. Mathematical content
**Language L.** `forall x1..xn : Int, t1 <= c1 -> ... -> tm <= cm -> t0 <= c0`, terms built from variables, literals, `+`,
literal multiples, `/ k`, `% k` (k >= 2 literal).

**Definition (1-step sharp).** A valid, non-vacuous L-theorem is 1-step sharp if (i) lowering `c0` by 1 makes it false,
(ii) raising any single `ci` by 1 makes it false. Dropped hypotheses are those whose constant can be raised without bound
and whose removal keeps validity.

**Proposition (one pass suffices).** Tighten the conclusion first, then relax hypotheses one at a time to their maximum.
The result is 1-step sharp. *Proof.* Validity is monotone in each constant. Weakening a later hypothesis can only shrink
the room available to an earlier one, which was already at its maximum and is still valid; likewise the conclusion's
minimum can only rise, and it is still valid at its current value. (Paper proof; not formalized.)

**Residue-gap theorem (Lean-checked, all moduli).** For `a, b, g > 0` with `g | a`, `g | b`:
`-(b - g) <= x % a - x % b <= a - g`; and if `a*u + b*v = g` then some `x` attains `a - g`.
Bezout's identity is taken as a hypothesis because Lean core does not contain it.

**Weighted residue law (paper proof + 80 Lean-checked instances).** With `g = gcd(a,b)`,
`max_x c1*(x % a) + c2*(x % b) = max(c1,0)*(a-g) + max(c2,0)*(b-g) + max(0, c1+c2)*(g-1)`.
*Proof sketch.* The attainable pairs are exactly `(g*i + r, g*j + r)` with `0 <= r < g`; the objective is separable in i, j, r.
Not formalized in general.

## 4. Experimental evidence (actual runs)
| Experiment | Result |
| --- | --- |
| Sharpen 120 random slack theorems (2-3 variables, 6-10 hypotheses) | 120 sharpened; mean hypotheses 7.3 -> 1.6; 542/542 Lean declarations accepted |
| Repair 11 false statements | 7 repairable by one template atom, 13 repairs; 39/39 Lean declarations accepted (theorem, non-vacuity, weakest-ness) |
| Random hunt, 300 conjectured differences | 249 unbounded, 51 bounded with exact two-sided range (20 of them constant); 204/204 Lean declarations accepted |
| Law finder, 240 random two-parameter families | 74 bounded on the 6x6 training grid; 58 fitted; 57 survive 10 held-out parameter pairs; 1 fit refuted; 14 surviving laws involve gcd/min/max |
| Weighted residue law, 80 fresh (a,b,c1,c2), 35 non-coprime | 80/80 predictions equal the exact maximum; 160/160 Lean declarations accepted |
| General theorem `lean/ResidueGap.lean` | accepted, no `sorry`, axioms propext + Quot.sound |

Most random-hunt output is trivia (`0 <= x - x <= 0` appears). The hunt shows the loop runs, not that it finds interesting theorems.

## 5. Machine verification
Lean sources: `out/bench_sharpen.lean`, `out/bench_repair.lean`, `out/hunt.lean`, `out/master_instances.lean`,
`lean/ResidueGap.lean`. Theorems use `first | omega | lia | grind`; counterexamples and witnesses use explicit values
and `decide`. `omega` alone failed on 4 of 204 hunt goals (its documented incompleteness); the `lia` fallback closed them.
`lia`/`grind` proofs additionally use `Classical.choice`. Z3 is never trusted: a wrong Z3 answer shows up as a Lean failure.

## 6. Algorithm
1. Non-vacuity witness (Z3) -> 2. validity or counterexample -> 3. minimise the conclusion constant by exponential +
binary search on validity -> 4. for each hypothesis, maximise its constant or drop it -> 5. for each constant, extract a
counterexample to the one-step-stronger statement -> 6. emit Lean and check.
Repair: for each template atom `t <= c`, binary-search the largest `c` giving validity, reject vacuous repairs.
Law finder: exact sup/inf on a parameter grid -> exact rational fit over a feature set
(a, b, ab, gcd, lcm, min, max, a%b, a/b, squares, gcd products), at most 3 features -> held-out test.

## 7. Prototype
`sharpen.py` (engine + Lean emission), `discover.py` (hunt + law finder), `bench.py`, `master_test.py`, `run_all.sh`.
Standalone; it imports nothing from ProofScope and changes nothing in the repository. Natural home: `experiments/sota11/`.

## 8. Failed or weak hypotheses
- Random generation as a source of interesting theorems: failed. 83% unbounded, the rest mostly trivial.
- `omega` as sole certifier: incomplete on nested mod; needed `lia`.
- Division families in the law finder: almost none bounded, so every discovered law is about remainders.
- One fitted law, `max b*((b*x) % a) + a*(x % b) = 2ab - a - b*gcd`, fit all 36 training points and was refuted on held-out moduli.
- Hypothesis-order "Pareto frontier": three orders gave the same theorem on the demo; no evidence yet that orders matter in practice.
- 16 of 74 bounded families have no formula in the feature set (all involve nested mod or `(a*x) % b` sharing a variable).

## 9. Generalization
The sharpening loop needs only a decidable (or semi-decidable) validity oracle with models and a monotone parameter;
it transfers directly to linear real arithmetic, bit-vectors and difference logic. It does not transfer to statements
outside decidable fragments without a much weaker guarantee. The law finder is limited by its feature set.

## 10. Breakthrough assessment: Level 2
Useful, working, fully certified tooling plus one end-to-end data-to-general-theorem demonstration. Not Level 3 or 4:
the theorem proved is classical, the component techniques (unsat-core style hypothesis minimisation, optimisation modulo
theories, formula fitting) are known, the language is narrow, and no literature search for prior systems was done.
A skeptical expert would call this a clean prototype, not a discovery.

## 11. Next frontier
The coupled-variable families the fitter could not explain, e.g. the exact maximum of `a*(x % b) + b*((b*x) % a)` and
of `((x % a) % b)` combinations. These couple a residue with a multiplied residue, the closed form is not in
{gcd, lcm, min, max, floor} of (a,b), and the data suggest Euclid-algorithm or continued-fraction structure.
That is the first place this engine produced a question whose answer I do not know.