"""SOTA-9 mission B: audits taken straight from a Lean source file, by declaration name."""
import os
import shutil
import unittest
from pathlib import Path
from tempfile import mkdtemp

from proofscope.source_audit import statements

HAVE_LEAN = bool(os.environ.get("PROOFSCOPE_REPL")) and shutil.which("lean") is not None
POSITIVE = {"PROVED_EQUIVALENT", "PROVED_IMPLICATION", "DISPROVED_EQUIVALENCE"}

PAPER = """namespace Foo
variable {α : Type _} (xs : List α)
theorem len_app (ys : List α) : (xs ++ ys).length = xs.length + ys.length := by simp
theorem len_app_swap (ys : List α) : (ys ++ xs).length = xs.length + ys.length := by simp; omega
theorem div_self_any (n : Nat) : n / n = 1 := sorry
theorem div_self_pos (n : Nat) (h : n ≠ 0) : n / n = 1 := Nat.div_self (Nat.pos_of_ne_zero h)
def double (n : Nat) : Nat := 2 * n
def mystery (n : Nat) : Nat := sorry
theorem mystery_pos (n : Nat) : mystery n = mystery n := rfl
theorem mystery_pos' (n : Nat) : mystery n + 0 = mystery n := by simp
end Foo
namespace Bar
theorem len_app : True := trivial
end Bar
"""

CHEAT = """axiom cheat : False
theorem one_eq_one : (1 : Nat) = 1 := rfl
theorem zero_eq_one : (0 : Nat) = 1 := cheat.elim
"""


class Universes(unittest.TestCase):
    def info(self, name, lp):
        return {"name": name, "levelParams": lp}

    def test_monomorphic(self):
        R, C, u, note = statements(self.info("A", []), self.info("B", []))
        self.assertEqual((R, C, u), ("type_of% @A", "type_of% @B", []))

    def test_shared_positional(self):
        R, C, u, note = statements(self.info("A", ["u", "v"]), self.info("B", ["w", "z"]))
        self.assertEqual(R, "type_of% @A.{u_ps1, u_ps2}")
        self.assertEqual(C, "type_of% @B.{u_ps1, u_ps2}")
        self.assertEqual(u, ["universe u_ps1 u_ps2"])

    def test_different_counts_separate(self):
        R, C, u, note = statements(self.info("A", ["u"]), self.info("B", []))
        self.assertEqual((R, C), ("type_of% @A.{u_psr1}", "type_of% @B"))
        self.assertIn("separate", note)


@unittest.skipUnless(HAVE_LEAN, "needs Lean 4.34.1 + PROOFSCOPE_REPL")
class SourceEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from proofscope.source_audit import source_audit
        cls.sa, cls.tmp = staticmethod(source_audit), Path(mkdtemp())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_(self, text, r, c):
        return self.sa(text, r, c, self.tmp / f"{abs(hash((text, r, c)))}")

    def test_variables_and_universes_kept(self):
        rep = self.run_(PAPER, "Foo.len_app", "len_app_swap")
        self.assertEqual(rep["status"], "PROVED_EQUIVALENT")
        self.assertEqual(rep["source"]["universes"], "shared positionally")
        self.assertIn("{α : Type u_1} (xs ys : List α)", rep["statements_display"]["R"])   # `variable`s are binders
        self.assertIn("import PSrc_", rep["certificate_source"])
        self.assertIn("type_of% @Foo.len_app.{u_ps1}", rep["certificate_source"])

    def test_implication_and_sorry_proof_note(self):
        rep = self.run_(PAPER, "div_self_any", "div_self_pos")
        self.assertEqual(rep["status"], "PROVED_IMPLICATION")
        self.assertEqual(rep["unknown"], ["C → R"])
        self.assertTrue(any("uses sorry" in d for d in rep["diagnostics"]))

    def test_statement_over_sorry_definition_flagged(self):
        rep = self.run_(PAPER, "mystery_pos", "mystery_pos'")
        self.assertTrue(any("placeholder definitions" in n for n in rep["not_established"]))

    def test_ambiguous_and_missing_names(self):
        self.assertEqual(self.run_(PAPER, "len_app", "len_app_swap")["status"], "NOT_EVALUABLE")   # Foo.len_app vs Bar.len_app
        self.assertEqual(self.run_(PAPER, "nope", "len_app_swap")["status"], "NOT_EVALUABLE")

    def test_non_proposition_refused(self):
        rep = self.run_(PAPER, "double", "len_app_swap")
        self.assertEqual(rep["status"], "NOT_EVALUABLE")
        self.assertIn("not a proposition", rep["diagnostics"][0])

    def test_compile_error_refused(self):
        rep = self.run_(PAPER + "\ntheorem broken : 1 = 2 := rfl\n", "div_self_any", "div_self_pos")
        self.assertEqual(rep["status"], "NOT_EVALUABLE")

    def test_source_axiom_cannot_certify(self):
        rep = self.run_(CHEAT, "one_eq_one", "zero_eq_one")
        self.assertFalse(any(p["declaration"].endswith(("impl_RC", "equiv")) for p in rep["proved"]))
        self.assertNotIn(rep["status"], {"PROVED_EQUIVALENT"})
        for p in rep["proved"]:
            self.assertNotIn("cheat", p["axioms"])


if __name__ == "__main__":
    unittest.main()
