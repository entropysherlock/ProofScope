"""Held-out split: written after the engine was frozen (compare.py, certify.py, bench.py hashes recorded in
benchmark/ENGINE_FREEZE.txt) and run once. Annotation: Claude (Anthropic), 2026-11-08, from the definitions.
The same author wrote the engine, so this is held out from tuning, not independent of the author."""
import json
from pathlib import Path

N = [["n", "Nat"]]
NM = [["n", "Nat"], ["m", "Nat"]]
L = [["l", "List Nat"]]
I = [["z", "Int"]]
B1, B2 = {"n": 40}, {"n": 15, "m": 15}
C = [
 ("h_square_mono_gap", "extra hypothesis", NM, "m ≤ n ∧ 1 ≤ m", "m * m ≤ n * n", "m ≤ n", "m * m ≤ n * n", B2, "APPLICABILITY_GAP", True),
 ("h_mod3_equiv", "harmless rewrite", N, "n % 3 = 0", "3 ∣ n", "3 ∣ n", "n % 3 = 0", B1, "EQUIVALENT", False),
 ("h_mod_bound_wrong", "incorrect constant", NM, "0 < m", "n % m ≤ m", "0 < m", "n % m < m - 1", B2, "CONCLUSION_GAP", True),
 ("h_mod_bound_weaker_ok", "incorrect constant", NM, "0 < m", "n % m < m", "0 < m", "n % m ≤ m", B2, "EQUIVALENT", False),
 ("h_pow_threshold", "incorrect constant", N, "5 ≤ n", "n * n < 2 ^ n", "4 ≤ n", "n * n ≤ 2 ^ n", B1, "APPLICABILITY_GAP", True),
 ("h_missing_pos_mod", "missing hypothesis", NM, "True", "n % m ≤ n", "0 < m", "n % m ≤ n", B2, "LEAN_STRONGER", False),
 ("h_reversed_div", "reversed inequality", NM, "0 < m", "n / m ≤ n", "0 < m", "n ≤ n / m", B2, "CONCLUSION_GAP", True),
 ("h_vacuous_mod", "vacuous hypotheses", N, "n % 4 = 1 ∧ n % 2 = 0", "False", "True", "True", B1, "VACUOUS", True),
 ("h_vacuous_lt", "vacuous hypotheses", NM, "n < m ∧ m < n", "n = m", "n ≤ m", "n ≤ m", B2, "VACUOUS", True),
 ("h_nonvac_two", "vacuous hypotheses", NM, "n < m ∧ m < n + 2", "m = n + 1", "m = n + 1", "n < m ∧ m < n + 2", B2, "EQUIVALENT", False),
 ("h_domain_small", "domain restriction", N, "n ≤ 20", "n % 2 < 2", "True", "n % 2 < 2", B1, "APPLICABILITY_GAP", True),
 ("h_sub_trunc_gap", "unintended default value", NM, "True", "n - m + m = max n m", "True", "n - m + m = n", B2, "CONCLUSION_GAP", True),
 ("h_sub_trunc_ok", "unintended default value", NM, "m ≤ n", "n - m + m = n", "m ≤ n", "n = n - m + m", B2, "EQUIVALENT", False),
 ("h_div_zero_junk", "unintended default value", NM, "True", "n / m * m + n % m = n", "0 < m", "n / m * m + n % m = n", B2, "LEAN_STRONGER", False),
 ("h_list_append_len", "harmless rewrite", [["l", "List Nat"], ["k", "List Nat"]], "True", "(l ++ k).length = l.length + k.length", "True", "(l ++ k).length = k.length + l.length", {}, "EQUIVALENT", False),
 ("h_list_nonempty_gap", "empty-set edge case", L, "l ≠ []", "l.length ≥ 1", "True", "l.length ≥ 1", {}, "APPLICABILITY_GAP", True),
 ("h_int_abs_gap", "type coercion", I, "0 ≤ z", "z.natAbs = z.toNat", "True", "z.natAbs = z.toNat", {}, "APPLICABILITY_GAP", True),
 ("h_int_sq_equiv", "harmless rewrite", I, "True", "0 ≤ z * z", "True", "z * z ≥ 0", {}, "EQUIVALENT", False),
 ("h_quant_exists_weak", "quantifier swap", N, "0 < n", "∃ k, k < n", "0 < n", "∀ k, k < n", B1, "CONCLUSION_GAP", True),
 ("h_mislinked2", "incorrectly linked theorem", N, "True", "n * 0 = 0", "True", "0 + n = n", B1, "EQUIVALENT", True),
]
out = Path(__file__).resolve().parent / "dev_v05_heldout"
out.mkdir(exist_ok=True)
for (cid, fam, b, hl, cl, hr, cr, bounds, exp, failure) in C:
    (out / f"{cid}.json").write_text(json.dumps({"id": cid, "family": fam, "split": "dev_v05_heldout", "binders": b,
        "lean_hyp": hl, "lean_concl": cl, "ref_hyp": hr, "ref_concl": cr, "bounds": bounds, "expected": exp,
        "fidelity_failure": failure, "tactics": {}, "annotation": "Claude (Anthropic), 2026-11-08, after engine freeze",
        "note": "v0.5 held-out set; used to diagnose and fix two misses in v0.6, so it is no longer held out"},
        indent=2, ensure_ascii=False))
print(len(C), "held-out cases")
