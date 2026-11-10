"""SOTA-15 ScopeElim engine: fragment detection, abstention, certificates and the soundness gate."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from proofscope import scopeelim as se
from proofscope.scope_expr import Unsupported, evaluate, parse, to_lean
from proofscope.toolchain import Toolchain

ROOT = Path(__file__).resolve().parents[2]


def horn(i, ref, frm, symbols=None):
    return {"id": i, "kind": "horn", "symbols": symbols or {"S": 1}, "reference": ref, "formal": frm}


def cl(var, bound, prems, concl, guard="True", **kw):
    return {"vars": [[var, bound]], "guard": guard, "prems": prems, "concl": concl, **kw}


class TestExpr(unittest.TestCase):
    def test_nat_semantics(self):
        self.assertEqual(evaluate(parse("3 - 5 + 7 / 0 + 7 % 0"), {}), 7)
        self.assertEqual(to_lean(parse("Nat.gcd (n + 1) 6 = 1")), "((Nat.gcd (n + 1) 6) = 1)")

    def test_unparsed_input_abstains(self):
        for s in ["∃ k, k < 2 ^ n", "a ∣ b", "n < 2 ^ n ↔ True"]:
            with self.assertRaises(Unsupported):
                parse(s)

    def test_detect_abstains_outside_fragment(self):
        base = {"id": "x", "binders": [["n", "Nat"]], "ref_hyp": "True", "lean_hyp": "True"}
        bad = [{"ref_concl": "n * n ≤ 2 ^ n", "lean_concl": "n < 2 ^ n"},            # two symbols
               {"ref_concl": "2 ^ n < 2 ^ (n + 1)", "lean_concl": "n < 2 ^ n"},      # two occurrences
               {"ref_concl": "n < 3 ^ n", "lean_concl": "n < 2 ^ n"},                # two live positions
               {"ref_concl": "n + 0 = n", "lean_concl": "n = n"}]                    # no symbol
        for b in bad:
            with self.assertRaises(Unsupported):
                se.detect({**base, **b})
        with self.assertRaises(Unsupported):
            se.detect({**base, "binders": [["n", "Int"]], "ref_concl": "n < 2 ^ n", "lean_concl": "n ≤ 2 ^ n"})

    def test_detect_fragments(self):
        base = {"id": "x", "binders": [["n", "Nat"]]}
        f = se.detect({**base, "ref_hyp": "True", "ref_concl": "n < 2 ^ n", "lean_hyp": "True", "lean_concl": "n ≤ 2 ^ n"})
        self.assertEqual((f["fragment"], f["position"]), ("func", 1))
        h = se.detect({**base, "ref_hyp": "Nat.gcd n 6 = 1", "ref_concl": "Nat.gcd (n + 1) 6 = 1",
                       "lean_hyp": "Nat.gcd n 6 = 1", "lean_concl": "Nat.gcd (n + 2) 6 = 1"})
        self.assertEqual((h["fragment"], h["position"], h["const"]), ("horn", 0, 1))


@unittest.skipUnless(shutil.which("lean"), "Lean not on PATH")
class TestEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="ps_sota15_"))
        base = Toolchain.find()
        b = se.build_lib(base, cls.tmp / "lib")
        assert b["ok"], b
        cls.tc = se.lib_toolchain(base, cls.tmp / "lib")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_spec(self, spec):
        return se.compare(spec, self.tc, self.tmp / "lib", self.tmp / "work" / spec["id"])

    def test_bounded_reference_used_twice(self):
        r = self.run_spec(horn("b_twice", [cl("x", "8", [["S", ["x"]]], ["S", ["x + 1"]])],
                               [cl("y", "6", [["S", ["y"]]], ["S", ["y + 2"]])]))
        self.assertEqual(r["verdict"], "LEAN_WEAKER")
        self.assertTrue(r["complete_fragment"])
        self.assertEqual(r["axioms"]["fwd"], [])

    def test_bounded_identical_and_vacuous(self):
        c = cl("x", "4", [["S", ["x"]]], ["S", ["x + 1"]])
        self.assertEqual(self.run_spec(horn("b_same", [c], [c]))["verdict"], "SCHEMA_EQUIVALENT")
        r = self.run_spec(horn("b_vac", [c], [cl("y", "4", [], ["S", ["0"]], guard="False")]))
        self.assertEqual(r["directions"]["fwd"], "ENTAILS")
        self.assertTrue(r["vacuous"]["fwd"])

    def test_local_rule_and_dependent_bound(self):
        ref = [{"vars": [["x", "3"], ["y", "x + 1"]], "guard": "y < x", "prems": [["S", ["y"]]], "concl": ["S", ["x"]]}]
        frm = [cl("a", "3", [], ["S", ["a"]], locals=[{"prems": [], "concl": ["S", ["0"]]}])]
        r = self.run_spec(horn("b_local", ref, frm))
        self.assertEqual(r["directions"]["fwd"], "ENTAILS")
        self.assertEqual(r["verdict"], "INCONCLUSIVE")           # converse is outside the definite fragment
        self.assertIn("bwd", r["notes"])

    def test_symbolic_and_function(self):
        r = self.run_spec(horn("s_twice", [cl("x", None, [["S", ["x"]]], ["S", ["x + 1"]])],
                               [cl("y", None, [["S", ["y"]]], ["S", ["y + 2"]])]))
        self.assertEqual(r["verdict"], "LEAN_WEAKER")
        f = self.run_spec({"id": "f_vac", "kind": "func",
                           "reference": {"var": "n", "guard": "True", "arg": "n", "rel": "w < n"},
                           "formal": {"var": "n", "guard": "True", "arg": "n + 1", "rel": "w = 7"}})
        self.assertEqual(f["verdict"], "LEAN_WEAKER")
        self.assertTrue(f["reference_vacuous"])

    def test_search_is_not_trusted(self):
        """A wrong search result (here: a forged 'derivation') must end in an abstention."""
        orig = se._bounded_direction
        se._bounded_direction = lambda R, F: {"status": "ENTAILS", "active": 1,
                                              "tactics": [f"intro {R.args()} hR; sorry", f"intro {R.args()} hR; exact hR"]}
        try:
            r = self.run_spec(horn("b_forged", [cl("x", "3", [], ["S", ["0"]], guard="False")],
                                   [cl("y", "3", [], ["S", ["y"]])]))
        finally:
            se._bounded_direction = orig
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertEqual(r["certificates"], [])

    def test_claimdelta_adapter(self):
        base = {"binders": [["n", "Nat"]]}
        twice = {**base, "id": "a_twice", "ref_hyp": "Nat.gcd n 6 = 1", "ref_concl": "Nat.gcd (n + 1) 6 = 1",
                 "lean_hyp": "Nat.gcd n 6 = 1", "lean_concl": "Nat.gcd (n + 2) 6 = 1"}
        shift = {**base, "id": "a_shift", "ref_hyp": "1 ≤ n", "ref_concl": "n < 2 ^ n",
                 "lean_hyp": "True", "lean_concl": "n + 1 < 2 ^ (n + 1)"}
        self.assertEqual(se.compare_claimdelta(twice, self.tc, self.tmp / "w1")["verdict"], "LEAN_WEAKER")
        self.assertEqual(se.compare_claimdelta(shift, self.tc, self.tmp / "w2")["verdict"], "SCHEMA_EQUIVALENT")
        mislinked = {**shift, "id": "a_mislink", "binders": [["n", "Nat"]], "ref_concl": "n < 2 ^ n ∧ True"}
        r = se.compare_claimdelta(mislinked, self.tc, self.tmp / "w3")
        self.assertIn(r["verdict"], ("SCHEMA_EQUIVALENT", "INCONCLUSIVE"))

    def test_frozen_v08_labels_never_contradicted(self):
        d = ROOT / "proofscope" / "benchmark" / "claimdelta_v08"
        ok = {"SCHEMA_EQUIVALENT": {"SCHEMA_EQUIVALENT"}, "CLAIM_LEAN_WEAKER": {"LEAN_WEAKER"},
              "CLAIM_LEAN_STRONGER": {"LEAN_STRONGER"}, "CLAIM_INCOMPARABLE": {"INCOMPARABLE"}}
        decided = 0
        for p in sorted(d.glob("*.json")):
            spec = json.loads(p.read_text())
            try:
                se.detect(spec)
            except Unsupported:
                continue
            v = se.compare_claimdelta(spec, self.tc, self.tmp / "v08" / spec["id"])["verdict"]
            if v != "INCONCLUSIVE":
                decided += 1
                self.assertIn(v, ok.get(spec["expected_claimdelta"], set()), spec["id"])
        self.assertGreaterEqual(decided, 5)


if __name__ == "__main__":
    unittest.main()
