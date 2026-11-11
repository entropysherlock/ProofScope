"""SOTA-17: multi-occurrence comparison (`proofscope.multiocc`, `lean/ProofScope/MultiOcc.lean`).

Needs Lean on PATH (skipped otherwise). Z3 is needed for class detection and for witnesses; without it
the engine abstains, which the tests that require a decision treat as a skip.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from proofscope import multiocc
from proofscope.scopeelim import lib_toolchain
from proofscope.toolchain import Toolchain

HAVE = shutil.which("lean") is not None and multiocc.z3 is not None


@unittest.skipUnless(HAVE, "needs lean and z3")
class MultiOcc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="ps17_"))
        base = Toolchain.find()
        b = multiocc.build_lib(base, cls.tmp / "lib")
        assert b["ok"], b
        cls.tc = lib_toolchain(base, cls.tmp / "lib")
        cls.n = 0

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_case(self, ref, frm, rguard="True", fguard="True"):
        type(self).n += 1
        spec = {"id": f"t{self.n}", "kind": "multi", "reference": {"guard": rguard, "body": ref},
                "formal": {"guard": fguard, "body": frm}}
        return multiocc.compare(spec, self.tc, self.tmp / f"w{self.n}")

    def fwd(self, *a, **k):
        return self.run_case(*a, **k)["directions"]["fwd"]

    # --- the library itself -----------------------------------------------------------------------
    def test_library_axioms(self):
        src = multiocc.SRC / "ProofScope" / "MultiOcc.lean"
        r = self.tc.run([self.tc.lean, str(src)], cwd=multiocc.SRC)
        self.assertEqual(r.returncode, 0, r.output[-2000:])
        self.assertNotIn("sorryAx", r.output)
        self.assertIn("'ProofScope.MultiOcc.step_elim' depends on axioms: [propext, Classical.choice, Quot.sound]", r.output)
        self.assertIn("'ProofScope.MultiOcc.two_point_exact' does not depend on any axioms", r.output)

    # --- step class ----------------------------------------------------------------------------------
    def test_step_entails_three_sites(self):
        self.assertEqual(self.fwd("f n + 1 ≤ f (n + 1) ∧ f (n + 1) ≤ f n + 2",
                                  "f (n + 3) ≤ f n + 5 ∨ f (n + 2) = f n + 4"), "ENTAILS")

    def test_step_separated_three_sites(self):
        # with increments in [1, 3] the same disjunction fails
        self.assertEqual(self.fwd("f n + 1 ≤ f (n + 1) ∧ f (n + 1) ≤ f n + 3",
                                  "f (n + 3) ≤ f n + 5 ∨ f (n + 2) = f n + 4"), "SEPARATED")

    def test_exact_increment_is_affine(self):
        self.assertEqual(self.fwd("f (n + 1) = f n + 2", "f (2 * n) + f 0 = 2 * f n ∧ f (n + 5) = f n + 10"), "ENTAILS")
        self.assertEqual(self.fwd("f (n + 1) = f n + 2", "f (2 * n) = 2 * f n"), "SEPARATED")

    def test_two_way_between_step_claims(self):
        row = self.run_case("f n + 1 ≤ f (n + 1) ∧ f (n + 1) ≤ f n + 2", "f n ≤ f (n + 1) ∧ f (n + 1) ≤ f n + 2")
        self.assertEqual(row["directions"], {"fwd": "ENTAILS", "bwd": "SEPARATED"})
        self.assertEqual(row["verdict"], "LEAN_WEAKER")

    def test_base_bound(self):
        # f 0 ≥ 0 and increments ≥ 2 give f n ≥ 2 n; the bound 2 n + 1 fails at f 0 = 0
        self.assertEqual(self.fwd("f n + 2 ≤ f (n + 1)", "2 * n ≤ f n"), "ENTAILS")
        self.assertEqual(self.fwd("f n + 2 ≤ f (n + 1)", "2 * n + 1 ≤ f n"), "SEPARATED")

    def test_truncated_subtraction(self):
        self.assertEqual(self.fwd("f n + 1 ≤ f (n + 1) ∧ f (n + 1) ≤ f n + 3", "f (n + 1) - f n ≤ 3 ∧ f n - f (n + 1) = 0"), "ENTAILS")
        self.assertEqual(self.fwd("f n ≤ f (n + 1)", "f n - f (n + 2) = f (n + 2) - f n"), "SEPARATED")

    # --- lower class -------------------------------------------------------------------------------
    def test_monotone_and_strict(self):
        self.assertEqual(self.fwd("f n ≤ f (n + 1)", "f n ≤ f (2 * n) ∧ f (2 * n) ≤ f (3 * n + 1)"), "ENTAILS")
        self.assertEqual(self.fwd("f n ≤ f (n + 1)", "f n < f (n + 2)"), "SEPARATED")
        self.assertEqual(self.fwd("f n < f (n + 1)", "f n + 2 ≤ f (n + 2) ∧ n ≤ f n"), "ENTAILS")

    def test_colliding_sites(self):
        # 2 n and n + 3 coincide at n = 3 only
        self.assertEqual(self.fwd("f n < f (n + 1)", "f (2 * n) = f (n + 3) → n = 3"), "ENTAILS")
        self.assertEqual(self.fwd("f n ≤ f (n + 1)", "f (2 * n) = f (n + 3) → n = 3"), "SEPARATED")

    # --- pointwise class ---------------------------------------------------------------------------
    def test_pointwise_multi_site(self):
        self.assertEqual(self.fwd("n ≤ f (2 * n + 1) ∧ f (2 * n + 1) ≤ n + 3", "f (2 * n + 3) ≤ f (2 * n + 5) + 2",
                                  rguard="2 ≤ n", fguard="1 ≤ n"), "ENTAILS")
        self.assertEqual(self.fwd("n ≤ f (2 * n + 1) ∧ f (2 * n + 1) ≤ n + 3", "f (2 * n + 3) ≤ f (2 * n + 5) + 2",
                                  rguard="2 ≤ n"), "SEPARATED")

    def test_pointwise_collision_needs_congruence(self):
        self.assertEqual(self.fwd("f n % 2 = 0", "n = 3 → f (2 * n) = f (n + 3)"), "ENTAILS")
        self.assertEqual(self.fwd("f n % 2 = 0", "f (2 * n) = f (n + 3)"), "SEPARATED")

    def test_pointwise_true_guard(self):
        self.assertEqual(self.fwd("f n = 2 * n", "f (n + 1) + 3 ≤ f (2 * n + 1) ∨ 2 * n ≤ f (2 * n + 1) + f 0",
                                  fguard="1 ≤ n"), "ENTAILS")

    # --- outside the fragment: must abstain --------------------------------------------------------
    def test_abstains_outside(self):
        for ref, frm in [("f (n + 2) = f n + 2", "f (n + 4) = f n + 4"),          # stride 2
                         ("f (n + 1) = f n + 2 * n + 1", "f 3 = 9"),              # Theorem C's reference
                         ("f (f n) = n", "f (f (f n)) = f n"),                    # nested
                         ("f 0 + f 1 = f 2", "f 2 ≥ f 0"),                        # three sites, not majority-closed
                         ("f (n + 1) = f n + 1 ∨ f (n + 1) = f n + 3", "f (n + 2) ≠ f n + 3"),  # non-convex steps
                         ("f n * f n = f (2 * n)", "f 0 * f 0 = f 0")]:
            row = self.run_case(ref, frm)
            self.assertEqual(row["verdict"], "INCONCLUSIVE", (ref, frm, row))
            self.assertNotIn("ENTAILS", row["directions"].values())
            self.assertNotIn("SEPARATED", row["directions"].values())

    def test_nonconvex_steps_are_really_different(self):
        # increments in {1, 3} entail this claim; increments in [1, 3] do not. A class guess of
        # step(1, 3) for the first reference would be unsound; the bridge lemma must reject it.
        self.assertEqual(self.fwd("f n + 1 ≤ f (n + 1) ∧ f (n + 1) ≤ f n + 3", "f (n + 1) ≠ f n + 2"), "SEPARATED")
        orig = multiocc._step_params
        multiocc._step_params = lambda H, lo, hi: (1, 3)
        try:
            row = self.run_case("f (n + 1) = f n + 1 ∨ f (n + 1) = f n + 3", "f (n + 1) ≠ f n + 2")
        finally:
            multiocc._step_params = orig
        self.assertNotEqual(row["directions"]["fwd"], "SEPARATED", row)

    # --- search is not trusted ---------------------------------------------------------------------
    def test_wrong_witness_gives_no_certificate(self):
        orig = multiocc._witnesses
        multiocc._witnesses = lambda cls, C, count=3: [([0], [0] * len(C.sites)), ([2], [7] * len(C.sites))]
        try:
            row = self.run_case("f n + 1 ≤ f (n + 1) ∧ f (n + 1) ≤ f n + 2", "f (n + 3) ≤ f n + 6")
        finally:
            multiocc._witnesses = orig
        self.assertEqual(row["directions"]["fwd"], "ENTAILS", row)
        self.assertNotIn("nfwd", row["certificates"])

    def test_inconsistent_points_rejected(self):
        # values that violate the step bounds cannot be extended; Lean must refuse the list
        orig = multiocc._witnesses
        multiocc._witnesses = lambda cls, C, count=3: [([0], [0, 9])]
        try:
            row = self.run_case("f n + 1 ≤ f (n + 1) ∧ f (n + 1) ≤ f n + 2", "f (n + 1) ≤ f n + 2")
        finally:
            multiocc._witnesses = orig
        self.assertNotIn("nfwd", row["certificates"])
        self.assertEqual(row["directions"]["fwd"], "ENTAILS")

    def test_two_bound_variables(self):
        # Mathlib `StrictMono.add_le_nat`: m + f n ≤ f (m + n)
        spec = lambda body: {"id": "tv", "kind": "multi", "reference": {"body": "f n < f (n + 1)"},
                             "formal": {"vars": ["m", "n"], "body": body}}
        row = multiocc.compare(spec("m + f n ≤ f (m + n)"), self.tc, self.tmp / "tv1")
        self.assertEqual(row["directions"]["fwd"], "ENTAILS", row)
        row = multiocc.compare(spec("m + f n + 1 ≤ f (m + n)"), self.tc, self.tmp / "tv2")
        self.assertEqual(row["directions"]["fwd"], "SEPARATED", row)

    def test_large_literals(self):
        self.assertEqual(self.fwd("f n + 1 ≤ f (n + 1)", "n + 18446744073709551616 ≤ f (n + 18446744073709551616)"), "ENTAILS")


if __name__ == "__main__":
    unittest.main()
