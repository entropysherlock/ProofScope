"""Frozen manifests and blinded execution.

`freeze` commits the public inputs and the gold file by canonical-JSON digest (bench/sota4/integrity.py),
plus dataset version, selection and review protocol ids, engine commit, toolchain and budgets.
`verify` re-checks every digest; any mismatch, missing or extra file is fatal.
`sandbox` gives the engine a fresh directory containing only that case's public file and an environment with
no gold-related variables; the gold file is never copied, passed, or referenced there. In CI the execution job
does not have the gold file at all (it is removed before execution and scored in a later job).
A digest commits bytes; it does not make a label correct or independent.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from bench.sota4.integrity import file_digest
from bench.sota7.schema import SCHEMA, validate_gold, validate_public

MANIFEST = "proofscope-eval-manifest/1"


class IntegrityBreach(RuntimeError):
    pass


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def engine_commit(repo: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "UNKNOWN"


def load_public(public_dir: Path) -> dict:
    cases = {}
    for f in sorted(Path(public_dir).glob("*.json")):
        c = json.loads(f.read_text(encoding="utf-8"))
        validate_public(c)
        if f.stem != c["case_id"]:
            raise IntegrityBreach(f"file name {f.name} does not match case_id")
        cases[c["case_id"]] = c
    return cases


def load_gold(gold_file: Path, cases: dict) -> dict:
    gold = {}
    for line in Path(gold_file).read_text(encoding="utf-8").splitlines():
        if line.strip():
            g = json.loads(line)
            if g["case_id"] not in cases:
                raise IntegrityBreach(f"gold for unknown case {g['case_id']}")
            validate_gold(g, cases[g["case_id"]]["task"])
            gold[g["case_id"]] = g
    if set(gold) != set(cases):
        raise IntegrityBreach(f"gold/case mismatch: {sorted(set(cases) ^ set(gold))}")
    return gold


def freeze(public_dir: Path, gold_file: Path, out: Path, *, dataset_version: str, selection_protocol: str,
           review_protocol: str, repo: Path, toolchain: dict, budgets: dict) -> dict:
    cases = load_public(public_dir)
    load_gold(gold_file, cases)
    m = {"schema": MANIFEST, "case_schema": SCHEMA, "dataset_version": dataset_version,
         "selection_protocol": selection_protocol, "review_protocol": review_protocol,
         "engine_commit": engine_commit(repo), "toolchain": toolchain, "budgets": budgets,
         "cases": [{"case_id": k, "task": c["task"], "input_canonical_sha256": file_digest(
             (Path(public_dir) / f"{k}.json").read_bytes())} for k, c in sorted(cases.items())],
         "gold_sha256": _sha(gold_file)}
    m["manifest_sha256"] = hashlib.sha256(json.dumps(m, sort_keys=True).encode()).hexdigest()
    Path(out).write_text(json.dumps(m, indent=1))
    return m


def verify_manifest(manifest: Path, public_dir: Path, gold_file: Path | None = None) -> dict:
    m = json.loads(Path(manifest).read_text())
    body = {k: v for k, v in m.items() if k != "manifest_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != m.get("manifest_sha256"):
        raise IntegrityBreach("manifest self-digest mismatch")
    present = sorted(p.stem for p in Path(public_dir).glob("*.json"))
    listed = [c["case_id"] for c in m["cases"]]
    if present != sorted(listed) or len(set(listed)) != len(listed):
        raise IntegrityBreach(f"public case set differs from manifest: {sorted(set(present) ^ set(listed))}")
    for c in m["cases"]:
        if file_digest((Path(public_dir) / f"{c['case_id']}.json").read_bytes()) != c["input_canonical_sha256"]:
            raise IntegrityBreach(f"input digest mismatch for {c['case_id']}")
    load_public(public_dir)
    if gold_file is not None and _sha(gold_file) != m["gold_sha256"]:
        raise IntegrityBreach("gold file digest mismatch")
    return m


SCRUB = ("GOLD", "LABEL", "SOTA7_PRIVATE")


def sandbox(case: dict, public_dir: Path) -> tuple[Path, dict]:
    d = Path(tempfile.mkdtemp(prefix="ps7_case_"))
    shutil.copy(Path(public_dir) / f"{case['case_id']}.json", d / "case.json")
    env = {k: v for k, v in os.environ.items() if not any(s in k.upper() for s in SCRUB)}
    return d, env
