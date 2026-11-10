# Competitor capability matrix (`python -m bench.sota7.competitors`)

| system | structural | closed equiv. | closed non-equiv. | open relation | source fidelity | assumption explanation | repair | certified repair minimality |
|---|---|---|---|---|---|---|---|---|
| ProofScope SOTA-6 | — | kernel | kernel | — | adapter v2 + source-link theorems | kernel (finite fragments) | kernel (declared grammar) | kernel (declared grammar) |
| BEq+ | yes | kernel (bidirectional proof) | — | — | — | — | — | — |
| SemantEq | yes (normalization) | — | — | — | — | — | — | — |
| FormalRx / FormalRx-CC | — | — | Lean-checked witness (CC) | — | LLM diagnosis | — | LLM correction (uncertified) | — |
| BPF (Faithfulness Gap) | — | — | — | — | probe-based statistical | — | — | — |

**Rules:**
- Systems are compared only on capabilities they claim.
- An unsupported capability is "unsupported", never "wrong".
- An installation failure is NOT_INSTALLED, never a mathematical failure.
- Matched tasks use identical manifest budgets.

The SOTA-7 `competitors` job is an availability smoke test only. **No competitor benchmark was run.**
