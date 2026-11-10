"""SOTA-9: the report layer never fabricates or upgrades a verdict.

Unit tests need no Lean. The end-to-end tests run only when PROOFSCOPE_REPL and `lean` are available.
"""
import json
import os
import shutil
import threading
import unittest
import urllib.request
from pathlib import Path
from tempfile import mkdtemp

from proofscope.auditor import report_from_row, markdown, _hints

C = lambda k: {"declaration": f"NS.{k}", "statement": "…", "axioms": []}
POSITIVE = {"PROVED_EQUIVALENT", "PROVED_IMPLICATION", "DISPROVED_EQUIVALENCE"}


class ReportMapping(unittest.TestCase):
    def test_mutual_derivation(self):
        r = report_from_row({"verdict": "CERTIFIED_LOGICAL_EQUIVALENCE", "direction": "mutual_derivation",
                             "certificates": {k: C(k) for k in ("wf_R", "wf_C", "impl_RC", "impl_CR", "equiv")}})
        self.assertEqual(r["status"], "PROVED_EQUIVALENT")
        self.assertEqual(len(r["proved"]), 3)                      # wf_ hidden
        self.assertTrue(any("closed propositions" in x for x in r["not_established"]))

    def test_implication_keeps_converse_unknown(self):
        for d, k, conv in (("reference_implies_candidate", "impl_RC", "C → R"), ("candidate_implies_reference", "impl_CR", "R → C")):
            r = report_from_row({"verdict": "CERTIFIED_IMPLICATION", "direction": d, "certificates": {k: C(k)}})
            self.assertEqual(r["status"], "PROVED_IMPLICATION")
            self.assertEqual(r["unknown"], [conv])

    def test_difference(self):
        r = report_from_row({"verdict": "CERTIFIED_LOGICAL_DIFFERENCE", "direction": "reference_false_formalization_true",
                             "certificates": {"diff_RL": C("diff_RL")}, "witnesses": {"wit_R": {"n": 0}}})
        self.assertEqual(r["status"], "DISPROVED_EQUIVALENCE")
        self.assertEqual(r["counterexample"], {"n": 0})

    def test_abstain_is_unknown_never_positive(self):
        for row in ({"verdict": "ABSTAIN"}, {"verdict": "INCONCLUSIVE", "reason": "timeout"}, {"verdict": "RESOURCE_EXHAUSTED"},
                    {}, {"verdict": "CERTIFIED_SOMETHING_NEW", "certificates": {"equiv": C("equiv")}}):
            r = report_from_row(row)
            self.assertEqual(r["status"], "UNKNOWN", row)
            self.assertTrue(any("not evidence of difference" in u for u in r["unknown"]))

    def test_verdict_without_certificate_is_downgraded(self):
        cases = [("CERTIFIED_LOGICAL_EQUIVALENCE", "mutual_derivation", {"impl_RC": C("impl_RC")}),
                 ("CERTIFIED_IMPLICATION", "reference_implies_candidate", {"impl_CR": C("impl_CR")}),   # wrong direction
                 ("CERTIFIED_LOGICAL_DIFFERENCE", "reference_true_formalization_false", {}),
                 ("CERTIFIED_LOGICAL_EQUIVALENCE", None, {"equiv": C("equiv")})]
        for v, d, certs in cases:
            r = report_from_row({"verdict": v, "direction": d, "certificates": certs})
            self.assertEqual(r["status"], "UNKNOWN", (v, d))
            self.assertTrue(any("shown as UNKNOWN" in x for x in r["diagnostics"]))
            self.assertFalse(any(p["declaration"].split(".")[-1].startswith(("equiv", "impl_", "diff_")) for p in r["proved"]))

    def test_partial_facts_stay_visible_without_relation(self):
        r = report_from_row({"verdict": "ABSTAIN", "certificates": {"true_R": C("true_R")}})
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertEqual([p["meaning"] for p in r["proved"]], ["R is true"])

    def test_inconsistent_is_surfaced(self):
        r = report_from_row({"verdict": "INCONSISTENT", "reason": "x", "certificates": {"equiv_defeq": C("equiv_defeq")}})
        self.assertEqual(r["status"], "ENGINE_INCONSISTENT")
        self.assertEqual(r["proved"], [])

    def test_extraction_failure_hints_not_applied(self):
        r = report_from_row({"verdict": "INCONCLUSIVE", "failure_class": "EXTRACTION", "reason": "extraction failed",
                             "detail": "Unknown identifier `Tendsto`"})
        self.assertEqual(r["status"], "NOT_EVALUABLE")
        self.assertTrue(r["hints"] and all(h["applied"] is False for h in r["hints"]))
        self.assertIn("Filter", r["hints"][0]["suggestion"])

    def test_cjcs_extraction_failure_after_delta_ok_is_unknown(self):
        r = report_from_row({"verdict": "INCONCLUSIVE", "failure_class": "EXTRACTION", "reason": "extraction failed",
                             "delta": {"status": "OK"}})
        self.assertEqual(r["status"], "UNKNOWN")

    def test_markdown_shows_status(self):
        r = report_from_row({"verdict": "ABSTAIN"}); r.update(inputs={"reference": "A", "candidate": "B", "preamble": [], "imports": []})
        md = markdown(r)
        self.assertIn("UNKNOWN", md)
        self.assertNotIn("PROVED", md)

    def test_hints_on_free_text(self):
        self.assertEqual(_hints("no problem here"), [])


