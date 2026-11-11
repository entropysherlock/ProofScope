# SOTA-17: multi-occurrence comparison (branch `research/sota17-multioccurrence`)

Base: `v1.2-review` @ `198e17c`. Lean 4.34.1, core only. Research director: Caleb J. Westfall.
All numbers are runs by the author of the engine. Track B cases are author-generated; Track C
declarations are sampled from Mathlib by a seeded, hashed procedure.

**Classification: Level 2.** No Level 3 claim is made. Section 3 says why.

## 1. Result in one paragraph

Up to SOTA-16 a function symbol could be eliminated only when it occurred once on each side. This
branch handles a formal claim that reads `f` at any finite number of sites (repeated, colliding,
depending on several bound variables), against a reference from one of three classes, two of which
use the symbol twice themselves (`f n + a ≤ f (n+1) ≤ f n + b`, and `f n + a ≤ f (n+1)`, which
covers monotone and strictly monotone). The criterion is exact and kernel-checked. The principle
behind it is the Baker-Pixley theorem; the instances are elementary. On real Mathlib statements the
fragment is almost never reached: 1 of 69 declarations that bind a function `ℕ → ℕ`, 0 of 200
uniformly sampled declarations.

## 2. Theorems (`lean/ProofScope/MultiOcc.lean`, 26 axiom reports, fresh `leanchecker` replay)

Setting: `M : (Z → W) → Prop` is the model class of the reference. The formal claim is
`Form B t θ f := ∀ y, B y → θ y ((t y).map f)`, where `t y : List Z` are the sites.
`E2 M z₁ w₁ z₂ w₂ := ∃ f, M f ∧ f z₁ = w₁ ∧ f z₂ = w₂` is the binary projection of the class.

| Name | Statement | Axioms |
|---|---|---|
| `two_point_exact` | For any `M`, with two sites: entailment iff `∀ y w₁ w₂, B y → E2 M (t₁ y) w₁ (t₂ y) w₂ → θ y w₁ w₂` | none |
| `pairwise_insufficient` | For `f 0 + f 1 = f 2` the points `(0,0),(1,0),(2,1)` are pairwise extendable and not jointly extendable | propext, Quot.sound |
| `baker_pixley` | If `M` is closed under the pointwise action of a majority operation on `W`, every finite list of points that is pairwise extendable in `M` is jointly extendable in `M` (`Z` arbitrary) | propext |
| `majority_elim` | For such `M`: `(∀ f, M f → Form B t θ f) ↔ ∀ y, B y → ∀ vs, vs.length = (t y).length → ((∃ f, M f) ∧ PairExt M ((t y).zip vs)) → θ y vs` | propext |
| `step_E2` | For `a ≤ b`: `E2 (Step a b) z₁ w₁ z₂ w₂` iff `a·z₁ ≤ w₁`, `a·z₂ ≤ w₂` and, for `zᵢ ≤ zⱼ`, `wᵢ + a·(zⱼ − zᵢ) ≤ wⱼ ≤ wᵢ + b·(zⱼ − zᵢ)` | standard |
| `step_points`, `step_elim` | Joint extension and the exact elimination criterion for `Step a b`, any number of sites | standard |
| `lower_E2`, `lower_points`, `lower_elim` | The same for `Lower a` (`f x + a ≤ f (x+1)`) | standard |
| `pointwise_points`, `pointwise_elim` | Reference of Theorem B (one site) against a formal claim with any number of sites: admissibility of each point and functionality of the list | standard |
| `sq_majority_closed`, `sq_E2` | Theorem C's reference `Sq` is closed under the median, and its binary projection is the graph of squaring | propext, Quot.sound |

"standard" is `propext, Classical.choice, Quot.sound`. `elim_sound` (criterion ⇒ entailment) and
`sep_of_points` use `propext` only.

Proof of `baker_pixley`: induction on the number of points. For `a :: b :: c :: r`, the induction
hypothesis gives members `f_a, f_b, f_c` through the list without `a`, without `b`, without `c`.
`μ(f_a, f_b, f_c)` is in `M`, and at every point of the list at least two of the three functions
take the prescribed value, so the majority does. No finiteness of `Z` or `W` is used, because full
models are combined.

Proof of `step_E2` (⇐): for `z₁ ≤ z₂` the function

    x ↦ w₁ − a·(z₁ − x)                           if x ≤ z₁
        max (w₁ + a·(x − z₁)) (w₂ − b·(z₂ − x))    if z₁ < x ≤ z₂
        w₂ + a·(x − z₂)                           otherwise

