# SL-001 source audit (Phase A)

Audit date: 2026-11-11 (UTC). Performed by Claude (Anthropic) for Caleb J. Westfall by cloning and
reading the repositories below. Nothing here is taken from press coverage. Where a fact could not be
checked from a primary source, it is listed under "Not verified".

## 1. Primary sources inspected

| Source | Repository | Commit inspected | Commit date | Licence (file read) |
|---|---|---|---|---|
| OpenAI mathematics release | https://github.com/openai/math | `4eaee87548250b2682affda7d05d947c05554bae` (main) | 2026-10-29 | Apache-2.0 (`LICENSE`, `lean/LICENSE`) |
| same, commit cited by Formal Conjectures | https://github.com/openai/math | `adc7f1241b42e322a6451854ab7e4b4c146bf78a` | 2026-10-06 | Apache-2.0 |
| Formal Conjectures (Google DeepMind) | https://github.com/google-deepmind/formal-conjectures | `da703a5f239f734a47ede2f4e99b9ccc9e644cb5` (main) | 2026-11-11 | Apache-2.0 (`LICENSE`) |
| same, last commit before the release | same | `89294ea02bd7cd678d59984add52cb4baef3dbf4` | 2026-10-03 | Apache-2.0 |
| same, the commit that added the links | same | `3dfd999dfe5a3a1c739d362d3189daf9e08d9fa8` (PR #6898) | 2026-10-11 | Apache-2.0 |

Toolchains: openai/math `lean/` pins Lean `v4.34.1` and Mathlib `d13f23b723b8a846827a245b89c10fc7d3f11612`.
Formal Conjectures pins Lean `v4.33.1` and Mathlib `v4.33.1`. They are **not** the same environment, so
any formal comparison needs statement transport (PROTOCOL.md section 7).

## 2. What the OpenAI release contains (verified)

* `lean/OAI/` holds 162,417 `.lean` files in one library; `lean/ComparatorChallenges/` holds 838 files
  (a statement-only `.lean` challenge and a `.json` Comparator config per formalized result).
* `lean/formalization.yaml` maps each formalized result to a Comparator config and a declaration.
* `history.md` records three withdrawals on 2026-10-07 and later formalization fixes (2026-10-26, 2026-10-29).
* The release README recommends compiling small portions only. The import closure of a single result is
  large: 813 library modules for the Erdős 970 declaration (measured by this audit).

## 3. How the matched pairs were found

No matching by name, text similarity or model judgement was used. Formal Conjectures itself asserts the
matches: PR #6898 (merged 2026-10-11) marked problems solved and attached a
`formal_proof using lean4 at "<openai/math permalink>#L<line>"` attribute to each. Every theorem under
`FormalConjectures/ErdosProblems/` at the frozen head that carries such a link to `openai/math` is a case.
`sl001.py build-cases` regenerates the list from the source; `verify-freeze` checks it.

**Result: 18 linked theorem statements across 13 Erdős problems**
(3, 138, 184, 304, 371, 416 ×2, 431 ×2, 508 ×2, 952, 968, 970 ×2, 978 ×2, 1150). The list is `cases.jsonl`.
A further 17 links to `openai/math` exist outside `ErdosProblems/` (Wikipedia 9, Arxiv 3, Green 2,
Paper 2, OpenQuantumProblems 1); they are out of scope for SL-001 and noted for a follow-up.

Each case is therefore an **asserted link**: "statement B in Formal Conjectures is formally proved at
declaration A in openai/math". SL-001 audits that assertion.

## 4. Has this audit already been done?

* **Formal Conjectures PR #6898** states its own checks: changed modules build, each link resolves to a
  theorem, a grep for `sorry`, and inspection of Comparator configs. A reviewer executed one bridge proof
  (circulant Hadamard, not an Erdős problem) and wrote that the other comparisons were source-level review
  and that Comparator was not run. The PR itself records that several links differ from the repository
  statement by a transport step not present in the linked proof, including Erdős 371, 952 and 1150.
  Source: https://github.com/google-deepmind/formal-conjectures/pull/6898 (read 2026-11-11).
* **Bastounis, Circelli, Hansen, "Navier–Stokes lost in translation"** (arXiv:2610.08144) compares Lean
  code with the paper for one non-Erdős result. Known to this audit only through a secondary summary.
* **Palomar** (https://palomar-registry.org, Lean FRO and ICARM) registers Lean proofs after a Comparator
  run and an LLM check of the informal description. Formal Conjectures added a linter on 2026-10-29
  requiring Palomar links for solved research problems; the 18 OpenAI links carry
  `set_option linter.style.formal_proof_palomar false`, i.e. they are not yet backed by Palomar entries.
* No published machine-checked bridge from the OpenAI declarations to the 18 Formal Conjectures
  statements was found. Absence of a search result is not proof of absence.

## 5. Independence of the two sides (important limitation)

The mission assumed Formal Conjectures statements are *independent* formalizations of the problems.
That cannot be assumed and is false in at least one inspected case:

* Erdős 970: the Formal Conjectures file was added on 2026-09-07 (PR #5229). Its definition
  `IsJacobsthalBound` is character-for-character the definition in OpenAI's Comparator challenge
  `ComparatorChallenges/Jacobsthal.lean` (preprint dated 2026-09-25). The OpenAI statement was evidently
  written with the public Formal Conjectures (or a derived) formalization in view.
* `erdos_970.variants.iterated_log` did not exist before the release; it was added by the linking PR
  to record the OpenAI result. It is not independent of A in any sense.

Consequences. (i) Agreement between A and B is evidence about *transcription*, not independent
corroboration of faithfulness to Erdős's problem. (ii) Stage 1 classifies each case by a frozen,
mechanical independence rule (PROTOCOL.md section 6) and reports the classes separately. (iii) No SL-001
outcome can raise a faithfulness level above `unassessed`.

## 6. Compatibility

Lean 4.33.1 (B) versus 4.34.1 (A), different Mathlib revisions, and B uses Formal Conjectures utilities
(`answer(...)`, attributes, the `module` system). The Formal Conjectures statements at the frozen head no
longer wrap propositions in `answer(...)`. Whether each B transports to A's environment without change is
an empirical question for Stage 2; a failure is recorded as `unsupported_input` or
`blocked_infrastructure`, never as a mathematical finding.

## 7. Cases inspected before the protocol was frozen (disclosure)

To design the audit, three cases were read by hand before freezing: Erdős 970 (`erdos_970`, used as the
single pilot for the Stage 1 code), Erdős 3 and Erdős 371 (file diffs only). No checker was run on any
case before the freeze. Observations made on those three cases are therefore exploratory.

## 8. Not verified

* The OpenAI library was not built. No statement in this audit is a claim that any OpenAI proof compiles.
* Press reports that the Lean file for Erdős 3 "proves a weaker bound" were not confirmed or refuted.
  At the inspected commits the linked declaration is `manuscriptReciprocalProgressionTheorem`.
* The Erdős problems forum post listing 23 problems could not be fetched (robots exclusion); the count of
  23 comes from secondary coverage. This audit's own count is 13 problems with links in Formal Conjectures.
* Whether OpenAI used Formal Conjectures or FrontierMath Erdős statements as targets is inferred from
  dates and verbatim text, not from any statement by OpenAI.
