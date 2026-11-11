# SOTA-18: competitive evaluation of ProofScope (ProofScope / SemantEq / BEq+)

Research director: Caleb J. Westfall. Executed by Claude (Anthropic), 2026-11-11.
Report: [`docs/sota18_competitive_evaluation.md`](../../docs/sota18_competitive_evaluation.md).

## Order of events (each step is a commit on `research/sota18-independent-evaluation`)

1. `PROTOCOL.md`, `competitors.json`, `ENGINE_HASHES.txt`: pre-registration, before any case was selected
   (amendment 1, before any data was loaded).
2. `make_selection.py` run on GitHub Actions; the runner itself committed `frozen/manifest.json` and
   `frozen/cases.jsonl` (bot commit `745e3e2`, run 42965331884). Its output reproduced the first
   selection run (42965078900) bit for bit (`cases_sha256 a90f00ae…`).
3. Synthetic Track C smoke stage (`trackC_smoke.jsonl`, never pooled): three runs to fix infrastructure
   (BEq+ toolchain default, artifact paths, adapter universe names). It exposed soundness finding F1
   (`SOUNDNESS.md`), recorded as amendment 2 before the headline run.
4. `RUN_FREEZE.txt`: harness hashes; then the headline run (`RUN_STAGE` = `full`).
5. `results/full/run_<id>_<attempt>/`: raw per-pair records committed by the `collect` job.
6. `score.py`: the pre-registered scoring; `summary_H0.json` and `summary_H1.json`.

## Files

| Path | What |
|---|---|
| `PROTOCOL.md` | tasks, semantics, mappings, budgets, metrics, decision gate, amendments |
| `competitors.json` | literature and implementation audit (repos, commits, licenses, task, status) |
| `make_selection.py` | text-only selection of Track A and Track B |
| `frozen/` | `manifest.json` (ids, gold labels, provenance, hashes), `cases.jsonl` (statements) |
| `run_proofscope.py` | Lean-checked adapter (print, round trip) and the two frozen engines |
| `run_semanteq.py`, `run_beqplus.py` | competitor drivers (native toolchains, unmodified methods) |
| `score.py` | pre-registered scoring (`--mode H0` frozen engine, `--mode H1` fail-closed reading) |
| `published_context.json` | SemantEq's published per-pair verdicts restricted to our ProofNetVerif samples (context only) |
| `SOUNDNESS.md`, `soundness/` | finding F1 and its minimal counterexamples |
| `.github/workflows/sota18-select.yml`, `sota18-evaluate.yml` | the two workflows |

## Data licenses

ProofNetVerif (`PAug/ProofNetVerif`, revision `91183e5`) is MIT; EPLA (ASSESS @`bc79335`) is Apache-2.0.
`frozen/cases.jsonl` redistributes their statements with attribution under those licenses.

## Reproduce

    # selection (needs Hugging Face access)
    python experiments/sota18/make_selection.py SEMANTEQ_DIR ASSESS_DIR OUT     # must give cases_sha256 a90f00ae…
    # ProofScope (Lean 4.34.1 on PATH, Mathlib v4.34.1 built, LEAN_PATH from `lake env`)
    PROOFSCOPE_IMPORTS=Mathlib python experiments/sota18/run_proofscope.py experiments/sota18/frozen/cases.jsonl OUT/ps --shard 0/24
    # SemantEq (its own toolchain; `lake exe cache get && lake build semanteq` in its checkout)
    python experiments/sota18/run_semanteq.py SEMANTEQ_DIR experiments/sota18/frozen/cases.jsonl OUT/se --shard 0/12
    # BEq+ (LeanInteract checkout; `elan default leanprover/lean4:v4.8.0`)
    uv run --python 3.11 --with LEANINTERACT_DIR python experiments/sota18/run_beqplus.py LEANINTERACT_DIR experiments/sota18/frozen/cases.jsonl OUT/bq --shard 0/12
    # scoring
    python experiments/sota18/score.py experiments/sota18/results/full/run_<id>_<attempt> --mode H0 --out summary_H0.json

The workflow `SOTA-18 Competitive Evaluation` does all of this on GitHub-hosted runners when
`experiments/sota18/RUN_STAGE` changes on this branch.