has increments in `[a, b]` and passes through both points (`stepFun_step`).

What makes a fragment tractable, as far as these theorems show: (i) the model class is closed under
a majority operation, so two-point information is complete; (ii) the binary projection has a
closed form in linear arithmetic. `sq_majority_closed` shows (i) does not imply (ii).

## 3. Novelty audit

| Candidate | Nearest known results | Verdict |
|---|---|---|
| Majority-closed classes are determined by binary projections (`baker_pixley`, `majority_elim`) | Baker and Pixley 1975 (algebras with a majority term; subalgebras of powers are determined by two-fold projections). Jeavons, Cohen and Cooper 1998, *Constraints, consistency and closure* (near-unanimity of arity k+1 gives k-decomposability). Infinite-domain versions in the work of Bodirsky and coauthors on ω-categorical templates | Classical. The Lean statement for function classes on an arbitrary domain is a restatement with the same proof |
| Pointwise reference against several formal sites (`pointwise_elim`) | Ackermann's reduction; local theory extensions (Sofronie-Stokkermans 2005, guarded bounds are local); array property fragment (Bradley, Manna and Sipma 2006) | Classical |
| Closed form for increments in `[a, b]`, and for monotone / strictly monotone (`step_E2`, `lower_E2`) | Difference-bound constraints; Habermehl, Iosif and Vojnar 2008, *What else is decidable about integer arrays?* (decidability for array formulas with difference constraints between neighbouring cells); monotone functions as a local extension (Sofronie-Stokkermans 2005) | Elementary. Decidability of the fragment follows from known results; the closed form is a short calculation |
| `MonoElim` (SOTA-15) is a special case | - | `Lower 0` with pointwise boxes is not covered here; see section 8 |

Not found in the literature in this form: the use of the two facts as an exact, kernel-checked
criterion for *comparing* two schematic statements, with separations certified by constructing a
total function from finitely many points. That is a packaging and engineering contribution. It is
not a new theorem, so the Level 3 gate of the mission is not met.

The literature search was a keyword search plus prior knowledge; it is not a systematic review.

## 4. Engine (`proofscope/multiocc.py`, `python3 -m proofscope.multiocc SPEC.json --out DIR`)

A claim is `∀ vars, guard → body`; `f` may occur at any argument terms in `body`. For a direction
"H entails C" the hypothesis side must be in a class:

| Class | Recognised when | ENTAILS certificate | SEPARATED certificate |
|---|---|---|---|
| `step` | sites `n`, `n+1`; `guard → body` equivalent to `u + a ≤ v ∧ v ≤ u + b` | `step_pair` at every ordered pair of sites of `C`, then `omega` | instance and values from Z3, `step_points`, evaluation of `C` |
| `lower` | same with `u + a ≤ v` | `lower_pair`, `omega` | `lower_points` |
| `pointwise` | one site `k·n + c`, `k ≥ 1` | `adm_of_ref` at the solved instance of every site, congruence facts for coinciding sites, `omega`; or vacuity | `pointwise_points` with a certificate that every argument admits a value |

The class parameters are guessed with Z3 and enter the certificate only through a Lean proof of
`H f → class f` (or the converse for separations), so a wrong guess yields no certificate
(`test_nonconvex_steps_are_really_different`). Witnesses from Z3 are untrusted
(`test_wrong_witness_gives_no_certificate`, `test_inconsistent_points_rejected`). The conclusion
side may bind several variables; the hypothesis side one.

Each verdict is a Lean theorem about the native statements `∀ f, Ref f → Frm f` or its negation,
accepted by `proofscope.certify` (tactic closes, clean recompile, standard axioms only,
`leanchecker` replay). The existing engine (`scopeelim.py`, `claimdelta.py`) is unchanged; the new
module is not yet wired into `claimdelta --scopeelim`.

Not complete: `omega` is not a full Presburger procedure, and Z3 may fail to return a witness.
Abstentions are reported as `UNKNOWN`; unsupported shapes as `UNSUPPORTED`.

## 5. Evaluation

### Track A: regression

`python3 -m pytest tests -q`: 138 passed, 1 skipped (base: 120 passed, 1 skipped; 18 new tests).
No existing module was modified, so every v1.3 and SOTA-16 certificate path is untouched.

### Track B: multi-occurrence cases (`experiments/sota17/`, frozen in `FREEZE.txt` before the first run)

