import unittest
from proofscope.strength import inspect, bound

def case(lean, ref, ty="Nat"):
    return {"id": "test", "binders": [["n", ty]], "lean_hyp": "True",
            "ref_hyp": "True", "lean_concl": lean, "ref_concl": ref}

class StrengthTests(unittest.TestCase):
    def test_weaker(self):
        r = inspect(case("n ≤ 2 ^ n", "n < 2 ^ n"))
        self.assertEqual(r["status"], "LEAN_WEAKER_BOUND_SCHEMA")
        self.assertEqual(len(r["lean_certificates"]), 2)
        self.assertIn("NOT concrete theorem strictness", r["certificate_scope"])

    def test_stronger(self):
        self.assertEqual(inspect(case("n < 2 ^ n", "n ≤ 2 ^ n"))["status"],
                         "LEAN_STRONGER_BOUND_SCHEMA")

    def test_reverse_order(self):
        self.assertEqual(inspect(case("n ≥ 2", "n > 2"))["status"],
                         "LEAN_WEAKER_BOUND_SCHEMA")

    def test_changed_constants(self):
        r = inspect(case("n ≤ 3 * n", "n ≤ 2 * n"))
        self.assertEqual(r["status"], "BOUND_EXPRESSION_CHANGED")
        self.assertFalse(r["lean_certificates"])

    def test_same_comparison(self):
        self.assertEqual(inspect(case("(n + 1) ≤ (2 * n)", "(n + 1) ≤ (2 * n)"))["status"],
                         "SAME_BOUND_FORM")

    def test_unrelated_truths(self):
        self.assertEqual(inspect(case("n + 0 = n", "n * 1 = n"))["status"], "NOT_ANALYZED")

    def test_different_hypotheses(self):
        s = case("n ≤ 3", "n < 3")
        s["ref_hyp"] = "0 < n"
        self.assertEqual(inspect(s)["status"], "NOT_ANALYZED")

    def test_no_claim_about_int(self):
        self.assertEqual(inspect(case("n ≤ 3", "n < 3", "Int"))["status"], "NOT_ANALYZED")

    def test_malformed(self):
        self.assertIsNone(bound("(n ≤ 2"))
        self.assertIsNone(bound("n ≤ 2 < 3"))
        self.assertIsNone(bound("n ≤ (2"))

    def test_digest_changes(self):
        a = inspect(case("n ≤ 3", "n < 3"))["spec_sha256"]
        b = inspect(case("n ≤ 4", "n < 3"))["spec_sha256"]
        self.assertNotEqual(a, b)

if __name__ == "__main__":
    unittest.main()
