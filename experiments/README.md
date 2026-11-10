# SHARPEN research experiments (SOTA-11 through SOTA-13)

This branch is isolated from the verified ProofScope core. It is a research archive and **not** a production integration or state-of-the-art claim.

## What is checked in

- `sota11/REPORT.md`: Claude's reported results, limitations and reproduction instructions for SHARPEN.
- `sota11/lean/ResidueGap.lean`: supplied general residue-gap Lean source.
- `sota12/REPORT.md`: Claude's reported fiber lemma, reduction engine and tests.
- `sota12/lean/Fiber.lean`: supplied Lean source for fiber bounds, attainment and Westfall reduction.
- `sota13/periodic_opt.py`: an explicit-table, pure-Python prototype for exact multi-period optimization under the equal-pairwise-GCD condition. Includes an exhaustive-oracle comparison self-test.

## IMPORTANT: incomplete source import

The conversation also contains `ProofScope_SOTA11_sharpen.zip` and `ProofScope_SOTA12_fiber.zip`, which hold the full Python engines, generated Lean cases, and test outputs. **Those ZIP contents are NOT yet committed on this branch.** The reports refer to artifacts not present here. Do not claim their reported 542/542, 772 theorems, or other validation counts are reproducible from this branch alone.

The two standalone Lean files were transferred as supplied. Their original author's recorded checker results are documented in the reports; no fresh Lean build has been run through this GitHub patch. The SOTA-13 prototype is **not Lean-verified** and has not been benchmarked against other systems.

## Running what is present

- `lean experiments/sota11/lean/ResidueGap.lean`
- `lean experiments/sota12/lean/Fiber.lean`
- `python3 experiments/sota13/periodic_opt.py`

The Lean sources were developed with Lean 4.34.1 (core, without Mathlib), per the supplied reports.

## Mathematical scope of SOTA-13

For functions represented by complete period tables of lengths `n_i`, if all pairwise GCDs equal `h`, the maximum of their sum is the maximum across residue classes modulo `h` of the sum of their per-class maxima. CRT yields an attaining integer.

This uses classical mathematics. It does not solve arbitrary modular optimization, does not handle arbitrary periods with incompatible GCD structure, and does not prove a new theorem in Lean.

## Next work needed

1. Import the complete SOTA-11 and SOTA-12 source ZIP contents preserving provenance.
2. Re-run the exact Lean and Python checks and capture CI artifacts.
3. Implement Lean certificates for SOTA-13, including attainment.
4. Explore optimization with arbitrary pairwise-GCD matrices and multiple coupled terms.
5. Review any novelty claims only after concrete results are verified.
