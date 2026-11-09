"""BEq+ adapter (LeanInteract pinned 768e18ebcb5c7ec34d308768a785389eeac37798)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .. import outcomes

DRIVER = Path(__file__).with_name("beqplus_driver.py")


def prepare(case: dict, workdir: Path, leaninteract_dir: Path, lean_version: str, per_proof_s: int) -> dict:
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "pair.json").write_text(json.dumps(case, ensure_ascii=False))
    return {"cmd": [sys.executable, str(DRIVER), "--leaninteract", str(leaninteract_dir), "--lean-version", lean_version,
                    "--timeout", str(per_proof_s), str(workdir / "pair.json"), str(workdir / "out.json")]}


def parse(case: dict, out_path: Path) -> dict:
    if not out_path.exists():
        return {"native_verdict": None}
    r = json.loads(out_path.read_text())
    out = {"native_verdict": r.get("beq_plus"), "startup_s": r.get("startup_s")}
    for t in ("A", "B"):
        out[f"track_{t}"] = outcomes.beqplus(r.get("beq_plus"), t)
    return out
