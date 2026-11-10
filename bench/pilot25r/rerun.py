"""PS-25R pilot rerun: the same 23 adapted cases, same strings and hashes as bench/pilot25_run, executed by the
recovered engine through the unchanged SOTA-7 runner/seal/replay, under the budget of the frozen pilot protocol
(docs/sota5/PILOT_PROTOCOL_v1.md item 7: 12000 MB whole-tree; the 900 CPU-s measurement run). The Pilot-25
budget (8000 MB / 120 CPU-s) was copied from the core-Lean synthetic dry run, not from that protocol.
A preamble is applied only if bench/pilot25r/source_headers.json (built by headers.py from the original
archive) lists one for the case; otherwise the case runs exactly as before.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from bench.pilot25r.cases import load
from bench.sota4.integrity import file_digest
from bench.sota7.blind import verify_manifest
from bench.sota7.runner import main as engine_run
from bench.sota7.schema import validate_public

ROOT = Path("pilot25r_results")
PUBLIC = ROOT / "public"
BUDGET = {"cpu_s": 900, "mem_mb": 12000, "wall_s": 2000}
HEADERS = Path("bench/pilot25r/source_headers.json")


def prepare(base_commit: str) -> Path:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    heads = json.loads(HEADERS.read_text())["cases"] if HEADERS.exists() else {}
    intake = []
    for d in load():
        rec = {"case_id": d["id"], "original_sha256": d["original_sha256"], "adaptation_status": d["source_status"]}
        if d["source_status"] == "ADAPTED_UNVERIFIED":
            pre = (heads.get(d["id"]) or {}).get("preamble") or []
            case = {"schema": "proofscope-eval/1", "case_id": d["id"], "task": "relation", "domain": "external",
                    "difficulty": "unreviewed",
                    "provenance": {"source": "ProofNetVerif (Grok-supplied, independently unverified rows)",
                                   "url": "https://huggingface.co/datasets/PAug/ProofNetVerif", "retrieved": "2026-11-09",
                                   "license": "MIT", "upstream_revision": "UNVERIFIED", "original_sha256": d["original_sha256"]},
                    "environment": {"lean": "4.34.1", "mathlib": "d13f23b723b8a846827a245b89c10fc7d3f11612",
                                    "imports": ["Mathlib"], "preamble": pre},
                    "reference": {"text": "See original public package; hash in provenance", "lean": d["R"]},
                    "candidate": {"text": "See original public package; hash in provenance", "lean": d["F"]}}
            validate_public(case)
            f = PUBLIC / f"{d['id']}.json"
            f.write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n")
            rec.update(preamble=pre, preamble_source="original archive" if pre else "none available",
                       statements_sha256=hashlib.sha256(f"{d['R']}\0{d['F']}".encode()).hexdigest())
        else:
            rec["reason"] = d.get("reason") or d.get("R")
        intake.append(rec)
    (ROOT / "intake.json").write_text(json.dumps(intake, ensure_ascii=False, indent=1))
    cases = sorted(PUBLIC.glob("*.json"))
    m = {"schema": "proofscope-eval-manifest/1", "case_schema": "proofscope-eval/1",
         "dataset_version": "Grok Pilot25 public v2, adaptation audit v1 (PS-25R rerun)",
         "selection_protocol": "GROK_AI_PROVISIONAL; NOT EXTERNAL_HUMAN_ADJUDICATION", "review_protocol": "NONE; GOLD WITHHELD",
         "engine_commit": base_commit, "toolchain": {"lean": "4.34.1", "mathlib": "d13f23b723b8a846827a245b89c10fc7d3f11612",
                                                    "repl": "193cf4bb9a22bb3fc6d25774f0fe6a70db1fd6ee"},
         "budgets": {"relation": BUDGET, "repair": BUDGET},
         "cases": [{"case_id": f.stem, "task": "relation", "input_canonical_sha256": file_digest(f.read_bytes())} for f in cases],
         "gold_sha256": "NOT_PROVIDED; NO GOLD COMMITMENT"}
    m["manifest_sha256"] = hashlib.sha256(json.dumps(m, sort_keys=True).encode()).hexdigest()
    mf = ROOT / "manifest.json"
    mf.write_text(json.dumps(m, indent=2))
    verify_manifest(mf, PUBLIC)
    return mf


if __name__ == "__main__":
    mf = prepare(sys.argv[1] if len(sys.argv) > 1 else "UNKNOWN")
    engine_run(["--manifest", str(mf), "--public", str(PUBLIC), "--out", str(ROOT / "execution")])
