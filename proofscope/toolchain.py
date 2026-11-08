"""Locate and run the Lean toolchain (lean, leanchecker, lake)."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CmdResult:
    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str
    seconds: float

    @property
    def output(self) -> str:
        return (self.stdout or "") + (self.stderr or "")

    def as_dict(self) -> dict:
        return {"cmd": self.cmd, "returncode": self.returncode, "seconds": round(self.seconds, 2),
                "output_tail": self.output[-4000:]}


@dataclass
class Toolchain:
    lean: str
    leanchecker: str | None = None
    lake: str | None = None
    project: Path | None = None          # optional Lake project (e.g. one that depends on Mathlib)
    env: dict = field(default_factory=dict)

    @classmethod
    def find(cls, project: str | Path | None = None) -> "Toolchain":
        lean = shutil.which("lean")
        if not lean:
            raise FileNotFoundError(
                "`lean` was not found on PATH. Install elan (https://github.com/leanprover/elan) "
                "or put a Lean toolchain's bin/ directory on PATH.")
        bindir = Path(lean).resolve().parent
        def sibling(name: str) -> str | None:
            p = bindir / name
            return str(p) if p.exists() else shutil.which(name)
        tc = cls(lean=lean, leanchecker=sibling("leanchecker"), lake=sibling("lake"))
        if project:
            tc.project = Path(project).resolve()
            tc.env = tc._lake_env()
        return tc

    def _lake_env(self) -> dict:
        """LEAN_PATH exactly as `lake env` computes it for the project."""
        if not self.lake:
            raise FileNotFoundError("`lake` not found; it is needed to use a Lake project")
        r = subprocess.run([self.lake, "env", "printenv", "LEAN_PATH"], cwd=self.project,
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("`lake env` failed in %s:\n%s" % (self.project, r.stderr[-2000:]))
        return {"LEAN_PATH": r.stdout.strip()}

    def version(self) -> str:
        return self.run([self.lean, "--version"]).output.strip()

    def run(self, cmd: list[str], cwd: str | Path | None = None, extra_path: str | Path | None = None,
            timeout: float | None = None) -> CmdResult:
        env = dict(os.environ)
        env.update(self.env)
        if extra_path:
            env["LEAN_PATH"] = os.pathsep.join(p for p in [str(extra_path), env.get("LEAN_PATH", "")] if p)
        t0 = time.time()
        try:
            r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
            return CmdResult(cmd, r.returncode, r.stdout, r.stderr, time.time() - t0)
        except subprocess.TimeoutExpired as e:
            return CmdResult(cmd, -9, e.stdout or "", (e.stderr or "") + "\nTIMEOUT", time.time() - t0)

    def compile(self, src: Path, olean: Path | None, root: Path, timeout: float | None = None) -> CmdResult:
        """Compile `src` (inside source root `root`) optionally writing an .olean."""
        cmd = [self.lean, "-R", str(root), str(src)]
        if olean is not None:
            olean.parent.mkdir(parents=True, exist_ok=True)
            cmd[1:1] = ["-o", str(olean)]
        return self.run(cmd, cwd=root, extra_path=olean.parent if olean else None, timeout=timeout)

    def replay(self, module: str, build_root: Path, fresh: bool = False,
               timeout: float | None = None) -> CmdResult:
        """Re-check a compiled module's declarations with leanchecker (same kernel, independent replay)."""
        if not self.leanchecker:
            return CmdResult(["leanchecker"], 127, "", "leanchecker not available", 0.0)
        cmd = [self.leanchecker] + (["--fresh"] if fresh else []) + [module]
        return self.run(cmd, cwd=build_root, extra_path=build_root, timeout=timeout)
