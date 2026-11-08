import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import unittest
from hypothesis_pilot import graph, analyze, verify

class PilotTests(unittest.TestCase):
    def test_every_graph(self):
        self.assertEqual(len([graph(i) for i in range(64)]),64)
    def test_all_certificates(self):
        self.assertTrue(verify(analyze()))
    def test_minimal_sets(self):
        sets={tuple(x["hypotheses"]) for x in analyze()["minimal_sufficient_subsets"]}
        self.assertEqual(sets,{("bipartite",),("forest",),("connected","few_edges"),("connected","max_degree_two")})
    def test_counterexample(self):
        self.assertFalse(graph(11)["triangle_free"])
        self.assertTrue(graph(11)["few_edges"])

if __name__ == "__main__":
    unittest.main()
