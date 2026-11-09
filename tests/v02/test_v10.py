"""v1.0: Assumption Delta (soundness of the model scope) and boundary witness synthesis."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from proofscope import adelta as A


class Unit(unittest.TestCase):
    def test_witnesses_pick_carrier_then_operations(self):
        ws = A.witnesses([{"name": "α", "type": "Type"}, {"name": "op", "type": "α → α → α"}])
        self.assertIn(["Bool", "fun a _ => a"], ws)
        self.assertIn(["Empty", "fun a _ => a"], ws)

    def test_no_nested_by(self):
        self.assertFalse(any("(by " in t for t in A.sep_tactics([{"name": "α", "type": "Type"}], 0)))


@unittest.skipUnless(shutil.which("lean"), "Lean not on PATH")
class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from proofscope.toolchain import Toolchain
        cls.tc = Toolchain.find()
        cls.out = Path(tempfile.mkdtemp())
        assert A.build(cls.tc, cls.out / "build")["ok"]

    def run_spec(self, i, r, l):
        return A.run_case({"id": i, "reference": r, "lean": l}, self.tc, self.out / "build", self.out / i)

    def test_hidden_commutativity_is_restrictive_with_model(self):
        asc = "∀ (a b c : α), op (op a b) c = op a (op b c)"
        r = self.run_spec("comm", f"∀ (α : Type) (op : α → α → α), ({asc}) → ∀ (a : α), op a a = op a a",
                          f"∀ (α : Type) (op : α → α → α) [Std.Commutative op], ({asc}) → ∀ (a : α), op a a = op a a")
        self.assertEqual(r["verdict"], "LEAN_WEAKER_BY_ASSUMPTION")
        self.assertEqual(r["assumptions"][0]["witness_model"][:2], ["Bool", "fun (a x : Bool) => a"])

    def test_point_binder_makes_nonempty_redundant(self):
        # regression for the v1.0 block-1 soundness bug (adversarial x01)
        r = self.run_spec("x01", "∀ (α : Type) (x : α), x = x", "∀ (α : Type) (x : α) [Nonempty α], x = x")
        self.assertEqual(r["verdict"], "ASSUMPTION_EQUIVALENT")


if __name__ == "__main__":
    unittest.main()
