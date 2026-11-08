# Challenge statements used by the static-scan demo

`CliqueFreeLog.lean`, `CourtadeKumar.lean` and `DepthFive.lean` are copied unmodified (apart from a three-line
attribution header) from the OpenAI comparator corpus, [openai/math](https://github.com/openai/math) at commit
`4eaee87548250b2682affda7d05d947c05554bae`, (c) OpenAI, licensed under the Apache License 2.0.
They import Mathlib and contain `sorry` by design: comparator challenges state theorems, they do not prove them.
ProofScope only scans them as text; it does not compile them.
