# SOTA-3 development failures: method (SOTA-4 Task H)

SOTA-3 (run 42701174017): CJCS on the 24-pair Mathlib development suite gave 3 certified positive, 5
certified negative, 16 records outside the evaluated classes. Those records are GitHub artifacts
(`sota3-runs-cjcs-<shard>`); this development session could not read them, so **no cause is asserted here**.

`bench/sota4/failures.py` (run by the `summary` job) reads every original record and adds, beside the
untouched original status and `evaluation_class`, a cause:

| cause | rule |
|---|---|
| RESOURCE_CPU_BUDGET | status TIMEOUT_CPU (tier 20 + measured startup allowance exhausted for the whole process tree) |
| RESOURCE_WALL / RESOURCE_MEMORY | TIMEOUT_WALL / OOM |
| ADAPTER_INPUT / ADAPTER_ENVIRONMENT | the statement did not round-trip / the adapter failed outside the declaration |
| ENGINE_LAUNCH / ENGINE_CRASH | launch error / non-zero exit with no engine row |
| EXTRACTION | engine row with `extraction failed` |
| CERTIFICATE_INFRASTRUCTURE | certify INFRASTRUCTURE_ERROR / PREAMBLE_ERROR |
| SEARCH_INCOMPLETE | evaluated ABSTAIN (listed, not a failure) |
| UNCLASSIFIED | anything else, with log tail, for manual review |

and the last pipeline stage that started (extract, stage-1 search, certify probe, certificate compile,
witness readout) from the work directory. The same tool classifies the SOTA-3 and SOTA-4 re-runs under the
unchanged tier-20 policy, so the before/after comparison uses one classification.

Working hypothesis (to be confirmed or refuted by the job, not assumed): most of the 16 are
RESOURCE_CPU_BUDGET; the earlier stage-level diagnosis measured ≈48 CPU-s for CJCS on the negative fixture
with 7 Lean processes, against a 20 s tier plus the startup allowance. Mechanisms visible in the code that
could also produce non-evaluations: F3 (one failed obligation discards every certificate of a pair, which
yields ABSTAIN, not an infrastructure class).
