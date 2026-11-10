"""SOTA-5: relation records never overstate a certificate (hostile item 15, misleading labels)."""
import unittest

from proofscope.experimental.relations import describe


def row(certs, **kw):
    return {"reference": "X", "lean": "Y", "certificates": {k: {"declaration": k, "statement": "s", "axioms": []} for k in certs}, **kw}


class Relations(unittest.TestCase):
    def test_both_true_is_reported_as_closed_only(self):
        r = describe(row(["true_R", "true_L", "equiv_both_true"]))
        self.assertEqual(r["relation"], "CLOSED_EQUIVALENCE_BOTH_TRUE")
        self.assertIn("unrelated theorems", r["does_not_establish"])

    def test_both_false_mentions_hidden_strength(self):
        self.assertIn("strict strength", describe(row(["equiv_both_false"]))["does_not_establish"])

    def test_abstention_and_partial_are_not_negative(self):
        r = describe(row(["true_R", "link_L"]))
        self.assertEqual(r["relation"], "NOT_CERTIFIED")
        self.assertIn("never a negative result", r["does_not_establish"])

    def test_difference_carries_witness(self):
        r = describe(row(["diff_RL"], witnesses={"wit_R": ["0"]}))
        self.assertEqual((r["relation"], r["witness"]), ("CLOSED_DIFFERENCE", ["0"]))

    def test_contradictory_certificates_flagged(self):
        self.assertEqual(describe(row(["equiv_defeq", "diff_RL"]))["relation"], "INCONSISTENT_REPORT")


if __name__ == "__main__":
    unittest.main()
