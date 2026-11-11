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

    def test_budget_binds_the_whole_process_tree(self):
        # SOTA-1 defect: a per-process rlimit let 4 busy children use 4 budgets and report OK
        code = ("import multiprocessing as m\ndef f():\n  x=0\n  while True: x+=1\n"
                "ps=[m.Process(target=f) for _ in range(4)]\n[p.start() for p in ps]\n[p.join() for p in ps]")
        r = run_limited(["python3", "-c", code], cpu_s=2, mem_mb=2000, wall_s=60)
        self.assertEqual(r.status, "TIMEOUT_CPU")
        self.assertLess(r.cpu_tree_s, 2.6)
        self.assertGreaterEqual(r.processes_seen, 2)

    def test_orphans_are_counted_and_killed(self):
        code = "import os,time\nif os.fork()==0:\n  if os.fork()==0:\n    x=0\n    while True: x+=1\n  os._exit(0)\ntime.sleep(20)"
        r = run_limited(["python3", "-c", code], cpu_s=1.5, mem_mb=2000, wall_s=60)
        self.assertEqual(r.status, "TIMEOUT_CPU")

    def test_finished_tree_is_fully_accounted(self):
        code = ("import multiprocessing as m\ndef f():\n  x=0\n  for i in range(2*10**6): x+=1\n"
                "ps=[m.Process(target=f) for _ in range(3)]\n[p.start() for p in ps]\n[p.join() for p in ps]")
        r = run_limited(["python3", "-c", code], cpu_s=30, mem_mb=2000, wall_s=60)
        self.assertEqual(r.status, "OK")
        self.assertGreater(r.cpu_tree_s, r.cpu_peak_polled_s * 0.5)
        self.assertGreaterEqual(r.cpu_tree_s, r.cpu_root_wait4_s)

    def test_wall_timeout_is_not_a_cpu_timeout(self):
        self.assertEqual(run_limited(["sleep", "20"], cpu_s=5, mem_mb=200, wall_s=1).status, "TIMEOUT_WALL")

    def test_launch_errors(self):
        self.assertEqual(run_limited(["no-such-binary-x"], 5, 200, 10).status, "LAUNCH_ERROR")
        self.assertEqual(run_limited(["python3", "-c", "0"], 5, 200, 10, inputs=("rel/path.jsonl",)).status, "LAUNCH_ERROR")
        self.assertEqual(run_limited(["python3", "-c", "0"], 5, 200, 10, inputs=("/nonexistent/x.jsonl",)).status, "LAUNCH_ERROR")
        self.assertEqual(run_limited(["python3", "-c", "0"], 5, 200, 10, cwd="/nonexistent-dir").status, "LAUNCH_ERROR")

    def test_nonzero_exit_is_error(self):
        self.assertEqual(run_limited(["python3", "-c", "import sys; sys.exit(3)"], 5, 200, 10).status, "ERROR")

    def test_memory_watchdog(self):
        r = run_limited(["python3", "-c", "import time;a=bytearray(600*2**20);a[::4096]=b'x'*len(a[::4096]);time.sleep(3)"],
                        cpu_s=10, mem_mb=200, wall_s=30)
        self.assertEqual(r.status, "OOM")


if __name__ == "__main__":
    unittest.main()


FAKE_LAKE = """#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
assert args[:3] == ["exe", "semanteq", "--raw"], args
inp, out = args[-2], args[-1]
pair = json.loads(open(inp).readline())
assert "reference" in pair and "candidate" in pair
v = "MalformedInput" if "MALFORMED" in pair["reference"] else ("ExactMatch" if pair["reference"].split("\\n")[-2:] and
     pair["reference"].replace("ref", "") == pair["candidate"].replace("cand", "") else "Inconclusive")
open(out, "w").write(json.dumps({"_meta": {}}) + "\\n" + json.dumps({"id": pair["id"], "verdict": v, "elapsedMs": 1}) + "\\n")
"""


