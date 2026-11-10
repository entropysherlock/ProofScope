"""WESTFALL SOTA-13: exact optimization of compatible periodic tables.

This is an experimental Python prototype, NOT a Lean-certified theorem.
The exactness argument is the generalized Chinese remainder theorem.

Given period tables T_i and periods n_i with
    gcd(n_i, n_j) == h
for every i != j, optimize sum_i T_i[x % n_i] by grouping
positions by their residue modulo h. A CRT witness attains the
computed score. Complexity is O(sum_i n_i + k^2 log N) in the
explicit-table model, excluding large-integer arithmetic costs.

No claim of algorithmic or mathematical novelty is made.
"""
from math import gcd, lcm
from random import Random


def crt_merge(r: int, m: int, s: int, n: int) -> tuple[int, int]:
    """Merge compatible congruences x=r mod m and x=s mod n."""
    if m <= 0 or n <= 0:
        raise ValueError("Periods must be positive")
    h = gcd(m, n)
    if (s - r) % h:
        raise ValueError("Incompatible congruences")
    q = n // h
    t = 0 if q == 1 else (((s - r) // h) * pow(m // h, -1, q)) % q
    period = lcm(m, n)
    x = (r + m * t) % period
    assert x % m == r % m and x % n == s % n
    return x, period


def exact_periodic_max(*tables: list[int]) -> tuple[int, int, int]:
    """Return exact (maximum, attaining x, joint period).

    Requires all pairwise GCDs of individual periods to be equal.
    Does NOT assume the tables are mathematically independent.
    """
    if not tables or any(not t for t in tables):
        raise ValueError("At least one nonempty table is required")
    periods = [len(t) for t in tables]
    h = gcd(periods[0], periods[1]) if len(periods) > 1 else periods[0]
    if any(gcd(periods[i], periods[j]) != h
           for i in range(len(periods)) for j in range(i)):
        raise ValueError("Pairwise GCD condition is not satisfied")

    per_class_max = []
    per_class_arg = []
    for table in tables:
        maximum = [None] * h
        witness = [None] * h
        for i, value in enumerate(table):
            r = i % h
            if maximum[r] is None or value > maximum[r]:
                maximum[r] = value
                witness[r] = i
        per_class_max.append(maximum)
        per_class_arg.append(witness)

    winning_class = max(
        range(h),
        key=lambda r: sum(maxima[r] for maxima in per_class_max),
    )
    objective = sum(maxima[winning_class] for maxima in per_class_max)

    x, period = per_class_arg[0][winning_class], periods[0]
    for i in range(1, len(tables)):
        x, period = crt_merge(
            x, period, per_class_arg[i][winning_class], periods[i]
        )
    assert sum(t[x % len(t)] for t in tables) == objective
    return objective, x, period


def brute_max(*tables: list[int]) -> tuple[int, int, int]:
    """Independent, deliberately slow oracle over the full joint period."""
    period = lcm(*(len(t) for t in tables))
    x = max(range(period), key=lambda x: sum(t[x % len(t)] for t in tables))
    return sum(t[x % len(t)] for t in tables), x, period


def selftest(trials: int = 3000, seed: int = 20261110) -> None:
    rng = Random(seed)
    checks = 0
    for _ in range(trials):
        k = rng.choice([2, 3, 4])
        h = rng.randint(1, 6)
        # Equal pairwise GCD by requiring coprime multipliers.
        multipliers = rng.sample([1, 5, 7, 11, 13], k)
        tables = [
            [rng.randint(-50, 50) for _ in range(h * n)]
            for n in multipliers
        ]
        exact = exact_periodic_max(*tables)
        brute = brute_max(*tables)
        assert exact[0] == brute[0], (tables, exact, brute)
        assert sum(t[exact[1] % len(t)] for t in tables) == exact[0]
        checks += 1

    f = [3, -5, 17, 1, 9, -7]
    g = [1, 8, 13, 21, -4, 0, 1, 3, 5, 7]
    value, witness, _ = exact_periodic_max(f, g)
    assert value == 30 and witness == 2

    # Cross-check that the restriction is actually enforced.
    try:
        exact_periodic_max([0] * 6, [0] * 10, [0] * 15)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected unsupported-period error")

    print(f"PASS: {checks} seeded randomized cases vs exhaustive oracle")
    print("PASS: worked example and incompatible-GCD rejection")


if __name__ == "__main__":
    selftest()
