# Relationship to ProofScope

ScopeLedger grew out of [ProofScope](https://github.com/entropysherlock/ProofScope), Caleb J.
Westfall's earlier project on auditing what formal proofs establish.

**What ProofScope achieved.** A kernel-as-final-authority design; certificate-backed verdicts; frozen,
pre-registered evaluations run in public CI; a real, narrow capability (kernel proofs that a changed
hypothesis is redundant) that two established checkers missed on a handful of pairs.

**What its own evaluation found (SOTA-18, 2026-11-11, decision: PIVOT).** On 477 real statement pairs
SemantEq and BEq+ certified more equivalences than ProofScope and were significantly better in paired
comparison. ProofScope's distinguishing "certified difference" verdict fired 3 times, matched the label
once, and produced no concrete counterexample. The frozen engine had a soundness defect (47 uncertified
"no difference" outputs on statements it never elaborated, 17 of them wrong). 40% of pairs failed inside
the engines on universe-polymorphic statements. The full report is on the branch
`research/sota18-independent-evaluation` of the ProofScope repository; SOTA-19 on
`research/sota19-strategic-pivot`.

**What ScopeLedger keeps and drops.** It keeps the evidence discipline and the CI practice. It drops the
equivalence engine: comparison is delegated to existing tools. No ProofScope benchmark number is a
ScopeLedger result.

**Funding status, stated exactly.** A seed-grant application to the Renaissance Philanthropy AI for
Math Fund was submitted for ProofScope. It has not been approved, and it has not been updated to
describe ScopeLedger. ScopeLedger is a possible evolution of that research, not an approved replacement.
An application for Anthropic API credits is pending; none have been awarded. The project runs on free
infrastructure.
