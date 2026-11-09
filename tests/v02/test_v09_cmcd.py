"""v0.9 CMCD: pools, closers without nested `by`, and one end-to-end localized certificate."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from proofscope import cmcd as M


class Unit(unittest.TestCase):
    def test_no_nested_by_in_portfolios(self):
        tacs = M.entail_tactics(1) + M.sep_tactics(["Nat → Nat"], [0, 1, 2, 3]) + M.law_tactics()
        self.assertFalse(any("(by " in t or ", by " in t for t in tacs))

    def test_law_tactics_use_antecedent(self):
        import re
        self.assertTrue(all(t.startswith("intro h") and re.search(r"\bh\b", t[7:]) for t in M.law_tactics()))

    def test_pools(self):
        self.assertIn("fun a b => if a = b then 1 else 0", M.pool("Nat → Nat → Nat", [0, 1, 2, 3]))
        self.assertIn("fun l => List.length l", M.pool("List Nat → Nat", [0]))
        self.assertEqual(M.pool("Real → Real", [0]), [])


@unittest.skipUnless(shutil.which("lean"), "Lean not on PATH")
class EndToEnd(unittest.TestCase):
    def test_localizes_the_weakening_edit(self):
        from proofscope.toolchain import Toolchain
        tc = Toolchain.find()
        out = Path(tempfile.mkdtemp())
        self.assertTrue(M.build(tc, out / "build")["ok"])
        spec = {"id": "t", "reference": "∀ (n : Nat), (2 * n ≤ n * n) → (n < 2 ^ n)",
                "lean": "∀ (n : Nat), (n + n ≤ n * n) → (n ≤ 2 ^ n)"}
        r = M.run_case(spec, tc, out / "build", out / "w")
        self.assertEqual(r["verdict"], "CLAIM_LEAN_WEAKER")
        self.assertEqual(r["localized_at"], [2])
        self.assertEqual(r["steps"][0]["relation"], "SCHEMA_EQUIVALENT")
        cm = r["steps"][1]["certificates"]["sepW_e2"]
        self.assertTrue(set(cm["axioms"]) <= {"propext", "Classical.choice", "Quot.sound"})


if __name__ == "__main__":
    unittest.main()
