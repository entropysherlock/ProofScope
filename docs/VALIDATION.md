# Validation and independent replay

## What has been validated

| Item | By whom | How |
|---|---|---|
| Unit tests | the project's own CI | `pytest -q` |
| Smoke tests 1–4 | the project's own CI | Lean 4.34.1 kernel plus `leanchecker` on synthetic statements |
| SL-001 Stage 1 | the project's own CI | deterministic script over pinned commits |
| Anything at all | an independent party | **not yet** |

No result in this repository is independent verification. Everything was produced by one AI-assisted
pipeline directed by one person.

## Replaying Stage 1 yourself

```sh
git clone --filter=blob:none --no-checkout https://github.com/google-deepmind/formal-conjectures fc
git clone --filter=blob:none --no-checkout --depth 1 https://github.com/openai/math oai
cd oai
git sparse-checkout set --no-cone '/lean/OAI/**' '/lean/ComparatorChallenges/**'
git fetch --filter=blob:none --depth 1 origin 4eaee87548250b2682affda7d05d947c05554bae adc7f1241b42e322a6451854ab7e4b4c146bf78a
git checkout 4eaee87548250b2682affda7d05d947c05554bae
cd ..
python experiments/SL-001/sl001.py verify-freeze --fc fc
python experiments/SL-001/sl001.py stage1 --fc fc --oai oai --out my-stage1
diff -r my-stage1 experiments/SL-001/results/stage1
```

The output is byte-for-byte deterministic given the pinned commits. A difference is a finding; please
open an issue.

## Replaying a certificate

A certificate names its toolchain, dependencies, artifact hash and proposition hash. To replay: install
the named Lean release, fetch the artifact at the recorded commit, confirm the hashes, run
`experiments/SL-001/kernel_check.py <file> <theorem> "<proposition>"`, and compare the axiom list.
If you are not an author of the original record, add an `evidence` record at level `reproduced`.
No certificate about a real mathematical statement exists in the ledger yet.