120 seeded cases, 240 directions: 40 `step`, 30 `lower`, 30 `pointwise` references with a formal
claim of 2 to 4 sites, and 20 `outside` cases in which neither side is in a class. In every case the
converse direction has an unsupported hypothesis side by construction, so 100 directions are inside
the fragment and 140 are outside.

Independent labels (`labels.py`; no engine, no Lean, no pairwise criterion): ENTAILS when Z3 or
cvc5 refutes `H(f) ∧ ¬C(f)` with `f` uninterpreted; SEPARATED from a finite prefix `v_0 .. v_N`
found without uninterpreted symbols and extended by an elementary argument, or from an explicit
function `α·z + β`. 180 of 240 directions are labelled.

| Configuration | Certified (of 100 inside) | ENTAILS / SEPARATED | Certified outside (of 140) | Contradict a label | Certified without a label |
|---|---|---|---|---|---|
| v1.3 + SOTA-16 baseline | 0 | - | 0 | - | - |
| SOTA-17, first (frozen) run | 96 | 28 / 68 | 0 | 0 | 13 |
| SOTA-17 after fixes | 100 | 29 / 71 | 0 | 0 | 13 |

The baseline is 0 because no case has one site on each side, which is the only shape it accepts.
That is a statement about expressiveness, not about the baseline's quality on its own fragment.

First-run defects (all in the pointwise class, all abstentions): (1) with guard `True` the
instantiated fact was left under `True →`, which `omega` does not open; (2) a `dsimp` step closed
the goal and the following `omega` then failed on "no goals"; (3) the proof that every argument
admits a value used the SOTA-16 candidate set, which lacks residues of the solved instance, and its
expensive alternative ran out of heartbeats before cheaper ones were tried. Fixed after the freeze.

The 13 certified directions without a label are entailments (7 `step`, 6 `lower`) that Z3 and cvc5
did not refute within 4 s; the labeller's prefix search found no counterexample for them either.
A retry with 60 s limits (`extend_labels.py`) was stopped after two directions, neither of which it
labelled; the other eleven were not attempted. They are Lean theorems about the stated claims; what the labels would add is
a check on the generated statements.

Plain uninterpreted-function refutation decided 16 of the 100 inside directions (all entailments).
Median 1.7 s per case, maximum 4.4 s; median certificate module 1.8 kB.

### Track C: Mathlib pilot (`experiments/sota17/mathlib_pilot/`)

Pin: Mathlib `v4.34.1`, `d13f23b`. `extract.py` finds 189,240 `theorem`/`lemma` signatures
(text only; hash in `selection.json`). Selection (`make_selection.py`, seed 20261117):

* C1: 200 declarations sampled uniformly.
* C2: all 69 declarations whose own signature binds a function `ℕ → ℕ`, split by a hash of the
  name into 27 development and 42 held-out declarations. The translator was written against the
  development half only and frozen (`FREEZE.txt`) before the other two sets were read or run.

Task: translate the hypothesis on the function and the conclusion into the claim grammar and
certify "hypothesis entails conclusion". There is no Mathlib build in this pipeline: statements are
not elaborated, translation is syntactic, and two definitions are unfolded by a fixed dictionary
(`StrictMono f ↦ ∀ n, f n < f (n+1)`, `Monotone f ↦ ∀ n, f n ≤ f (n+1)`). The certified statement
is about the abstraction.

| Stage | C1 (200) | C2 development (27) | C2 held-out (42) |
|---|---|---|---|
| signature extracted | 200 | 27 | 42 |
| binders understood | 0 | 14 | 24 |
| abstracted into the grammar | 0 | 1 | 0 |
| hypothesis in a supported class | 0 | 1 | 0 |
| certified | 0 | 1 | 0 |

The one certified declaration is `StrictMono.add_le_nat` (`m + f n ≤ f (m + n)`), 0.9 s. Synthetic
perturbation (labelled synthetic): with the hypothesis weakened to `f k ≤ f (k+1)` the engine
certifies SEPARATED at `m = 2, n = 0`.

Main reasons for failure in C2: several hypotheses on the function (10), no hypothesis on the
function (11), several function symbols (9), no bracketed binder for the function (8), hypothesis
that is neither a `∀` over `ℕ` nor a dictionary law (8), typeclass binders (7). In C1, 136 of 200
declarations do not mention a function `ℕ → ℕ` at all. No real discrepancy was found; none was
looked for beyond the task above. No source-to-formalization pair was evaluated.

