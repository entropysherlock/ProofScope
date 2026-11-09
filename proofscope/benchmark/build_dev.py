"""Development split of the ProofScope theorem-comparison benchmark (written before the engine was frozen).

Each case: formal statement ∀x, H_L → C_L vs reference ∀x, H_R → C_R. `fidelity_failure` is the ground truth a
reviewer cares about: True when the formal statement does NOT establish the reference claim (a gap or vacuity).
`expected` is the precise engine label. Annotation: Claude (Anthropic), Nov 8 2026, from the definitions alone.
"""
import json
from pathlib import Path

N = [["n", "Nat"]]
NM = [["n", "Nat"], ["m", "Nat"]]
B1 = {"n": 30}
B2 = {"n": 12, "m": 12}
QSWAP_GAP = ("exact ⟨0, trivial, trivial, fun k => ⟨k + 1, Nat.lt_succ_self k⟩, "
             "fun ⟨m, h⟩ => Nat.lt_irrefl m (h m)⟩")

C = [
 # ---- missing hypothesis in the formal statement (formal claims more: covers the reference)
 ("missing_hyp_pred", "missing hypothesis", N, "True", "n - 1 + 1 = n", "0 < n", "n - 1 + 1 = n", B1, "LEAN_STRONGER", False),
 ("missing_hyp_div", "missing hypothesis", NM, "True", "n / m * m ≤ n", "0 < m", "n / m * m ≤ n", B2, "LEAN_STRONGER", False),
 ("missing_hyp_sub", "missing hypothesis", NM, "True", "n - m + m ≥ n", "m ≤ n", "n - m + m ≥ n", B2, "LEAN_STRONGER", False),
 # ---- extra hypothesis: formal theorem misses objects the reference covers
 ("extra_hyp_even", "extra hypothesis", N, "n % 2 = 0", "n ≤ n * n", "True", "n ≤ n * n", B1, "APPLICABILITY_GAP", True),
 ("extra_hyp_pos", "extra hypothesis", NM, "0 < m", "n ≤ n + m", "True", "n ≤ n + m", B2, "APPLICABILITY_GAP", True),
 ("extra_hyp_big", "extra hypothesis", N, "10 ≤ n", "n < 2 ^ n", "True", "n < 2 ^ n", B1, "APPLICABILITY_GAP", True),
 # ---- threshold constant in the hypothesis
 ("threshold_too_high", "incorrect constant", N, "5 ≤ n", "2 * n + 1 ≤ n * n", "3 ≤ n", "2 * n + 1 ≤ n * n", B1, "APPLICABILITY_GAP", True),
 ("threshold_lower_ok", "incorrect constant", N, "3 ≤ n", "2 * n + 1 ≤ n * n", "5 ≤ n", "2 * n + 1 ≤ n * n", B1, "LEAN_STRONGER", False),
 # ---- constant in the conclusion
 ("concl_const_weak", "incorrect constant", N, "1 ≤ n", "n ≤ 2 * n * n", "1 ≤ n", "2 * n ≤ n * n", B1, "CONCLUSION_GAP", True),
 ("concl_bound_weaker", "incorrect constant", N, "True", "n ≤ 3 * n", "True", "n ≤ 2 * n", B1, "EQUIVALENT", False),
 ("concl_bound_wrong", "incorrect constant", N, "True", "n / 2 ≤ n", "True", "n / 2 < n", B1, "CONCLUSION_GAP", True),
 # ---- reversed inequality in the conclusion
 ("reversed_ineq", "reversed inequality", NM, "m ≤ n", "m ≤ n", "m ≤ n", "n ≤ m", B2, "CONCLUSION_GAP", True),
 ("reversed_ineq_strict", "reversed inequality", N, "0 < n", "n - 1 < n", "0 < n", "n < n - 1", B1, "CONCLUSION_GAP", True),
 # ---- quantifier swap
 ("quantifier_swap", "quantifier swap", N, "True", "∀ k : Nat, ∃ m : Nat, k < m", "True", "∃ m : Nat, ∀ k : Nat, k < m", {}, "CONCLUSION_GAP", True),
 # ---- domain restriction
 ("domain_odd_only", "domain restriction", N, "n % 2 = 1", "n % 2 = 1", "True", "n % 2 = 1 ∨ n % 2 = 0", B1, "APPLICABILITY_GAP", True),
 ("domain_bounded", "domain restriction", N, "n < 10", "n < n + 1", "True", "n < n + 1", B1, "APPLICABILITY_GAP", True),
 # ---- empty edge cases
 ("empty_list_excluded", "empty-set edge case", [["l", "List Nat"]], "l ≠ []", "l.length ≥ 0", "True", "l.length ≥ 0", {}, "APPLICABILITY_GAP", True),
 ("empty_list_harmless", "empty-set edge case", [["l", "List Nat"]], "0 < l.length", "l ≠ []", "l ≠ []", "0 < l.length", {}, "EQUIVALENT", False),
 # ---- junk values: division and truncated subtraction
 ("junk_div_hyp", "unintended default value", NM, "n / m = 0", "n < m ∨ m = 0", "0 < m ∧ n / m = 0", "n < m", B2, "LEAN_STRONGER", False),
 ("junk_div_concl", "unintended default value", NM, "True", "n / m ≤ n", "True", "n / m < n + 1", B2, "EQUIVALENT", False),
 ("junk_sub_concl", "unintended default value", NM, "True", "n - m ≤ n", "True", "n - m < n", B2, "CONCLUSION_GAP", True),
 ("trunc_sub_eq_zero", "unintended default value", NM, "n - m = 0", "n ≤ m", "n ≤ m", "n - m = 0", B2, "EQUIVALENT", False),
 # ---- coercion
 ("int_coercion_harmless", "type coercion", NM, "((n : Int) - m) ≥ 0", "m ≤ n", "m ≤ n", "((n : Int) - m) ≥ 0", B2, "EQUIVALENT", False),
 ("nat_vs_int_sub", "type coercion", NM, "True", "n - m ≥ 0", "True", "((n : Int) - m) ≥ 0", B2, "CONCLUSION_GAP", True),
 # ---- vacuous hypotheses
 ("vacuous_range", "vacuous hypotheses", N, "n < 3 ∧ 5 < n", "False", "3 ≤ n", "True", B1, "VACUOUS", True),
 ("vacuous_parity", "vacuous hypotheses", N, "n % 2 = 0 ∧ n % 2 = 1", "False", "True", "True", B1, "VACUOUS", True),
 ("nonvacuous_tight", "vacuous hypotheses", N, "3 ≤ n ∧ n ≤ 3", "n = 3", "n = 3", "3 ≤ n", B1, "EQUIVALENT", False),
 # ---- harmless rewrites (negative controls: suspicious-looking but equivalent)
 ("rewrite_dvd", "harmless rewrite", N, "2 ∣ n", "(n / 2) * 2 = n", "n % 2 = 0", "n / 2 + n / 2 = n", B1, "EQUIVALENT", False),
 ("rewrite_ne_zero", "harmless rewrite", N, "n ≠ 0", "0 < n", "0 < n", "1 ≤ n", B1, "EQUIVALENT", False),
 ("rewrite_not_le", "harmless rewrite", N, "¬ n ≤ 2", "3 ≤ n", "3 ≤ n", "2 < n", B1, "EQUIVALENT", False),
 ("rewrite_ge", "harmless rewrite", NM, "m ≤ n", "n ≥ m", "n ≥ m", "m ≤ n", B2, "EQUIVALENT", False),
 ("rewrite_ceil_div", "harmless rewrite", NM, "0 < m", "(n + m - 1) / m = n / m + (if n % m = 0 then 0 else 1)", "0 < m", "(n + m - 1) / m = n / m + (if n % m = 0 then 0 else 1)", B2, "EQUIVALENT", False),
 # ---- mislinked: two unrelated true statements (known limitation: uniform comparison cannot see this)
 ("mislinked_true_true", "incorrectly linked theorem", N, "True", "n + 0 = n", "True", "n * 1 = n", B1, "EQUIVALENT", True),
]

TACTICS = {"quantifier_swap": {"concl_gap": [QSWAP_GAP]}}
out = Path(__file__).resolve().parent / "dev"
out.mkdir(exist_ok=True)
for (cid, fam, b, hl, cl, hr, cr, bounds, exp, failure) in C:
    d = {"id": cid, "family": fam, "split": "dev", "binders": b, "lean_hyp": hl, "lean_concl": cl,
         "ref_hyp": hr, "ref_concl": cr, "bounds": bounds, "expected": exp, "fidelity_failure": failure,
         "tactics": TACTICS.get(cid, {}), "annotation": "Claude (Anthropic), 2026-11-08, from the definitions"}
    (out / f"{cid}.json").write_text(json.dumps(d, indent=2, ensure_ascii=False))
print(len(C), "dev cases")
