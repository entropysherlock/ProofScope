# CMCD blind suite — frozen independent evaluation (2026-11-09)

**Author:** ChatGPT (OpenAI), independently from Claude (the CMCD engine developer).
**Engine freeze:** v0.9 block 2 in `../CMCD_FREEZE.txt`, before this suite was written.
**Number of cases:** 28. **Harmless cases:** 10/28.
**Mathematics:** Lean 4.34.1 core; Nat, Int, List Nat and quantifier logic.
**Protocol:** Submitted with SHA-256 hashes in the same commit. No CMCD engine execution on these cases before freezing.
**Status:** Author-assigned labels, not independently human-adjudicated ground truth.
**Evaluation:** One GitHub CMCD run after commit; publish all disagreements, inconclusives, certificate rejections and infrastructure failures. Never silently alter labels. Corrections require a new version.

Labels concern the *shared-operator abstraction*, not ordinary truth of the two concrete statements. Because both source and engine are machine-authored, this suite is developer-independent, not a substitute for external human review. The author inspected the public specification and engine's relation policy to define labels, but did not inspect CMCD predictions for these cases before freezing.

Case IDs, annotations, and rationales are committed to permit post-hoc hostile review. An `expected_localized_at` field records an anticipated edit index for simple single-edit pairs; `null` indicates no verified localization expectation.

**No state-of-the-art or superiority claim follows from this suite.**
