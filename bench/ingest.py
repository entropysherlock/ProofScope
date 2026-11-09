"""Build the candidate pool (cases + source labels, kept in separate files) from public sources.

    python -m bench.ingest epla --assess-dir DIR --out pool/        # ASSESS repo at a pinned commit
    python -m bench.ingest proofnetverif --split test --out pool/   # Hugging Face PAug/ProofNetVerif (runner only)

Source labels are what the source published. They are NOT gold: gold comes only from the blinded
adjudication. They are written to `source_labels.jsonl`, never into `cases.jsonl`.
Every source is a vendor-home benchmark for at least one competitor (EPLA: ASSESS/TransTED;
ProofNetVerif: BEq+, and SemantEq re-adjudicated its test split); results on these slices are reported
per source and never pooled with the new independent holdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .canonical import norm_hash, validate, write_jsonl


def _cid(*parts: str) -> str:
    return "c-" + hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:12]


def epla(assess_dir: Path) -> tuple[list[dict], list[dict]]:
    import subprocess
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=assess_dir, capture_output=True, text=True).stdout.strip()
    cases, labels = [], []
    for split, fname in (("epla-minif2f", "EPLA-miniF2F.json"), ("epla-proofnet", "EPLA-ProofNet.json")):
        data = json.loads((assess_dir / "benchmark" / fname).read_text())
        for e in data:
            for j, s in enumerate(e["sub_questions"]):
                c = {"case_id": _cid(split, str(e["id"]), str(j)), "group": f"{split}:{e['name']}", "source": split,
                     "source_ref": f"{fname}#id={e['id']}/sub={j}", "ref_header": e["header"], "ref_decl": e["FL (Label)"],
                     "cand_header": s["header"], "cand_decl": s["FL (Prediction)"],
                     "informal": e.get("NL"), "generator": s.get("tag"),
                     "provenance": {"repo": "https://github.com/XiaoyangLiu-sjtu/ASSESS", "commit": commit,
                                    "license": "Apache-2.0", "file": f"benchmark/{fname}"}}
                assert not validate(c), validate(c)
                cases.append(c)
                labels.append({"case_id": c["case_id"], "source_label_equivalent": s.get("likeness after transformation"),
                               "source_label_field": "likeness after transformation", "source": split})
    return cases, labels


def proofnetverif(split: str) -> tuple[list[dict], list[dict]]:
    from datasets import load_dataset
    ds = load_dataset("PAug/ProofNetVerif", split=split)
    cases, labels = [], []
    for i, ex in enumerate(ds):
        ref, cand = ex["lean4_formalization"], ex["lean4_prediction"]
        name = ex["id"]
        c = {"case_id": _cid("pnv", split, str(i)), "group": f"pnv:{name}", "source": f"proofnetverif-{split}",
             "source_ref": f"pnv:{split}:{i:04d}:{name}", "ref_header": ex["lean4_src_header"], "ref_decl": ref,
             "cand_header": ex["lean4_src_header"], "cand_decl": cand, "informal": ex.get("nl_statement"),
             "provenance": {"dataset": "PAug/ProofNetVerif", "split": split, "row": i}}
        if validate(c):
            continue
        cases.append(c)
        labels.append({"case_id": c["case_id"], "source_label_equivalent": bool(ex["correct"]),
                       "source_label_field": "correct", "source": c["source"]})
    return cases, labels


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.ingest")
    ap.add_argument("source", choices=["epla", "proofnetverif"])
    ap.add_argument("--assess-dir", type=Path)
    ap.add_argument("--split", default="test")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    cases, labels = epla(a.assess_dir) if a.source == "epla" else proofnetverif(a.split)
    tag = a.source if a.source == "epla" else f"pnv-{a.split}"
    write_jsonl(a.out / f"{tag}.cases.jsonl", cases)
    write_jsonl(a.out / f"{tag}.source_labels.jsonl", labels)
    dup = len(cases) - len({norm_hash(c["cand_decl"]) + norm_hash(c["ref_decl"]) for c in cases})
    print(json.dumps({"source": tag, "cases": len(cases), "exact_duplicate_pairs": dup}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
