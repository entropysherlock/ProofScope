"""Hand triage of the 31 certified FormalMATH findings that have no entry in the ICML 2026 audit's released per-item
results and were not among the first 8 hand-checked findings (see TRIAGE.md).

Each finding is already certified in Lean (the negation, or vacuity, of the unchanged benchmark statement is
kernel-checked). This file records WHY each statement is false and checks the witness with exact arithmetic, independently
of Lean, wherever the reason is arithmetic. Reasons that rest on Lean elaboration (operator precedence, autoImplicit,
the meaning of % on a field) are stated with the elaborated goal that the hunt recorded in findings.jsonl.

Run: python3 triage_31.py  ->  writes triage_31.json and prints a summary.
"""
import json, math
from fractions import Fraction as Q
from pathlib import Path

D = Path(__file__).parent

# Categories, most significant first.
INFORMAL = "Source problem or stated answer is wrong"
TYPO = "Typo in the statement"
FORMAL = "Incorrect formalization (meaning changed)"
AUTOIMP = "Undeclared identifier became a variable (autoImplicit)"
SCOPE = "Binder / precedence scope error"
EDGE = "Domain edge case not excluded (n = 0)"
LEAN = "Lean-semantics artifact (missing side condition or wrong type)"


def totient(n):
    return sum(1 for k in range(1, n + 1) if math.gcd(k, n) == 1)


def is_prime_power(m):
    if m < 2:
        return False
    p = next(d for d in range(2, m + 1) if m % d == 0)
    while m % p == 0:
        m //= p
    return m == 1


