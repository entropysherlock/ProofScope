import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from hypothesis_duality import analyze_rows
from hypothesis_pilot import graph, HYPOTHESES

class DualityTests(unittest.TestCase):
    def test_four_vertex_graphs(self):
        r=analyze_rows([graph(i) for i in range(64)],HYPOTHESES,"triangle_free")
        self.assertEqual(r["countermodel_count"],23)
        self.assertEqual(len(r["violation_patterns"]),2)
        self.assertEqual(r["assumption_subsets_crosschecked"],32)
        self.assertEqual({frozenset(x["hypotheses"]) for x in r["minimal_sufficient_sets"]},
                         {frozenset(["bipartite"]),frozenset(["forest"]),
                          frozenset(["connected","few_edges"]),frozenset(["connected","max_degree_two"])})
    def test_empty_violation_set_means_no_sufficient_hypotheses(self):
        r=analyze_rows([{"mask":0,"h":True,"goal":False},
                        {"mask":1,"h":False,"goal":True}],["h"],"goal")
        self.assertEqual(r["minimal_sufficient_sets"],[])
    def test_vacuous_sufficiency_is_disclosed(self):
        r=analyze_rows([{"mask":0,"a":False,"goal":False},
                        {"mask":1,"a":False,"goal":True}],["a"],"goal")
        self.assertEqual(r["minimal_sufficient_sets"][0]["admissible_count"],0)
        self.assertIsNone(r["minimal_sufficient_sets"][0]["nonvacuity_witness"])
    def test_reject_non_boolean(self):
        with self.assertRaises(ValueError):
            analyze_rows([{"h":1,"goal":False}],["h"],"goal")

if __name__=="__main__":
    unittest.main()
