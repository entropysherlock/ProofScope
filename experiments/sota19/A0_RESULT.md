# SOTA-19 pilot A0: result (run 43006906965, repaired harness)

Run 43001388917 is invalid (see `ABLATION_PROTOCOL.md`, amendment 1). Numbers below are from
43006906965: 399 pairs, 0 pair timeouts, 33 pairs with at least one statement-elaboration timeout
(those theorems are not counted).

| Quantity | Value |
|---|---|
| SOTA-18 wins reproduced by G (apply + ProofScope's portfolio) | **2 of 4** (miniF2F 68, 237); missed 430, 298 |
| ProofScope H1 equivalences also certified by G | **50 of 75 (67 %)**; of the 37 certificate-backed ones, 12 |
| G equivalences | 90, all consistent with the labels (0 wrong) |
| G equivalences no other system (ProofScope, SemantEq, BEq+) certified | 0 |
| ProofScope equivalences no other system and not G certified | 2 (miniF2F 430, 298) |

**Pre-registered reading: H_struct.** G misses 2 of the 4 wins and covers fewer than 75 % of ProofScope's
equivalences, so ProofScope's hypothesis alignment carries real weight over "apply + portfolio": it
handles hypotheses that are split, merged or generalized (298: a conjunction against separate
hypotheses; 430: an additivity hypothesis restricted to positive arguments).

**Size of the effect.** Two pairs out of 477 are certified by ProofScope and by nothing else tested,
including the baseline. The capability is real and narrow.
