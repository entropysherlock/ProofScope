# External datasets (screen of 2026-11-09; contents not downloaded or inspected here)

The network allowlist in this sandbox blocks Hugging Face and project sites. Availability and licences
below are taken from the papers and pages found by search. They are not verified by download.

| resource | what it contains (as published) | licence (as stated) | suitable for | risks |
|---|---|---|---|---|
| ProofNetVerif (Poiroux, Weiss, Kunčak, Bosselut, EMNLP 2025; HF `PAug/ProofNetVerif`) | 3,752 NL / reference Lean / predicted Lean triples with binary equivalence labels; 1,142 equivalent | MIT | Track A/B binary relation; source for missing-hypothesis and domain cases | binary labels only; its authors also built BEq+ (a competitor); a Lean-version port may be needed |
| ProofNet-Verified ("Ground False", ICML 2026, `github.com/marcusm117/ProofNet-Verified`) | ProofNet audited: 104 of 367 formalizations false, 100 more unfaithful; corrected set | not verified | real misformalizations with provability and strength analysis | LLM judge in its pipeline; check licence |
| RLM25 (same EMNLP 2025 paper) | 619 research-level NL/Lean pairs from six formalization projects | Apache 2.0 | difficult Mathlib-dependent cases | equivalence labels must be added by reviewers |
| DriftBench (Mohammad & Sheikh, "The Faithfulness Gap", arXiv 2606.16541, MusIML @ ICML 2026) | 2,183 NL/Lean 4 pairs over six Mathlib subfields; drift labels for quantifier inversion, hypothesis omission and two further categories; gold formalizations; two experts, κ = 0.81 | not verified (pmlrbd.github.io/BPF) | hypothesis omission and quantifier drift; repairs (gold formalization) | licence and availability unverified; workshop paper |
| Mathlib | real theorem statements and restatements | Apache 2.0 | equivalence pairs (e.g. `_iff` vs `_of` forms), repairs from history | heavy contamination risk for any LLM-built tool |

**Contamination.**
- ProofScope's development used only author-written fixtures, which are listed in `PILOT_PROTOCOL_v1`'s
  exclusions.
- The engines were never run on any external dataset.
- The language models that helped write ProofScope may have seen public datasets during training. Cases
  should therefore be drawn from items published after the model's knowledge cutoff, or from reviewer-made
  variants, where possible.
