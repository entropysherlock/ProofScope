"""Exact finite-model counterexample/hitting-set duality.

A set of hypotheses implies the conclusion on enumerated models iff it
intersects the violated-hypothesis set for every countermodel.
This is established hypergraph duality, not a novel mathematical theorem.
"""
import argparse
from itertools import combinations
import json
from pathlib import Path
from hypothesis_pilot import graph, HYPOTHESES

def subsets(items):
    return [frozenset(s) for n in range(len(items)+1) for s in combinations(items,n)]

def analyze_rows(rows, hypotheses, target):
    names=tuple(hypotheses)
    if not rows or len(set(names))!=len(names) or target in names:
        raise ValueError("Invalid empty input or duplicate/overlapping predicate names")
    if any(any(type(r.get(h)) is not bool for h in (*names,target)) for r in rows):
        raise ValueError("All predicate evaluations must be Boolean")
    bad=[r for r in rows if not r[target]]
    violation_sets={frozenset(h for h in names if not r[h]) for r in bad}
    def hit(S):
        return all(bool(S & V) for V in violation_sets)
    def direct(S):
        return all(r[target] for r in rows if all(r[h] for h in S))
    candidates=subsets(names)
    assert all(hit(S)==direct(S) for S in candidates)
    minimal=[S for S in candidates if hit(S) and all(not hit(S-{h}) for h in S)]
    evidence=[]
    for S in minimal:
        admissible=[r for r in rows if all(r[h] for h in S)]
        removal={}
        for h in sorted(S):
            witness=next((r for r in bad if all(r[x] for x in S-{h})),None)
            assert witness is not None
            removal[h]=witness.get("mask",rows.index(witness))
        evidence.append({
            "hypotheses":[h for h in names if h in S],
            "admissible_count":len(admissible),
            "nonvacuity_witness":admissible[0].get("mask",rows.index(admissible[0])) if admissible else None,
            "removal_counterexamples":removal
        })
    return {
        "model_count":len(rows),
        "countermodel_count":len(bad),
        "violation_patterns":[[h for h in names if h in V] for V in sorted(violation_sets,key=lambda V:(len(V),tuple(sorted(V))))],
        "assumption_subsets_crosschecked":len(candidates),
        "sufficient_subsets":sum(hit(S) for S in candidates),
        "minimal_sufficient_sets":evidence,
        "limit":"Finite enumeration only; not a Lean kernel proof or a new mathematical result"
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="duality-evidence")
    args=ap.parse_args()
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=True)
    result=analyze_rows([graph(i) for i in range(64)],HYPOTHESES,"triangle_free")
    (out/"duality.json").write_text(json.dumps(result,indent=2)+"\n")
    lines=["# ProofScope — Counterexample/hitting-set pilot","",
           "Status: exhaustive finite-model computation, **not Lean certified**.","",
           f"Models: {result['model_count']}; countermodels: {result['countermodel_count']}; "
           f"distinct violation patterns: {len(result['violation_patterns'])}.","",
           "Every assumption subset is independently crosschecked against direct model enumeration.","",
           "## Minimal sufficient sets"]
    for e in result["minimal_sufficient_sets"]:
        lines.append("- "+", ".join(e["hypotheses"])+
                     f"; admissible={e['admissible_count']}; nonvacuity mask={e['nonvacuity_witness']}; "+
                     "deletion counterexamples="+json.dumps(e["removal_counterexamples"]))
    lines += ["","This is elementary hypergraph-transversal duality, not a new theorem.",
              "Paper fidelity and Lean kernel checking remain outside this pilot."]
    (out/"REPORT.md").write_text("\n".join(lines)+"\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
