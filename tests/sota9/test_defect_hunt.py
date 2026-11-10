"""Defect hunt: planted defects are certified, true statements and placeholders are not (core Lean)."""
import json
import os
import shutil
import unittest
from pathlib import Path
from tempfile import mkdtemp

from proofscope.defect_hunt import Tactics, grid_alts, split_code, theorem_name

HAVE_LEAN = bool(os.environ.get("PROOFSCOPE_REPL")) and shutil.which("lean") is not None
ROWS = [
    {"id": "true1", "lean_code": "theorem t1 (n : Nat) (h : n > 3) : n * 2 > 7 := sorry"},
    {"id": "false_nat", "lean_code": "theorem t2 (n : Nat) : n - 1 + 1 = n := sorry"},
    {"id": "vacuous", "lean_code": "theorem t3 (a : Int) (h1 : a > 5) (h2 : a < 2) : a = 7 := sorry"},
    {"id": "autobound", "lean_code": "theorem t4 (n : Nat) : n = undefinedThing := sorry"},
    {"id": "placeholder", "lean_code": "abbrev sol : Nat := sorry\ntheorem t5 : sol = 3 := sorry"},
    {"id": "false_int", "lean_code": "theorem t6 (a b : Int) (h : a < b) : a * a < b * b := sorry"},
    {"id": "true_neg", "lean_code": "theorem t8 (n : Nat) : ¬ (n + 1 = 0) := sorry"},
    {"id": "foreign_import", "lean_code": "import Std\ntheorem t7 : True := sorry"},
]


class Pure(unittest.TestCase):
    def test_grid_needs_numeric_binders(self):
        t = Tactics(False)
        self.assertEqual(grid_alts([{"isProp": False, "kind": "other", "bi": "explicit"}], t), [])
        g = grid_alts([{"isProp": False, "kind": "nat", "bi": "explicit"}, {"isProp": True, "kind": "other", "bi": "explicit"}], t)
        self.assertTrue(g[0].startswith("(intro h; refine absurd (@h ((0) : Nat) ?_) ?_"))
        self.assertNotIn("(by ", "".join(g))            # no nested `by`: Lean would log, not throw, its errors

    def test_split_and_name(self):
        self.assertIsNone(split_code("import Std\ntheorem a : True := sorry", True))
        self.assertEqual(theorem_name("lemma foo\n: True := sorry\ntheorem bar (x : Nat) : x = x := sorry"), "bar")


@unittest.skipUnless(HAVE_LEAN, "needs Lean 4.34.1 + PROOFSCOPE_REPL")
class CoreHunt(unittest.TestCase):
    def test_planted(self):
        from proofscope.defect_hunt import run
        out = Path(mkdtemp())
        try:
            s = run([{**r, "source": "test"} for r in ROWS], out, minutes=2, workers=2, mathlib=False)
            found = {f["id"]: f for f in s["verified_findings"]}
            self.assertEqual(set(found), {"false_nat", "vacuous", "autobound", "false_int"})
            self.assertEqual(found["false_nat"]["kind"], "FALSE")
            self.assertEqual(found["vacuous"]["kind"], "VACUOUS")
            self.assertTrue(found["autobound"]["autobound"])
            for f in found.values():
                self.assertTrue(set(f["axioms"]) <= {"propext", "Classical.choice", "Quot.sound"})
                self.assertEqual(f["replay"], "leanchecker OK")
            res = {json.loads(l)["id"]: json.loads(l)["status"] for l in (out / "results.jsonl").read_text().splitlines()}
            self.assertEqual(res["placeholder"], "SKIP_PLACEHOLDER")
            self.assertEqual(res["foreign_import"], "SKIP_IMPORTS")
            self.assertEqual(res["true1"], "NO_DEFECT_FOUND")
            self.assertEqual(res["true_neg"], "NO_DEFECT_FOUND")
        finally:
            shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
