"""v0.8 ClaimDelta: relation logic, obligation shapes, and one end-to-end certified run."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from proofscope import claimdelta as C


def spec(i, rh, rc, lh, lc, b=(("n", "Nat"),)):
    return {"id": i, "binders": [list(x) for x in b], "ref_hyp": rh, "ref_concl": rc, "lean_hyp": lh, "lean_concl": lc}


class RelationTests(unittest.TestCase):
    def test_relation_table(self):
        self.assertEqual(C.relation({"fwd_s1", "bwd_s1"}, "s1"), "SCHEMA_EQUIVALENT")
        self.assertEqual(C.relation({"fwd_s1", "sepW_s1"}, "s1"), "LEAN_WEAKER")
        self.assertEqual(C.relation({"bwd_s1", "sepS_s1"}, "s1"), "LEAN_STRONGER")
        self.assertEqual(C.relation({"sepW_s1", "sepS_s1"}, "s1"), "INCOMPARABLE")
        self.assertEqual(C.relation({"fwd_s1", "sepS_s1"}, "s1"), "INCONSISTENT")
        self.assertEqual(C.relation({"bwd_s1", "sepW_s1"}, "s1"), "INCONSISTENT")
        self.assertEqual(C.relation(set(), "s1"), "INCONCLUSIVE")

    def test_pools(self):
        self.assertIn("fun k => k", C.pool("Nat → Nat", [0, 1, 2, 3]))
        self.assertEqual(C.pool("Real → Real", [0]), [])

    def test_closed(self):
        self.assertEqual(C.closed([["n", "Nat"]], "True", "n < 2 ^ n"), "∀ (n : Nat), (True) → (n < 2 ^ n)")


@unittest.skipUnless(shutil.which("lean"), "Lean not on PATH")
class EndToEnd(unittest.TestCase):
    def test_false_reference_is_not_called_harmless_rewriting(self):
        # cd009 from the frozen SOTA-15 suite: the reference is false at n = 1.
        # Implication from a false reference is not evidence of faithful rewriting.
        from proofscope.toolchain import Toolchain
        tc = Toolchain.find()
        with tempfile.TemporaryDirectory(prefix="ps_false_reference_") as d:
            out = Path(d)
            self.assertTrue(C.build_abstractor(tc, out / "build")["ok"])
            case = spec("false_ref_sota15", "1 ≤ n", "2 ^ (2 * n) = 0",
                        "n < 3", "2 ^ (n + 1) < n")
            r = C.run_case(case, tc, out / "build", out / "case")
            self.assertNotEqual(r["verdict"], "EQUIVALENT_BY_LAWS", r)
            self.assertEqual(r["reference_status"], "REFUTED", r)
            self.assertEqual(r["verdict"], "REFERENCE_REFUTED", r)
            self.assertIn("refFalse", r["reference_certificates"])
            self.assertTrue(set(r["reference_certificates"]["refFalse"]["axioms"]) <=
                            {"propext", "Classical.choice", "Quot.sound"})

    def test_two_pow_weaker_and_harmless_rewrite(self):
        from proofscope.toolchain import Toolchain
        tc = Toolchain.find()
        out = Path(tempfile.mkdtemp())
        self.assertTrue(C.build_abstractor(tc, out / "build")["ok"])
        r = C.run_case(spec("w", "True", "n < 2 ^ n", "True", "n ≤ 2 ^ n"), tc, out / "build", out / "w")
        self.assertEqual(r["verdict"], "CLAIM_LEAN_WEAKER")
        cert = r["subsets"]["s1"]["certificates"]
        self.assertIn("sepW_s1", cert)
        self.assertTrue(set(cert["sepW_s1"]["axioms"]) <= {"propext", "Classical.choice", "Quot.sound"})
        h = C.run_case(spec("h", "True", "n < 2 ^ n", "True", "n + 1 ≤ 2 ^ n"), tc, out / "build", out / "h")
        self.assertEqual(h["verdict"], "SCHEMA_EQUIVALENT")


if __name__ == "__main__":
    unittest.main()
