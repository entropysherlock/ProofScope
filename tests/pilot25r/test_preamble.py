"""PS-25R: source-header preamble (open / universe lines) for the CJCS engine. Core Lean; needs PROOFSCOPE_REPL."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from proofscope.experimental import cjcs4 as E
from proofscope.toolchain import Toolchain

HAVE = bool(shutil.which("lean") and shutil.which("leanchecker") and os.environ.get("PROOFSCOPE_REPL")) \
    and not os.environ.get("PROOFSCOPE_IMPORTS")
SPEC = {"id": "pre", "reference": "∀ (n : Nat), succ n ≠ 0", "lean": "∀ (n : Nat), n + 1 ≠ 0"}


@unittest.skipUnless(HAVE, "Lean 4.34.1, leanchecker, PROOFSCOPE_REPL (core mode)")
class Preamble(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = Path(tempfile.mkdtemp())
        cls.tc = Toolchain.find()
        assert E.build(cls.tc, cls.t / "b")["ok"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.t)

    def run_with(self, pre, name, spec=SPEC):
        old = os.environ.get("PROOFSCOPE_PREAMBLE")
        if pre is None:
            os.environ.pop("PROOFSCOPE_PREAMBLE", None)
        else:
            os.environ["PROOFSCOPE_PREAMBLE"] = pre
        try:
            return E.run_case(spec, self.tc, self.t / "b", self.t / name)
        finally:
            if old is None:
                os.environ.pop("PROOFSCOPE_PREAMBLE", None)
            else:
                os.environ["PROOFSCOPE_PREAMBLE"] = old

    def test_without_source_context_the_case_is_not_evaluable(self):
        """Reproduces the Pilot-25 failure class: an identifier that needs an `open`."""
        row = self.run_with(None, "a")
        self.assertEqual(row["verdict"], "INCONCLUSIVE")
        self.assertEqual(row["failure_class"], "EXTRACTION")

    def test_with_source_context_the_case_is_evaluated_and_certified(self):
        row = self.run_with("open Nat", "b")
        self.assertEqual(row["verdict"], "CERTIFIED_LOGICAL_EQUIVALENCE")
        self.assertIn("open Nat\n", row["certificate_source"])          # the certificate states the same context

    def test_universe_line_allowed(self):
        row = self.run_with("universe u", "c", {"id": "u", "reference": "∀ (X : Type u) (x : X), x = x",
                                                 "lean": "∀ (X : Type u) (x : X), x = x"})
        self.assertEqual(row["verdict"], "CERTIFIED_LOGICAL_EQUIVALENCE")

    def test_meaning_changing_lines_refused(self):
        for bad in ("axiom cheat : False", "variable (n : Nat)", "set_option autoImplicit true", "open Nat in",
                    "notation \"succ\" => Nat.zero", "open Nat\ndef succ := 0"):
            with self.subTest(bad=bad):
                row = self.run_with(bad, "d")
                self.assertEqual(row["verdict"], "INCONCLUSIVE")
                self.assertIn("not allowed", row["reason"])


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(HAVE, "Lean 4.34.1, leanchecker, PROOFSCOPE_REPL (core mode)")
class NoMetaNamespaceLeak(unittest.TestCase):
    def test_lean_meta_names_do_not_resolve_in_user_statements(self):
        """PS-25R bug: `open Lean Elab Command` in the search source used to make `Name` mean `Lean.Name`."""
        t = Path(tempfile.mkdtemp())
        try:
            tc = Toolchain.find()
            assert E.build(tc, t / "b")["ok"]
            os.environ.pop("PROOFSCOPE_PREAMBLE", None)
            row = E.run_case({"id": "leak", "reference": "∀ (x : Name), x = x", "lean": "∀ (x : Name), x = x"},
                             tc, t / "b", t / "w")
            self.assertEqual((row["verdict"], row["failure_class"]), ("INCONCLUSIVE", "EXTRACTION"))
        finally:
            shutil.rmtree(t)
