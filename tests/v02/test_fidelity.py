"""Definition-fidelity engine tests. Lean-dependent tests skip when `lean` is not on PATH."""

import shutil
import tempfile
import unittest
from pathlib import Path

from proofscope.controls import run_controls
from proofscope.separate import (AGREE_DOMAIN, BOUNDED_ONLY, EQUIVALENT, IN_DOMAIN, INCONCLUSIVE, INCONSISTENT,
                                 OUTSIDE_ONLY, PairSpec, build_module, classify, run_pair)
from proofscope.toolchain import Toolchain

PAIRS = Path(__file__).resolve().parents[2] / "proofscope" / "pairs"
HAVE_LEAN = shutil.which("lean") is not None


class ClassifyTests(unittest.TestCase):
    def test_table(self):
        self.assertEqual(classify({"equal_all"}), EQUIVALENT)
        self.assertEqual(classify({"witness_domain"}), IN_DOMAIN)
        self.assertEqual(classify({"witness_domain_bounded"}), IN_DOMAIN)
        self.assertEqual(classify({"agree_domain", "witness_all"}), OUTSIDE_ONLY)
        self.assertEqual(classify({"agree_domain"}), AGREE_DOMAIN)
        self.assertEqual(classify({"agree_domain_bounded"}), BOUNDED_ONLY)
        self.assertEqual(classify(set()), INCONCLUSIVE)

    def test_contradictions_flagged(self):
        self.assertEqual(classify({"equal_all", "witness_all"}), INCONSISTENT)
        self.assertEqual(classify({"agree_domain", "witness_domain"}), INCONSISTENT)

    def test_every_alternative_must_close_goal(self):
        s = PairSpec(id="z", custom="n", reference="n", binders=[["n", "Nat"]])
        src, spans = build_module(s, mathlib=False)
        alts = [l for l in src.splitlines() if l.strip().startswith("| (")]
        self.assertTrue(alts)
        self.assertTrue(all(l.rstrip().endswith("; done)") for l in alts))

    def test_bundled_specs_load(self):
        specs = [PairSpec.load(p) for p in sorted(PAIRS.glob("*.json"))]
        self.assertGreaterEqual(len(specs), 13)
        self.assertEqual(len({s.ident for s in specs}), len(specs))


@unittest.skipUnless(HAVE_LEAN, "Lean toolchain not installed")
class LeanFidelityTests(unittest.TestCase):
    def test_kernel_controls(self):
        r = run_controls(Toolchain.find(), Path(tempfile.mkdtemp()))
        self.assertTrue(r["honest_accepted"], r["steps"])
        self.assertTrue(r["forged_rejected"], r["steps"])

    def test_labelled_pairs(self):
        tc = Toolchain.find()
        for p in sorted(PAIRS.glob("*.json")):
            s = PairSpec.load(p)
            with self.subTest(spec=p.name):
                r = run_pair(s, tc, Path(tempfile.mkdtemp()))
                self.assertNotEqual(r["classification"], INCONSISTENT)
                if s.expected:
                    self.assertEqual(r["classification"], s.expected, r["interpretation"])

    def test_relative_workdir_replays_certificates(self):
        # CLI defaults to a relative --out; ensure Lean receives absolute paths.
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            relative = Path(folder).relative_to(Path.cwd()) / "work" / "C1"
            spec = PairSpec.load(PAIRS / "C1_equivalent_rewritten.json")
            result = run_pair(spec, Toolchain.find(), relative)
            self.assertEqual(result["classification"], EQUIVALENT, result.get("probe"))
            self.assertTrue(result["certificates"])

    def test_sorry_route_rejected(self):
        r = run_pair(PairSpec.load(PAIRS / "C8_sorry_route_rejected.json"), Toolchain.find(), Path(tempfile.mkdtemp()))
        self.assertEqual(r["rejected"].get("equal_all"), "depends on sorryAx")


if __name__ == "__main__":
    unittest.main()