class RunnerPlumbing(unittest.TestCase):
    """Plumbing only: a stand-in `lake` checks that the runner hands SemantEq absolute, existing paths
    from inside the tool directory (the SOTA-1 failure) and that outputs are parsed and classified."""

    def test_semanteq_paths_from_relative_out(self):
        import os
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            tool = t / "se"
            (t / "bin").mkdir()
            tool.mkdir()
            lake = t / "bin" / "lake"
            lake.write_text(FAKE_LAKE)
            lake.chmod(0o755)
            cases = [{"case_id": "avail-calibration-identical", "group": "g", "source": "s", "ref_header": "import Mathlib",
                      "ref_decl": "theorem ref (x : Nat) : x = x := by sorry", "cand_header": "import Mathlib",
                      "cand_decl": "theorem cand (x : Nat) : x = x := by sorry"},
                     {"case_id": "avail-malformed", "group": "g", "source": "s", "ref_header": "MALFORMED",
                      "ref_decl": "theorem r : True", "cand_header": "", "cand_decl": "theorem c : True"}]
            C.write_jsonl(t / "cases.jsonl", cases)
            env = dict(os.environ, PATH=f"{t / 'bin'}:{os.environ['PATH']}")
            r = subprocess.run([sys.executable, "-m", "bench.runner", "--system", "semanteq", "--tool-dir", str(tool),
                                "--cases", str(t / "cases.jsonl"), "--tier", "20", "--mem-mb", "2000", "--out", "runs_rel"],
                               cwd=str(t), env=dict(env, PYTHONPATH=str(Path(__file__).resolve().parents[2])),
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            import json
            rec = json.loads((t / "runs_rel/semanteq/t20/avail-calibration-identical.r0.json").read_text())
            self.assertEqual(rec["status"], "OK", rec)
            self.assertEqual(rec["native_verdict"], "ExactMatch")
            self.assertEqual(rec["evaluation_class"], "EVALUATED_POSITIVE_STRUCTURAL")
            bad = json.loads((t / "runs_rel/semanteq/t20/avail-malformed.r0.json").read_text())
            self.assertEqual(bad["track_A"]["certified"], "UNSUPPORTED_INPUT")
            self.assertEqual(bad["evaluation_class"], "INPUT_NOT_EVALUABLE")
            self.assertTrue(rec["budget"]["compliant"])


class Classification(unittest.TestCase):
    def test_classes(self):
        from bench.runner import evaluation_class as E
        ok = lambda a, b, kind=None: {"status": "OK", "native_verdict": "v", "certificate_kind": kind,
                                      "track_A": {"certified": a}, "track_B": {"certified": b}}
        self.assertEqual(E(ok("EQUIV", "EQUIV", "kernel")), "EVALUATED_POSITIVE_KERNEL")
        self.assertEqual(E(ok("EQUIV", "EQUIV", "structural")), "EVALUATED_POSITIVE_STRUCTURAL")
        self.assertEqual(E(ok("ABSTAIN", "NONEQUIV", "kernel")), "EVALUATED_NEGATIVE_FIDELITY")
        self.assertEqual(E(ok("ABSTAIN", "ABSTAIN")), "EVALUATED_ABSTAIN")
        self.assertEqual(E({"status": "TIMEOUT_CPU"}), "RESOURCE_EXHAUSTED")
        self.assertEqual(E({"status": "NON_ELABORATING"}), "INPUT_NOT_EVALUABLE")
        self.assertEqual(E({"status": "OK", "native_verdict": None}), "NOT_EVALUATED_INFRA")
        self.assertEqual(E({"status": "LAUNCH_ERROR"}), "NOT_EVALUATED_INFRA")
        self.assertEqual(E(ok("UNSUPPORTED_INPUT", "UNSUPPORTED_INPUT")), "INPUT_NOT_EVALUABLE")
        self.assertEqual(E(ok("TIMEOUT_WALL", "TIMEOUT_WALL")), "RESOURCE_EXHAUSTED")
        self.assertEqual(E(ok("ERROR", "ERROR")), "NOT_EVALUATED_INFRA")

    def test_gate_fails_closed(self):
        from bench.gate import system_report
        cases = ["avail-calibration-identical", "avail-equivalent-rename", "avail-nonequivalent-hypothesis"]
        good = {"status": "OK", "evaluation_class": "EVALUATED_ABSTAIN", "native_verdict": "x",
                "track_A": {"certified": "ABSTAIN"}, "track_B": {"certified": "ABSTAIN"}, "budget": {"compliant": True}}
        err = dict(good, status="ERROR", evaluation_class="NOT_EVALUATED_INFRA", budget={"compliant": False})
        self.assertTrue(system_report({c: good for c in cases[:2]}, cases, [])["gate_pass"])
        self.assertFalse(system_report({cases[0]: good, cases[1]: err}, cases, [])["gate_pass"])
        self.assertFalse(system_report({}, cases, [])["gate_pass"])
        over = dict(good, budget={"compliant": False})
        self.assertFalse(system_report({cases[0]: good, cases[1]: over}, cases, [])["gate_pass"])


class BeqDriverPlumbing(unittest.TestCase):
    """Plumbing only: stand-in `lean_interact` and `beq_plus.py` check that the driver keeps upstream's
    DEFAULT_TIMEOUT, passes the declarations and merged header, and that the result is parsed."""

    def test_driver_uses_upstream_default_timeout(self):
        import json
        import os
        import subprocess
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "li" / "examples").mkdir(parents=True)
            (t / "li" / "examples" / "beq_plus.py").write_text(
                "DEFAULT_TIMEOUT = 60\n"
                "def beq_plus(f1, f2, header, server, timeout_per_proof):\n"
                "    assert timeout_per_proof == 60 and 'import Mathlib' in header\n"
                "    return f1.split(':', 1)[1] == f2.split(':', 1)[1]\n")
            (t / "pkg" / "lean_interact").mkdir(parents=True)
            (t / "pkg" / "lean_interact" / "__init__.py").write_text(
                "class TempRequireProject:\n    def __init__(self, **k): pass\n"
                "class LeanREPLConfig:\n    def __init__(self, **k): pass\n"
                "class AutoLeanServer:\n    def __init__(self, **k): pass\n")
            from bench.adapters import beqplus as B
            case = {"case_id": "x", "ref_header": "import Mathlib", "cand_header": "import Mathlib\nopen Real",
                    "ref_decl": "theorem a : 1 = 1 := by sorry", "cand_decl": "theorem b : 1 = 1 := by sorry"}
            prep = B.prepare(case, t / "w", t / "li", "v4.8.0")
            self.assertNotIn("--timeout", prep["cmd"])
            r = subprocess.run(prep["cmd"], env=dict(os.environ, PYTHONPATH=str(t / "pkg")), capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = B.parse(case, t / "w" / "out.json")
            self.assertEqual(out["native_verdict"], True)
            self.assertEqual(out["per_proof_timeout_s"], 60)
            self.assertEqual(out["certificate_kind"], "kernel")
            self.assertEqual(json.loads((t / "w" / "out.json").read_text())["beq_plus"], True)
