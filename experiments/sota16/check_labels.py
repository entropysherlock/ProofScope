"""Compare engine results with the independent labels; exit non-zero on any contradiction."""
import json
import sys
from pathlib import Path

rows = json.loads(Path(sys.argv[1]).read_text())
labels = json.loads(Path(sys.argv[2]).read_text())
config = sys.argv[3] if len(sys.argv) > 3 else "sota16"
st = lambda r, d: (r.get("directions") or {}).get(d, "UNKNOWN")
wrong, checked, unlabelled, by = [], 0, [], {}
for r in rows:
    for d in ("fwd", "bwd"):
        lab = labels[r["id"]][d]
        if st(r, d) == "UNKNOWN":
            continue
        if lab["label"] is None:
            unlabelled.append([r["id"], d, st(r, d)])
            continue
        checked += 1
        by[lab["by"]] = by.get(lab["by"], 0) + 1
        if lab["label"] != st(r, d):
            wrong.append([r["id"], d, st(r, d), lab["label"], lab["by"]])
total = sum(l[d]["label"] is not None for l in labels.values() for d in ("fwd", "bwd"))
rep = {"config": config, "labelled_directions": total, "certified_and_labelled": checked, "label_sources": by,
       "contradictions": wrong, "certified_without_independent_label": unlabelled,
       "open_directions": [[r["id"], d] for r in rows for d in ("fwd", "bwd") if st(r, d) == "UNKNOWN"]}
print(json.dumps(rep, indent=1, ensure_ascii=False))
if len(sys.argv) > 4:
    Path(sys.argv[4]).write_text(json.dumps(rep, indent=1, ensure_ascii=False))
sys.exit(1 if wrong else 0)
