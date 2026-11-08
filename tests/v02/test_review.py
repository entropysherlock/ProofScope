"""Scope-fidelity worksheet tests (v0.3). No Lean or network needed."""

import json
import tempfile
import unittest
from pathlib import Path

from proofscope.review import build, junk_exposure, load_ledger, parse_doc

COMMIT = "4eaee87548250b2682affda7d05d947c05554bae"
DOC = """# Demo result

The following describes the scope of the Lean formalization related to the following accompanying paper(s):

- [Demo paper](../../preprints/Demo/paper.pdf)

## Scope

For every n the demo bound holds.

## Comparator links

| Result | Comparator statement |
| --- | --- |
| Plain link | [A.lean](../ComparatorChallenges/A.lean) |
| Anchored link | [B.lean](../ComparatorChallenges/B.lean#L12) |
"""


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "docs").mkdir()
        (self.root / "ComparatorChallenges").mkdir()
        (self.root / "docs" / "001.md").write_text(DOC)
        (self.root / "ComparatorChallenges" / "A.lean").write_text(
            "import Mathlib\n-- comment\ndef v : ℝ := sInf {x : ℝ | 0 < x}\ntheorem a : v = 0 := by\n  sorry\n")
        (self.root / "ComparatorChallenges" / "B.lean").write_text(
            "def g (s : Set ℝ) : ℝ := sInf s\ntheorem b (s : Set ℝ) (h : s.Nonempty) (hb : BddBelow s) : g s ≤ g s := le_rfl\n")
        (self.root / "ComparatorChallenges" / "Orphan.lean").write_text("theorem o : True := trivial\n")
        self.ledger = self.root / "ledger.json"
        self.ledger.write_text(json.dumps({"commit": COMMIT, "reviews": [
            {"challenge": "A", "verdict": "FAITHFUL", "reviewer": "x", "reviewer_type": "AI_PRELIMINARY",
             "date": "2026-11-08", "notes": "n"}]}))

    def test_parse_doc_accepts_line_anchors(self):
        """Regression: openai/math links like LocalSmoothing.lean#L84 were missed."""
        d = parse_doc(DOC)
        self.assertEqual([c["path"] for c in d["challenges"]],
                         ["../ComparatorChallenges/A.lean", "../ComparatorChallenges/B.lean"])
        self.assertEqual(len(d["papers"]), 1)

    def test_junk_exposure_respects_guards(self):
        self.assertTrue(junk_exposure("def v : ℝ := sInf {x : ℝ | 0 < x}"))
        self.assertFalse(junk_exposure("theorem b (h : s.Nonempty) (hb : BddBelow s) : sInf s ≤ sInf s"))

    def test_build_counts_and_orphans(self):
        s = build(self.root, Path(tempfile.mkdtemp()), self.ledger, COMMIT)
        self.assertEqual(s["scope_documents"], 1)
        self.assertEqual(s["linked_challenges"], 2)
        self.assertEqual(s["missing_links"], 0)
        self.assertEqual(s["with_junk_exposure_flags"], 1)
        self.assertEqual(s["reviewed"], 1)
        self.assertEqual(s["human_reviewed"], 0)
        self.assertEqual(s["challenges_without_scope_document"], ["Orphan"])

    def test_ledger_ignored_for_other_commit(self):
        self.assertEqual(load_ledger(self.ledger, "0" * 40), {})
        self.assertIn("A", load_ledger(self.ledger, COMMIT))

    def test_invalid_verdict_rejected(self):
        bad = self.root / "bad.json"
        bad.write_text(json.dumps({"commit": COMMIT, "reviews": [
            {"challenge": "A", "verdict": "PROVED_CORRECT", "reviewer": "x", "reviewer_type": "HUMAN",
             "date": "d", "notes": "n"}]}))
        with self.assertRaises(ValueError):
            load_ledger(bad, COMMIT)


if __name__ == "__main__":
    unittest.main()
