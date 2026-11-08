# Evidence from earlier runs

Each archive below holds the raw outputs of one run from November 8, 2026, unmodified (so internal hashes such as
the V23 manifest stay valid). Build products (`.olean`, `.ilean`, `.c`) were removed from the V0.8 run to keep the
repository small. Archive checksums are in [`SHA256SUMS`](SHA256SUMS); verify with `sha256sum -c SHA256SUMS`.
The section headings name the archive (`<name>.zip`).

The scripts that produced V0.6.1, V0.8 and V0.9-R were one-off Colab cells and are **not** included. The
`proofscope` package in this repository is a clean re-implementation of the V0.9-R method and reproduces its
headline real-definition result (case R1) on core Lean.

## `v02_local_runs.zip`: ProofScope v0.2 local runs (not GitHub Actions)

Sandbox runs with Lean 4.34.1 before v0.2 reached GitHub, kept for comparison with the first CI run:
the openai/math project audit without build (PASS; 208/208 catalog entries mechanically consistent; 374-file
import closure hashed, no text-level hazards) and the fidelity benchmark (12/12; 39 certificates replayed).

## `v23_westfall_hadwiger.zip`: source-based reproduction of the WESTFALL Lean package

- **What:** `verify.py` rebuilds the six `PFRS.*` modules on top of a pinned checkout of
  [openai/math](https://github.com/openai/math), audits axioms on 21 theorem targets, runs an honest/forged
  kernel control and replays the six modules with `leanchecker`.
- **Result:** all mandatory stages passed (`westfall_verify_work/REPORT.md`, full log in `V23_full_execution.log`).
- **Pins:** `MANIFEST.json`, SHA-256 `63d4fe3b419c147b1bf4174bb84487e50b54747ef55247cce269dad7dca427bb`.
- **Naming note:** the manifest and report are titled "V22" because V22 is the version of the pin file and
  harness; V23 is the November 8 run of it. The files were not renamed, so the hash above still matches.
- **Limits:** official Mathlib binary cache; non-fresh replay of the six WESTFALL modules only, with the same
  kernel; not an independent mathematical referee of the manuscript.

## `v08_vacuity_run_20261108_174138.zip`: vacuity, definition and coverage pilot

- **What:** vacuity analysis of top-level hypotheses in 20 comparator challenges (`WestfallVac.lean`
  emits kernel-checked satisfiability or contradiction certificates), a definition audit, and paper-to-Lean
  coverage worksheets for nine papers.
- **Result:** 25 statement outcomes: 5 `NONVACUOUS_PROVEN`, 9 `INCONCLUSIVE_SEARCH_FAILED`,
  11 `NO_TOPLEVEL_HYPOTHESES`; 390 definitions with 86 heuristic flags; 276 paper statements, all
  `NEEDS_HUMAN_REVIEW` (`summary.md`).
- **Limits:** top-level hypotheses only; inconclusive is never a pass; coverage rows are unreviewed.

## `v09r_definition_pilot_run_20261108_185854.zip`: definition-fidelity pilot

- **What:** five flagged definitions from real challenges compared with justified references, plus 7 controls
  and 6 mutants, with certificates replayed by `leanchecker` (`WESTFALL_V09R_REPORT.md`).
- **Result:** three certified equivalent, one certified different only outside the theorem's domain, one
  bounded agreement, one inconclusive; no theorem-relevant discrepancy. 12/13 controls and mutants labelled
  correctly (the miss was a bits-versus-nats entropy mutant); 39 certificates replayed. The corpus-wide
  definition audit in this run found 10,297 definitions across 418 challenges, 2,026 flagged.
- **Limits:** references and domains were AI-curated; controls are self-built and not held out.
