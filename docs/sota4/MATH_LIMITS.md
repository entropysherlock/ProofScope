# Mathematical limitations (SOTA-4 Task N)

1. **Complete non-equivalence detection is impossible in general.** `¬(R ↔ L)` is equivalent to proving
   one side and refuting the other (`nonequiv_iff`); deciding it decides provability, which is undecidable
   for first-order arithmetic. *Mathematical limitation.* Every engine must abstain on some pairs (h12,
   x12). What can improve is coverage of decidable or bounded fragments: *engineering*.
2. **`difference_needs_a_proof`.** A certified difference needs a proof of one side. When both sides are
   open, no sound difference certificate exists, whatever the search (x12, h12). *Mathematical.* When one
   side is provable but beyond the portfolio (x10: `n ≥ 2 → n*n ≥ 4` needs nonlinear arithmetic in core
   Lean) it is *engineering* (better provers, Mathlib tactics).
3. **Certified joint scope composition.** `joint_failure_iff` is proved for telescopes that share H and
   have aligned binders. Mapping real statement pairs onto such a telescope (J1) needs a certified link
   for the joint extraction. With dependent binders, an added or dropped binder that later types mention
   has no well-typed alignment, and the decomposition is undefined. *Mixed*: linking is engineering, the
   dependent case needs new mathematics (a notion of region over dependent telescopes).
4. **Minimal law-relative explanation.** Minimal sets of laws Φ under which `R ↔ L` holds are minimal
   unsatisfiable-core style objects: computing one requires an equivalence prover inside a search over
   subsets; minimum (not minimal) is NP-hard even propositionally. *Mathematical* for optimality,
   *engineering* for useful minimal (not minimum) answers. Not implemented in this mission, by instruction.
5. **Countermodel synthesis over Mathlib structures.** Finite countermodels exist only for some
   theories; ordered fields, complete spaces and many analytic structures have no finite models, so
   refutation needs symbolic witnesses (e.g. specific reals, matrices) and proofs about them. *Mostly
   mathematical* for completeness; *engineering* for curated carrier registries, which is what ProofScope
   has.
