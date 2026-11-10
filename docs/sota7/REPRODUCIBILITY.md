# Reproducing SOTA-7

**Requirements:**
- Lean 4.34.1 with `leanchecker`;
- leanprover-community/repl `193cf4bb9a22bb3fc6d25774f0fe6a70db1fd6ee`, built with 4.34.1, with
  `PROOFSCOPE_REPL` pointing at it;
- Python 3.12.

Mathlib `d13f23b` is needed only for Mathlib cases.

```bash
python -m bench.sota7.make_synthetic --out bench/sota7/synthetic            # regenerates the committed fixtures
python -m bench.sota7.dryrun_freeze manifest.json
mv bench/sota7/synthetic/gold.jsonl /somewhere/withheld/                     # the engine side never has it
python -m bench.sota7.runner  --manifest manifest.json --public bench/sota7/synthetic/public --out run
python -m bench.sota7.replay  --run run --public bench/sota7/synthetic/public --out replay.jsonl
python -m bench.sota7.scoring --manifest manifest.json --public bench/sota7/synthetic/public \
       --gold /somewhere/withheld/gold.jsonl --run run --replay replay.jsonl --out scores.json
python -m bench.sota7.report  --scores scores.json --competitors competitor-status.json --out summary
python -m unittest tests.sota7.test_schema_integrity tests.sota7.test_scoring_adversarial tests.sota7.test_blinding_replay
```

**For an external dataset:**
1. Write public case files and a gold file in the `proofscope-eval/1` format (`bench/sota7/schema.py`).
2. Freeze them with `blind.freeze`.
3. Run the same commands.

No engine change is needed.

**What is deterministic and what is not.** Outcome classes are deterministic: two local runs gave identical
classes, and `expected_classes.json` guards them in CI. The record hash is not, because the records contain
measured CPU, wall time and memory.
