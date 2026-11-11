# Architecture

```
scopeledger/         Python package (no runtime dependencies)
  schema.py          record types, vocabularies, fail-closed validation
  records.py         append-only store: one JSON file per record under ledger/
  provenance.py      hashing and git source references
  certificate.py     derived status of statements and claims
  cli.py             scope-check
ledger/              the public records (claims, statements, evidence, relations, reviews)
experiments/SL-001/  frozen protocol, cases, auditor, kernel checker, smoke tests, results
.github/workflows/   tests.yml (unit tests), sl001-audit.yml (smoke, Stage 1, build probe)
```

Design choices: Git is the database and the history; no server. Validation happens at write time and
again in CI over the whole ledger. The kernel checker shells out to `lean` and `leanchecker` and treats
anything other than a clean, replayed, axiom-bounded proof of the *expected proposition* as a
non-certified outcome with a specific name. Existing tools (Comparator, SemantEq, BEq+, Palomar) are to
be called, not reimplemented; adapters are future work and none exists yet.

Lessons carried over from ProofScope: verdicts were once emitted for statements that never elaborated
(SOTA-18 finding F1), and one experiment run had to be invalidated for a harness fault (SOTA-19 pilot
A0, first run). Hence: every outcome names whether its input elaborated; exit codes and error lines
reject a file before any axiom report is read; result collection never depends on a shell pipeline that
can fail silently; invalid runs are kept and marked.
