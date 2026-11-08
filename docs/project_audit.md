# Pinned project audit (v0.2)

`python3 -m proofscope.project` audits one exact commit of a public Lean 4 project.

```bash
python3 -m proofscope.project \
  --repo https://github.com/openai/math \
  --commit 4eaee87548250b2682affda7d05d947c05554bae \
  --subdir lean --catalog \
  --modules OAI.Combinatorics.HadwigerCounterexample.Main \
  --output proofscope-project-evidence
```

Add `--build --decls NAME ...` to compile the targets, print their axioms and replay them with `leanchecker`.
`--build` executes the project's own code (Lake configuration, macros, tactics): use it only in a sandbox
without credentials, such as the **ProofScope Project Audit** workflow.

## Stages

| Stage | What is checked | Runs project code? |
|---|---|---|
| S0 | Inputs: `https://github.com/OWNER/REPO`, full 40-hex commit, safe subdirectory, well-formed Lean names | no |
| S1 | Fetch exactly that commit, verify `HEAD`, record the git tree hash | no |
| S2 | `lean-toolchain`, Lake `require`s, `lake-manifest.json` revisions (exact commits or not) | no |
| S3 | Local import closure of every target module; SHA-256 of each file in `SOURCE_MANIFEST.json` | no |
| S4 | Text scan of that closure: `sorry`, `admit`, `axiom`, `native_decide`, `unsafe`, `implemented_by`/`extern`, `debug.skipKernelTC`, debug/trust options | no |
| S5 | `formalization.yaml` main results: file exists, declaration found under its full name, comparator config lists it, permitted axioms standard, challenge module exists, solution module imports the catalog file | no |
| S6 | `lake exe cache get` (if Mathlib), `lake build`, `#print axioms` per declaration, `leanchecker` replay per module | **yes** |

## Labels

| Label | Meaning |
|---|---|
| VERIFIED | Established mechanically in this run; the log is in `logs/`. |
| WARNING | Established, but weakens trust (custom axiom, unpinned dependency, catalog file not imported by its solution module). |
| FAIL | Something that should hold does not (`sorry` in a target, declaration missing, unpinned manifest). |
| INCONCLUSIVE | Could not be completed. Never counted as a pass. |
| HUMAN_REVIEW | Not decidable mechanically. Paper-to-Lean statement fidelity is always in this category. |
| INFO | Context only. |

## Outputs

`REPORT.md`, `report.json`, `SOURCE_MANIFEST.json`, `catalog_audit.json` (when `--catalog`), and one JSON log per
command in `logs/`.

## Known limits

- S3-S5 read text. A hazard produced by a macro or metaprogram can escape them; S6 (`#print axioms`, replay) is the semantic check.
- `leanchecker` is the same kernel implementation as Lean. Replay detects tampered `.olean` files; it is not an independent kernel.
- S6 with Mathlib trusts the official binary cache.
- Large projects (openai/math has 42 dependencies) may exceed a hosted runner's disk or time limit with `--build`. That is reported as FAIL or INCONCLUSIVE, never as success.
