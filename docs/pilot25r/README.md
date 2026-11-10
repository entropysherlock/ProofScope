# PS-25R — Pilot-25 engine recovery

Caleb J. Westfall · branch `research/pilot25-engine-recovery` from `5ab4729` (pilot branch). The frozen SOTA-7
commit `666c873` and the pilot branch are untouched.

**Evidence labels:**
- [L] reproduced locally, in core Lean, in the development sandbox;
- [T] software tests;
- [CI] produced by `.github/workflows/pilot25-recovery.yml`, not yet run;
- [U] unverified here.

**Authoritative artifact.** Run 42753579082, artifact 13734722756, could **not** be retrieved: this session
has git read access only, and GitHub artifacts need an authenticated download. The per-case outcomes in the
brief (14 memory, 9 input) are used as reported [U]. Which case had which outcome is not known here; the
CI `diagnose`, `telemetry` and `pilot-rerun` jobs produce that per case.

## A. Root causes

### Memory (14 cases)
1. **The budget does not follow the frozen protocol [L].**
   - `bench/pilot25_run/execute.py` sets 8000 MB and 120 CPU-s. Those are the values of the core-Lean
     synthetic dry run (`bench/sota7/dryrun_freeze.py`).
   - The frozen pilot protocol (`docs/sota5/PILOT_PROTOCOL_v1.md`, item 7) fixes 12000 MB whole-tree, plus a
     900 CPU-s measurement run.
   - The same engine's documented Mathlib peaks are 9,577 MB (SOTA-4) at median 28 CPU-s, with a maximum of
     422 CPU-s. Both are above 8000 MB / 120 s.
2. **Most of the counted memory is file-backed, not allocated [L].**
   - `bench/limits.py` caps the *sum of VmRSS* over the process tree. VmRSS includes file-backed pages:
     memory-mapped `.olean` files and the Lean shared library.
   - In core Lean, after the REPL imports the extractor and search code, VmRSS is 1574 MB. RssFile is
     1429 MB (91%) and RssAnon (private) is only 144 MB.
   - Mathlib's `.olean` files are many gigabytes, so on a Mathlib run most of an 8000 MB cap is consumed by
     mapped library pages before any search. The magnitude for Mathlib is [CI]: the `telemetry` job records
     per stage the peaks of VmRSS, RssAnon and RssFile for the frozen and recovered engines.
3. **Pathological growth from the engine** (state accumulation, `exact?` initialising its index, search
   branching) is **not established**. It is measured by the `telemetry` job, whose per-stage peaks
   (BUILD / SEARCH / VERIFY / REPLAY) separate a high Mathlib baseline from growth during search [CI].

**The limiter is not changed.** Its methodology is shared with the competitor runs, and redefining memory
would make earlier comparisons incomparable. The correction is to use the protocol's budget, and to report
private and file-backed memory separately.

### Input not evaluable (9 cases)
These are not yet attributed per case [CI: `diagnose` matrix]. Five general failure classes were found and
reproduced [L]:

| class | reproduction (core Lean) | Pilot-25 cases showing it in their text (static reading, not elaboration) |
|---|---|---|
| MISSING_CONTEXT: `open` lines stripped from the ProofNet source | `succ` unknown without `open Nat`, resolves with it | bare `Tendsto`/`atTop`/`𝓝`/`Injective` (c2f1c, c6bb0), `X` (c132a, ca8bc), `span` (c3070, ca8bc), `Icc` (c57be) |
| MISSING_CONTEXT: undeclared universe | `Type u` → "unknown universe level `u`" | c3070, c733a |
| INVALID_SOURCE: literal `...` | "unexpected token '...'" | c5324 (candidate) |
| INVALID_SOURCE: free identifier | `i` unknown | c1f44 (`i`), c2f1c (`a`), ca8bc (`R`, `X`) |
| UNSUPPORTED_FORMALIZATION: unannotated binder in term context | `∀ {R} [Add R] …` → unresolved metavariables | ca2dd (`{R}`) |

### Two engine bugs found during the reproduction [L][T]
1. **Error-blind extraction.**
   - Lean recovers from an elaboration error by inserting `sorry`, so the extractor still printed three
     results.
   - The engine checked only that the count was 3. A statement with an unknown identifier was therefore sent
     into proof search as `… sorry …`: in core Lean it ended as ABSTAIN instead of INPUT_NOT_EVALUABLE.
   - This is sound, because nothing can certify, but it is misclassified, and with Mathlib it can mean long
     searches on a broken statement.
2. **Namespace leak.**
   - The search metaprogram's `open Lean Elab Command` was not scoped, so it stayed open for user
     statements: `Name` resolved to `Lean.Name`.

## B. Changes (engine diff limited to three files, asserted by the `integrity` job)
| file | change | why |
|---|---|---|
| `proofscope/experimental/cjcs4.py` | extraction fails closed on any elaboration error; optional `PROOFSCOPE_PREAMBLE` (only `open …`, `open scoped …`, `universe …`; anything else refused), applied to both the search session and the certificate header | bugs A.1 and MISSING_CONTEXT; the preamble is source context, not a change of statement |
| `lean/ProofScope/CJCSSearch.lean` | `open Lean Elab Command` moved inside the namespace | bug A.2 |
| `bench/sota7/runner.py` | passes `environment.preamble` to the engine | so that public cases can carry their source header |

**New files:**
- `bench/pilot25r/`: case loader, elaboration matrix, telemetry, header recovery from the *original*
  archive, protocol-budget rerun, report;
- `tests/pilot25r/test_preamble.py`;
- `.github/workflows/pilot25-recovery.yml`.

**No statement is rewritten.** A preamble is applied only if `headers.py` finds the lines verbatim in the
original `PILOT50_PUBLIC_v2.zip` case file. That archive is not available here, so no preamble is applied in
the rerun as committed.

## D. Regressions [L][T]
- **78 tests pass:**
  - PS-25R (5);
  - SOTA-7: 12 + 10 + 10;
  - SOTA-6 repair (6);
  - SOTA-5: d03 (4) and relations (5);
  - SOTA-4: hostile (11) and integrity (15).
- **The 24 core development and held-out pairs** give the same verdicts and the same certificate sets as the
  SOTA-4 record.
- **The SOTA-7 synthetic dry-run classes** are unchanged.

The `regressions` job repeats all of this and also runs `tests.sota5.test_lawrel`.

## E–F. External results
**Not yet run [CI].** The `pilot-rerun` job runs the same 23 cases (same strings and hashes, protocol budget,
sealed and replayed), and `report` writes one row per original case. With no preamble available, the cases
that need `open` lines will still be INPUT_NOT_EVALUABLE, now classified correctly. Certified results so
far: **zero** reported, because none has been run.

## G. Limitations
- The memory accounting is unchanged.
- The source headers must be recovered from the original archive.
- Cases containing `...` or free identifiers stay INVALID_SOURCE.
- Two topology cases are not adaptable.
- The provenance is AI-selected and unverified, and there are no gold labels, so the run is not an
  independent evaluation.

## H. Significance
This is engineering recovery. It is not evidence of mathematical capability until the rerun produces
certified, replayed results, and those are scored against independently adjudicated labels.
