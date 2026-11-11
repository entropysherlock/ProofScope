#!/usr/bin/env python3
"""Fail-closed kernel check of one Lean theorem against an expected proposition.

Lessons built in (ProofScope SOTA-18 finding F1, SOTA-19 pilot A0 first run):
  * no verdict is ever produced for input that did not elaborate;
  * Lean's error recovery adds a `sorryAx`-backed declaration after a failed proof,
    so a non-zero exit code or any `error` line rejects the file outright;
  * `#print axioms` alone is not trusted: the exact proposition is re-checked by
    elaborating `theorem _ : <expected> := @<name>`, the compiled module is replayed
    by `leanchecker`, and the source is scanned for escape hatches;
  * compile failure, unapproved axioms, timeout and missing tools are distinct outcomes.

This checks core-Lean files (no Mathlib) and is used by the SL-001 smoke tests.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ALLOWED = ("propext", "Classical.choice", "Quot.sound")
ESCAPES = re.compile(r'\b(sorry|admit|native_decide|implemented_by|unsafe|axiom|opaque|extern|run_cmd|elab|macro)\b')


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def run(cmd, cwd, timeout, env=None):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"


def check(lean_file: str, theorem: str, expected_prop: str, timeout: int = 120,
          allowed=ALLOWED) -> dict:
    src = Path(lean_file).read_text(encoding="utf-8")
    out = {"file": lean_file, "theorem": theorem, "expected_proposition": expected_prop,
           "artifact_sha256": sha(src.encode()), "proposition_sha256": sha(" ".join(expected_prop.split()).encode()),
           "kernel_replay": False, "elaborated_without_error": False, "sorry_free": False,
           "axioms": None, "outcome": None, "reason": None}
    lean, checker = shutil.which("lean"), shutil.which("leanchecker")
    if not lean:
        return {**out, "outcome": "blocked_infrastructure", "reason": "lean not on PATH"}
    code_only = re.sub(r'/-.*?-/', '', src, flags=re.S)
    code_only = re.sub(r'--.*', '', code_only)
    hit = ESCAPES.search(code_only)
    if hit:
        return {**out, "outcome": "unsupported_input", "reason": f"source uses '{hit.group(1)}'"}
    with tempfile.TemporaryDirectory() as d:
        mod = "SLCheck"
        body = (src + f"\n\ntheorem SL001.prop_check : ({expected_prop}) := @{theorem}\n"
                f"#print axioms {theorem}\n#print axioms SL001.prop_check\n")
        (Path(d) / f"{mod}.lean").write_text(body, encoding="utf-8")
        rc, log = run([lean, "-o", f"{mod}.olean", f"{mod}.lean"], d, timeout)
        out["replay_log"] = log[-2000:]
        if rc is None:
            return {**out, "outcome": "timeout", "reason": "elaboration exceeded budget"}
        if rc != 0 or re.search(r'\berror\b', log):
            return {**out, "outcome": "compile_failure",
                    "reason": "did not elaborate, or does not prove the expected proposition"}
        out["elaborated_without_error"] = True
        if "sorry" in log:
            return {**out, "outcome": "compile_failure", "reason": "sorry reported by Lean"}
        ax = []
        found = 0
        for m in re.finditer(r"'([^']+)' (depends on axioms: \[([^\]]*)\]|does not depend on any axioms)", log):
            found += 1
            if m.group(3):
                ax += [a.strip() for a in m.group(3).split(",")]
        if found != 2:
            return {**out, "outcome": "blocked_infrastructure", "reason": "could not read axiom report"}
        out["axioms"] = sorted(set(ax))
        out["sorry_free"] = "sorryAx" not in ax
        bad = [a for a in out["axioms"] if a not in allowed]
        if bad:
            return {**out, "outcome": "unsupported_input", "reason": f"unapproved axioms {bad}"}
        if not checker:
            return {**out, "outcome": "blocked_infrastructure", "reason": "leanchecker not on PATH; no replay"}
        rc, clog = run([checker, mod], d, timeout, {**os.environ, "LEAN_PATH": d})
        out["replay_log"] += "\n[leanchecker] " + clog[-500:]
        if rc != 0:
            return {**out, "outcome": "compile_failure" if rc else "timeout",
                    "reason": "independent replay by leanchecker failed"}
        out["kernel_replay"] = True
        v = subprocess.run([lean, "--version"], capture_output=True, text=True).stdout.strip()
        out.update(outcome="certified", checker="lean kernel + leanchecker replay", toolchain=v,
                   dependencies="Lean core only", axiom_source="print_axioms+proposition_recheck+replay")
    return out


if __name__ == "__main__":
    print(json.dumps(check(sys.argv[1], sys.argv[2], sys.argv[3]), indent=2))
