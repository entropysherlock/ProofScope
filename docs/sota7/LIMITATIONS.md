# Limitations (SOTA-7)

* **No independent evaluation has been run.** No external case has been selected or labelled. All 11
  dry-run cases and their labels were written by the engine developer, one of them is a deliberately wrong
  label, and none of them is evidence of accuracy.
* **Blinding against a malicious engine is procedural.** The engine runs as the same OS user as the
  operator. Blinding is enforced by process and job separation, plus canary and environment tests, not by OS
  permissions.
* **Relation verdicts are about closed propositions.** Formulation-level relations come from the gold
  labels. When a closed-only equivalence meets a non-equivalent gold label, the case is reported as
  CLOSED_ONLY_*, never counted as correct.
* **Replay checks proof objects and statement identity against the public strings.** It cannot check that
  those strings formalize the source mathematics; that is the reviewers' job.
* **Narrow repair fragment.** Repair tasks need the hypothesis-form fragment and a declared grammar (SOTA-6).
* **No competitor results.** The competitor job only probes availability.
* **Small denominators.** With n = 9 decisive dry-run cases, "0 errors" means a 95% upper bound of 0.336.
