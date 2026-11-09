"""Research Audit (v0.6): theorem dossiers for real research statements.

    python3 -m proofscope.research prepare --oai-lean DIR --commit SHA --out PROJECT [--limit N]
    python3 -m proofscope.research annotate --oai-lean DIR --project PROJECT --dossiers DIR --out DIR

`prepare` builds a Lake project that requires Mathlib at exactly the revision pinned by the audited corpus and
copies the comparator challenge statements into it unchanged (module `ResearchChallenges.<Name>`), selecting
statements round-robin across subject areas. Challenges that import the corpus's own modules (not only Mathlib)
are excluded and counted. `annotate` merges provenance into each dossier: corpus commit, source path and hash,
subject area, the scope document and the papers it cites (the paper → Lean link), and the artifact kind.

Comparator challenges are *statements*: their proofs are `sorry` by design, so `axiom_status = SORRY` is expected
and is reported as STATEMENT_ONLY, not as a defect.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

from .review import parse_doc


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _area_map(lean: Path) -> dict[str, str]:
    """challenge stem → subject area, from the corpus catalog (`OAI/<Area>/...`) when available."""
    out: dict[str, str] = {}
    cat = lean / "formalization.yaml"
    if cat.is_file():
        try:
            import yaml
            for e in (yaml.safe_load(cat.read_text()).get("status") or {}).get("main_results") or []:
                stem = Path(e.get("comparator_config", "")).stem
                parts = e.get("file", "").split("/")
                if stem and len(parts) > 2 and parts[0] == "OAI":
                    out.setdefault(stem, parts[1])
        except ImportError:
            pass
    return out


def _doc_map(lean: Path) -> dict[str, dict]:
    m: dict[str, dict] = {}
    for d in sorted((lean / "docs").glob("*.md")):
        info = parse_doc(d.read_text(errors="replace"))
        for c in info["challenges"]:
            m.setdefault(Path(c["path"]).stem, {"scope_document": f"lean/docs/{d.name}", "title": info["title"],
                                                "papers": info["papers"], "result": c["result"]})
    return m


def prepare(lean: Path, commit: str, out: Path, limit: int) -> dict:
    manifest = json.loads((lean / "lake-manifest.json").read_text())
    ml = next(p for p in manifest["packages"] if p["name"] == "mathlib")
    out.mkdir(parents=True, exist_ok=True)
    (out / "ResearchChallenges").mkdir(exist_ok=True)
    shutil.copy(lean / "lean-toolchain", out / "lean-toolchain")
    (out / "lakefile.toml").write_text(
        'name = "research"\n\n[[require]]\nname = "mathlib"\n'
        f'git = "{ml["url"]}"\nrev = "{ml["rev"]}"\n\n[[lean_lib]]\nname = "ResearchChallenges"\n')
    areas = _area_map(lean)
    pool: dict[str, list[Path]] = {}
    excluded = []
    for f in sorted((lean / "ComparatorChallenges").glob("*.lean")):
        imports = re.findall(r"^import\s+(\S+)", f.read_text(errors="replace"), re.M)
        if any(not (i == "Mathlib" or i.startswith("Mathlib.")) for i in imports):
            excluded.append(f.stem)
            continue
        pool.setdefault(areas.get(f.stem, "Uncatalogued"), []).append(f)
    chosen: list[tuple[str, Path]] = []
    queues = {a: list(v) for a, v in sorted(pool.items())}
    while len(chosen) < limit and any(queues.values()):
        for a in list(queues):
            if queues[a] and len(chosen) < limit:
                chosen.append((a, queues[a].pop(0)))
    sel = []
    for area, f in chosen:
        dst = out / "ResearchChallenges" / f.name
        shutil.copy(f, dst)
        sel.append({"module": f"ResearchChallenges.{f.stem}", "challenge": f.stem, "area": area,
                    "source_path": f"lean/ComparatorChallenges/{f.name}", "sha256": _sha(f)})
    info = {"corpus_commit": commit, "mathlib_rev": ml["rev"], "toolchain": (lean / "lean-toolchain").read_text().strip(),
            "selected": sel, "areas": sorted({s["area"] for s in sel}),
            "excluded_non_mathlib_imports": excluded, "available": sum(len(v) for v in pool.values())}
    (out / "selection.json").write_text(json.dumps(info, indent=2))
    return info


def annotate(lean: Path, project: Path, dossiers: Path, out: Path) -> dict:
    sel = json.loads((project / "selection.json").read_text())
    by_mod = {s["module"]: s for s in sel["selected"]}
    docs = _doc_map(lean)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    inputs = sorted(dossiers.glob("*.json"))
    index = dossiers.parent / "dossier_index.json"
    if index.exists():
        extracted = len(json.loads(index.read_text())["theorems"])
        if extracted != len(inputs):
            raise RuntimeError(f"DOSSIER_COUNT_MISMATCH: index lists {extracted} records, {len(inputs)} files present")
    skipped = []
    for p in inputs:
        d = json.loads(p.read_text())
        s = by_mod.get(d.get("module"))
        if not s:
            skipped.append(d.get("dossier_key") or d.get("theorem_id"))
            continue
        d["source_commit"] = sel["corpus_commit"]
        d["corpus"] = "https://github.com/openai/math"
        d["area"] = s["area"]
        d["source_path"] = s["source_path"]
        d["source_sha256"] = s["sha256"]
        d["artifact_kind"] = "comparator challenge statement (proof is sorry by design)"
        if d["axiom_status"] == "SORRY":
            d["trust_status"] = "STATEMENT_ONLY"
        elif d["axiom_status"] in ("NONE", "STANDARD"):
            d["trust_status"] = "PROVED_STANDARD_AXIOMS"
        else:
            d["trust_status"] = "NONSTANDARD_AXIOMS"
        tr = docs.get(s["challenge"])
        d["paper_trace"] = ({"scope_document": tr["scope_document"], "result": tr["result"],
                             "papers": tr["papers"], "status": "LINKED_BY_CORPUS_DOCS",
                             "semantic_review": "NOT_REVIEWED"} if tr else {"status": "NO_SCOPE_DOCUMENT"})
        (out / p.name).write_text(json.dumps(d, indent=2, ensure_ascii=False))
        rows.append(d)
    summary = {"input_records": len(inputs), "dossiers": len(rows),
               "skipped_not_in_selection": skipped, "areas": sorted({r["area"] for r in rows}),
               "theorems": sum(r["kind"] == "theorem" for r in rows),
               "by_trust_status": {k: sum(r["trust_status"] == k for r in rows)
                                   for k in ("STATEMENT_ONLY", "PROVED_STANDARD_AXIOMS", "NONSTANDARD_AXIOMS")},
               "by_kernel_status": {k: sum(r["kernel_status"] == k for r in rows)
                                    for k in ("REPLAYED", "REPLAY_FAILED", "NOT_REPLAYED")},
               "with_paper_trace": sum(r["paper_trace"]["status"] == "LINKED_BY_CORPUS_DOCS" for r in rows),
               "corpus_commit": sel["corpus_commit"], "mathlib_rev": sel["mathlib_rev"]}
    (out / "research_index.json").write_text(json.dumps(summary, indent=2))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m proofscope.research")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--oai-lean", required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int, default=150)
    q = sub.add_parser("annotate")
    q.add_argument("--oai-lean", required=True)
    q.add_argument("--project", required=True)
    q.add_argument("--dossiers", required=True)
    q.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "prepare":
        info = prepare(Path(a.oai_lean), a.commit, Path(a.out), a.limit)
        print(json.dumps({k: (v if k != "selected" else len(v)) for k, v in info.items() if k != "excluded_non_mathlib_imports"}
                         | {"excluded": len(info["excluded_non_mathlib_imports"])}, indent=2))
        print(" ".join(s["module"] for s in info["selected"]), file=open(Path(a.out) / "modules.txt", "w"))
    else:
        s = annotate(Path(a.oai_lean), Path(a.project), Path(a.dossiers), Path(a.out))
        print(json.dumps(s, indent=2))
        print("\nVERDICT\n - " + (f"{s['dossiers']} research-statement dossiers across {len(s['areas'])} areas, "
                                  f"{s['with_paper_trace']} linked to papers by the corpus's scope documents. They show "
                                  "what Lean elaborated; they do not say any statement matches its paper."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
