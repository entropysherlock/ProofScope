"""v1.2: countermodel registry, round-robin witness search, joint decision for interacting assumption
changes (the v1.1 defect), coverage scoring, frozen evaluation split."""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from proofscope import adelta12 as A
from proofscope import models as M
from proofscope import v12 as V

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "proofscope" / "benchmark"


class Unit(unittest.TestCase):
    def test_registry_families(self):
        self.assertIn("DihedralGroup 3", M.MATHLIB_CARRIERS)
        self.assertIn("Finset (Fin 2)", M.MATHLIB_CARRIERS)
        self.assertIn("ZMod 4", M.MATHLIB_CARRIERS)
        for c in M.MATHLIB_CARRIERS.values():
            self.assertTrue(c["vals"])

    def test_no_unsafe_tactics(self):
        text = (ROOT / "proofscope" / "models.py").read_text() + (ROOT / "proofscope" / "adelta12.py").read_text()
        for bad in ("native_decide", "sorry", "admit", "axiom "):
            self.assertNotIn(bad, text)

    def test_round_robin_reaches_late_carriers(self):
        old = dict(A.CARRIERS)
        try:
            A.CARRIERS["Late"] = {"vals": ["late0"], "op2": ["o"], "op1": ["u"], "rel": ["r"]}
            scope = [{"name": "α", "type": "Type"}, {"name": "a", "type": "α"}, {"name": "b", "type": "α"},
                     {"name": "c", "type": "α"}]
            ws = A.witnesses(scope)
            self.assertIn(["Late", "late0", "late0", "late0"], ws)
        finally:
            A.CARRIERS.clear(); A.CARRIERS.update(old)

    def test_scoring(self):
        self.assertTrue(V.matches("INCONCLUSIVE_DEPENDENT", "INCONCLUSIVE"))
        s = V.score_row({"verdict": "ASSUMPTION_INCOMPARABLE", "expected": "LEAN_STRONGER_BY_ASSUMPTION",
                         "must_not_be": ["ASSUMPTION_INCOMPARABLE"]})
        self.assertTrue(s["unsound"] and s["certified"] and not s["match"])

    def test_shard_partition(self):
        ps = [f"p{i}" for i in range(10)]
        parts = [V._shard(ps, f"{i}/3") for i in range(3)]
        self.assertEqual(sorted(sum(parts, [])), sorted(ps))

    def test_eval_split_frozen_and_wide(self):
        rows = [json.loads(p.read_text()) for p in sorted((BENCH / "mathlib_v12_eval").glob("*.json"))]
        self.assertGreaterEqual(len(rows), 60)
        self.assertGreaterEqual(len({r["domain"] for r in rows} - {"Adversarial"}), 6)
        for r in rows:
            self.assertIn("expected", r); self.assertIn("label_basis", r); self.assertNotIn(r["expected"], r["must_not_be"])
        h = hashlib.sha256()
        for p in sorted((BENCH / "mathlib_v12_eval").glob("*.json")):
            h.update(p.name.encode()); h.update(p.read_bytes())
        self.assertIn(h.hexdigest(), (BENCH / "V12_FREEZE.txt").read_text())


@unittest.skipUnless(shutil.which("lean"), "Lean not on PATH")
class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from proofscope.toolchain import Toolchain
        cls.tc = Toolchain.find()
        cls.out = Path(tempfile.mkdtemp())
        assert A.build(cls.tc, cls.out / "build")["ok"]

    def test_v11_mixed_defect_fixed(self):
        # v1.1: ASSUMPTION_INCOMPARABLE (unsound); 2 ≤ n implies 1 ≤ n
        r = A.run_case({"id": "z", "reference": "∀ (n : Nat), 2 ≤ n → n + 0 = n",
                        "lean": "∀ (n : Nat), 1 ≤ n → n + 0 = n"}, self.tc, self.out / "build", self.out / "z")
        self.assertEqual(r["verdict"], "LEAN_STRONGER_BY_ASSUMPTION")
        self.assertEqual(r["mode"], "mixed")

    def test_mixed_necessity_needs_reference_assumption(self):
        # v1.1: REFERENCE_NEEDS_ASSUMPTION from a witness violating the reference's own 1 ≤ n
        r = A.run_case({"id": "y", "reference": "∀ (n : Nat), 1 ≤ n → n ≠ 0",
                        "lean": "∀ (n : Nat), n = 3 → n ≠ 0"}, self.tc, self.out / "build", self.out / "y")
        self.assertEqual(r["verdict"], "LEAN_WEAKER_BY_ASSUMPTION")


if __name__ == "__main__":
    unittest.main()
