"""SOTA-4 Task J: adversarial controls for the one-process CJCS engine. Each test states its expected result.
Needs `lean`, `leanchecker` (Lean 4.34.1) and PROOFSCOPE_REPL; skipped otherwise. Core Lean only."""
import copy
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from proofscope import adelta12 as A
from proofscope.experimental import cjcs as S3
from proofscope.experimental import cjcs4 as E
from proofscope.toolchain import Toolchain

HAVE = bool(shutil.which("lean") and shutil.which("leanchecker") and os.environ.get("PROOFSCOPE_REPL")) and not A.MATHLIB
HDR = A.import_lines() + S3.HEADER


@unittest.skipUnless(HAVE, "Lean 4.34.1, leanchecker and PROOFSCOPE_REPL required (core mode)")
class Hostile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.tc = Toolchain.find()
        cls.build = cls.tmp / "build"
        assert E.build(cls.tc, cls.build)["ok"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def w(self, name):
        return self.tmp / name

    # -- the verifier is authoritative ------------------------------------------------------------
    def test_unverifiable_proposal_is_rejected(self):
        """Expected: a search proposal whose tactic does not prove its statement certifies nothing."""
        v = E.verify("H1", HDR, {"bogus": ("2 + 2 = 5", ["decide"])}, self.tc, self.w("h1"))
        self.assertEqual(v["status"], "VERIFY_REJECTED")
        self.assertEqual(v["certificates"], {})

    def test_sorry_proposal_is_rejected(self):
        """Expected: sorryAx in a proposal is rejected even though the module compiles."""
        v = E.verify("H2", HDR, {"s": ("2 + 2 = 5", ["sorry"])}, self.tc, self.w("h2"))
        self.assertEqual(v["certificates"], {})
        self.assertIn("sorryAx", v["rejected"]["s"])

    def test_native_decide_axiom_is_rejected(self):
        """Expected: a proof through Lean.ofReduceBool (native_decide) is not a certificate."""
        v = E.verify("H3", HDR, {"n": ("10 * 10 = 100", ["native_decide"])}, self.tc, self.w("h3"))
        self.assertEqual(v["certificates"], {})
        self.assertIn("non-standard axioms", v["rejected"]["n"])

    def test_difference_without_its_dependency_is_rejected(self):
        """Expected: `diff_RL` proposed without a proposed `false_R` cannot verify (fail closed)."""
        R, L = "∀ (n : Nat), n = 0", "∀ (n : Nat), n = n"
        props = {"true_L": (L, ["(intros; trivial)"]),
                 "diff_RL": (f"¬ (({R}) ↔ ({L}))", ["exact fun h => false_R (h.mpr true_L)"])}
        v = E.verify("H4", HDR, props, self.tc, self.w("h4"))
        self.assertEqual(v["status"], "VERIFY_REJECTED")
        self.assertNotIn("diff_RL", v["certificates"])

    def test_genuine_proposal_is_certified_and_replayed(self):
        """Control: a correct proposal is certified with its axiom report and a leanchecker replay."""
        v = E.verify("H5", HDR, {"ok": ("2 + 2 = 4", ["decide"])}, self.tc, self.w("h5"))
        self.assertIn("ok", v["certificates"])
        self.assertEqual(v["replay"]["returncode"], 0)

    def test_forged_search_result_cannot_change_verdict(self):
        """Expected: if the search process lies (claims a refutation of a true reference), the verdict is
        not a difference: verification rejects the forged proposal."""
        orig = E.search

        def lying_search(repl, env, ns, obligations):
            env2, rows = orig(repl, env, ns, obligations)
            for k in obligations:
                if k in ("link_R", "wit_R", "false_R"):
                    rows[k] = {"name": k, "status": "proposed", "alt": 0}
            return env2, rows
        E.search = lying_search
        try:
            row = E.run_case({"id": "forged", "reference": "∀ (n : Nat), n + 0 = n", "lean": "∀ (n : Nat), n = n + 1"},
                             self.tc, self.build, self.w("h6"))
        finally:
            E.search = orig
        # the lie would yield "both false" (equivalence) or "reference false"; neither may be certified.
        # Losing the true verdict (the formalization is false at 1) is the accepted price: fail closed.
        self.assertNotIn("false_R", row["certificates"])
        self.assertNotEqual(row["direction"] if "direction" in row else None, "reference_false_formalization_true")
        self.assertNotEqual(row["direction"] if "direction" in row else None, "both_false")

    # -- process management -----------------------------------------------------------------------
    def test_search_timeout_is_reported_and_leaves_no_orphan(self):
        """Expected: a search that exceeds its timeout gives INCONCLUSIVE/SEARCH_TIMEOUT (never a verdict
        and never an abstention) and no REPL process survives."""
        old = E.SEARCH_TIMEOUT_S
        E.SEARCH_TIMEOUT_S = 0.05
        try:
            row = E.run_case({"id": "to", "reference": "∀ (n : Nat), n = n", "lean": "∀ (n : Nat), n = n"},
                             self.tc, self.build, self.w("h7"))
        finally:
            E.SEARCH_TIMEOUT_S = old
        self.assertEqual(row["verdict"], "INCONCLUSIVE")
        self.assertEqual(row["failure_class"], "SEARCH_TIMEOUT")
        time.sleep(0.5)
        ps = subprocess.run(["ps", "-o", "pid=,ppid=,comm=", "--ppid", str(os.getpid())], capture_output=True, text=True).stdout
        self.assertNotIn("repl", ps)
        live = subprocess.run(["pgrep", "-f", str(self.w("h7"))], capture_output=True, text=True).stdout.strip()
        self.assertEqual(live, "")

    def test_search_process_crash_is_infrastructure_not_abstention(self):
        """Expected: a REPL that dies is reported as INCONCLUSIVE/SEARCH_PROCESS."""
        row = E.run_case({"id": "crash", "reference": "True", "lean": "True"}, self.tc, self.build, self.w("h8"),
                         repl_exe="/bin/false")
        self.assertEqual(row["verdict"], "INCONCLUSIVE")
        self.assertIn(row["failure_class"], ("SEARCH_PROCESS", "SEARCH_TIMEOUT"))

    # -- state isolation (finding F2) ---------------------------------------------------------------
    def test_point_pools_do_not_leak_between_cases(self):
        """Expected: the ℕ point pool is the same before and after a case with literals (SOTA-3 leaked)."""
        before = copy.deepcopy(A.POINT_POOLS)
        E.run_case({"id": "lits", "reference": "∀ (n : Nat), n ≠ 17", "lean": "∀ (n : Nat), n ≠ 13"},
                   self.tc, self.build, self.w("h9"))
        self.assertEqual(A.POINT_POOLS, before)

    def test_sota3_point_pool_leak_is_real(self):
        """Documents finding F2 on the frozen SOTA-3 helper: calling it mutates global state."""
        before = copy.deepcopy(A.POINT_POOLS)
        try:
            S3.with_literal_points("∀ (n : Nat), n ≠ 17", "x")
            self.assertNotEqual(A.POINT_POOLS, before)
        finally:
            A.POINT_POOLS.clear()
            A.POINT_POOLS.update(before)


@unittest.skipUnless(HAVE, "Lean 4.34.1, leanchecker and PROOFSCOPE_REPL required (core mode)")
class HostileSuite(unittest.TestCase):
    """research/cjcs/sota4_hostile: every case has an explicit expected result or a must-not set."""

    def test_suite(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            tc = Toolchain.find()
            assert E.build(tc, tmp / "build")["ok"]
            for f in sorted((Path(__file__).resolve().parents[2] / "research/cjcs/sota4_hostile").glob("*.json")):
                spec = json.loads(f.read_text())
                row = E.run_case(spec, tc, tmp / "build", tmp / spec["id"])
                with self.subTest(case=spec["id"], verdict=row["verdict"]):
                    self.assertNotIn(row["verdict"], spec["must_not_be"])
                    for k in row.get("certificates") or {}:
                        self.assertIn(k, row["certificate_source"])
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
