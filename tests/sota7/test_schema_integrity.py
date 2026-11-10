"""SOTA-7: case schema, label-leak rejection, frozen-manifest integrity (no Lean needed)."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from bench.sota7 import blind as B
from bench.sota7 import schema as S

SYN = Path(__file__).resolve().parents[2] / "bench/sota7/synthetic"
BUD = {"relation": {"cpu_s": 60, "mem_mb": 4000, "wall_s": 200}, "repair": {"cpu_s": 60, "mem_mb": 4000, "wall_s": 200}}


def first_case():
    return json.loads(sorted((SYN / "public").glob("*.json"))[0].read_text())


class Schema(unittest.TestCase):
    def test_synthetic_cases_valid(self):
        cases = B.load_public(SYN / "public")
        B.load_gold(SYN / "gold.jsonl", cases)

    def test_label_wording_in_metadata_rejected(self):
        c = first_case()
        for field, val in (("domain", "algebra (non-equivalent pair)"), ("difficulty", "expected stronger")):
            d = copy.deepcopy(c); d[field] = val
            with self.assertRaises(S.SchemaError):
                S.validate_public(d)
        d = copy.deepcopy(c); d["provenance"]["source"] = "gold: faithful"
        with self.assertRaises(S.SchemaError):
            S.validate_public(d)

    def test_extra_public_field_rejected(self):
        d = first_case(); d["expected"] = "EQUIVALENT"
        with self.assertRaisesRegex(S.SchemaError, "not allowed"):
            S.validate_public(d)

    def test_revealing_case_id_rejected(self):
        d = first_case(); d["case_id"] = "d03_nat_sub_cast"
        with self.assertRaisesRegex(S.SchemaError, "opaque"):
            S.validate_public(d)

    def test_independent_gold_needs_two_reviewers_with_reasons(self):
        g = {"schema": S.SCHEMA, "case_id": "c" + "0" * 12, "relation": "EQUIVALENT", "adjudication": "AGREED",
             "labeler_class": "INDEPENDENT", "reviewers": ["r1"], "rationales": ["ok"]}
        with self.assertRaises(S.SchemaError):
            S.validate_gold(g, "relation")
        g.update(reviewers=["r1", "r2"], rationales=["ok", ""])
        with self.assertRaises(S.SchemaError):
            S.validate_gold(g, "relation")
        g.update(rationales=["proof", "proof"])
        S.validate_gold(g, "relation")

    def test_synthetic_cannot_pose_as_independent(self):
        g = {"schema": S.SCHEMA, "case_id": "c" + "0" * 12, "relation": "EQUIVALENT", "adjudication": "SYNTHETIC_DEVELOPMENT",
             "labeler_class": "INDEPENDENT", "reviewers": ["a", "b"], "rationales": ["x", "y"]}
        with self.assertRaises(S.SchemaError):
            S.validate_gold(g, "relation")


class Integrity(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        shutil.copytree(SYN, self.t / "syn")
        self.pub, self.gold, self.m = self.t / "syn/public", self.t / "syn/gold.jsonl", self.t / "m.json"
        B.freeze(self.pub, self.gold, self.m, dataset_version="t", selection_protocol="t", review_protocol="t",
                 repo=self.t, toolchain={}, budgets=BUD)

    def tearDown(self):
        shutil.rmtree(self.t)

    def test_verifies(self):
        B.verify_manifest(self.m, self.pub, self.gold)

    def test_input_change_rejected(self):
        f = sorted(self.pub.glob("*.json"))[0]
        d = json.loads(f.read_text()); d["candidate"]["lean"] += " "
        f.write_text(json.dumps(d))
        with self.assertRaisesRegex(B.IntegrityBreach, "input digest"):
            B.verify_manifest(self.m, self.pub)

    def test_whitespace_reformat_accepted(self):
        f = sorted(self.pub.glob("*.json"))[0]
        f.write_bytes(json.dumps(json.loads(f.read_text()), indent=4, ensure_ascii=False).replace("\n", "\r\n").encode())
        B.verify_manifest(self.m, self.pub)

    def test_extra_or_missing_case_rejected(self):
        f = sorted(self.pub.glob("*.json"))[0]
        shutil.copy(f, self.pub / ("c" + "f" * 12 + ".json"))
        with self.assertRaises(B.IntegrityBreach):
            B.verify_manifest(self.m, self.pub)
        (self.pub / ("c" + "f" * 12 + ".json")).unlink(); f.unlink()
        with self.assertRaises(B.IntegrityBreach):
            B.verify_manifest(self.m, self.pub)

    def test_gold_change_rejected(self):
        self.gold.write_text(self.gold.read_text().replace("REF_STRONGER", "EQUIVALENT", 1))
        with self.assertRaisesRegex(B.IntegrityBreach, "gold"):
            B.verify_manifest(self.m, self.pub, self.gold)

    def test_manifest_edit_rejected(self):
        m = json.loads(self.m.read_text()); m["budgets"]["relation"]["cpu_s"] = 9999
        self.m.write_text(json.dumps(m))
        with self.assertRaisesRegex(B.IntegrityBreach, "self-digest"):
            B.verify_manifest(self.m, self.pub)


if __name__ == "__main__":
    unittest.main()
