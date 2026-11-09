"""SOTA-4 Task K: the labelling pipeline refuses to weaken independence. Synthetic reviewer ids only;
no real labels are created by these tests."""
import unittest

from bench.pilot import labels as P

CASES = [{"case_id": f"c{i}", "ref_decl": "theorem a : True := sorry", "cand_decl": "theorem b : True := sorry",
          "source_label": "SECRET", "system_output": "SECRET"} for i in range(4)]
IDS = {c["case_id"] for c in CASES}


def lab(rev, a, b):
    return [{"case_id": f"c{i}", "reviewer": rev, "track_A": a[i], "track_B": b[i], "rationale": "r", "minutes_spent": 3}
            for i in range(4)]


class Pilot(unittest.TestCase):
    def test_packets_are_blind_and_independently_ordered(self):
        pk = P.packets(CASES, ["rev1", "rev2"], {"rev1": 1, "rev2": 2})
        for rows in pk.values():
            for r in rows:
                self.assertNotIn("source_label", r)
                self.assertNotIn("system_output", r)
        self.assertEqual(sorted(r["case_id"] for r in pk["rev1"]), sorted(IDS))

    def test_missing_track_b_is_rejected(self):
        l = lab("rev1", ["EQUIVALENT"] * 4, ["FAITHFUL"] * 4)
        del l[0]["track_B"]
        with self.assertRaises(P.LabelError):
            P.validate(l, IDS, "rev1")

    def test_incomplete_label_set_is_rejected(self):
        with self.assertRaises(P.LabelError):
            P.validate(lab("rev1", ["EQUIVALENT"] * 4, ["FAITHFUL"] * 4)[:3], IDS, "rev1")

    def test_conflicted_or_repeated_participants_are_rejected(self):
        l1 = lab("rev1", ["EQUIVALENT"] * 4, ["FAITHFUL"] * 4)
        l2 = lab("rev2", ["EQUIVALENT"] * 4, ["FAITHFUL"] * 4)
        with self.assertRaises(P.LabelError):
            P.finalize(l1, l2, [], {"rev2"}, "adj")
        with self.assertRaises(P.LabelError):
            P.finalize(l1, l2, [], set(), "rev1")

    def test_disagreement_and_unsure_need_adjudication(self):
        l1 = lab("rev1", ["EQUIVALENT", "EQUIVALENT", "UNSURE", "NOT_EQUIVALENT"], ["FAITHFUL"] * 4)
        l2 = lab("rev2", ["EQUIVALENT", "NOT_EQUIVALENT", "UNSURE", "NOT_EQUIVALENT"], ["FAITHFUL"] * 4)
        q = P.agree(l1, l2)["adjudication_queue"]
        self.assertEqual([x["case_id"] for x in q], ["c1", "c2"])
        gold = {g["case_id"]: g for g in P.finalize(l1, l2, [{"case_id": "c1", "track": "track_A", "label": "NOT_EQUIVALENT", "adjudicator": "adj"}], set(), "adj")}
        self.assertEqual(gold["c0"]["track_A"], "EQUIVALENT")
        self.assertEqual(gold["c1"]["track_A_basis"], "adjudicated")
        self.assertEqual(gold["c2"]["track_A"], "UNRESOLVED")

    def test_track_b_is_never_inferred_from_track_a(self):
        l1 = lab("rev1", ["EQUIVALENT"] * 4, ["UNSURE"] * 4)
        l2 = lab("rev2", ["EQUIVALENT"] * 4, ["UNSURE"] * 4)
        for g in P.finalize(l1, l2, [], set(), "adj"):
            self.assertEqual(g["track_A"], "EQUIVALENT")
            self.assertEqual(g["track_B"], "UNRESOLVED")

    def test_kappa(self):
        self.assertAlmostEqual(P.kappa(["a", "a", "b", "b"], ["a", "a", "b", "b"]), 1.0)
        self.assertAlmostEqual(P.kappa(["a", "b", "a", "b"], ["b", "a", "b", "a"]), -1.0)


if __name__ == "__main__":
    unittest.main()