HAVE_LEAN = bool(os.environ.get("PROOFSCOPE_REPL")) and shutil.which("lean") is not None


@unittest.skipUnless(HAVE_LEAN, "needs Lean 4.34.1 + PROOFSCOPE_REPL")
class EndToEndCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from proofscope.auditor import audit
        cls.audit, cls.tmp = staticmethod(audit), Path(mkdtemp())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_(self, r, c, pre=None):
        return self.audit(r, c, pre, self.tmp / str(abs(hash((r, c, str(pre))))))

    def test_division_one_way(self):
        rep = self.run_("∀ (n : Nat), n / n = 1", "∀ (n : Nat), n ≠ 0 → n / n = 1")
        self.assertEqual(rep["status"], "PROVED_IMPLICATION")
        self.assertEqual(rep["unknown"], ["C → R"])
        self.assertTrue(rep["certificate_source"])

    def test_free_identifier_not_evaluable(self):
        rep = self.run_("∀ (n : Nat), succ n ≠ 0", "∀ (n : Nat), n + 1 ≠ 0")
        self.assertEqual(rep["status"], "NOT_EVALUABLE")
        self.assertTrue(any(h["unknown"] == "succ" and not h["applied"] for h in rep["hints"]))

    def test_preamble_makes_it_evaluable_without_rewriting(self):
        rep = self.run_("∀ (n : Nat), succ n ≠ 0", "∀ (n : Nat), n + 1 ≠ 0", ["open Nat"])
        self.assertIn(rep["status"], POSITIVE | {"UNKNOWN"})
        self.assertEqual(rep["inputs"]["reference"], "∀ (n : Nat), succ n ≠ 0")   # input never rewritten

    def test_malicious_preamble_rejected(self):
        rep = self.run_("True", "True", ["axiom cheat : False"])
        self.assertEqual(rep["status"], "NOT_EVALUABLE")

    def test_false_vs_true_not_equivalent(self):
        rep = self.run_("∀ (n : Nat), n + 1 = n", "∀ (n : Nat), n + 0 = n")
        self.assertNotEqual(rep["status"], "PROVED_EQUIVALENT")


@unittest.skipUnless(HAVE_LEAN, "needs Lean 4.34.1 + PROOFSCOPE_REPL")
class UIServer(unittest.TestCase):
    def test_http_roundtrip(self):
        from http.server import ThreadingHTTPServer
        from proofscope import ui
        ui.Handler.out_dir = Path(mkdtemp()); self.addCleanup(shutil.rmtree, ui.Handler.out_dir, True)
        srv = ThreadingHTTPServer(("127.0.0.1", 0), ui.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            self.assertIn("ProofScope", urllib.request.urlopen(base).read().decode())
            body = json.dumps({"reference": "∀ (n : Nat), n + 0 = n", "candidate": "∀ (m : Nat), m = m + 0"}).encode()
            rep = json.loads(urllib.request.urlopen(urllib.request.Request(base + "/audit", body, method="POST")).read())
            self.assertEqual(rep["status"], "PROVED_EQUIVALENT")
            self.assertNotIn("engine_row", rep)
            body = json.dumps({"source": "theorem a (n : Nat) : n + 0 = n := rfl\ntheorem b (m : Nat) : m = m + 0 := rfl\n",
                               "ref": "a", "cand": "b"}).encode()
            rep = json.loads(urllib.request.urlopen(urllib.request.Request(base + "/audit_source", body, method="POST")).read())
            self.assertEqual(rep["status"], "PROVED_EQUIVALENT")
            self.assertIn("a : ∀ (n : Nat), n + 0 = n", rep["statements_display"]["R"])
            bad = json.loads(urllib.request.urlopen(urllib.request.Request(base + "/audit", b"{not json", method="POST")).read())
            self.assertEqual(bad["status"], "ERROR")
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
