"""SOTA-8: derivation engine, fail-closed behaviour, scoring of one-way implications. Core Lean + REPL."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from bench.sota7.scoring import classify
from proofscope.experimental import cjcs4 as E
from proofscope.experimental import sota8 as S8
from proofscope.toolchain import Toolchain

HAVE = bool(shutil.which("lean") and shutil.which("leanchecker") and os.environ.get("PROOFSCOPE_REPL")) \
    and not os.environ.get("PROOFSCOPE_IMPORTS")
DEV = Path(__file__).resolve().parents[2] / "research/sota8/dev"


@unittest.skipUnless(HAVE, "Lean 4.34.1, leanchecker, PROOFSCOPE_REPL (core mode)")
class Engine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = Path(tempfile.mkdtemp()); cls.tc = Toolchain.find()
        assert E.build(cls.tc, cls.t / "b")["ok"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.t)

    def run_dev(self, name):
        spec = json.loads((DEV / f"{name}.json").read_text())
        os.environ["PROOFSCOPE_PREAMBLE"] = "\n".join(spec.get("preamble", []))
        try:
            return S8.run_case(spec, self.tc, self.t / "b", self.t / name)
        finally:
            os.environ.pop("PROOFSCOPE_PREAMBLE", None)

    def test_equivalence_of_open_problem_formulations_without_proving_either(self):
        """Goldbach-type statement: certified equivalent by mutual derivation; neither side is proved."""
        r = self.run_dev("g1_goldbach_reformulated")
        self.assertEqual((r["verdict"], r["direction"]), ("CERTIFIED_LOGICAL_EQUIVALENCE", "mutual_derivation"))
        self.assertNotIn("true_R", r.get("certificates", {}))

    def test_one_way_is_reported_as_one_way(self):
        r = self.run_dev("g3_one_way")
        self.assertEqual((r["verdict"], r["direction"]), ("CERTIFIED_IMPLICATION", "reference_implies_candidate"))
        self.assertIn("converse not certified", r["note"])

    def test_free_identifier_is_not_auto_bound(self):
        """autoImplicit is off: a misspelled name is an input error, not a new universally quantified variable."""
        r = self.run_dev("g4_free_identifier")
        self.assertEqual((r["verdict"], r["failure_class"]), ("INCONCLUSIVE", "EXTRACTION"))

    def test_forged_derivation_is_rejected_by_the_verifier(self):
        """Hostile: the search claims both directions for a one-way pair; the clean verifier rejects the forged one."""
        orig = E.search if False else None
        real = S8.E._infos

        def forged(resp, tag):
            out = real(resp, tag)
            if tag == "CJCS_SEARCH" and out:
                for row in out[0]:
                    if row["name"] in ("impl_CR", "equiv"):
                        row.update(status="proposed", alt=0)
            return out
        S8.E._infos = forged
        try:
            r = self.run_dev("g3_one_way")
        finally:
            S8.E._infos = real
        self.assertNotEqual(r["verdict"], "CERTIFIED_LOGICAL_EQUIVALENCE")
        self.assertNotIn("equiv", r.get("certificates", {}))


class Scoring(unittest.TestCase):
    V = {"replay": "VERIFIED"}

    def test_one_way_rules(self):
        rc = {"claim": {"claim": "IMPLICATION_ONE_WAY", "direction": "reference_implies_candidate"}}
        self.assertEqual(classify(rc, self.V, {"relation": "REF_STRONGER"}), "CORRECT_PARTIAL")
        self.assertEqual(classify(rc, self.V, {"relation": "EQUIVALENT"}), "CORRECT_PARTIAL")
        self.assertEqual(classify(rc, self.V, {"relation": "CAND_STRONGER"}), "INCORRECT")
        self.assertEqual(classify(rc, self.V, {"relation": "INCOMPARABLE"}), "INCORRECT")
        self.assertEqual(classify(rc, {"replay": "REJECTED"}, {"relation": "REF_STRONGER"}), "INVALID_CERTIFICATE")

    def test_mutual_derivation_is_closed_level(self):
        """Found by the synthetic run: `2 + 2 = 4` vs `∀ n, n + 0 = n` is 'derived' both ways by proving each side
        outright. Mutual derivation is therefore closed-level evidence."""
        md = {"claim": {"claim": "EQUIVALENT_CLOSED", "basis": "mutual_derivation"}}
        tt = {"reference": "TRUE", "candidate": "TRUE"}
        self.assertEqual(classify(md, self.V, {"relation": "NOT_EQUIVALENT", "closed_truth": tt}), "CLOSED_ONLY_AGREEMENT")
        self.assertEqual(classify(md, self.V, {"relation": "NOT_EQUIVALENT"}), "CLOSED_ONLY_UNCHECKED")
        self.assertEqual(classify(md, self.V, {"relation": "NOT_EQUIVALENT", "closed_truth": {"reference": "FALSE", "candidate": "TRUE"}}), "INCORRECT")
        self.assertEqual(classify(md, self.V, {"relation": "EQUIVALENT"}), "CORRECT")


if __name__ == "__main__":
    unittest.main()
