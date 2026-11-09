"""v1.1: dependent-structure linking (instance binders), minimality classes, hostile regressions."""
import shutil
import tempfile
import unittest
from pathlib import Path

from proofscope import adelta11 as A


class Unit(unittest.TestCase):
    def test_instance_binders_are_redeclared_as_instances(self):
        m = [{"name": "α", "type": "Type", "inst": False}, {"name": "i1", "type": "Mul α", "inst": True}]
        self.assertEqual(A.binders(m), "(α : Type) [i1 : Mul α]")
        self.assertEqual(A.binders(m, True), "(α : Type) (i1 : Mul α)")

    def test_instance_pool_builds_structures(self):
        self.assertIn("⟨fun a _ => a⟩", A._pool_for("Mul Bool", "Bool"))


@unittest.skipUnless(shutil.which("lean"), "Lean not on PATH")
class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from proofscope.toolchain import Toolchain
        cls.tc = Toolchain.find()
        cls.out = Path(tempfile.mkdtemp())
        assert A.build(cls.tc, cls.out / "build")["ok"]

    def test_shared_instance_binder_links(self):
        # the core-Lean reproduction of the Mathlib m04 linking failure
        r = A.run_case({"id": "l", "reference": "∀ (α : Type) [Mul α] (a : α), a * a = a * a",
                        "lean": "∀ (α : Type) [Mul α], (∀ (x y : α), x * y = y * x) → ∀ (a : α), a * a = a * a"},
                       self.tc, self.out / "build", self.out / "l")
        self.assertEqual(r["verdict"], "LEAN_WEAKER_BY_ASSUMPTION")
        self.assertEqual(r["assumptions"][0]["witness_model"][0], "Bool")

    def test_substitutable_assumptions(self):
        r = A.minimality({"id": "s", "statement": "∀ (n : Nat), n ≠ 0 → 0 < n → 1 ≤ n"},
                         self.tc, self.out / "build", self.out / "s")
        self.assertEqual(r["verdict"], "HAS_REDUNDANT_ASSUMPTIONS")
        self.assertEqual(r["jointly_necessary_pairs"], [[0, 1]])


if __name__ == "__main__":
    unittest.main()
