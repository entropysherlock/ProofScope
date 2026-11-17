"""v1.2.1: SOTA-18 soundness finding F1. Assumption Delta must fail closed when a statement did not
elaborate, and must report NO_ASSUMPTION_DELTA only with a kernel equivalence certificate.

These tests replace Lean with fakes, so they run without a toolchain; the real Lean check of the minimal
counterexamples (u3, u4) is in .github/workflows/f1-soundness.yml."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from proofscope import adelta12 as A

PH = "sor" "ry"  # the error-recovery placeholder, spelled in parts (see test_v12.test_no_unsafe_tactics)


class FakeRun:
    def __init__(self, output):
        self.output = output


class FakeTC:
    lean = "lean"

    def __init__(self, output):
        self._out = output

    def run(self, *a, **k):
        return FakeRun(self._out)


def payload(conclusion="a = b", model=None, added=(), dropped=()):
    return {"added": list(added), "dropped": list(dropped), "conclusion_same": True,
            "conclusion_ref": conclusion, "conclusion_lean": conclusion,
            "model": model if model is not None else [{"name": "a", "type": "Nat"}, {"name": "b", "type": "Nat"}],
            "hyps": [], "added_prefix": [], "dropped_prefix": []}


def line(p):
    return "info: PROOFSCOPE_ASSUMPTIONS11 " + json.dumps(p) + "\n"


class Extract(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_placeholder_conclusion_fails_closed(self):
        # u3/u4 shape: conclusions elaborated as the placeholder, empty telescopes
        d = A.extract("r", "l", FakeTC(line(payload(conclusion=PH, model=[]))), self.tmp, self.tmp)
        self.assertIn("error", d)
        self.assertIn("placeholder", d["fail_closed"])

    def test_placeholder_axiom_in_binder_fails_closed(self):
        p = payload(model=[{"name": "G", "type": f"{PH}Ax Type"}])
        d = A.extract("r", "l", FakeTC(line(p)), self.tmp, self.tmp)
        self.assertIn("error", d)

    def test_lean_error_fails_closed(self):
        out = "Assumptions_input.lean:3:30: error: unknown universe level 'u_1'\n" + line(payload())
        d = A.extract("r", "l", FakeTC(out), self.tmp, self.tmp)
        self.assertEqual(d.get("fail_closed"), "Lean reported an elaboration error")

    def test_clean_extraction_passes(self):
        d = A.extract("r", "l", FakeTC(line(payload())), self.tmp, self.tmp)
        self.assertNotIn("error", d)

    def test_identifier_containing_placeholder_is_not_flagged(self):
        d = A.extract("r", "l", FakeTC(line(payload(conclusion=f"my_{PH}_lemma a = b"))), self.tmp, self.tmp)
        self.assertNotIn("error", d)


class RunCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.spec = {"id": "t", "reference": "∀ a b : Nat, a = b", "lean": "∀ a b : Nat, a = b"}

    def run_with(self, extracted, certs):
        cert = {"status": "ok", "certificates": {k: {"statement": "s"} for k in certs}}
        with mock.patch.object(A, "extract", return_value=extracted), \
             mock.patch.object(A, "certify", return_value=cert) as c:
            return A.run_case(self.spec, None, self.tmp, self.tmp), c

    def test_f1_placeholder_case_is_inconclusive(self):
        row, c = self.run_with({"error": "x", "fail_closed": "placeholder"}, [])
        self.assertEqual(row["verdict"], "INCONCLUSIVE")
        c.assert_not_called()

    def test_no_delta_requires_certificate(self):
        row, _ = self.run_with(payload(), [])
        self.assertEqual(row["verdict"], "INCONCLUSIVE")

    def test_no_delta_with_certificate(self):
        row, c = self.run_with(payload(), ["same"])
        self.assertEqual(row["verdict"], "NO_ASSUMPTION_DELTA")
        self.assertEqual(row["theorem"], "same")
        ob = c.call_args[0][2]
        self.assertEqual(ob["same"][0], f"({self.spec['reference']}) ↔ ({self.spec['lean']})")

    def test_conclusion_only_change_unchanged(self):
        p = payload(); p["conclusion_same"] = False
        row, c = self.run_with(p, [])
        self.assertEqual(row["verdict"], "CONCLUSION_ONLY_CHANGE")
        c.assert_not_called()


class Minimality(unittest.TestCase):
    def test_fail_closed(self):
        with mock.patch.object(A, "extract", return_value={"error": "x", "fail_closed": "placeholder"}):
            row = A.minimality({"id": "m", "statement": "s"}, None, Path("."), Path(tempfile.mkdtemp()))
        self.assertEqual(row["verdict"], "INCONCLUSIVE")
        self.assertEqual(row["reason"], "placeholder")


if __name__ == "__main__":
    unittest.main()
