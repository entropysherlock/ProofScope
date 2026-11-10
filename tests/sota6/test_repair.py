"""SOTA-6 adversarial tests for certified minimal repair. Each test states its expected result."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from proofscope.experimental import repair as RP
from proofscope.toolchain import Toolchain

HAVE = bool(shutil.which("lean") and shutil.which("leanchecker"))
SPECS = Path(__file__).resolve().parents[2] / "research/sota6/repair"


def spec(name, **over):
    s = json.loads((SPECS / f"{name}.json").read_text())
    s.update(over)
    return s


@unittest.skipUnless(HAVE, "Lean 4.34.1 and leanchecker required")
class Repair(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.tc = Toolchain.find()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_(self, s):
        return RP.run(s, self.tmp / s["id"], self.tc)

    def test_two_distinct_minimal_repairs_and_valid_nonminimal_excluded(self):
        """Expected: n ≠ 0 and 0 < n are both minimal (cost 1); the cost-2 combination is valid but not
        reported as minimal; 2 ≤ n (true statement, wrong region) is separated at n = 1."""
        r = self.run_(spec("r1_division_nonzero"))
        self.assertEqual(r["outcome"], "MINIMAL_REPAIR")
        self.assertEqual(sorted(x["mask"] for x in r["repairs"]), [1, 2])
        self.assertEqual(r["separations"][4], {"n": 1})

    def test_forged_separation_witness_is_rejected(self):
        """Hostile: the search claims the empty edit is separated at n = 1 (it is not). Expected: the kernel
        `decide` fails, nothing certified."""
        orig = RP.parse_eval

        def forged(out):
            t = orig(out)
            if t:
                t[0] = (t[0][0], 1)          # point index 1 = {n: 1}
            return t
        RP.parse_eval = forged
        try:
            r = self.run_(spec("r1_division_nonzero"))
        finally:
            RP.parse_eval = orig
        self.assertFalse(r["certified"])
        self.assertEqual(r["outcome"], "UNKNOWN")

    def test_source_substitution_attack_is_rejected(self):
        """Hostile: the candidate's structured form claims hypothesis n ≠ 0 while its source text has none.
        Expected: the source-link theorem fails, nothing certified."""
        s = spec("r1_division_nonzero", id="r1_subst", candidate={"hyps": ["n ≠ 0"], "concl": "n / n = 1"})
        r = self.run_(s)
        self.assertFalse(r["certified"])

    def test_failed_proof_search_is_not_negative(self):
        """Expected: with a portfolio that proves nothing, no repair is claimed, and no-repair is not claimed
        either (unseparated masks remain UNKNOWN)."""
        orig = RP.PORTFOLIO
        RP.PORTFOLIO = ["exact absurd"]
        try:
            r = self.run_(spec("r2_square_order"))
        finally:
            RP.PORTFOLIO = orig
        self.assertNotIn(r["outcome"], ("MINIMAL_REPAIR", "VERIFIED_REPAIR", "NO_REPAIR_IN_GRAMMAR"))
        self.assertEqual([u["mask"] for u in r["unknown_masks"]], [1, 3, 5, 7, 9, 11, 13, 15][:len(r["unknown_masks"])])

    def test_grammar_without_repair_is_certified_as_such(self):
        """Expected: if the only edit is `0 ≤ x`, no mask repairs r3, and that is certified (every mask
        separated at an explicit point)."""
        s = spec("r3_conclusion_disjunct", id="r3_norepair", edits=[{"add_hyp": "0 ≤ x"}])
        r = self.run_(s)
        self.assertEqual(r["outcome"], "NO_REPAIR_IN_GRAMMAR")
        self.assertTrue(r["certified"])

    def test_vacuous_reference_is_matched_only_by_the_same_empty_region(self):
        """A vacuous reference (`n < 0` over ℕ). Expected: the empty edit is separated (regions differ);
        adding `n < 0` is the minimal repair. Formulation equivalence treats the two vacuous statements as
        the same formulation; the report must not call either a meaningful theorem (documented limitation)."""
        s = {"id": "vac", "context": [["n", "Nat"]],
             "reference_source": "∀ (n : Nat), n < 0 → n = 5", "candidate_source": "∀ (n : Nat), n = 5",
             "reference": {"hyps": ["n < 0"], "concl": "n = 5"}, "candidate": {"hyps": [], "concl": "n = 5"},
             "edits": [{"add_hyp": "n < 0"}, {"add_hyp": "n = 5"}], "pool": {"n": [0, 1, 5]}}
        r = self.run_(s)
        self.assertEqual(r["outcome"], "MINIMAL_REPAIR")
        self.assertEqual([x["mask"] for x in r["repairs"]], [1])


if __name__ == "__main__":
    unittest.main()
