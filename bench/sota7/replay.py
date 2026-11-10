"""Independent certificate replay and source identity, in a fresh directory, without the engine.

For every record with a certificate: recompile the certificate module from the sealed file (fresh temp dir,
`lean -o`), require no error, parse `#print axioms` for every relevant declaration (no sorryAx, nothing
outside propext / Classical.choice / Quot.sound), replay with `leanchecker`, and check source identity:
  relation: each decisive declaration's statement is rebuilt from the PUBLIC input strings
            (`¬ ((R) ↔ (F))` for differences, `(R) ↔ (F)` for equivalences) and must occur verbatim in the
            certificate as `theorem <name> : <statement>`;
  repair:   `theorem R_source_stmt : (<reference.lean>) ↔` and `theorem F_source_stmt : (<candidate.lean>) ↔`
            must occur verbatim.
What replay does NOT establish: that the public Lean statements correctly formalize the source mathematics.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from bench.sota7.blind import load_public
from bench.sota7.runner import verify_seal

STD = {"propext", "Classical.choice", "Quot.sound"}
DECISIVE = {"diff_RL", "diff_LR", "equiv_defeq", "equiv_both_true", "equiv_both_false", "impl_RC", "impl_CR", "equiv"}


def _imports_env(case):
    env = dict(os.environ)
    return env


def expected_statements(case: dict, decls: dict) -> dict:
    R, F = case["reference"]["lean"], case["candidate"]["lean"]
    out = {}
    for k in decls:
        if k in ("diff_RL", "diff_LR"):
            out[k] = f"¬ (({R}) ↔ ({F}))"
        elif k in ("equiv_defeq", "equiv_both_true", "equiv_both_false", "equiv"):
            out[k] = f"({R}) ↔ ({F})"
        elif k == "impl_RC":
            out[k] = f"({R}) → ({F})"
        elif k == "impl_CR":
            out[k] = f"({F}) → ({R})"
    return out


def replay_one(rec: dict, case: dict, run_dir: Path, lean: str, leanchecker: str) -> dict:
    cert = rec.get("certificate")
    if not cert:
        return {"case_id": rec["case_id"], "replay": "NO_CERTIFICATE"}
    src = (run_dir / "certs" / rec["case_id"] / cert["file"]).read_text()
    d = Path(tempfile.mkdtemp(prefix="ps7_replay_"))
    try:
        if rec["task"] == "relation":
            ns = cert["namespace"]
            rel = Path(*ns.split(".")).with_suffix(".lean")
            mod = ns
            decls = [k for k in cert["declarations"] if k in DECISIVE]
            # identity: rebuilt from public strings, not from the record
            exp = expected_statements(case, decls)
            for k, st in exp.items():
                if f"theorem {k} : {st} :=" not in src:
                    return {"case_id": rec["case_id"], "replay": "REJECTED", "reason": f"source identity: {k} statement not built from the public input"}
            names = [f"{ns}.{k}" for k in decls]
            if not names:
                return {"case_id": rec["case_id"], "replay": "NO_DECISIVE_DECLARATION",
                        "reason": "only partial certificates; nothing decisive to verify"}
        else:
            rel, mod = Path("ReplayCert.lean"), "ReplayCert"
            for tag, s in (("R_source_stmt", case["reference"]["lean"]), ("F_source_stmt", case["candidate"]["lean"])):
                if f"theorem {tag} : ({s}) ↔" not in src:
                    return {"case_id": rec["case_id"], "replay": "REJECTED", "reason": f"source identity: {tag} does not state the public input"}
            names = [n for n in cert["declarations"]]
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_text(src)
        olean = d / "build" / rel.with_suffix(".olean")
        olean.parent.mkdir(parents=True, exist_ok=True)
        c = subprocess.run([lean, "-R", str(d), "-o", str(olean), str(d / rel)], capture_output=True, text=True, timeout=1800)
        log = c.stdout + c.stderr
        if c.returncode != 0 or ": error" in log:
            return {"case_id": rec["case_id"], "replay": "REJECTED", "reason": "certificate does not compile", "log": log[-1500:]}
        axioms = {}
        for n in names:
            m = re.search(rf"'{re.escape(n)}' (does not depend on any axioms|depends on axioms: \[([^\]]*)\])", log)
            if not m:
                return {"case_id": rec["case_id"], "replay": "REJECTED", "reason": f"no axiom report for {n}"}
            axioms[n] = [] if m.group(2) is None else [a.strip() for a in m.group(2).split(",")]
            if "sorryAx" in axioms[n] or not set(axioms[n]) <= STD:
                return {"case_id": rec["case_id"], "replay": "REJECTED", "reason": f"axioms of {n}: {axioms[n]}"}
        env = dict(os.environ)
        env["LEAN_PATH"] = os.pathsep.join([str(d / "build")] + ([env["LEAN_PATH"]] if env.get("LEAN_PATH") else []))
        r = subprocess.run([leanchecker, mod], capture_output=True, text=True, timeout=1800, cwd=str(d / "build"), env=env)
        if r.returncode != 0:
            return {"case_id": rec["case_id"], "replay": "REJECTED", "reason": "leanchecker replay failed", "log": (r.stdout + r.stderr)[-1000:]}
        return {"case_id": rec["case_id"], "replay": "VERIFIED", "axioms": axioms, "declarations": names,
                "scope": "proof objects of the stated Lean propositions; not the interpretation of the source mathematics"}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.sota7.replay")
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--public", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    verify_seal(a.run)
    cases = load_public(a.public)
    lean, chk = shutil.which("lean"), shutil.which("leanchecker")
    res = [replay_one(json.loads(l), cases[json.loads(l)["case_id"]], a.run, lean, chk)
           for l in (a.run / "records.jsonl").read_text().splitlines()]
    a.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in res))
    for r in res:
        print(r["case_id"], r["replay"], r.get("reason", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
