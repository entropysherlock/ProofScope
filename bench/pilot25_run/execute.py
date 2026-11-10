"""Run the frozen SOTA-7 engine against original-source-linked, externally selected Pilot-25 inputs.
The dataset carries only Lean proposition translations, original input hashes, no gold labels.
Two compound-def cases remain not adaptable; never silently discard them.
"""
from __future__ import annotations
import base64, hashlib, json, os, subprocess, sys, zlib
from pathlib import Path
from bench.sota4.integrity import file_digest
from bench.sota7.runner import main as engine_run
from bench.sota7.blind import verify_manifest
from bench.sota7.schema import validate_public

ROOT=Path("bench/pilot25_run")
BASE="666c873371f30fe7d79a7b46f607e425ad7d1bd4"
PUBLIC=ROOT/"public"
RESULTS=Path("pilot25_results")
DATA=ROOT/"case_payload.b64"
BUDGET={"cpu_s":120,"mem_mb":8000,"wall_s":400}

def prepare():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    payload=DATA.read_text().strip()
    data=json.loads(zlib.decompress(base64.b64decode(payload)))
    statuses=[]
    for d in data:
        record={"case_id":d["id"],"original_sha256":d["original_sha256"],"adaptation_status":d["source_status"]}
        if d["source_status"]=="ADAPTED_UNVERIFIED":
            case={"schema":"proofscope-eval/1","case_id":d["id"],"task":"relation",
                  "domain":"external","difficulty":"unreviewed",
                  "provenance":{"source":"ProofNetVerif (Grok-supplied, independently unverified rows)",
                                "url":"https://huggingface.co/datasets/PAug/ProofNetVerif",
                                "retrieved":"2026-11-09","license":"MIT",
                                "upstream_revision":"UNVERIFIED",
                                "original_sha256":d["original_sha256"]},
                  "environment":{"lean":"4.34.1","mathlib":"v4.34.1","imports":["Mathlib"]},
                  "reference":{"text":"See original public package; hash in provenance","lean":d["R"]},
                  "candidate":{"text":"See original public package; hash in provenance","lean":d["F"]}}
            validate_public(case)
            f=PUBLIC/(d["id"]+".json")
            f.write_text(json.dumps(case,ensure_ascii=False,indent=2)+"\n")
            record["adapted_sha256"]=hashlib.sha256(f.read_bytes()).hexdigest()
        else: record["reason"]=d["reason"]
        statuses.append(record)
    (RESULTS/"intake.json").write_text(json.dumps({"original_public_zip_sha256":"7b95556e761d9bb77f95cc60ba04b5b4cc8c1e61d15663bf7198babe36b8d201",
               "original_file_count":25,"engine_eligible_by_syntax":sum(s["adaptation_status"]=="ADAPTED_UNVERIFIED" for s in statuses),
               "labels":"NOT_PROVIDED; NO SCORING","cases":statuses},indent=2))
    cases=sorted(PUBLIC.glob("*.json"))
    manifest={"schema":"proofscope-eval-manifest/1","case_schema":"proofscope-eval/1",
         "dataset_version":"Grok Pilot25 public v2, adaptation audit v1",
         "selection_protocol":"GROK_AI_PROVISIONAL; NOT EXTERNAL_HUMAN_ADJUDICATION",
         "review_protocol":"NONE; GOLD WITHHELD",
         "engine_commit":BASE,
         "toolchain":{"lean":"4.34.1","mathlib":"d13f23b723b8a846827a245b89c10fc7d3f11612",
                      "repl":"193cf4bb9a22bb3fc6d25774f0fe6a70db1fd6ee"},
         "budgets":{"relation":BUDGET,"repair":BUDGET},
         "cases":[{"case_id":f.stem,"task":"relation","input_canonical_sha256":file_digest(f.read_bytes())} for f in cases],
         "gold_sha256":"NOT_PROVIDED; NO GOLD COMMITMENT"}
    manifest["manifest_sha256"]=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    mf=RESULTS/"manifest.json";mf.write_text(json.dumps(manifest,indent=2))
    verify_manifest(mf,PUBLIC)
    print("PREPARED",len(cases),"cases; 2 original cases NOT_ADAPTABLE; no gold accessed",flush=True)
    return mf

if __name__=="__main__":
    m=prepare()
    print("EXECUTING FROZEN SOTA7 RUNNER",flush=True)
    engine_run(["--manifest",str(m),"--public",str(PUBLIC),"--out",str(RESULTS/"execution")])
