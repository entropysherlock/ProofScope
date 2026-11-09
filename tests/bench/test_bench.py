"""Unit tests for the SOTA-1 benchmark infrastructure. All data here is synthetic test fixture data for
the code paths; none of it is a benchmark result."""
import tempfile
import unittest
from pathlib import Path

from bench import canonical as C
from bench import outcomes as O
from bench import score as S
from bench import seal as SE
from bench.adapters import _decl as D
from bench.limits import run_limited


class Canonical(unittest.TestCase):
    def test_labels_never_in_cases(self):
        c = {"case_id": "x", "group": "g", "source": "s", "ref_header": "h", "ref_decl": "theorem a : True",
             "cand_header": "h", "cand_decl": "theorem b : True", "correct": True}
        self.assertTrue(any("label-like" in e for e in C.validate(c)))

    def test_body_normalizes_name_and_proof(self):
        self.assertEqual(C.statement_body("theorem foo (n : ℕ) :  n = n := by sorry"),
                         C.statement_body("theorem bar (n : ℕ) : n = n"))

    def test_with_sorry_keeps_let_in_statement(self):
        d = "theorem t (p : Prop) : let q := ¬¬p; p = q"
        self.assertEqual(D.with_sorry(d), d + " := sorry")
        self.assertEqual(D.with_sorry("theorem t : True := by sorry"), "theorem t : True := sorry")


class Outcomes(unittest.TestCase):
    def test_failed_search_is_never_nonequiv_certified(self):
        self.assertEqual(O.semanteq("Inconclusive", "A")["certified"], "ABSTAIN")
        self.assertEqual(O.semanteq("LikelyTooWeak", "B")["certified"], "ABSTAIN")
        self.assertEqual(O.beqplus(False, "A")["certified"], "ABSTAIN")
        self.assertEqual(O.beqplus(False, "A")["native"], "NONEQUIV")

    def test_proofscope_schema_difference_only_in_track_b(self):
        self.assertEqual(O.proofscope("LEAN_WEAKER_BY_ASSUMPTION", "A")["certified"], "ABSTAIN")
        self.assertEqual(O.proofscope("LEAN_WEAKER_BY_ASSUMPTION", "B")["certified"], "NONEQUIV")
        self.assertEqual(O.proofscope("BOTH_CLAIMS_FALSE", "A")["certified"], "EQUIV")
        self.assertEqual(O.proofscope("BOTH_CLAIMS_FALSE", "B")["certified"], "ABSTAIN")


class Stats(unittest.TestCase):
    def test_reference_values(self):
        self.assertEqual(S.clopper_pearson(5, 10), (0.1871, 0.8129))
        self.assertEqual(S.clopper_pearson(0, 30)[1], 0.1157)
        self.assertAlmostEqual(S.mcnemar_exact(1, 9), 0.021484375)

    def test_recall_counts_abstentions(self):
        m = S.metrics(["TP", "ABSTAIN", "TN", "FN"], ["equivalent", "equivalent", "non_equivalent", "equivalent"])
        self.assertEqual(m["recall_equiv"], round(1 / 3, 4))
        self.assertEqual(m["decisive_coverage"], 0.75)

    def test_infra_is_not_abstention(self):
        self.assertEqual(S.classify("TIMEOUT_CPU", "equivalent"), "INFRA:TIMEOUT_CPU")


class Seal(unittest.TestCase):
    def test_commitment_and_group_disjointness(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            cases, labels = [], []
            for i in range(60):
                g = f"g{i // 3}"
                cases.append({"case_id": f"c{i}", "group": g, "source": "fx", "ref_header": "",
                              "ref_decl": f"theorem r{i // 3} (n : Nat) : n + {i // 3} = n + {i // 3}",
                              "cand_header": "", "cand_decl": f"theorem p{i} (m : Nat) : m * {i} = {i} * m"})
                labels.append({"case_id": f"c{i}", "source_label_equivalent": i % 2 == 0, "source": "fx"})
            C.write_jsonl(t / "fx.cases.jsonl", cases)
            C.write_jsonl(t / "fx.source_labels.jsonl", labels)
            m = SE.build(t, ["fx"], 20, 6, 1, t / "out")
            pilot = C.read_jsonl(t / "out" / "pilot.cases.jsonl")
            prim = C.read_jsonl(t / "out" / "primary.cases.jsonl")
            self.assertFalse({c["group"] for c in pilot} & {c["group"] for c in prim})
            for c in prim:
                self.assertFalse(C.validate(c))
            lab = C.read_jsonl(t / "out" / "custodian" / "primary.labels.jsonl")
            salt = (t / "out" / "custodian" / "salt.txt").read_text().strip()
            self.assertTrue(SE.verify(lab, salt, m["primary"]["label_commitment"]))
            lab[0]["source_label_equivalent"] = not lab[0]["source_label_equivalent"]
            self.assertFalse(SE.verify(lab, salt, m["primary"]["label_commitment"]))


class Limits(unittest.TestCase):
    def test_cpu_limit_is_timeout(self):
        r = run_limited(["python3", "-c", "while True: pass"], cpu_s=1, mem_mb=512, wall_s=30)
        self.assertEqual(r.status, "TIMEOUT_CPU")

    def test_memory_watchdog(self):
        r = run_limited(["python3", "-c", "import time;a=bytearray(600*2**20);a[::4096]=b'x'*len(a[::4096]);time.sleep(3)"],
                        cpu_s=10, mem_mb=200, wall_s=30)
        self.assertEqual(r.status, "OOM")


if __name__ == "__main__":
    unittest.main()
