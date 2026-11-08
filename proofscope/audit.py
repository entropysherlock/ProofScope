"""ProofScope v0.1: reproducible kernel controls and limited proof-scope inventory.

This is a DEMONSTRATION, not a certification of arbitrary papers.
The negative control is only the fixed bundled example.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GOOD = ROOT / "examples/KernelControl/Good.lean"
FORGED = ROOT / "examples/KernelControl/Forged.lean"
EXPECTED_LEAN = "Lean (version 4.34.1"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def run(argv, *, env=None, cwd=None, timeout=240, output_dir: Path, log_name: str):
    try:
        p = subprocess.run(
            [str(x) for x in argv],
            capture_output=True, text=True, env=env, cwd=cwd, timeout=timeout
        )
        result = {
            "command": [str(x) for x in argv],
            "exit_code": p.returncode,
            "stdout": p.stdout[-30000:],
            "stderr": p.stderr[-30000:],
            "execution_error": None,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        result = {
            "command": [str(x) for x in argv],
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "execution_error": repr(exc),
        }
    (output_dir / log_name).write_text(json.dumps(result, indent=2) + "\n")
    return result


def classified_failure(result: dict) -> bool:
    s = (result.get("stdout", "") + result.get("stderr", "")).lower()
    return (
        result.get("exit_code") not in (0, None)
        and result.get("execution_error") is None
        and "declaration type mismatch" in s
        and "kc_forged" in s
        and "could not resolve module" not in s
    )


def source_inventory(paths):
    return [
        {"path": str(p.relative_to(ROOT)), "sha256": digest(p)}
        for p in paths
    ]


def audit(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    build = out / "build" / "KernelControl"
    build.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["LEAN_PATH"] = str(out / "build") + (
        os.pathsep + env["LEAN_PATH"] if env.get("LEAN_PATH") else ""
    )

    paths = [GOOD, FORGED, Path(__file__).resolve()]
    check = {
        "project": "ProofScope by Caleb J. Westfall",
        "version": "0.1.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "scope": "Bundled Lean kernel-controls only; no paper-to-Lean equivalence certified",
        "sources": source_inventory(paths),
        "trust": [
            "Lean 4.34.1 and its kernel",
            "GitHub-hosted runner and GitHub Actions",
            "Elan bootstrap download"
        ],
        "checks": {},
        "status": "NOT_CERTIFIED",
    }

    try:
        version = run(["lean", "--version"], env=env, output_dir=out,
                      log_name="01_lean_version.json")
        version_ok = (version["exit_code"] == 0
                      and EXPECTED_LEAN in version["stdout"])
        check["checks"]["lean_version"] = "PASS" if version_ok else "FAIL"

        positive = run(
            ["lean", "-o", build / "Good.olean", GOOD], env=env,
            output_dir=out, log_name="02_good_compile.json"
        )
        positive_compiles = positive["exit_code"] == 0 and (build / "Good.olean").exists()
        check["checks"]["good_compiles"] = "PASS" if positive_compiles else "FAIL"

        good_replay = run(
            ["leanchecker", "--fresh", "KernelControl.Good"], env=env,
            cwd=ROOT, output_dir=out, log_name="03_good_replay.json"
        ) if positive_compiles else None
        good_ok = good_replay is not None and good_replay["exit_code"] == 0
        check["checks"]["valid_proof_kernel_replay"] = "PASS" if good_ok else "FAIL"

        forged_compile = run(
            ["lean", "-o", build / "Forged.olean", FORGED], env=env,
            output_dir=out, log_name="04_forged_compile.json"
        )
        forged_built = (forged_compile["exit_code"] == 0
                        and (build / "Forged.olean").exists())
        check["checks"]["forged_control_artifact"] = (
            "PASS" if forged_built else "FAIL"
        )

        forged_replay = run(
            ["leanchecker", "--fresh", "KernelControl.Forged"], env=env,
            cwd=ROOT, output_dir=out, log_name="05_forged_replay.json"
        ) if forged_built else None
        forgery_ok = forged_replay is not None and classified_failure(forged_replay)
        check["checks"]["kernel_rejects_forged_declaration"] = (
            "PASS" if forgery_ok else "FAIL"
        )

        # Inventory-based scope statement; not mathematical equivalence.
        check["statement_inventory"] = {
            "Good.lean": re.findall(
                r"^theorem\s+([A-Za-z_][\w']*)", GOOD.read_text(), flags=re.M
            ),
            "Forged.lean": ["kc_forged (deliberate corrupted declaration)"]
        }
        check["checks"]["paper_to_lean_fidelity"] = "NOT_EVALUATED"
        checks = [
            check["checks"][k] for k in (
                "lean_version", "good_compiles", "valid_proof_kernel_replay",
                "forged_control_artifact", "kernel_rejects_forged_declaration"
            )
        ]
        if all(x == "PASS" for x in checks):
            check["status"] = "DEMO_CONTROLS_PASS"
    finally:
        (out / "report.json").write_text(json.dumps(check, indent=2) + "\n")
        summary = [
            "# ProofScope audit — prototype",
            "",
            "Overall: **" + check["status"] + "**",
            "",
            "This report covers only the two bundled test modules.",
            "It does **not** certify a paper's claims or 418 challenge files.",
            "",
            "## Checks",
        ]
        summary += [f"- {name}: **{status}**"
                    for name, status in check["checks"].items()]
        summary += [
            "", "## Trust and limitations",
            "- The same Lean implementation performs compilation and kernel replay.",
            "- This is a deliberately forged, fixed control—not a general proof checker.",
            "- No paper-to-Lean statement-fidelity conclusion is made.",
            "- See report.json and individual command logs for audit evidence.",
        ]
        (out / "REPORT.md").write_text("\n".join(summary) + "\n")
    print(json.dumps({"status": check["status"], "checks": check["checks"]}, indent=2))
    return 0 if check["status"] == "DEMO_CONTROLS_PASS" else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="proofscope-evidence")
    args = ap.parse_args()
    sys.exit(audit(Path(args.output).resolve()))


if __name__ == "__main__":
    main()
