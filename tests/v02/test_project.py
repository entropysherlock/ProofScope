"""Pinned-project auditor tests.

* Pure tests always run.
* The fixture test (tests/fixtures/demo_project) needs git and a Lean toolchain with lake.
* The live openai/math test needs network access and runs only with PROOFSCOPE_NETWORK_TESTS=1.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from proofscope import project as P
from proofscope.scan import scan_text

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "demo_project"
HAVE_LAKE = shutil.which("lake") is not None and shutil.which("git") is not None
OAI_COMMIT = "4eaee87548250b2682affda7d05d947c05554bae"


class ValidationTests(unittest.TestCase):
    ok = ("https://github.com/openai/math", OAI_COMMIT, "lean", ["OAI.Foo.Main", "OAI.X.main'"])

    def test_accepts_good_inputs(self):
        P.validate(*self.ok)

    def test_rejects_branch_names(self):
        with self.assertRaises(P.InputError):
            P.validate("https://github.com/openai/math", "main", "", [])

    def test_rejects_short_sha(self):
        with self.assertRaises(P.InputError):
            P.validate("https://github.com/openai/math", OAI_COMMIT[:12], "", [])

    def test_rejects_non_github_and_injection(self):
        for repo in ["https://evil.example/x/y", "https://github.com/a/b; rm -rf /", "file:///etc", "git@github.com:a/b"]:
            with self.assertRaises(P.InputError, msg=repo):
                P.validate(repo, OAI_COMMIT, "", [])

    def test_rejects_path_traversal(self):
        for sub in ["../x", "a/../../b", "/abs", "a;b"]:
            with self.assertRaises(P.InputError, msg=sub):
                P.validate("https://github.com/openai/math", OAI_COMMIT, sub, [])

    def test_rejects_bad_lean_names(self):
        for n in ["Foo$(id)", "a b", "Foo;bar", "-rf"]:
            with self.assertRaises(P.InputError, msg=n):
                P.validate("https://github.com/openai/math", OAI_COMMIT, "", [n])


class StoppedAuditTests(unittest.TestCase):
    def test_invalid_input_stops_without_claims(self):
        out = Path(tempfile.mkdtemp())
        rc = P.main(["--repo", "https://github.com/openai/math", "--commit", OAI_COMMIT,
                     "--modules", "Ok.Module", "$(touch /tmp/proofscope_pwned)", "--output", str(out)])
        rep = json.loads((out / "report.json").read_text())
        self.assertEqual(rc, 1)
        self.assertEqual(rep["overall"], "FAIL")
        self.assertEqual([f["stage"] for f in rep["findings"]], ["S0"])
        self.assertFalse(Path("/tmp/proofscope_pwned").exists())
        self.assertIn("Nothing was scanned", (out / "REPORT.md").read_text())


class VerdictScopeTests(unittest.TestCase):
    def test_no_hazard_claim_without_a_scan(self):
        """Regression: catalog-only audit must not claim a trust-hazard scan."""
        A = P.Audit(Path(tempfile.mkdtemp()))
        A.add("S5", "catalog entries mechanically consistent", "1 checked", P.VERIFIED, "1 consistent")
        args = type("Args", (), {"commit": OAI_COMMIT, "repo": "https://github.com/openai/math", "build": False})()
        lines = P.verdict(A, args, "PASS", {})
        self.assertFalse(any("No trust hazards" in l for l in lines))
        self.assertTrue(any("no import closure was hashed" in l for l in lines))


class ParserRegressionTests(unittest.TestCase):
    """Each case below was a false alarm on the real openai/math catalog before it was fixed."""

    def names(self, src):
        return {d.full_name for d in scan_text(src).decls}

    def test_indented_declaration(self):
        self.assertIn("OAI.D.main", self.names("namespace OAI\nnamespace D\nsection\n theorem main : True := trivial\nend\nend D\nend OAI"))

    def test_universe_parameters(self):
        self.assertIn("OAI.G.exp", self.names("namespace OAI.G\ntheorem exp.{v} (C : Sort v) : True := trivial\nend OAI.G"))

    def test_dotted_namespace_closed_in_two_steps(self):
        src = "namespace OAI\nnamespace S.M\nlemma a : True := trivial\nend M\ntheorem t : True := trivial\nend S\nend OAI"
        self.assertIn("OAI.S.t", self.names(src))

    def test_noncomputable_section(self):
        src = "namespace OAI\nsection\nnoncomputable section\nnamespace E.P\nend P\ntheorem main_theorem : True := trivial\nend E\nend\nend\nend OAI"
        self.assertIn("OAI.E.main_theorem", self.names(src))


class ClosureAndCatalogTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "Pkg").mkdir()
        (self.root / "Pkg" / "A.lean").write_text("import Mathlib\nnamespace Pkg\ntheorem a : True := trivial\nend Pkg\n")
        (self.root / "Pkg" / "B.lean").write_text("import Pkg.A\n-- import Pkg.Ghost\nnamespace Pkg\ntheorem b : True := trivial\nend Pkg\n")
        (self.root / "Pkg" / "Main.lean").write_text("import Pkg.B\nnamespace Pkg\ntheorem main : True := trivial\nend Pkg\n")
        (self.root / "Pkg" / "Lonely.lean").write_text("namespace Pkg\ntheorem lonely : True := trivial\nend Pkg\n")
        (self.root / "ComparatorChallenges").mkdir()

    def test_closure_follows_local_imports_only(self):
        local, external = P.closure(self.root, ["Pkg.Main"])
        self.assertEqual(set(local), {"Pkg.Main", "Pkg.B", "Pkg.A"})
        self.assertEqual(external, {"Mathlib"})

    def test_catalog_checks(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML not installed")
        cfg = {"challenge_module": "Pkg.Main", "solution_module": "Pkg.Main", "theorem_names": ["Pkg.a", "Pkg.lonely"],
               "definition_names": [], "permitted_axioms": ["propext", "Quot.sound", "Classical.choice"]}
        (self.root / "ComparatorChallenges" / "C.json").write_text(json.dumps(cfg))
        (self.root / "formalization.yaml").write_text(
            "version: v0.4\nstatus:\n  main_results:\n"
            "    - {declaration: Pkg.a, file: Pkg/A.lean, comparator_config: ComparatorChallenges/C.json}\n"
            "    - {declaration: Pkg.lonely, file: Pkg/Lonely.lean, comparator_config: ComparatorChallenges/C.json}\n"
            "    - {declaration: Pkg.nothere, file: Pkg/A.lean, comparator_config: ComparatorChallenges/C.json}\n")
        A = P.Audit(Path(tempfile.mkdtemp()))
        rows = {r["declaration"]: r for r in P.s5_catalog(A, self.root, None)}
        self.assertEqual(rows["Pkg.a"]["status"], P.VERIFIED)
        self.assertEqual(rows["Pkg.lonely"]["checks"]["solution_module_imports_catalog_file"], P.WARNING)
        self.assertEqual(rows["Pkg.nothere"]["checks"]["declaration_in_file"], P.FAIL)


@unittest.skipUnless(HAVE_LAKE, "git and a Lean toolchain with lake are required")
class FixtureBuildTests(unittest.TestCase):
    """End-to-end on a tiny Mathlib-free project with an honest module and planted flaws."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        repo = cls.tmp / "repo"
        shutil.copytree(FIXTURE, repo, ignore=shutil.ignore_patterns(".lake"))
        g = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(g + ["init", "-q"], cwd=repo, check=True)
        subprocess.run(g + ["add", "-A"], cwd=repo, check=True)
        subprocess.run(g + ["commit", "-qm", "fixture"], cwd=repo, check=True)
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
        out = cls.tmp / "out"
        cls.rc = P.main(["--allow-local", "--repo", f"file://{repo}", "--commit", sha,
                         "--modules", "Demo.Basic", "Demo.Flawed",
                         "--decls", "Demo.add_comm'", "Demo.sum_formula", "Demo.unproved_claim", "Demo.uses_axiom",
                         "--build", "--output", str(out), "--workdir", str(cls.tmp / "src")])
        cls.report = json.loads((out / "report.json").read_text())
        cls.by = {(f["check"], f["subject"]): f["status"] for f in cls.report["findings"]}

    def test_fetch_verified(self):
        self.assertEqual(self.by[("fetch pinned commit", self.report["inputs"]["commit"])], "VERIFIED")

    def test_honest_declarations_verified(self):
        self.assertEqual(self.by[("axioms of declaration", "Demo.add_comm'")], "VERIFIED")
        self.assertEqual(self.by[("axioms of declaration", "Demo.sum_formula")], "VERIFIED")

    def test_sorry_is_fail_and_axiom_is_warning(self):
        self.assertEqual(self.by[("axioms of declaration", "Demo.unproved_claim")], "FAIL")
        self.assertEqual(self.by[("axioms of declaration", "Demo.uses_axiom")], "WARNING")
        self.assertEqual(self.by[("trust hazard in import closure", "sorry")], "FAIL")

    def test_replay_and_overall(self):
        self.assertEqual(self.by[("kernel replay (leanchecker, non-fresh)", "Demo.Basic")], "VERIFIED")
        self.assertEqual(self.report["overall"], "FAIL")
        self.assertEqual(self.rc, 1)


@unittest.skipUnless(os.environ.get("PROOFSCOPE_NETWORK_TESTS") == "1", "set PROOFSCOPE_NETWORK_TESTS=1")
class LiveOpenAIMathTests(unittest.TestCase):
    def test_catalog_audit_without_build(self):
        out = Path(tempfile.mkdtemp())
        rc = P.main(["--repo", "https://github.com/openai/math", "--commit", OAI_COMMIT, "--subdir", "lean",
                     "--catalog", "--output", str(out / "o"), "--workdir", str(out / "s")])
        rep = json.loads((out / "o" / "report.json").read_text())
        row = next(f for f in rep["findings"] if f["check"] == "catalog entries mechanically consistent")
        self.assertEqual(row["status"], "VERIFIED", row["detail"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
