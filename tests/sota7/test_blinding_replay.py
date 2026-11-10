"""SOTA-7: blinded execution, sealing and independent replay with malicious certificates.
Needs Lean 4.34.1 + leanchecker (repair cases only; no REPL, no Mathlib)."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from bench.sota7 import blind as B
from bench.sota7 import replay as RP
from bench.sota7 import runner as RU

SYN = Path(__file__).resolve().parents[2] / "bench/sota7/synthetic"
HAVE = bool(shutil.which("lean") and shutil.which("leanchecker"))
BUD = {"relation": {"cpu_s": 120, "mem_mb": 8000, "wall_s": 400}, "repair": {"cpu_s": 120, "mem_mb": 8000, "wall_s": 400}}
CANARY = "CANARY-7f3a91-GOLD-ONLY"


@unittest.skipUnless(HAVE, "Lean 4.34.1 and leanchecker required")
class BlindRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = Path(tempfile.mkdtemp())
        pub = cls.t / "public"; pub.mkdir()
        gold = []
        for line in (SYN / "gold.jsonl").read_text().splitlines():
            g = json.loads(line)
            if g["dev_name"] in ("repair_nonzero", "repair_none"):
                g["rationales"] = [g["rationales"][0] + " " + CANARY]
                gold.append(g)
                shutil.copy(SYN / "public" / f"{g['case_id']}.json", pub)
        (cls.t / "gold.jsonl").write_text("".join(json.dumps(g) + "\n" for g in gold))
        cls.ids = sorted(g["case_id"] for g in gold)
        cls.m = B.freeze(pub, cls.t / "gold.jsonl", cls.t / "m.json", dataset_version="t", selection_protocol="t",
                         review_protocol="t", repo=cls.t, toolchain={}, budgets=BUD)
        os.environ["SOTA7_GOLD_PATH"] = str(cls.t / "gold.jsonl")     # a tempting variable the sandbox must drop
        try:
            cls.run_dir = cls.t / "run"
            cls.run_dir.mkdir()
            cases = B.load_public(pub)
            recs = [RU.run_case(cases[i], pub, cls.run_dir, BUD["repair"]) | {"input_canonical_sha256": e["input_canonical_sha256"]}
                    for i, e in zip(cls.ids, cls.m["cases"])]
            (cls.run_dir / "records.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
            RU.seal(cls.run_dir, cls.m)
        finally:
            del os.environ["SOTA7_GOLD_PATH"]
        cls.pub, cls.cases = pub, cases

    @classmethod
    def tearDownClass(cls):
        for p in cls.t.rglob("*"):
            try:
                os.chmod(p, 0o755)
            except OSError:
                pass
        shutil.rmtree(cls.t)

    def recs(self):
        return [json.loads(l) for l in (self.run_dir / "records.jsonl").read_text().splitlines()]

    def test_sandbox_sees_only_the_public_case(self):
        for r in self.recs():
            self.assertEqual(r["sandbox_visible_files"], ["case.json", "spec.json"])

    def test_sandbox_env_drops_gold_variables(self):
        os.environ["SOTA7_GOLD_PATH"] = "/secret"
        try:
            d, env = B.sandbox(self.cases[self.ids[0]], self.pub)
            shutil.rmtree(d)
        finally:
            del os.environ["SOTA7_GOLD_PATH"]
        self.assertNotIn("SOTA7_GOLD_PATH", env)

    def test_gold_canary_never_reaches_outputs(self):
        for p in self.run_dir.rglob("*"):
            if p.is_file():
                self.assertNotIn(CANARY, p.read_text(errors="ignore"), p)

    def test_records_are_read_only_and_sealed(self):
        self.assertFalse(os.access(self.run_dir / "records.jsonl", os.W_OK) and os.geteuid() != 0)
        RU.verify_seal(self.run_dir)

    def test_modified_record_detected(self):
        t = Path(tempfile.mkdtemp())
        try:
            shutil.copytree(self.run_dir, t / "run")
            p = t / "run" / "records.jsonl"
            os.chmod(p, 0o644)
            p.write_text(p.read_text().replace('"NO_REPAIR_IN_GRAMMAR"', '"MINIMAL_REPAIR"'))
            with self.assertRaisesRegex(RuntimeError, "modified after sealing"):
                RU.verify_seal(t / "run")
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_genuine_certificates_replay(self):
        for r in self.recs():
            self.assertEqual(RP.replay_one(r, self.cases[r["case_id"]], self.run_dir, shutil.which("lean"),
                                           shutil.which("leanchecker"))["replay"], "VERIFIED")

    def _replay_text(self, r, text):
        t = Path(tempfile.mkdtemp())
        try:
            (t / "certs" / r["case_id"]).mkdir(parents=True)
            (t / "certs" / r["case_id"] / "certificate.lean").write_text(text)
            return RP.replay_one(r, self.cases[r["case_id"]], t, shutil.which("lean"), shutil.which("leanchecker"))
        finally:
            shutil.rmtree(t)

    def _cert(self, r):
        return (self.run_dir / "certs" / r["case_id"] / "certificate.lean").read_text()

    def test_sorry_certificate_rejected(self):
        r = next(x for x in self.recs() if x["claim"]["claim"] == "MINIMAL_REPAIR")
        src = self._cert(r)
        i = src.index("theorem repair_")
        j = src.index(":= by", i)
        k = src.index("\n\n", j) if "\n\n" in src[j:] else src.index("\ntheorem", j)
        bad = src[:j] + ":= by\n  sorry" + src[k:]
        self.assertEqual(self._replay_text(r, bad)["replay"], "REJECTED")

    def test_extra_axiom_rejected(self):
        r = next(x for x in self.recs() if x["claim"]["claim"] == "MINIMAL_REPAIR")
        src = self._cert(r).replace("abbrev Γ", "axiom cheat : False\nabbrev Γ", 1)
        i = src.index("theorem repair_"); j = src.index(":= by", i)
        k = src.index("\ntheorem", j)
        bad = src[:j] + ":= (cheat.elim)\n" + src[k:]
        self.assertEqual(self._replay_text(r, bad)["replay"], "REJECTED")

    def test_statement_substitution_rejected(self):
        r = next(x for x in self.recs() if x["claim"]["claim"] == "MINIMAL_REPAIR")
        bad = self._cert(r).replace("theorem R_source_stmt : (∀ (n : Nat), n ≠ 0 → n / n = 1)",
                                    "theorem R_source_stmt : (∀ (n : Nat), 0 < n → n / n = 1)")
        rep = self._replay_text(r, bad)
        self.assertEqual(rep["replay"], "REJECTED")
        self.assertIn("source identity", rep["reason"])

    def test_missing_certificate(self):
        r = dict(self.recs()[0]); r["certificate"] = None
        self.assertEqual(RP.replay_one(r, self.cases[r["case_id"]], self.run_dir, "lean", "leanchecker")["replay"], "NO_CERTIFICATE")


if __name__ == "__main__":
    unittest.main()
