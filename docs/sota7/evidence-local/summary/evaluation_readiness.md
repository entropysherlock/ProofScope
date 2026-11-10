# SOTA-7 evaluation readiness

* Independent evaluation: **NOT RUN**
* Dry run: 11 synthetic development cases (labels written by the engine developer; not evidence of accuracy)
* Outcome classes: {'ABSTAIN': 2, 'CLOSED_ONLY_AGREEMENT': 1, 'CORRECT': 7, 'REPAIR_MISMATCH': 1}
* Decisive scored: 9, decisive errors: 0, 95% CI [0.0, 0.3363]
* Median / p95 / max CPU (s): 3.424 / 7.29 / 7.29
* Competitors: {'BEq+ (LeanInteract, Poiroux et al., EMNLP 2025)': 'NOT_INSTALLED', 'SemantEq': 'NOT_INSTALLED', 'ProofScope SOTA-6 (cjcs4 + repair)': 'AVAILABLE', 'FormalRx / FormalRx-CC (ICML 2026)': 'NOT_INTEGRATED', 'BPF (Faithfulness Gap, 2026)': 'NOT_INTEGRATED'} — NOT RUN (no independent dataset; smoke = availability probe only)

| case | task | claim | class | gold | replay | CPU s |
|---|---|---|---|---|---|---|
| c176c64a4a4e8 | repair | MINIMAL_REPAIR | CORRECT | REF_STRONGER | VERIFIED | 1.26 |
| c48da5ded8888 | relation | NOT_EQUIVALENT_CLOSED | CORRECT | REF_STRONGER | VERIFIED | 3.852 |
| c587fc98b63fd | relation | NOT_EQUIVALENT_CLOSED | CORRECT | CAND_STRONGER | VERIFIED | 3.822 |
| c875b3ed67722 | relation | ABSTAIN | ABSTAIN | UNRESOLVED | NO_DECISIVE_DECLARATION | 7.29 |
| c8e2aaf84b7f1 | relation | ABSTAIN | ABSTAIN | REF_STRONGER | NO_DECISIVE_DECLARATION | 6.561 |
| c9afeab885ade | repair | MINIMAL_REPAIR | CORRECT | REF_STRONGER | VERIFIED | 1.765 |
| ca8a9fea02948 | repair | MINIMAL_REPAIR | REPAIR_MISMATCH | REF_STRONGER | VERIFIED | 1.878 |
| cc7d81b9ebf12 | relation | EQUIVALENT_CLOSED | CORRECT | EQUIVALENT | VERIFIED | 3.424 |
| ce750c58a39bc | repair | MINIMAL_REPAIR | CORRECT | REF_STRONGER | VERIFIED | 1.553 |
| ceb669082a910 | repair | NO_REPAIR_IN_GRAMMAR | CORRECT | REF_STRONGER | VERIFIED | 1.057 |
| cf23978a86a65 | relation | EQUIVALENT_CLOSED | CLOSED_ONLY_AGREEMENT | NOT_EQUIVALENT | VERIFIED | 3.751 |