def T():
    out = {}

    def add(i, cat, ok, why):
        out[i] = {"category": cat, "witness_check": ok, "reason": why}

    # --- Source problem or stated answer wrong ---------------------------------------------------------------------
    n = 1
    lhs = sum(Q(2 * j + 1, j * j) for j in range(1, n + 1))
    rhs = n * ((n + 1) ** Q(2, n) - 1)
    add("theorem_proving_zh_blue_1183", INFORMAL, lhs == rhs == 3,
        "The problem asks for a strict inequality, but at n = 1 both sides equal 3. The reference solution's AM-GM "
        "argument proves only ≥ (equality when n = 1). Separately, the Lean exponent 2 / n is natural-number division, "
        "so for n ≥ 3 the right side is 0.")
    N = next(N for N in range(1, 200) if not any(is_prime_power(N + j) for j in (1, 2)))
    add("olymid-ref-base_9798", INFORMAL, N == 13,
        "The stated answer n ∈ {1, 3, 6} is wrong: the reference solution shows a suitable N exists for every n "
        "(N = (n+1)!² + 1). For n = 2, N = 13 already works: 14 and 15 are not prime powers. The Lean statement also has "
        "the → / ↔ scope error, which gives the n = 0 certificate.")

    # --- Typo ------------------------------------------------------------------------------------------------------
    a = b = c = Q(1)
    typo = 1 / (1 + 1 / (a + b)) + 1 / (1 + b + c) + 1 / (1 + c + a)
    right = 1 / (1 + a + b) + 1 / (1 + b + c) + 1 / (1 + c + a)
    add("theorem_proving_zh_blue_1269", TYPO, typo == Q(4, 3) and right == 1,
        "Part (2)'s first term is written 1/(1 + 1/(a+b)) in both the informal and Lean statements; the reference "
        "solution bounds 1/(1 + a + b). At a = b = c = 1 the typed version gives 4/3 > 1; the intended one gives 1.")

    # --- Incorrect formalization -----------------------------------------------------------------------------------
    n = 1
    proper = [d for d in range(1, n) if n % d == 0]
    all_div = [d for d in range(1, n + 1) if n % d == 0]
    add("olymid-ref-base_506", FORMAL,
        sum(proper) + len(all_div) == n and sum(proper) + len(proper) != n,
        "'The number of these divisors' means the divisors other than n, but Lean counts n.divisors.card (n included). "
        "n = 1 then satisfies the hypothesis (0 + 1 = 1) but is not 2m². Under the informal reading n = 1 fails it.")
    add("olymid-ref-base_9952", FORMAL,
        not any(y % 1 != 0 for y in range(2, 1000)),  # no y with ¬ 1 ∣ y, so the set is empty
        "p(x) is defined as the least prime y with ¬ x ∣ y; the problem says the least prime NOT DIVIDING x (¬ y ∣ x). "
        "For x = 1 the Lean set is empty (1 divides everything), so sInf gives p 1 = 0, contradicting hp1 : p 1 = 2. "
        "The hypotheses are inconsistent (VACUOUS).")
    add("aime_all_2007_II_4", FORMAL, Q(300, 100) != Q(240, 120),
        "Production is modelled as separate per-product rates, so h1 forces a = 3 and h2 forces a = 2: the hypotheses "
        "contradict each other (VACUOUS). The problem shares worker-hours between widgets and whoosits in one equation.")
    add("omni_theorem_4254", FORMAL, True,
        "n is not bound inside the set; it became a theorem-level variable. At n = 0 both sums are empty, every C "
        "qualifies, and the set has no least element. (The C binder is also unused.)")
    add("omni_theorem_4152", FORMAL, True,
        "'Largest k such that the property holds' is encoded as 'the property holds ↔ k = 1'. The property is downward "
        "closed, so k = 0 holds trivially (the empty index set) while 0 ≠ 1. Needs IsGreatest.")
    add("olymid-ref-base_6296", FORMAL, True,
        "Irrationality is encoded as ¬ ∃ x : ℚ, x = ∏' k, …, with the product itself computed in ℚ. "
        "'∃ x, x = t' is true for every t, so the statement is false regardless of the product. Needs the product in ℝ "
        "and ∃ q : ℚ, (q : ℝ) = ….")
    for i in ("theorem_proving_zh_blue_679", "theorem_proving_zh_blue_81"):
        add(i, FORMAL, True,
            "The problem asks for which n a 5-way equal-sum partition exists (answer: n = 5k or 5k − 1, k ≥ 2), but the "
            "Lean statement has no answer at all: it asserts every n works. False at n = 0, and also at n = 1 "
            "(sets summing to 1, 0, 0, 0, 0).")

    # --- autoImplicit ------------------------------------------------------------------------------------------------
    for i in ("olymid-ref-base_3668", "quantitative_reasoning_zh_blue_52"):
        add(i, AUTOIMP, True,
            "The file opens Real but not Complex, so `I` is not the imaginary unit: autoImplicit made it a universally "
            "quantified real variable (the recorded goal shows a bare `I`). With I = 0 the statement fails. The "
            "mathematical answer is correct.")
    L = Q(1, 4036081)
    add("olymid-ref-base_3668", AUTOIMP, 1 + L == Q(4036082, 4036081) and 2009 ** 2 == 4036081,
        out["olymid-ref-base_3668"]["reason"] + " (Check: with the true I the value is 1 + e^(−2 ln 2009) = 4036082/4036081.)")

    # --- Binder / precedence scope -------------------------------------------------------------------------------------
    arrow = ("'∀ n, cond → P n ↔ answer' parses as '(cond → P n) ↔ answer'. At n = 0 the left side is vacuously "
             "true and the answer is false.")
    for i in ("olymid-ref-base_10079", "olymid-ref-base_9813", "olymid-ref-base_2420"):
        add(i, SCOPE, True, arrow)
    swallow = ("The ∃ / ∀ binder extends to the end, swallowing the ↔: the statement reads 'cond ∧ ∃ x, (P x ↔ answer)'. "
               "At 0 the leading 'n > 0' (or 'k > 0') conjunct is false, so the whole statement is false.")
    for i in ("olymid-ref-base_10792", "olymid-ref-base_5988", "omni_theorem_1576", "omni_theorem_4220",
              "omni_theorem_3647"):
        add(i, SCOPE, True, swallow)

    # --- Edge case ----------------------------------------------------------------------------------------------------
    add("olymid-ref-base_2929", EDGE, 0 == (0 * 0 * (0 - 1)) // 4,
        "Nothing excludes n = 0: the double sum is empty (0), the right side is 0, but n + 1 = 1 is not prime. "
        "The informal problem says 'integers n' and has the same gap; the intended domain is n ≥ 1.")
    add("quantitative_reasoning_zh_blue_379", EDGE, True,
        "At n = 0, Fin 0 → ℤ is the empty family: all conditions hold vacuously (0 = 0 · y²), so the right side is true "
        "while the left side (n > 0 ∧ …) is false.")

    # --- Lean-semantics artifacts ---------------------------------------------------------------------------------------
    real_mod = ("`%` here is taken in ℝ, where Mathlib's field Euclidean-domain structure gives a % b = a − a·b/b = 0 "
                "for b ≠ 0. So the left side is 0. The informal answer is correct; the intended operation is the "
                "fractional part / integer remainder.")
    add("aime_all_1995_2", LEAN, (1995 ** 2) % 1000 == 25, real_mod + " (Check: product of roots is 1995² = 3980025.)")
    add("omni_theorem_1467", LEAN, (Q(101, 202) % 1) == Q(1, 2), real_mod + " With k = 1, n = 101 the true fractional "
        "part gives exactly 1/2.")
    s = sum(math.comb(a, b) % 3 for a in range(81) for b in range(81))
    add("omni_theorem_745", LEAN, s == 1816, real_mod + f" (Check: the integer residues sum to {s}, so 1816/6561 is right.)")
    add("omni_theorem_372", LEAN, 9 - 16 + 9 == 2 and max(9 - 16, 0) + 9 == 9,
        "v − e + f is computed in ℕ, where 9 − 16 truncates to 0, giving 9 ≠ 2. Over ℤ both parts hold.")
    add("u-math_404", LEAN, 7 * 7 - 11 * 7 + 28 == 0 and max(49 - 77, 0) + 28 == 28,
        "x defaults to ℕ, so 49 − 77 truncates to 0 and x = 7 gives 28 ≠ 0. Over ℤ (or ℝ), x = 7 is a common root.")
    add("olymid-ref-base_3256", LEAN, (3 * 4 + 5) // 8 == 2 == totient(1) + totient(2) and Q(17, 8) != 2,
        "(3n² + 5)/8 is natural-number division: at n = 2 it truncates 17/8 to 2, which equals φ(1) + φ(2). "
        "The informal answer is correct.")
    for i in ("olymid-ref-base_7209", "omni_theorem_919"):
        add(i, LEAN, True,
            "a = b = c = 1 is allowed, and Lean's logb 1 1 = 0/0 = 0, so the hypothesis holds and the sum of cubes is 0. "
            "The problem implicitly needs bases ≠ 1. (These two rows are duplicates of the same problem.)")
    return out


if __name__ == "__main__":
    import collections
    ov = json.loads((D / "icml2026_overlap.json").read_text())
    done = {"olymid-ref-base_1859", "olymid-ref-base_918", "olymid-ref-base_10553", "theorem_proving_zh_blue_1350",
            "olymid-ref-base_2124", "theorem_proving_zh_blue_988", "theorem_proving_zh_blue_1245", "omni_theorem_3461"}
    wanted = {k for k, v in ov.items() if v["icml"] == "ICML_NOTHING"} - done
    res = T()
    assert set(res) == wanted, (sorted(wanted - set(res)), sorted(set(res) - wanted))
    bad = [k for k, v in res.items() if not v["witness_check"]]
    assert not bad, bad
    (D / "triage_31.json").write_text(json.dumps(dict(sorted(res.items())), indent=1, ensure_ascii=False) + "\n")
    print(len(res), "findings; all witness checks pass")
    for c, n in collections.Counter(v["category"] for v in res.values()).most_common():
        print(f"{n:3d}  {c}")
