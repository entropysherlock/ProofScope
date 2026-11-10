# WESTFALL PROOFSCOPE SOTA-6 — CERTIFIED MATHEMATICAL SEMANTIC AUDITOR

Caleb J. Westfall · branch `research/sota6-certified-semantic-auditor` from `8affd967175c4629bf6e75cc03d44f01419c025e`.

**Evidence labels:**
- [P] mathematically proved;
- [K] Lean-kernel verified, which here also means `leanchecker` replay;
- [E] experimentally observed;
- [I] independently validated (nothing in this report is);
- [C] conjectural;
- [U] unsuccessful;
- [N] not yet tested.

## A. Executive verdict
**Level 2 on a restricted fragment. Not Level 3 or 4.**

* **Delivered: certified minimal repair under a finite edit grammar.** [K] It runs end to end:
  statement pair → discrepancy → minimum-cost repairs → one certificate module → explanation. It works for
  statements of the form ∀ γ, hyps → conclusion over an aligned context. It returns:
  - every repair of minimum cost within the grammar, as a Lean proof of formulation equivalence;
  - a kernel `decide` check that every cheaper edit is ruled out by an explicit counterexample point;
  - theorems linking both source texts to their structured forms, which blocks substitution attacks.
* **It worked on all three demonstrations** [K]: missing nonzero hypothesis, missing sign hypothesis in an
  order statement, and a dropped disjunct. One of them has two distinct minimal repairs.
* **Gate 1 (soundness): passed for this fragment.** `minimal_repair_sound`, `not_formEquiv_of_separates`
  and `formEquiv_iff_points` (completeness over finite contexts) [P][K].
* **Gate 2 (source fidelity): passed for the fragment's own inputs** [K]. Gates 3 and 4: passed on toy
  examples [K][E].
* **Gate 5 (novelty): not passed.** See section L.
* **Gate 6 (independent utility): not tested** [N].

## B. SOTA-5 baseline
* The SOTA-5 commit `8affd96` has a tree identical to the delivered patch [E, verified with git].
* Workflow jobs and artifacts are **not verified here**. This session can read git but cannot use the
  GitHub API or download artifacts, so the brief's numbers are used as reported.
* Nothing on the protected branches was touched. The `baseline` job checks the protected paths, including
  every SOTA-5 file, byte for byte.

## C. Prior art and capability matrix
| capability | status | closest work |
|---|---|---|
| Label, categorize, localize and correct misformalizations (LLM) | known and available | FormalRx (ICML 2026, 28-category taxonomy, trained diagnostic model) |
| Lean-checkable witness separating candidate from intended formalization | known and available | FormalRx-CC (ICML 2026, seven witness families, 204 examples) |
| Formal equivalence check plus diagnosis-guided repair (LLM) | known and available | Roundtrip verification and repair (Amrollahi, Lopez, Barrett 2026; SMT/Lean) |
| Counterexample search exposing misformalizations | known and available | Aristotle in Lean-GAP; formal counterexample search in MechGeo |
| Minimal sufficient assumption sets, hitting-set duality | known (theory and tools) | axiom pinpointing (MinAs), MUS/MCS enumeration (MARCO) |
| Kernel-certified relation types with explicit non-claims | known, not integrated elsewhere | ProofScope SOTA-5 |
| **Repair with a kernel proof that no cheaper repair exists in a declared grammar** | **potentially distinctive** | not found in the works above; related to minimal correction sets and program-repair minimality |
| Formulation equivalence (region + conclusion) as the repair target | potentially distinctive as a choice; mathematically elementary | — |
| New mathematics | not supported | — |

## D. Mathematics (`research/sota6/Repair.lean`, 9 declarations, all [P][K], no axioms beyond propext/Quot.sound)
- **Definition.** `FormEquiv R F`: the same hypothesis region, and the same conclusion on that region.
- **Theorems:**
  - `formEquiv_open`, `formEquiv_stmt`: FormEquiv implies open equivalence, which implies closed equivalence.
  - `open_equiv_trivial_for_true`: when both statements are true, open equivalence holds whatever they say.
    That is why open equivalence is the wrong repair target.
  - `div_open_equiv` and `div_not_formEquiv`: `n≠0 → n/n=1` and `2≤n → n/n=1` are open-equivalent but are
    not the same formulation; they are separated at n = 1.
  - `not_formEquiv_of_separates`: soundness of counterexample points.
  - `minimal_repair_sound`: a repair proof plus separations of every cheaper mask certify the minimum cost
    within the grammar.
  - `two_minimal_repairs`: minimality does not mean uniqueness.
  - `formEquiv_iff_points`: over a finite, exhaustively listed context, FormEquiv reduces to a check on
    points. In that case the search is complete and exact.
- **Complexity.** Exact minimal repair costs 2^n mask checks for n edits. That is unavoidable in general,
  because the problem contains minimal-correction-set search.

## E. Source-to-Lean integrity
The certificate module contains three kinds of link:
- `R_source_stmt` and `F_source_stmt`: each source statement *as written* ↔ its structured hypothesis form;
- the structured repair grammar `apply`;
- the Separates instance.

**Tested attack** [K]: a candidate whose structured form adds a hypothesis that is absent from its source.
`F_source_stmt` fails, the proof falls back to `sorryAx`, and the result is rejected.

The SOTA-5 adapter v2 standalone round-trip check remains the link from Lean declarations to source text.

## F. Assumption explanation
**The algebra example** (SOTA-5 `lawrel`, e1) [K]: there are two incomparable minimal sufficient law sets,
{comm} and {assoc, idem}.

