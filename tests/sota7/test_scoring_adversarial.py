"""SOTA-7: scoring rules and the 20-category adversarial taxonomy stay distinguishable (no Lean needed)."""
import unittest

from bench.sota7.scoring import ERRORS, classify, clopper_pearson

V = {"replay": "VERIFIED"}
G = lambda rel, **k: {"relation": rel, **k}
R = lambda claim, **k: {"claim": {"claim": claim, **k}}


class Rules(unittest.TestCase):
    def test_timeout_is_not_a_negative(self):
        self.assertEqual(classify(R("RESOURCE_EXHAUSTED"), {}, G("REF_STRONGER")), "RESOURCE_EXHAUSTED")

    def test_unverified_certificate_is_not_certified(self):
        for rep in ({}, {"replay": "REJECTED"}, {"replay": "NO_CERTIFICATE"}, {"replay": "NO_DECISIVE_DECLARATION"}):
            self.assertEqual(classify(R("NOT_EQUIVALENT_CLOSED", closed_truth={"reference": "FALSE", "candidate": "TRUE"}), rep,
                                      G("REF_STRONGER")), "INVALID_CERTIFICATE")

    def test_abstention_is_not_negative(self):
        self.assertEqual(classify(R("ABSTAIN"), V, G("EQUIVALENT")), "ABSTAIN")

    def test_unresolved_gold_scored_apart(self):
        self.assertEqual(classify(R("EQUIVALENT_CLOSED", basis="both_true"), V, G("UNRESOLVED")), "GOLD_UNRESOLVED")

    def test_closed_equivalence_never_counts_as_formulation_correct(self):
        both_true = R("EQUIVALENT_CLOSED", basis="both_true")
        self.assertEqual(classify(both_true, V, G("NOT_EQUIVALENT", closed_truth={"reference": "TRUE", "candidate": "TRUE"})), "CLOSED_ONLY_AGREEMENT")
        self.assertEqual(classify(both_true, V, G("NOT_EQUIVALENT")), "CLOSED_ONLY_UNCHECKED")
        self.assertEqual(classify(both_true, V, G("NOT_EQUIVALENT", closed_truth={"reference": "FALSE", "candidate": "TRUE"})), "INCORRECT")
        self.assertEqual(classify(R("EQUIVALENT_CLOSED", basis="definitional"), V, G("INCOMPARABLE")), "INCORRECT")

    def test_difference_against_equivalent_gold_is_error(self):
        self.assertEqual(classify(R("NOT_EQUIVALENT_CLOSED", closed_truth={"reference": "FALSE", "candidate": "TRUE"}), V, G("EQUIVALENT")), "INCORRECT")

    def test_repair_rules(self):
        mr = R("MINIMAL_REPAIR", repairs=[[0], [1]], minimal_cost=1)
        self.assertEqual(classify(mr, V, G("REF_STRONGER", intended_repairs=[[1]])), "CORRECT")
        self.assertEqual(classify(mr, V, G("REF_STRONGER", intended_repairs=[[2]])), "REPAIR_MISMATCH")
        self.assertEqual(classify(mr, V, G("REF_STRONGER", intended_repairs="NONE_IN_GRAMMAR")), "INCORRECT")
        self.assertEqual(classify(R("MINIMAL_REPAIR", repairs=[[0, 1]], minimal_cost=2), V,
                                  G("REF_STRONGER", intended_repairs=[[3]])), "MINIMALITY_CONFLICT")
        self.assertEqual(classify(R("NO_REPAIR_IN_GRAMMAR"), V, G("REF_STRONGER", intended_repairs=[[0]])), "INCORRECT")

    def test_clopper_pearson(self):
        self.assertEqual(clopper_pearson(0, 10), [0.0, 0.3085])
        self.assertEqual(clopper_pearson(0, 50)[1], 0.0711)
        self.assertIsNone(clopper_pearson(0, 0))


