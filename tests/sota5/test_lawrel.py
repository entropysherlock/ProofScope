"""SOTA-5: law-relative prototype. Expected results are stated per test; the Lean module is the certificate."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from proofscope.experimental import lawrel as LR
from proofscope.toolchain import Toolchain

HAVE = bool(shutil.which("lean") and shutil.which("leanchecker"))
SPECS = Path(__file__).resolve().parents[2] / "research/sota5/lawrel"


@unittest.skipUnless(HAVE, "Lean 4.34.1 and leanchecker required")
class LawRel(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_spec(self, name):
        return LR.run(json.loads((SPECS / f"{name}.json").read_text()), self.tmp / name, Toolchain.find())

    def test_e1_two_incomparable_minimal_sets(self):
        """Expected: {comm} and {assoc, idem} are the inclusion-minimal sufficient sets; no law is necessary."""
        r = self.run_spec("e1_absorption")
        self.assertTrue(r["certified"])
        self.assertEqual(sorted(map(sorted, r["minimal_sufficient"])), [["assoc", "idem"], ["comm"]])
        self.assertEqual(r["necessary_in_family"], [])
        self.assertEqual(r["subsets"]["none"]["status"], "REFUTED")

    def test_e2_idempotence_necessary(self):
        """Expected: {idem} is minimal and idem is necessary within the family."""
        r = self.run_spec("e2_square_idem")
        self.assertTrue(r["certified"])
        self.assertEqual(r["minimal_sufficient"], [["idem"]])
        self.assertEqual(r["necessary_in_family"], ["idem"])

    def test_countermodel_violating_background_law_is_rejected(self):
        """Hostile: a model that claims to satisfy laws it violates (the e1 separating model m0 satisfies only
        assoc; here it also claims comm and idem). Expected: the kernel rejects the module."""
        import subprocess
        spec = json.loads((SPECS / "e1_absorption.json").read_text())
        names = list(spec["laws"])
        tbl = [0, 0, 0, 0, 0, 0, 0, 1, 2]
        good, _, _ = LR.module(spec, names, {}, {"m0": (3, tbl, ["assoc"])}, [], {})
        bad, _, _ = LR.module(spec, names, {}, {"m0": (3, tbl, ["assoc", "comm", "idem"])}, [], {})
        tc = Toolchain.find()
        res = {}
        for tag, src in (("good", good), ("bad", bad)):
            f = self.tmp / f"{tag}.lean"
            f.write_text(src)
            r = subprocess.run([tc.lean, str(f)], capture_output=True, text=True)
            res[tag] = r.returncode == 0 and ": error" not in r.stdout + r.stderr
        self.assertTrue(res["good"])
        self.assertFalse(res["bad"])

    def test_unknown_is_not_negative(self):
        """No separating model and no proof: UNKNOWN, and it never appears as a refutation."""
        orig_find, orig_port = LR.find_model, LR.PROOF_PORTFOLIO
        LR.find_model = lambda laws, P, Q: None
        LR.PROOF_PORTFOLIO = ["exact absurd"]          # always fails
        try:
            r = self.run_spec("e2_square_idem")
        finally:
            LR.find_model, LR.PROOF_PORTFOLIO = orig_find, orig_port
        self.assertTrue(all(v["status"] == "UNKNOWN" for v in r["subsets"].values()))
        self.assertEqual(r["minimal_sufficient"], [])
        self.assertEqual(r["necessary_in_family"], [])


if __name__ == "__main__":
    unittest.main()
