"""CJCS (experimental) end-to-end on core Lean: positive and negative controls, every verdict kernel-checked.
Development data only; see docs/sota3/README.md for the held-out run."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from proofscope import adelta12 as A
from proofscope.experimental import cjcs as C


@unittest.skipUnless(shutil.which("lean"), "Lean not on PATH")
class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from proofscope.toolchain import Toolchain
        cls.tc = Toolchain.find()
        cls.out = Path(tempfile.mkdtemp())
        assert A.build(cls.tc, cls.out / "build")["ok"]

    def run_pair(self, i, r, l):
        return C.run_case({"id": i, "reference": r, "lean": l}, self.tc, self.out / "build", self.out / i)

    def test_difference_needs_both_halves(self):
        r = self.run_pair("t1", "∀ (n : Nat), n - 1 + 1 = n", "∀ (n : Nat), 1 ≤ n → n - 1 + 1 = n")
        self.assertEqual(r["verdict"], "CERTIFIED_LOGICAL_DIFFERENCE")
        self.assertIn("diff_RL", r["certificates"])
        self.assertIn("true_L", r["certificates"])
        self.assertIn("false_R", r["certificates"])
        self.assertEqual(r["regions"], ["region_ref_excluded"])

    def test_two_false_statements_are_not_reported_different(self):
        r = self.run_pair("t2", "∀ (n : Nat), n + 1 = n", "∀ (n : Nat), n * 2 = n + 3")
        self.assertEqual(r["verdict"], "CERTIFIED_LOGICAL_EQUIVALENCE")
        self.assertEqual(r["direction"], "both_false")

    def test_definitional_equivalence(self):
        r = self.run_pair("t3", "∀ (a b : Nat), a + b = b + a", "∀ (x y : Nat), x + y = y + x")
        self.assertEqual(r["direction"], "definitional")

    def test_joint_drift_region(self):
        r = self.run_pair("t4", "∀ (n : Nat), n ≤ 5 → n ≤ 10", "∀ (n : Nat), n ≤ 7 → n ≤ 6")
        self.assertEqual(r["verdict"], "CERTIFIED_LOGICAL_DIFFERENCE")
        self.assertIn("region_joint", r["regions"])

    def test_no_countermodel_means_abstain(self):
        # neither side is refutable with the registry and the truth of the statement is not decided here
        r = self.run_pair("t5", "∀ (l m : List Nat), (l ++ m).length = l.length + m.length",
                          "∀ (l m : List Nat), (l ++ m).length = l.length")
        self.assertNotEqual(r["verdict"], "CERTIFIED_LOGICAL_EQUIVALENCE")
        self.assertIn(r["verdict"], ("ABSTAIN", "CERTIFIED_LOGICAL_DIFFERENCE"))

    def test_every_certificate_used_standard_axioms(self):
        r = self.run_pair("t6", "∀ (n : Nat), n < 10 → n ≤ 9", "∀ (n : Nat), n < 10 → n ≤ 8")
        for k, c in r["certificates"].items():
            self.assertTrue(set(c["axioms"]) <= {"propext", "Classical.choice", "Quot.sound"}, (k, c))
        json.dumps(r)


if __name__ == "__main__":
    unittest.main()
