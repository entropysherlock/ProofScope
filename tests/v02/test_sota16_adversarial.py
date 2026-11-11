"""SOTA-16 adversarial tests: the Presburger pass must never produce a wrong verdict, never lose a
certificate the v1.3 portfolio finds, and must abstain outside its fragment."""
import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from proofscope import claimdelta as C
from proofscope import scopeelim as se
from proofscope.scope_expr import Unsupported
from proofscope.toolchain import Toolchain


def side(guard, arg, rel):
    return {"var": "n", "guard": guard, "arg": arg, "rel": rel}


def cd(i, rh, rc, lh, lc):
    return {"id": i, "binders": [["n", "Nat"]], "ref_hyp": rh, "ref_concl": rc, "lean_hyp": lh, "lean_concl": lc}


class TestAbstention(unittest.TestCase):
    def test_repeated_symbol_is_outside_the_fragment(self):
        for rc in ("2 ^ n < 2 ^ (n + 1)", "2 ^ n + 2 ^ n ≥ n", "2 ^ (2 ^ n) > n"):
            with self.assertRaises(Unsupported):
                se.detect(cd("rep", "True", rc, "True", "n < 2 ^ n"))

    def test_non_affine_argument_gets_no_presburger_tactics(self):
        for arg in ("n * n", "n / 2", "n - 1", "n % 3"):
            R = se.FunClaim.from_json(side("True", arg, "n < w"))
            self.assertEqual(se.presburger_tactics(R, R), {}, arg)


class TestToolchainTimeout(unittest.TestCase):
    def test_timeout_is_a_result_not_a_crash(self):
        # found by the SOTA-16 CI reproduction: a timed-out process returned bytes and raised TypeError
        r = Toolchain(lean="lean").run(["python3", "-c", "import time; print('x', flush=True); time.sleep(5)"], timeout=0.5)
        self.assertEqual(r.returncode, -9)
        self.assertIn("TIMEOUT", r.output)
        self.assertIsInstance(r.as_dict()["output_tail"], str)


@unittest.skipUnless(shutil.which("lean"), "Lean not on PATH")
class TestAdversarial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="ps_sota16_adv_"))
        cls.base = Toolchain.find()
        assert se.build_lib(cls.base, cls.tmp / "lib")["ok"]
        cls.tc = se.lib_toolchain(cls.base, cls.tmp / "lib")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_spec(self, i, ref, frm, pres=True):
        saved = se.PRESBURGER
        se.PRESBURGER = pres
        try:
            return se.compare({"id": i, "kind": "func", "reference": ref, "formal": frm}, self.tc,
                              self.tmp / "lib", self.tmp / "work" / (i + ("" if pres else "_off")))
        finally:
            se.PRESBURGER = saved

    def assert_never_wrong(self, r, fwd, bwd):
        """A direction may be certified as its true value or left open; nothing else."""
        self.assertIn(r["directions"]["fwd"], (fwd, "UNKNOWN"), r)
        self.assertIn(r["directions"]["bwd"], (bwd, "UNKNOWN"), r)
        self.assertNotEqual(r["verdict"], "INCONSISTENT", r)

    def test_slope3_congruence_decided(self):
        r = self.run_spec("s3_ok", side("True", "3 * n", "w % 3 = n % 3"), side("n % 3 = 1", "3 * n", "w % 3 = 1"))
        self.assertEqual(r["verdict"], "LEAN_WEAKER", r)

    def test_slope3_congruence_open_case_is_never_wrong(self):
        # fl070 of the frozen suite (open after SOTA-16): both directions are in fact separated
        r = self.run_spec("s3_open", side("3 ≤ n", "3 * n", "2 * w ≤ n ∧ w % 3 = n % 3"), side("3 ≤ n", "3 * n", "n < w"))
        self.assert_never_wrong(r, "SEPARATED", "SEPARATED")

    def test_constant_arguments(self):
        r = self.run_spec("c_both", side("True", "4", "w < 7 ∧ 3 ≤ w"), side("True", "4", "w < 9"))
        self.assertEqual(r["verdict"], "LEAN_WEAKER", r)
        # unsatisfiable only jointly: n = 0 forces f 4 = 0 and n = 1 forces f 4 = 1
        v = self.run_spec("c_joint", side("n < 2", "4", "w = n"), side("True", "n", "w = 9"))
        self.assert_never_wrong(v, "ENTAILS", "SEPARATED")

    def test_nat_encoding_traps(self):
        # truncated subtraction: over Nat, `w - n = 0` is `w ≤ n`; over the integers it is `w = n`
        r = self.run_spec("e_sub", side("True", "n", "w - n = 0"), side("True", "n", "w ≤ n"))
        self.assert_never_wrong(r, "ENTAILS", "ENTAILS")
        # division by zero is zero in Lean
        z = self.run_spec("e_div0", side("True", "n", "w / 0 = 0"), side("True", "n", "0 ≤ w"))
        self.assert_never_wrong(z, "ENTAILS", "ENTAILS")
        # literals beyond 64 bits
        big = self.run_spec("e_big", side("True", "n", "w = 100000000000000000000"),
                            side("True", "n", "w ≥ 99999999999999999999"))
        self.assertEqual(big["verdict"], "LEAN_WEAKER", big)

    def test_heavy_congruences_finish_and_lose_nothing(self):
        ref = side("True", "n", "w % 4 = n % 4 ∧ w % 3 = n % 3 ∧ n ≤ w")
        frm = side("True", "2 * n + 1", "w % 6 = 1 ∨ w < n")
        t0 = time.time()
        on = self.run_spec("mem", ref, frm)
        self.assertLess(time.time() - t0, 600)
        off = self.run_spec("mem", ref, frm, pres=False)
        self.assertNotEqual(on["certify_status"], "INFRASTRUCTURE_ERROR", on)
        self.assertLessEqual(set(off["certificates"]), set(on["certificates"]))
        for d in ("fwd", "bwd"):
            if off["directions"][d] != "UNKNOWN":
                self.assertEqual(on["directions"][d], off["directions"][d])

    def test_adapter_uses_presburger_pass_and_keeps_labels(self):
        spec = cd("ad_const", "True", "n < 2 ^ 3", "True", "2 ^ n ≤ n + 2")
        on = se.compare_claimdelta(spec, self.tc, self.tmp / "ad_on")
        self.assertEqual(on["verdict"], "LEAN_WEAKER", on)
        self.assertIn("fwd_s1", on["presburger_pass"]["certificates"])
        saved, se.PRESBURGER = se.PRESBURGER, False
        try:
            off = se.compare_claimdelta(spec, self.tc, self.tmp / "ad_off")
        finally:
            se.PRESBURGER = saved
        self.assertEqual(off["verdict"], "INCONCLUSIVE", off)
        self.assertLessEqual(set(off["certificates"]), set(on["certificates"]))

    def test_false_reference_survives_the_fallback(self):
        out = self.tmp / "false_ref"
        self.assertTrue(C.build_abstractor(self.base, out / "build")["ok"])
        self.assertTrue(se.build_lib(self.base, out / "scopeelim_lib")["ok"])
        p = self.tmp / "false_ref.json"
        p.write_text(json.dumps(cd("false_ref_fb", "1 ≤ n", "2 ^ (2 * n) = 0", "n < 3", "2 ^ (n + 1) < n")))
        row = C._one((str(p), out / "build", out, True))
        self.assertEqual(row["verdict"], "REFERENCE_REFUTED", row)
        self.assertNotIn("verdict_source", row)


if __name__ == "__main__":
    unittest.main()
