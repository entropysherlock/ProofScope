"""Blinded execution against the frozen SOTA-6 engines. Writes sealed, read-only execution records.

Engines (unchanged): relation task → proofscope.experimental.cjcs4 (CJCS one-process engine);
repair task → proofscope.experimental.repair (SOTA-6 certified minimal repair).
Each case runs in its own sandbox (blind.sandbox) under bench/limits.run_limited (whole process tree CPU,
peak RSS, process count) with the budget from the manifest. The runner never opens the gold file.

    python -m bench.sota7.runner --manifest M --public DIR --out RUNDIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

from bench.limits import run_limited
from bench.sota7.blind import sandbox, verify_manifest

REPO = Path(__file__).resolve().parents[2]


def engine_spec(c: dict) -> tuple[list[str], dict]:
    if c["task"] == "relation":
        spec = {"id": c["case_id"], "reference": c["reference"]["lean"], "lean": c["candidate"]["lean"]}
        return ["proofscope.experimental.cjcs4", "run", "spec.json", "--out", "out", "--jobs", "1"], spec
    r = c["repair"]
    spec = {"id": c["case_id"], "context": r["context"], "reference_source": c["reference"]["lean"],
            "candidate_source": c["candidate"]["lean"], "reference": r["reference"], "candidate": r["candidate"],
            "edits": r["edits"], "pool": r["pool"]}
    return ["proofscope.experimental.repair", "spec.json", "--out", "out"], spec


def claim_of(c: dict, row: dict | None) -> dict:
    """Normalize an engine row to a claim. Nothing here decides correctness."""
    if row is None:
        return {"claim": "NO_OUTPUT"}
    if c["task"] == "relation":
        v = row.get("verdict")
        if v == "CERTIFIED_LOGICAL_EQUIVALENCE":
            return {"claim": "EQUIVALENT_CLOSED", "basis": row.get("direction")}
        if v == "CERTIFIED_LOGICAL_DIFFERENCE":
            truth = {"reference_false_formalization_true": {"reference": "FALSE", "candidate": "TRUE"},
                     "reference_true_formalization_false": {"reference": "TRUE", "candidate": "FALSE"}}[row["direction"]]
            return {"claim": "NOT_EQUIVALENT_CLOSED", "closed_truth": truth}
        if v == "ABSTAIN":
            return {"claim": "ABSTAIN"}
        if row.get("reason") == "extraction failed" or row.get("failure_class") == "EXTRACTION":
            return {"claim": "INPUT_NOT_EVALUABLE"}
        return {"claim": "ENGINE_INCONCLUSIVE", "reason": row.get("reason")}
    o = row.get("outcome")
    if o in ("MINIMAL_REPAIR", "VERIFIED_REPAIR"):
        return {"claim": o, "repairs": [sorted(i for i in range(32) if (x["mask"] >> i) & 1) for x in row["repairs"]],
                "minimal_cost": row.get("minimal_cost")}
    if o == "NO_REPAIR_IN_GRAMMAR":
        return {"claim": o}
    return {"claim": "ABSTAIN", "proposed": row.get("proposed_outcome")}


def run_case(c: dict, public: Path, out: Path, budget: dict) -> dict:
    sb, env = sandbox(c, public)
    try:
        args, spec = engine_spec(c)
        (sb / "spec.json").write_text(json.dumps(spec, ensure_ascii=False))
        env["PYTHONPATH"] = str(REPO)
        imports = (c.get("environment") or {}).get("imports") or []
        if imports:
            env["PROOFSCOPE_IMPORTS"] = ",".join(imports)
        else:
            env.pop("PROOFSCOPE_IMPORTS", None)
        pre = (c.get("environment") or {}).get("preamble") or []
        if pre:
            env["PROOFSCOPE_PREAMBLE"] = "\n".join(pre)          # PS-25R: verbatim source header lines
        else:
            env.pop("PROOFSCOPE_PREAMBLE", None)
        visible = sorted(p.name for p in sb.iterdir())
        r = run_limited([sys.executable, "-m"] + args, budget["cpu_s"], budget["mem_mb"], budget["wall_s"],
                        cwd=str(sb), env=env, inputs=(str(sb / "spec.json"),))
        row = None
        if c["task"] == "relation":
            rp = sb / "out" / "rows" / "spec.json"
        else:
            rp = sb / "out" / "result.json"
        if rp.exists():
            row = json.loads(rp.read_text())
        cert_dir = out / "certs" / c["case_id"]
        cert_dir.mkdir(parents=True, exist_ok=True)
        cert = None
        if row and c["task"] == "relation" and row.get("certificate_source"):
            (cert_dir / "certificate.lean").write_text(row["certificate_source"])
            cert = {"file": "certificate.lean", "namespace": "ProofScopeCert.CJ_" + c["case_id"],
                    "declarations": {k: v["statement"] for k, v in (row.get("certificates") or {}).items()}}
        if row and c["task"] == "repair" and row.get("certificate") and Path(row["certificate"]).exists():
            shutil.copy(row["certificate"], cert_dir / "certificate.lean")
            cert = {"file": "certificate.lean", "declarations": sorted((row.get("axioms") or {}).keys())}
        if cert:
            cert["sha256"] = hashlib.sha256((cert_dir / "certificate.lean").read_bytes()).hexdigest()
        rec = {"case_id": c["case_id"], "task": c["task"], "sandbox_visible_files": visible,
               "status": r.status, "cpu_tree_s": round(r.cpu_tree_s, 3), "wall_s": round(r.wall_s, 3),
               "max_rss_mb": round(r.max_rss_mb, 1), "processes_seen": r.processes_seen,
               "engine_stats": (row or {}).get("stats"), "claim": claim_of(c, row) if r.status == "OK" else {"claim": "RESOURCE_EXHAUSTED" if r.status.startswith(("TIMEOUT", "OOM")) else "INFRA_ERROR"},
               "engine_reported_certified": (row or {}).get("certified") if c["task"] == "repair" else bool((row or {}).get("certificates")),
               "certificate": cert, "error_tail": ((r.stderr or "")[-1200:] if r.status != "OK" or row is None else "")}
        if r.status == "OK" and row is None:
            rec["claim"] = {"claim": "INFRA_ERROR"}
        return rec
    finally:
        shutil.rmtree(sb, ignore_errors=True)


def seal(out: Path, manifest: dict) -> dict:
    recs = out / "records.jsonl"
    s = {"records_sha256": hashlib.sha256(recs.read_bytes()).hexdigest(),
         "records": sum(1 for _ in recs.read_text().splitlines()), "manifest_sha256": manifest["manifest_sha256"],
         "certificates": {p.parent.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted((out / "certs").glob("*/certificate.lean"))}}
    (out / "seal.json").write_text(json.dumps(s, indent=1))
    for p in [recs, out / "seal.json"] + list((out / "certs").glob("*/certificate.lean")):
        os.chmod(p, 0o444)
    return s


def verify_seal(out: Path) -> dict:
    s = json.loads((out / "seal.json").read_text())
    if hashlib.sha256((out / "records.jsonl").read_bytes()).hexdigest() != s["records_sha256"]:
        raise RuntimeError("execution records were modified after sealing")
    for cid, h in s["certificates"].items():
        if hashlib.sha256((out / "certs" / cid / "certificate.lean").read_bytes()).hexdigest() != h:
            raise RuntimeError(f"certificate for {cid} modified after sealing")
    return s


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.sota7.runner")
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--public", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    m = verify_manifest(a.manifest, a.public)          # fatal on any integrity breach; gold not needed here
    from bench.sota7.blind import load_public
    cases = load_public(a.public)
    a.out.mkdir(parents=True, exist_ok=True)
    recs = []
    for e in m["cases"]:
        rec = run_case(cases[e["case_id"]], a.public.resolve(), a.out.resolve(), m["budgets"][cases[e["case_id"]]["task"]])
        rec["input_canonical_sha256"] = e["input_canonical_sha256"]
        rec["engine_commit"] = m["engine_commit"]
        recs.append(rec)
        print(json.dumps({k: rec[k] for k in ("case_id", "status", "cpu_tree_s")} | {"claim": rec["claim"]["claim"]}), flush=True)
    (a.out / "records.jsonl").write_text("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in recs))
    print(json.dumps(seal(a.out, m)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
