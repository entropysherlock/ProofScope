"""Exact finite-model hypothesis sensitivity pilot for four-vertex simple graphs.

Exhaustive Python check only: NOT a Lean kernel certificate or a new theorem.
"""
import argparse
import itertools
import json
from pathlib import Path

VERTICES = range(4)
EDGES = list(itertools.combinations(VERTICES, 2))
HYPOTHESES = ("connected", "few_edges", "max_degree_two", "bipartite", "forest")

def graph(mask):
    assert 0 <= mask < 64
    edges = [e for i,e in enumerate(EDGES) if mask & (1 << i)]
    adj = [set() for _ in VERTICES]
    for a,b in edges:
        adj[a].add(b)
        adj[b].add(a)
    seen, queue = {0}, [0]
    for v in queue:
        for w in sorted(adj[v] - seen):
            seen.add(w)
            queue.append(w)
    colors = {}
    bipartite = True
    for start in VERTICES:
        if start in colors: continue
        colors[start], q = 0, [start]
        for v in q:
            for w in sorted(adj[v]):
                if w not in colors:
                    colors[w] = 1 - colors[v]
                    q.append(w)
                elif colors[w] == colors[v]:
                    bipartite = False
    parent = list(VERTICES)
    def root(x):
        while parent[x] != x:
            x = parent[x]
        return x
    forest = True
    for a,b in edges:
        ra, rb = root(a), root(b)
        if ra == rb:
            forest = False
        else:
            parent[ra] = rb
    has_triangle = any(
        all(b in adj[a] for a,b in itertools.combinations(t,2))
        for t in itertools.combinations(VERTICES,3)
    )
    return {
        "mask":mask, "edges":[list(e) for e in edges],
        "connected":len(seen)==4,
        "few_edges":len(edges)<=3,
        "max_degree_two":max(map(len,adj))<=2,
        "bipartite":bipartite,
        "forest":forest,
        "triangle_free":not has_triangle,
    }

def holds(row, hs):
    return all(row[h] for h in hs)

def analyze():
    rows = [graph(i) for i in range(64)]
    valid, invalid = {}, {}
    for n in range(len(HYPOTHESES)+1):
        for hs in itertools.combinations(HYPOTHESES,n):
            key = "|".join(hs) or "(none)"
            allowed = [r for r in rows if holds(r, hs)]
            bad = [r for r in allowed if not r["triangle_free"]]
            if bad:
                invalid[key] = {"hypotheses":list(hs), "counterexample":bad[0]["mask"], "bad_count":len(bad)}
            else:
                valid[key] = {"hypotheses":list(hs), "admissible_count":len(allowed),
                              "nonvacuity_witness":allowed[0]["mask"] if allowed else None}
    minimal = []
    for v in valid.values():
        hs = v["hypotheses"]
        if all(any(holds(r,[x for x in hs if x!=removed]) and not r["triangle_free"]
                   for r in rows) for removed in hs):
            minimal.append(v)
    assert all(v["nonvacuity_witness"] is not None for v in minimal)
    return {
        "universe":"all 64 simple graphs on labeled vertices 0,1,2,3",
        "edge_bit_order":[list(e) for e in EDGES],
        "target":"triangle_free", "hypotheses":list(HYPOTHESES),
        "minimal_sufficient_subsets":minimal, "valid_subsets":valid,
        "invalid_subsets":invalid, "rows":rows,
        "limits":["Finite, labeled, four-vertex graphs only",
                  "Exhaustive Python check, not Lean kernel verification",
                  "These elementary graph facts are not new mathematics"],
    }

def verify(report):
    rows = [graph(i) for i in range(64)]
    assert report["rows"] == rows
    for v in report["valid_subsets"].values():
        allowed = [r for r in rows if holds(r,v["hypotheses"])]
        assert allowed and all(r["triangle_free"] for r in allowed)
        assert len(allowed) == v["admissible_count"]
        assert holds(rows[v["nonvacuity_witness"]],v["hypotheses"])
    for v in report["invalid_subsets"].values():
        r = rows[v["counterexample"]]
        assert holds(r,v["hypotheses"]) and not r["triangle_free"]
    for v in report["minimal_sufficient_subsets"]:
        hs = v["hypotheses"]
        for removed in hs:
            assert any(holds(r,[x for x in hs if x!=removed]) and not r["triangle_free"]
                       for r in rows)
    return True

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output",default="hypothesis-evidence")
    args = p.parse_args()
    dest = Path(args.output)
    dest.mkdir(parents=True,exist_ok=True)
    report = analyze()
    verify(report)
    (dest/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    lines = ["# ProofScope: finite-model hypothesis sensitivity pilot","",
             "**Scope:** all 64 four-vertex labeled simple graphs. **Not Lean certified.**","",
             "## Minimal sufficient assumption sets",""]
    for v in report["minimal_sufficient_subsets"]:
        hs = v["hypotheses"]
        lines.append(f"- {', '.join(hs)}; admissible graphs: {v['admissible_count']}; "
                     f"non-vacuity witness mask: {v['nonvacuity_witness']}")
        for removed in hs:
            reduced = [x for x in hs if x != removed]
            witness = next(r for r in report["rows"]
                           if holds(r,reduced) and not r["triangle_free"])
            lines.append(f"  - Remove {removed}: counterexample mask {witness['mask']}, "
                         f"edges {witness['edges']}")
    lines += ["","## Meaning","","Multiple incomparable minimal sufficient "
              "assumption sets can exist, so a single greedy deletion path can miss them.",
              "These are elementary graph facts, not new mathematics.",
              "No Lean kernel verification or paper-to-Lean fidelity is established."]
    (dest/"REPORT.md").write_text("\n".join(lines)+"\n")
    print("PASS: exhaustive four-vertex enumeration and report consistency check")
    print("Minimal sets:",[x["hypotheses"] for x in report["minimal_sufficient_subsets"]])
    print("Sufficient subsets:",len(report["valid_subsets"]),"/32")
    print("Evidence:",dest)

if __name__ == "__main__":
    main()