# category -> (record, replay, gold, expected class)
NE = {"reference": "FALSE", "candidate": "TRUE"}
TAXONOMY = {
    1: ("both true, unrelated", R("EQUIVALENT_CLOSED", basis="both_true"), V, G("NOT_EQUIVALENT", closed_truth={"reference": "TRUE", "candidate": "TRUE"}), "CLOSED_ONLY_AGREEMENT"),
    2: ("both false", R("EQUIVALENT_CLOSED", basis="both_false"), V, G("INCOMPARABLE", closed_truth={"reference": "FALSE", "candidate": "FALSE"}), "CLOSED_ONLY_AGREEMENT"),
    3: ("vacuous implication", R("EQUIVALENT_CLOSED", basis="both_true"), V, G("EQUIVALENT"), "CORRECT"),
    4: ("ℕ vs ℤ semantics", R("NOT_EQUIVALENT_CLOSED", closed_truth=NE), V, G("REF_STRONGER", closed_truth=NE), "CORRECT"),
    5: ("missing nonzero", R("ABSTAIN"), {}, G("REF_STRONGER"), "ABSTAIN"),
    6: ("coercion target lost", R("INPUT_NOT_EVALUABLE"), {}, G("REF_STRONGER"), "INPUT_NOT_EVALUABLE"),
    7: ("typeclass change", R("NOT_EQUIVALENT_CLOSED", closed_truth=NE), V, G("EQUIVALENT"), "INCORRECT"),
    8: ("hidden implicit variable", R("EQUIVALENT_CLOSED", basis="definitional"), V, G("NOT_EQUIVALENT"), "INCORRECT"),
    9: ("dropped dependent binder", R("NOT_EQUIVALENT_CLOSED", closed_truth=NE), V, G("REF_STRONGER"), "CORRECT"),
    10: ("quantifier reorder", R("NOT_EQUIVALENT_CLOSED", closed_truth={"reference": "TRUE", "candidate": "FALSE"}), V, G("CAND_STRONGER"), "CORRECT"),
    11: ("changed algebraic law", R("NOT_EQUIVALENT_CLOSED", closed_truth={"reference": "TRUE", "candidate": "FALSE"}), V, G("CAND_STRONGER", closed_truth={"reference": "FALSE", "candidate": "TRUE"}), "INCORRECT"),
    12: ("inconsistent background", R("EQUIVALENT_CLOSED", basis="both_true"), V, G("UNRESOLVED"), "GOLD_UNRESOLVED"),
    13: ("countermodel violates hypotheses", R("NOT_EQUIVALENT_CLOSED", closed_truth=NE), {"replay": "REJECTED"}, G("REF_STRONGER"), "INVALID_CERTIFICATE"),
    14: ("valid but nonminimal repair", R("MINIMAL_REPAIR", repairs=[[0, 1]], minimal_cost=2), V, G("REF_STRONGER", intended_repairs=[[0]]), "MINIMALITY_CONFLICT"),
    15: ("multiple minimal repairs", R("MINIMAL_REPAIR", repairs=[[0], [1]], minimal_cost=1), V, G("REF_STRONGER", intended_repairs=[[1]]), "CORRECT"),
    16: ("unresolved relationship", R("ABSTAIN"), {}, G("UNRESOLVED"), "ABSTAIN"),
    17: ("parse/elaboration failure", R("INPUT_NOT_EVALUABLE"), {}, G("EQUIVALENT"), "INPUT_NOT_EVALUABLE"),
    18: ("resource exhaustion", R("RESOURCE_EXHAUSTED"), {}, G("REF_STRONGER"), "RESOURCE_EXHAUSTED"),
    19: ("kernel verification failure", R("MINIMAL_REPAIR", repairs=[[0]], minimal_cost=1), {"replay": "REJECTED"}, G("REF_STRONGER", intended_repairs=[[0]]), "INVALID_CERTIFICATE"),
    20: ("source-to-certificate linkage", R("NOT_EQUIVALENT_CLOSED", closed_truth=NE), {"replay": "REJECTED", "reason": "source identity"}, G("REF_STRONGER"), "INVALID_CERTIFICATE"),
}


class Taxonomy(unittest.TestCase):
    def test_every_category_gets_its_class(self):
        for k, (name, rec, rep, gold, want) in TAXONOMY.items():
            with self.subTest(category=k, name=name):
                self.assertEqual(classify(rec, rep, gold), want)

    def test_failure_classes_are_distinguishable_and_never_success_or_negative(self):
        cls = {k: classify(r, p, g) for k, (_, r, p, g, _) in TAXONOMY.items()}
        for k in (5, 6, 13, 16, 17, 18, 19, 20):
            self.assertNotEqual(cls[k], "CORRECT")
            self.assertNotIn(cls[k], ERRORS)        # not counted as a mathematical verdict against the engine either
        self.assertEqual(len({cls[18], cls[6], cls[19], cls[5], cls[12]}), 5)


if __name__ == "__main__":
    unittest.main()
