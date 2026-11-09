"""SemantEq adapter (pinned f92767000e14d11744580946980cf874324f5d19, native toolchain v4.30.0-rc1).

Input is exactly SemantEq's documented pair format: each side is the full file text (the source header and
the declaration closed with `sorry`). One pair per process so the external whole-tree CPU limit binds.
SemantEq keeps its documented default `--timeout` (20 s wall); all paths passed are absolute."""
from __future__ import annotations

import json
from pathlib import Path

from .. import outcomes
from ._decl import with_sorry


def side(header: str, decl: str) -> str:
    return f"{header.rstrip()}\n\n{with_sorry(decl)}\n"


def prepare(case: dict, workdir: Path, semanteq_dir: Path, budget_s: int) -> dict:
    """`budget_s` is accepted for interface symmetry but NOT passed: SemantEq runs with its own default
    `--timeout` (20 s wall, README at the pin); the external whole-tree CPU limit is authoritative."""
    workdir = workdir.resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    inp, out = workdir / "pair.jsonl", workdir / "result.jsonl"
    inp.write_text(json.dumps({"id": case["case_id"], "reference": side(case["ref_header"], case["ref_decl"]),
                               "candidate": side(case["cand_header"], case["cand_decl"])}, ensure_ascii=False) + "\n")
    return {"cmd": ["lake", "exe", "semanteq", "--raw", str(inp), str(out)],
            "cwd": str(Path(semanteq_dir).resolve()), "result": str(out), "input": str(inp)}


def parse(case: dict, result_path: Path) -> dict:
    recs = []
    if result_path.exists():
        for line in result_path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if "_meta" not in r:
                    recs.append(r)
    if not recs:
        return {"native_verdict": None}
    v = recs[0].get("verdict")
    out = {"native_verdict": v, "elapsedMs": recs[0].get("elapsedMs"), "directions": recs[0].get("directions"),
           "certificate_kind": "kernel" if v == "EquivalentRestricted" else "structural" if v in ("ExactMatch", "DefEq") else None,
           "native_record": recs[0]}
    for t in ("A", "B"):
        out[f"track_{t}"] = outcomes.semanteq(v, t)
    return out
