# SL-002 report: Erdős 952 and 1150, OpenAI proofs versus Formal Conjectures statements

Caleb J. Westfall (research director); Claude (Anthropic), AI-assisted research and engineering.
2026-11-11. Every claim below is tied to a CI run on `entropysherlock/ProofScope`, branch
`scopeledger/staging`. Nothing here has been reviewed by anyone outside the project.

## 1. Question

Formal Conjectures (PR #6898, 2026-10-11) marks Erdős 952 and 1150 as solved and links each to a
declaration in `openai/math`. The PR itself says these links differ from the repository statements by
a "routine transport" that is not in the linked proof (952: norm versus distance; 1150: length versus
degree), and that apart from one non-Erdős case the comparisons were source-level review. Is the
Formal Conjectures statement actually a consequence of OpenAI's theorem, and what exactly is the
relation between the two statements?

## 2. The statements (verbatim, checked in CI by `check.py verbatim`)

| | OpenAI (`openai/math` @ `4eaee87`, Comparator challenge) | Formal Conjectures (@ `da703a5`) |
|---|---|---|
| 952 | `MainEndpoint`: no injective `z : ℕ → ℤ[i]` of **irreducibles** with complex **distance** `dist (z (t+1)) (z t) ≤ D` for a **real** `D` | `¬ ∃ x C, Injective x ∧ ∀ n, Prime (x n) ∧ (x (n+1) - x n).norm < C` with **prime**, Gaussian **norm** (squared distance), **integer** `C`, strict `<` |
| 1150 | `MainStatement`: ∀ η > 0, **for all large N** there is a ±1 vector of **length N** with `‖∑ ε_k z^k‖ ≤ (1+η)√N` at every point of the unit circle | `¬ ∃ c > 0, ∀ᶠ n, ∀ P : ℂ[X]` with ±1 coefficients and **degree n**, `⨆_{|z|=1} ‖P z‖ > (1+c)√n` — i.e. for every c, **infinitely many** degrees admit a polynomial with sup ≤ (1+c)√n |

Provenance of the Formal Conjectures core propositions: 952 since 2025-11-21 (PR #1250, Malhar A.
Patel; until PR #4992 of 2026-08-16 it wrongly asserted the positive statement); 1150 since 2026-02-06
(PR #2012, Karanjot Singh). Both predate OpenAI's preprints (dated 2026-09-23 and 2026-09-26).

## 3. Results

| Result | Lean declaration | Imports | Status |
|---|---|---|---|
| **952: the two statements are equivalent** | `ScopeLedger.SL002.E952.fc_iff_main : FCStatement ↔ MainEndpoint` | Mathlib only | kernel-checked; axioms `propext, Classical.choice, Quot.sound`; `leanchecker` replay exit 0 (run 43024368984) |
| **1150: OpenAI's statement implies Formal Conjectures'** | `ScopeLedger.SL002.E1150.main_implies_fc : MainStatement → FCStatement` | Mathlib only | same (run 43024368984) |
| 1150 reverse direction | — | — | **undecided**; not attempted, and not expected to be easy: the FC statement only asks for infinitely many good degrees, OpenAI's gives all large lengths |
| **952 FC statement from OpenAI's proof** | `ScopeLedger.SL002.E952.erdos_952` | Mathlib + 41 OpenAI files | kernel-checked; axioms `propext, Classical.choice, Quot.sound`; built in 272 s; all 69 modules, including OpenAI's 65, replayed by `leanchecker` (run 43024368984) |
| **1150 FC statement from OpenAI's proof** | `ScopeLedger.SL002.E1150.erdos_1150` | Mathlib + 24 OpenAI files | kernel-checked; axioms `propext, Classical.choice, Quot.sound`; built in 272 s; all 69 modules, including OpenAI's 65, replayed by `leanchecker` (run 43024368984) |

Why the 952 equivalence is not vacuous: two proved closed propositions are trivially equivalent. Here
the equivalence is proved in a context that contains a proof of *neither* side (Mathlib only; the
statements are definitions, not imported theorems). It shows that two formalizations written ten months
apart, by different authors, with different primitives (`Prime`/`Irreducible`, norm/distance,
integer/real bound, `<`/`≤`) state the same proposition. The mathematical content is small: prime equals
irreducible in a PID, the norm is the squared distance, and an integer bound `⌊D²⌋ + 1` exists.

What 1150 shows: the Formal Conjectures statement is the negation of Erdős's question and needs only
infinitely many good degrees; OpenAI proved the stronger "all large lengths" form. The transport needs
a re-indexing (length `n + 1` versus degree `n`), the construction of a `Polynomial` with prescribed
coefficients and its degree, a supremum over the sphere, and an ε-argument
(`(1 + c/2)√(n+1) ≤ (1+c)√n` once `n ≥ (1 + c/2)²/c`).

Runs: bridges in 43024368984 (Lake build), 43024708516 and 43025657829 (plain `lean`); assembly in
43024368984 (Lake build, 272 s) and reproduced in 43025657829 by the second build path (plain `lean`,
69/69 modules in 344 s, same axioms, 69/69 `leanchecker` replays). The plain-`lean` assembly in 43024708516 failed in 2 s for an infrastructure reason
(Lean refuses a source file outside its root directory); it is recorded as `blocked_infrastructure`,
not as a mathematical result, and was relaunched in 43025657829.

Side result: OpenAI's two proofs themselves (65 files, about 22,000 lines) compile from verbatim
sources against pinned Lean and Mathlib, and every module replays under `leanchecker`, with only the
three standard axioms. This is a replay by this project's own pipeline, not an independent review.

## 4. Method and soundness

* Verbatim copies of both sides; CI fails if any copy differs from the source after whitespace
  normalization (`check.py verbatim`, unit-tested to detect a one-character change).
* No `sorry`, `axiom`, `native_decide` or other escape hatch in SL-002's files (`check.py scan`).
* `#print axioms` on each result, checked against the allowed set; an absent report is a failure.
* `leanchecker` replay of each SL-002 module.
* The assembly applies the bridge to OpenAI's real constant, so it also checks that OpenAI's library
  definition is definitionally the one in its Comparator challenge.
* OpenAI's library is not built with its own 30-dependency Lake configuration; the 65 source files the
  two proofs need (Mathlib-only imports, verified by `fetch_oai.py`) are copied verbatim, with hashes,
  and compiled against the same Lean (4.34.1) and Mathlib (`d13f23b`). This changes the build, not the
  sources.

## 5. What is and is not new (hostile assessment)

Already available elsewhere:
* OpenAI ships Comparator configs asserting that its library proves its own challenge statements.
  Palomar would check exactly that (statement A), not the Formal Conjectures statement (B). The
  Formal Conjectures files disable the linter that requires a Palomar entry for these links. The
  Palomar database itself could not be queried from this environment.
* SemantEq and BEq+ decide equivalence between two formal statements. They were not run on these pairs.
  1150 is not an equivalence, so an equivalence checker's correct answer is "no"; it would not supply
  the one-way certificate. For 952 the transport needs a constructed witness (`⌊D²⌋ + 1`), which is
  outside rewriting-style allowed steps, but this was not tested.

New, as far as the searches in SOURCE_AUDIT.md and this report found:
* Kernel-checked bridges for two of the links that Formal Conjectures records as needing an unverified
  transport.
* A solution-free certificate that two independently written formalizations of Erdős 952 coincide.
* A precise record that for 1150 the repository statement is implied by, and in form weaker than, what
  OpenAI proved.

Not new and not claimed: any new mathematics; any check of OpenAI's informal papers; any statement about
whether either formal statement faithfully captures what Erdős asked (no human review has happened).
The bridges are about 180 lines of routine Lean. A Formal Conjectures maintainer could have written them;
the point is that no one had, and the link was nonetheless marked solved.

## 6. Reproduce

```sh
git clone -b scopeledger/staging https://github.com/entropysherlock/ProofScope sl && cd sl
# CI: .github/workflows/sl002-bridges.yml (bridges job ~2 min after the Mathlib cache)
```
Locally, with Lean 4.34.1 and a Mathlib-only Lake project at `d13f23b` (`lake exe cache get`):
`python experiments/SL-002/build.py <mathlib-project> experiments/SL-002/project <out> SL002.E952 SL002.E1150`,
then `lean experiments/SL-002/project/AuditBridges.lean` with `LEAN_PATH=<out>/lib:$(lake env printenv LEAN_PATH)`.

## 7. Errors made during this run (kept on the record)

* Commit `70d396c` says the first run's Lake build "ran for 40+ minutes … consistent with Lake
  rebuilding Mathlib". That was wrong: the build took 29 seconds and succeeded; I misjudged elapsed time.
  The plain-`lean` driver introduced in that commit is kept as a second, independent build path.
* The Stage 2 build probe for Erdős 970 (run 43019580697) failed twice: GitHub's bash runs with `-e`, so
  the harness died on the build's non-zero exit before recording why. The build failure itself is
  unexplained; that probe is superseded by the per-closure build used here.
