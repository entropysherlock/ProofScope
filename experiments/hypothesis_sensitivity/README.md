# Exact hypothesis sensitivity (finite graph pilot)

This research pilot exhaustively enumerates all 64 simple graphs on four labeled vertices. It checks which subsets of five candidate hypotheses guarantee the conclusion **triangle-free** and produces non-vacuity witnesses and counterexamples when individual hypotheses are removed.

The four inclusion-minimal sufficient sets are:
- `{bipartite}`
- `{forest}`
- `{connected, few_edges}`
- `{connected, max_degree_two}`

The generator verifies every output row and certificate against its graph representation. It is a **Python finite-model check**, not a Lean kernel proof. The graph-theoretic facts are elementary and not claimed as novel.

Run with `python3 experiments/hypothesis_sensitivity/hypothesis_pilot.py --output hypothesis-evidence` or use the separate GitHub Actions workflow **ProofScope Hypothesis Sensitivity Pilot**.

The research question motivated by this pilot is whether human-relevant theorem hypotheses can be systematically relaxed, and whether counterexample certificates can reveal multiple incomparable sufficient assumption sets on nontrivial Lean developments. Existing proof-generalization research (Gandhi, Tadipatri, Gowers, ITP 2025) must be considered in any novelty claim.
