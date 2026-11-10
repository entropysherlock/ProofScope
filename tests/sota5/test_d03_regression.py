"""SOTA-5: d03 regression. Reproduces the original error (an unannotated cast printed and re-elaborated
without its target type) and shows the repaired adapter. Core Lean analog of the Mathlib case."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from bench.sota5 import specs as S5
from proofscope.experimental import cjcs4 as E
from proofscope.toolchain import Toolchain

HAVE = bool(shutil.which("lean") and shutil.which("leanchecker") and os.environ.get("PROOFSCOPE_REPL")) \
    and not os.environ.get("PROOFSCOPE_IMPORTS")
CASE = {"case_id": "d03_core_analog", "ref_header": "", "cand_header": "",
        "ref_decl": "theorem ref_d03 : ∀ (n : Nat), ((n - 1 : Nat) : Int) = (n : Int) - 1 := by sorry",
        "cand_decl": "theorem cand_d03 : ∀ (n : Nat), 1 ≤ n → ((n - 1 : Nat) : Int) = (n : Int) - 1 := by sorry"}


@unittest.skipUnless(HAVE, "Lean 4.34.1, leanchecker, PROOFSCOPE_REPL; core mode")
class D03(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.rec = S5.prepare_case(CASE, cls.tmp / "prep", shutil.which("lean"))
        cls.tc = Toolchain.find()
        assert E.build(cls.tc, cls.tmp / "build")["ok"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_v1_print_loses_the_cast_target_and_fails_both_checks(self):
        for side in ("ref", "cand"):
            v1 = self.rec["sides"][side]["v1"]
            self.assertNotIn("Int", v1["printed"])
            self.assertFalse(v1["v1_check"])                 # the frozen runner's check catches it
            self.assertFalse(v1["v2_standalone_check"])

    def test_v2_print_round_trips_standalone(self):
        self.assertEqual(self.rec["status"], "OK")
        for side in ("ref", "cand"):
            self.assertIn(": Int)", self.rec["sides"][side]["v2"]["printed"])
            self.assertTrue(self.rec["sides"][side]["v2"]["v2_standalone_check"])

    def test_original_error_reproduced_on_unchecked_v1_strings(self):
        """Expected: exactly the SOTA-4 certificate family for d03 (a valid proof about the wrong statements)."""
        sp = {"id": "d03_v1", "reference": self.rec["sides"]["ref"]["v1"]["printed"],
              "lean": self.rec["sides"]["cand"]["v1"]["printed"]}
        row = E.run_case(sp, self.tc, self.tmp / "build", self.tmp / "v1")
        self.assertEqual(row["verdict"], "CERTIFIED_LOGICAL_EQUIVALENCE")
        self.assertEqual(sorted(row["certificates"]), ["equiv_both_true", "link_L", "link_R", "true_L", "true_R"])

    def test_repaired_strings_give_the_correct_certified_difference(self):
        sp = {"id": "d03_v2", "reference": self.rec["reference"], "lean": self.rec["lean"]}
        row = E.run_case(sp, self.tc, self.tmp / "build", self.tmp / "v2")
        self.assertEqual(row["verdict"], "CERTIFIED_LOGICAL_DIFFERENCE")
        self.assertEqual(row["direction"], "reference_false_formalization_true")
        self.assertEqual(row["witnesses"]["wit_R"], ["0"])
        self.assertIn("diff_RL", row["certificates"])


if __name__ == "__main__":
    unittest.main()