Not measured: elaboration, memory, any competitor on the same task.

## 6. Adversarial tests (`tests/v02/test_sota17_multiocc.py`, 18 tests)

Three and four sites; exact increments (`f` affine with unknown intercept); the base bound
`a·n ≤ f n`; truncated subtraction; sites that coincide at one instance only; pointwise references
with congruences; two bound variables; a literal beyond 64 bits; six shapes that must abstain
(stride 2, Theorem C's reference, nested application, `f 0 + f 1 = f 2`, non-convex increments,
products); wrong class guess; wrong and inconsistent witnesses.

## 7. Reproduction

    export PATH=<lean-4.34.1>/bin:$PATH ; pip install z3-solver cvc5 pytest
    python3 -m pytest tests -q
    python3 experiments/sota17/gen_cases.py                    # regenerates the cases bit-for-bit
    python3 experiments/sota17/labels.py OUT/labels.json       # about 10 minutes
    python3 experiments/sota17/run_eval.py OUT 4
    git clone --depth 1 --branch v4.34.1 https://github.com/leanprover-community/mathlib4 M
    python3 experiments/sota17/mathlib_pilot/extract.py M > population.json
    python3 experiments/sota17/mathlib_pilot/make_selection.py population.json   # must reproduce selection.json
    python3 experiments/sota17/mathlib_pilot/pilot.py C2_heldout OUT/pilot

Workflow `.github/workflows/sota17-reproduce.yml` runs all of this on a pull request to
`v1.2-review`.

## 7a. Reproduction on GitHub Actions

Run 42959056396 on commit `eadec1a` (GitHub-hosted runner, Lean 4.34.1, Python 3.12,
z3-solver 5.4.1.0, cvc5 1.4.2): all four jobs passed.

| Job | What it checked |
|---|---|
| MultiOcc.lean | compiles without diagnostics, 26 axiom reports within the standard three, `leanchecker --fresh` |
| Python regression suite | all of `tests/` |
| Track B | cases regenerated bit-for-bit; labels recomputed; engine and baseline rerun; no certified direction contradicts a label; totals equal to `results/postfix_summary.json` (100 certified, 29 / 71, 140 unsupported, baseline 0) |
| Track C | Mathlib at the pin; population re-extracted; `selection.json` reproduced; stage counts of all three splits equal to the committed results |

The first CI attempt (run 42957915483, commit `841cac4`) failed in Track C: the script then named
`select.py` shadowed Python's standard module `select` under Python 3.12 (it did not under the
local 3.13). The file was renamed without changing its content; the selection is unchanged.

The first-run (frozen) Track B numbers were not reproduced in CI; they are local only.

On the same pull request the existing workflow *SOTA-16 Reproduce Presburger Evaluation* failed
twice in its `Evaluate frozen` job: the runner was shut down about four minutes into the run of
the frozen SOTA-16 engine (`86e62a3`), with no output. That job does not execute any file changed
on this branch; the `Evaluate corrected` and label jobs passed. A re-run was started.

## 8. Limits and the next obstruction

* **Definability of the binary projection.** `majority_elim` is exact for every majority-closed
  reference, including Theorem C's, whose projection is squaring. For increments bounded by
  literals the projection is linear; for increments bounded by linear terms in `n` it is quadratic.
  The fragment boundary is where the n-fold composition of the step relation stops being
  Presburger-definable. Known results on transitive closures of difference-bound and octagonal
  relations (Comon and Jurski; Bozga, Iosif and Konečný) should cover periodic guards and strides
  `f (n + p)`; this was not done.
* **Conjunctions of hypotheses.** An intersection of majority-closed classes is majority-closed,
  so the pairwise criterion stays exact, but the binary projection of an intersection is not the
  intersection of the projections (bounds propagate along the domain). `Monotone ∧ bounded`
  (the hypotheses of `converges_of_monotone_of_bounded` and `Nat.stabilises_of_monotone` in the
  held-out set, which also need more than this) is an example. `MonoElim.mono_extension` (SOTA-15)
  is the one-site case.
* The hypothesis side has one bound variable; nested applications are unsupported; values and
  arguments are `Nat`.
* Engine and Track B cases have the same author. The labels are independent of the method, not of
  the author. Thirteen certified directions have no independent label.
* Real-statement coverage is 1 of 69 on the population the fragment could apply to.
