"""v0.5-v1.0 engine tests: theorem dossiers, theorem comparison, certificate gate, viewer.
Lean-dependent tests skip when `lean` is not on PATH."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from proofscope import compare as C
from proofscope.bench import baseline_label, detection, wilson

HAVE_LEAN = shutil.which("lean") is not None
ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "demo_project"



def _by_name(out, name):
    """Dossier files are keyed by module + name (v0.8); look one up through the index."""
    idx = json.loads((out / "dossier_index.json").read_text())["theorems"]
    hits = [t for t in idx if t["theorem_id"] == name]
    assert len(hits) == 1, hits
    return json.loads((out / hits[0]["dossier_file"]).read_text())

class ClassifyTests(unittest.TestCase):
    def test_priority_and_labels(self):
        self.assertEqual(C.classify({"vacuous", "app_gap"}), "VACUOUS")
        self.assertEqual(C.classify({"app_gap", "concl_gap"}), "APPLICABILITY_GAP")
        self.assertEqual(C.classify({"concl_gap"}), "CONCLUSION_GAP")
        self.assertEqual(C.classify({"transfer", "hyp_cover", "concl_cover", "hyp_back", "concl_back"}), "EQUIVALENT")
        self.assertEqual(C.classify({"transfer", "strict_hyp"}), "LEAN_STRONGER")
        self.assertEqual(C.classify({"transfer"}), "COVERS")
        self.assertEqual(C.classify({"hyp_cover", "concl_cover"}), "INCONCLUSIVE")  # transfer itself must be certified
        self.assertEqual(C.classify(set()), "INCONCLUSIVE")

    def test_contradictions(self):
        self.assertEqual(C.contradictions({"hyp_cover", "app_gap"}), ["hyp_cover & app_gap"])
        self.assertEqual(C.contradictions({"vacuous", "inhabited"}), ["vacuous & inhabited"])
        self.assertEqual(C.contradictions({"transfer", "concl_gap"}), [])

    def test_box_tactic_is_one_line(self):
        s = C.CompareSpec(id="x", binders=[["n", "Nat"], ["m", "Nat"]], lean_hyp="True", lean_concl="True",
                          ref_hyp="True", ref_concl="True", bounds={"n": 3, "m": 4})
        t = s._box_tactic("P n m")
        self.assertNotIn("\n", t)
        self.assertIn("∃ n, n < 3 ∧ ∃ m, m < 4 ∧ P n m", t)

    def test_metrics(self):
        rows = [{"fidelity_failure": True, "k": "CONCLUSION_GAP"}, {"fidelity_failure": False, "k": "EQUIVALENT"},
                {"fidelity_failure": True, "k": "INCONCLUSIVE"}]
        d = detection(rows, "k")
        self.assertEqual((d["tp"], d["fp"], d["fn"], d["abstain"]), (1, 0, 1, 1))
        self.assertEqual(wilson(0, 0), None)
        self.assertEqual(baseline_label({"lean_hyp": "a  b", "ref_hyp": "a b", "lean_concl": "c", "ref_concl": "c"}),
                         "EQUIVALENT")

    def test_benchmark_files(self):
        for split in ("dev", "dev_v05_heldout", "heldout_oracle"):
            files = list((ROOT / "proofscope" / "benchmark" / split).glob("*.json"))
            self.assertGreaterEqual(len(files), 20)
            for f in files:
                d = json.loads(f.read_text())
                self.assertIn(d["expected"], C.LABELS)
                self.assertIsInstance(d["fidelity_failure"], bool)


@unittest.skipUnless(HAVE_LEAN, "Lean toolchain not installed")
class LeanEngineTests(unittest.TestCase):
    def test_dossiers_core(self):
        from proofscope.dossier import run
        out = Path(tempfile.mkdtemp())
        s = run(["Init.Data.Nat.Lemmas"], ["Nat.add_comm", "Nat.lt_irrefl"], ["Init.Data.Nat.Lemmas"], out, module_limit=10)
        self.assertTrue(s["metaprogram_built"])
        self.assertEqual(s["errors"], [])
        self.assertGreaterEqual(s["dossiers"], 12)
        self.assertEqual(s["incomplete_extractions"], 0)
        d = _by_name(out, "Nat.add_comm")
        self.assertEqual(d["elaborated_type"], "∀ (n m : Nat), n + m = m + n")
        self.assertEqual(d["axiom_status"], "NONE")
        self.assertEqual(d["kernel_status"], "TOOLCHAIN_LIBRARY")

    def test_dossiers_project_with_replay(self):
        from proofscope.dossier import run
        proj = Path(tempfile.mkdtemp()) / "p"
        shutil.copytree(FIXTURE, proj, ignore=shutil.ignore_patterns(".lake"))
        subprocess.run(["lake", "build"], cwd=proj, check=True, capture_output=True)
        out = Path(tempfile.mkdtemp())
        s = run(["Demo"], [], ["Demo.Basic", "Demo.Flawed"], out, project=str(proj))
        self.assertEqual(s["by_kernel_status"]["REPLAYED"], 4)
        self.assertEqual(s["by_axiom_status"], {"NONE": 1, "STANDARD": 1, "NONSTANDARD": 1, "SORRY": 1})
        d = _by_name(out, "Demo.sum_formula")
        self.assertEqual(sorted(x["name"] for x in d["statement_dependencies"] if x["role"] == "definition"),
                         ["List.range", "List.sum"])

    def _cmp(self, **kw):
        from proofscope.toolchain import Toolchain
        spec = C.CompareSpec(id=kw.pop("id"), binders=[["n", "Nat"]], bounds={"n": 20}, **kw)
        return C.run_compare(spec, Toolchain.find(), Path(tempfile.mkdtemp()))

    def test_compare_gap_equiv_vacuous(self):
        self.assertEqual(self._cmp(id="g", lean_hyp="2 ≤ n", lean_concl="n ≤ n * n", ref_hyp="True",
                                   ref_concl="n ≤ n * n")["classification"], "APPLICABILITY_GAP")
        self.assertEqual(self._cmp(id="e", lean_hyp="n ≠ 0", lean_concl="True", ref_hyp="0 < n",
                                   ref_concl="True")["classification"], "EQUIVALENT")
        self.assertEqual(self._cmp(id="v", lean_hyp="n < 2 ∧ 3 < n", lean_concl="False", ref_hyp="True",
                                   ref_concl="True")["classification"], "VACUOUS")

    def test_adversarial_certificates_all_handled(self):
        from proofscope.bench import run_adversarial
        from proofscope.toolchain import Toolchain
        rows = run_adversarial(Toolchain.find(), Path(tempfile.mkdtemp()))
        self.assertGreaterEqual(len(rows), 20)
        bad = [r for r in rows if not r["correct"]]
        self.assertEqual(bad, [])
        forged = next(r for r in rows if r["id"] == "AdvSkipKernel")
        self.assertEqual(forged["reason"], "leanchecker replay failed")


class ViewerTests(unittest.TestCase):
    def test_viewer_is_self_contained(self):
        from proofscope.viewer import build
        d = Path(tempfile.mkdtemp())
        (d / "x.json").write_text(json.dumps({
            "theorem_id": "X.y</script><b>", "kind": "theorem", "module": "M", "elaborated_type": "True",
            "binders": [], "hypotheses": [], "conclusion": "True", "conclusion_shape": "True",
            "statement_dependencies": [], "proof_dependencies": [], "axioms": [], "source_locations": None,
            "unresolved_items": [], "kernel_status": "NOT_RUN", "axiom_status": "NONE", "source_commit": None}))
        out = build(d, None, Path(tempfile.mkdtemp()) / "r.html", "t")
        s = out.read_text()
        self.assertNotIn("http://", s.replace("http://www.w3.org", ""))
        self.assertNotIn("</script><b>", s)  # script-breaking content is escaped


if __name__ == "__main__":
    unittest.main()
