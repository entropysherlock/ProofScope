"""v0.8: dossier identity must survive identical constant names declared in different modules."""
import json
import tempfile
import unittest
from pathlib import Path

from proofscope import dossier as D
from proofscope import research as R


def rec(module, name, axioms=("propext",)):
    return {"theorem_id": name, "module": module, "axioms": list(axioms), "hypotheses": [], "binders": [],
            "conclusion": "True", "conclusion_shape": "True", "elaborated_type": "True", "kind": "theorem",
            "statement_dependencies": [], "proof_dependencies": [], "unresolved_items": [],
            "universe_params": [], "source_locations": {}}


class IdentityTests(unittest.TestCase):
    def test_same_name_two_modules_two_files(self):
        a, b = rec("RC.BassTrace", "OAI.BassTrace.K0.idem"), rec("RC.BassTorsionFree", "OAI.BassTrace.K0.idem")
        self.assertNotEqual(D.dossier_key(a), D.dossier_key(b))
        self.assertNotEqual(D.dossier_stem(a), D.dossier_stem(b))

    def test_stem_is_deterministic_and_bounded(self):
        r = rec("M" * 300, "x" * 300)
        self.assertEqual(D.dossier_stem(r), D.dossier_stem(dict(r)))
        self.assertLessEqual(len(D.dossier_stem(r)), 160)

    def test_annotate_rejects_count_mismatch(self):
        t = Path(tempfile.mkdtemp())
        (t / "raw" / "dossiers").mkdir(parents=True)
        (t / "raw" / "dossier_index.json").write_text(json.dumps({"theorems": [{}, {}]}))
        (t / "raw" / "dossiers" / "one.json").write_text(json.dumps(rec("M", "a")))
        (t / "proj").mkdir()
        (t / "proj" / "selection.json").write_text(json.dumps({"selected": [], "corpus_commit": "c",
                                                               "mathlib_rev": "m"}))
        with self.assertRaisesRegex(RuntimeError, "DOSSIER_COUNT_MISMATCH"):
            R.annotate(t, t / "proj", t / "raw" / "dossiers", t / "out")


if __name__ == "__main__":
    unittest.main()
