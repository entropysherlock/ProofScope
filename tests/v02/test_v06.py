"""v0.6 tests: oracle semantics and determinism, ps_arith, soundness theorems, research prep, SemantEq glue."""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "proofscope" / "benchmark"))
import gen_oracle as G  # noqa: E402

HAVE_LEAN = shutil.which("lean") is not None


class OracleSemanticsTests(unittest.TestCase):
    def test_lean_nat_semantics(self):
        e = {"n": 7, "m": 0}
        self.assertEqual(G.ev(G.div(G.N, G.M), e), 0)        # n / 0 = 0
        self.assertEqual(G.ev(G.mod(G.N, G.M), e), 7)        # n % 0 = n
        self.assertEqual(G.ev(G.sub(G.M, G.N), e), 0)        # truncated subtraction
        self.assertTrue(G.ev(G.dvd(G.L(0), G.L(0)), e))      # 0 ∣ 0
        self.assertFalse(G.ev(G.dvd(G.L(0), G.N), e))        # ¬ 0 ∣ 7
        self.assertTrue(G.ev(G.fa_lt("k", G.L(0), ("lit", 0) and G.lt(G.V("k"), G.L(0))), e))  # vacuous bounded ∀

    def test_rendering(self):
        self.assertEqual(G.lean(G.fa_lt("k", G.N, G.le(G.V("k"), G.N))), "(∀ k : Nat, k < n → (k ≤ n))")
        self.assertEqual(G.lean(G.pw(G.L(2), G.N)), "(2 ^ n)")

    def test_generation_is_deterministic(self):
        def digest():
            G.main()
            files = sorted((ROOT / "proofscope" / "benchmark" / "heldout_oracle").glob("*.json"))
            return hashlib.sha256(b"".join(f.read_bytes() for f in files)).hexdigest(), len(files)
        a, b = digest(), digest()
        self.assertEqual(a, b)
        self.assertGreaterEqual(a[1], 100)

    def test_oracle_existentials_are_witnessed(self):
        f = G.oracle(["n"], G.le(G.L(2), G.N), G.TRUE, G.TRUE, G.TRUE)
        self.assertTrue(f["app_gap"])          # n = 0 satisfies the reference but not 2 ≤ n
        self.assertFalse(f["vacuous"])


@unittest.skipUnless(HAVE_LEAN, "Lean toolchain not installed")
class LeanV06Tests(unittest.TestCase):
    def _lean(self, src: str) -> subprocess.CompletedProcess:
        d = Path(tempfile.mkdtemp())
        tac = (ROOT / "lean" / "ProofScope" / "Tactics.lean").read_text()
        (d / "T.lean").write_text(tac + "\n" + src)
        return subprocess.run(["lean", str(d / "T.lean")], capture_output=True, text=True)

    def test_ps_arith_proves_true_and_rejects_false(self):
        ok = self._lean("theorem t : ∀ (n m : Nat), 0 < m → n % m ≤ m → n % m < m := by intros; ps_arith\n"
                        "#print axioms t\n")
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertIn("does not depend on any axioms", ok.stdout)
        bad = self._lean("theorem f : ∀ (n m : Nat), n % m < m := by intros; ps_arith\n")
        self.assertNotEqual(bad.returncode, 0)

    def test_soundness_theorems_axiom_free_and_replayed(self):
        build = Path(tempfile.mkdtemp())
        (build / "ProofScope").mkdir()
        r = subprocess.run(["lean", "-R", str(ROOT / "lean"), "-o", str(build / "ProofScope" / "Soundness.olean"),
                            str(ROOT / "lean" / "ProofScope" / "Soundness.lean")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.count("does not depend on any axioms"), 9)
        rp = subprocess.run(["leanchecker", "--fresh", "ProofScope.Soundness"], cwd=build, capture_output=True,
                            text=True, env={"LEAN_PATH": str(build), "PATH": __import__("os").environ["PATH"]})
        self.assertEqual(rp.returncode, 0, rp.stdout + rp.stderr)


class ResearchAndCompetitorTests(unittest.TestCase):
    def test_research_prepare(self):
        from proofscope.research import prepare
        lean = Path(tempfile.mkdtemp())
        (lean / "ComparatorChallenges").mkdir()
        (lean / "docs").mkdir()
        (lean / "lean-toolchain").write_text("leanprover/lean4:v4.34.1\n")
        (lean / "lake-manifest.json").write_text(json.dumps({"packages": [
            {"name": "mathlib", "url": "https://github.com/leanprover-community/mathlib4.git", "rev": "a" * 40}]}))
        (lean / "ComparatorChallenges" / "A.lean").write_text("import Mathlib\ntheorem a : True := sorry\n")
        (lean / "ComparatorChallenges" / "B.lean").write_text("import OAI.Foo\ntheorem b : True := sorry\n")
        out = Path(tempfile.mkdtemp())
        info = prepare(lean, "c" * 40, out, 10)
        self.assertEqual([s["challenge"] for s in info["selected"]], ["A"])
        self.assertEqual(info["excluded_non_mathlib_imports"], ["B"])
        self.assertIn('rev = "' + "a" * 40 + '"', (out / "lakefile.toml").read_text())

    def test_semanteq_export_and_compare(self):
        from proofscope.competitors import semanteq as S
        out = Path(tempfile.mkdtemp())
        n = S.export(["dev"], out / "pairs.jsonl")
        self.assertGreaterEqual(n, 30)
        first = json.loads((out / "pairs.jsonl").read_text().splitlines()[0])
        self.assertTrue(first["reference"].startswith("import Mathlib\ntheorem r :"))
        (out / "se.jsonl").write_text(json.dumps({"id": first["id"], "verdict": "EquivalentRestricted"}) + "\n")
        (out / "ps.json").write_text(json.dumps({"rows": [{"id": first["id"], "classification": "EQUIVALENT"}]}))
        res = S.compare(out / "se.jsonl", out / "ps.json", out / "cmp.json")
        self.assertEqual(res["agree_equivalent"], 1)
        self.assertEqual(res["disagreements"], [])


if __name__ == "__main__":
    unittest.main()