**For hypothesis-form statements, the repair engine is the assumption explainer** [K]:
- **r1:** `n ≠ 0` and `0 < n` both suffice. `2 ≤ n` fails at n = 1, and `n % 2 = 1` fails at n = 2.
- **r2:** `0 ≤ a` suffices. `0 ≤ b` fails at (−2, 0), and `0 < a` fails at (0, 0).

**d11 against Mathlib's `Group`.** `D11Mathlib.lean` proves cand ⟺ commutativity, with S₃ separating the
pair. It **was not compiled here, because Mathlib is unavailable** [N]. The `mathlib-d11` job compiles it,
and if it fails, that failure is the result.

## G. Certified repair results [K] (`docs/sota6/evidence-local/`)
| demo | discrepancy | grammar (edits) | outcome | minimal repairs | cheaper masks separated |
|---|---|---|---|---|---|
| r1 | missing nonzero (`n / n = 1`) | +n≠0, +0<n, +2≤n, +n%2=1 | MINIMAL_REPAIR | {+n≠0}, {+0<n} | 1 of 1 |
| r2 | missing sign (`a ≤ b → a² ≤ b²` over ℤ) | +0≤a, +0≤b, +0<a, −(a≤b) | MINIMAL_REPAIR | {+0≤a} | 1 of 1 |
| r3 | dropped disjunct (`x² = 1 → x = 1`) | concl:=x=1∨x=0, concl:=x=1∨x=−1, +0≤x | MINIMAL_REPAIR | {concl:=x=1∨x=−1} | 1 of 1 |

## H. Kernel evidence
- `Repair.lean`: `leanchecker --fresh` exit 0, and 9 `#print axioms`, all within {propext, Quot.sound}.
- Certificates: each compiles, its axioms are within the standard three, and it replays with `leanchecker`
  (exit 0 in all three demos).
- **Remaining trust:**
  - the Lean kernel;
  - `decide` evaluation;
  - the Python generator, which is untrusted, since every claim it makes is re-proved in the module;
  - the declared grammar and context.

## I. Adversarial results (`tests/sota6/test_repair.py`, 6/6 pass [E][K])
1. Two minimal repairs are returned, and the valid but non-minimal cost-2 repair is excluded.
2. A forged counterexample point is rejected by the kernel, and nothing is certified.
3. A source substitution attack is rejected.
4. A failed proof search is never treated as negative and never reported as "no repair".
5. A grammar with no repair is certified as NO_REPAIR_IN_GRAMMAR.
6. A vacuous reference is matched only by the same empty region. That is a documented limitation:
   formulation equivalence does not flag vacuity.

**Not tested** [N]: a definition changed under the same name, a typeclass change, quantifier order, and
dependent binders. The fragment cannot express quantifier changes or dependent binders.

The SOTA-4 and SOTA-5 hostile suites are unchanged.

## J. Performance [E]
**Repair pipeline**, whole process tree (core Lean, including the certificate compile and `leanchecker`):

| demo | CPU | wall | peak memory | processes |
|---|---|---|---|---|
| r1 | 2.24 s | 2.08 s | 514 MB | 8 |
| r2 | 1.65 s | 1.47 s | 515 MB | 6 |
| r3 | 1.30 s | 1.22 s | 503 MB | 6 |

**CJCS on the Mathlib suite: no change and no new measurement** [U]. Mathlib is unavailable here. SOTA-5's
30.45 s median with 4 environment loads stands. The 10 s target remains unmet.

## K. Independent evaluation readiness
- `docs/sota5/PILOT_PROTOCOL_v1.md` remains frozen.
- SOTA-6 adds one label column per case: the adjudicated *intended repair*, wherever reviewers can state
  one. Repair correctness is then scored only against that column.
- No reviewers exist yet [N].

## L. Novelty and publication
**Engineering, plus a potentially distinctive methods combination. Not new mathematics, and not a
breakthrough.**

**The distinctive claim, stated narrowly:** among published work found, FormalRx, FormalRx-CC and roundtrip
repair suggest or verify corrections, but none returns a repair with a kernel proof that no cheaper repair
exists in a declared grammar, and none uses a repair target that rejects the "true but wrong region" repair.

**Each ingredient is known:** minimal correction sets, counterexample-guided search, and kernel certificates.

**A methods paper needs:**
- the fragment lifted to Mathlib statements;
- grammars that are not hand-written for each case;
- independently labelled intended repairs.

## M. Grant potential
A defensible seed objective: *"certified minimal repairs for hypothesis and conclusion misformalizations,
evaluated against independently adjudicated intended repairs on 50 real Lean/Mathlib statement pairs."*

It is concrete and falsifiable, and it addresses the problem stated in the brief: an AI proves a formally
valid theorem about the wrong statement.

## N. Strongest objections
* **Hand-written grammar.** The grammar and the structured hypothesis forms are written by hand per
  example, so the repair is only as good as the candidate edits supplied.
* **Narrow fragment.** It covers hypothesis-form statements over a flat aligned context. There are no
  quantifier alternations or dependent binders, and Mathlib statements cannot be used yet.
* **Toy evidence.** Three demonstrations and six tests, all developer-written. The search is exponential
  in the number of edits.
* **d11 is untested.** The Mathlib version has not been compiled by anyone yet.

## O. Next challenge
**Run the repair engine on 20 real Mathlib statement pairs.** The grammars must be generated
automatically from the pair: hypotheses of either side, plus conclusion swaps.

- **Pass:**
  - at least 10 MINIMAL_REPAIR outcomes, each matching a repair independently stated by a Lean-literate
    reviewer;
  - zero certified repairs that the reviewer judges wrong;
  - every certificate replays.
- **Fail:** any certified repair judged wrong, or fewer than 5 matches.
