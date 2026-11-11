# Invalid run (kept on purpose)

First full Stage 1 execution, local, 2026-11-11, at commit 73b6339. Invalid for two implementation
faults, both fixed by PROTOCOL.md amendment 1:

1. Comparator configs were matched on the unqualified declaration name, so declarations called `main`
   matched dozens of unrelated configs (cases E304, E431 variants.ostmann, E952, E1150).
2. A maintainer rewrite of `answer(False) ↔ P` into `¬ P` was reported as a changed statement body.

Do not cite numbers from this directory.
