#!/usr/bin/env python3
"""Copy the openai/math source files needed by the two linked theorems, verbatim.

Reads blobs from a git clone of openai/math at the frozen commit (no checkout needed), follows
imports from the two root modules, writes the files under <project>/OAI/..., and records each
file's SHA-256 in oai_files.json. Fails if a file outside OAI.* and Mathlib is imported.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

OAI_HEAD = "4eaee87548250b2682affda7d05d947c05554bae"
ROOTS = ["OAI.Analysis.Littlewood.Main", "OAI.NumberTheory.GaussianMoat.Main"]


def blob(repo, path):
    return subprocess.run(["git", "-C", repo, "show", f"{OAI_HEAD}:{path}"],
                          check=True, capture_output=True).stdout


def main(repo, project):
    seen, todo, files = set(), list(ROOTS), {}
    while todo:
        m = todo.pop()
        if m in seen:
            continue
        seen.add(m)
        rel = "lean/" + m.replace(".", "/") + ".lean"
        data = blob(repo, rel)
        files[m] = {"path": rel, "sha256": hashlib.sha256(data).hexdigest()}
        out = Path(project) / (m.replace(".", "/") + ".lean")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        for imp in re.findall(r'^\s*(?:public\s+)?import\s+(\S+)', data.decode(), re.M):
            if imp.startswith("OAI."):
                todo.append(imp)
            elif imp.split(".")[0] != "Mathlib":
                sys.exit(f"unexpected non-Mathlib import {imp} in {m}")
    manifest = {"source": "https://github.com/openai/math", "commit": OAI_HEAD, "license": "Apache-2.0",
                "roots": ROOTS, "n_files": len(files),
                "files": dict(sorted(files.items()))}
    Path(project, "oai_files.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"copied {len(files)} files")


if __name__ == "__main__":
    main(*sys.argv[1:])
