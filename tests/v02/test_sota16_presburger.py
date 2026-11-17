"""SOTA-16: instantiation certificates for the linear one-occurrence function fragment."""
import shutil
import tempfile
import unittest
from pathlib import Path

from proofscope import scope_smt
from proofscope import scopeelim as se
from proofscope.scope_expr import parse
from proofscope.toolchain import Toolchain


class TestTerms(unittest.TestCase):
    def test_affine(self):
        self.assertEqual(se.affine(parse("3 * n + 2"), "n"), (3, 2))
        self.assertEqual(se.affine(parse("(n + 1) * 2"), "n"), (2, 2))
        self.assertEqual(se.affine(parse("4"), "n"), (0, 4))
        self.assertIsNone(se.affine(parse("n * n"), "n"))
        self.assertIsNone(se.affine(parse("n / 2"), "n"))

    def test_bound_terms_contain_exact_lower_bound(self):
        ts = se.bound_terms(parse("z + 2 < 3 * w"), "w")       # least w is (z + 2) / 3 + 1
        self.assertIn("0", ts)
        self.assertIn("(((z + 2) - (0)) / 3 + 1)", ts)

    def test_period(self):
        self.assertEqual(se._period(parse("w % 2 = 0 ∧ w / 3 = n")), 6)


@unittest.skipUnless(shutil.which("lean"), "Lean not on PATH")
class TestCertificates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="ps_sota16_"))
        base = Toolchain.find()
        assert se.build_lib(base, cls.tmp / "lib")["ok"]
        cls.tc = se.lib_toolchain(base, cls.tmp / "lib")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_spec(self, i, ref, frm):
        spec = {"id": i, "kind": "func", "reference": dict(zip(("var", "guard", "arg", "rel"), ("n",) + ref)),
                "formal": dict(zip(("var", "guard", "arg", "rel"), ("n",) + frm))}
        return se.compare(spec, self.tc, self.tmp / "lib", self.tmp / "work" / i)

    def test_constant_argument_vacuity(self):
        # every n constrains f 3 from below, so no value exists: the reference is vacuous
        r = self.run_spec("p_vac", ("True", "3", "n < w"), ("True", "n", "w ≤ n + 2"))
        self.assertEqual(r["verdict"], "LEAN_WEAKER")
        self.assertTrue(r["reference_vacuous"])

    def test_congruence_and_slope(self):
        r = self.run_spec("p_mod", ("True", "2 * n + 1", "w % 3 = n % 3"), ("n % 3 = 1", "2 * n + 1", "w % 3 = 1"))
        self.assertEqual(r["verdict"], "LEAN_WEAKER")

    def test_without_z3_only_abstains_or_agrees(self):
        saved = scope_smt.z3
        scope_smt.z3 = None
        try:
            r = self.run_spec("p_noz3", ("1 ≤ n", "n", "n < w"), ("True", "n + 1", "n + 1 < w"))
        finally:
            scope_smt.z3 = saved
        self.assertIn(r["verdict"], ("SCHEMA_EQUIVALENT", "INCONCLUSIVE"))


if __name__ == "__main__":
    unittest.main()
