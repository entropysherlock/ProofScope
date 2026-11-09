"""SemantEq adapter (pinned f92767000e14d11744580946980cf874324f5d19, native toolchain v4.30.0-rc1).

Input is exactly SemantEq's documented pair format: each side is the full file text (the source header and
the declaration closed with `sorry`). One pair per process so the external CPU limit binds; SemantEq's own
`--timeout` is set to the same budget in wall seconds (its documented limit; compilation is not
interrupted by it, which is why the external limit is authoritative)."""
from __future__ import annotations

import json
from pathlib import Path

from .. import outcomes
from ._decl import with_sorry


def side(header: str, decl: str) -> str:
    return f"{header.rstrip()}\n\n{with_sorry(decl)}\n"


def prepare(case: dict, workdir: Path, semanteq_dir: Path, budget_s: int) -> dict:
    workdir.mkdir(parents=True, exist_ok=True)
    inp, out = workdir / "pair.jsonl", workdir / "result.jsonl"
    inp.write_text(json.dumps({"id": case["case_id"], "reference": side(case["ref_header"], case["ref_decl"]),
                               "candidate": side(case["cand_header"], case["cand_decl"])}, ensure_ascii=False) + "\n")
    return {"cmd": ["lake", "exe", "semanteq", "--raw", "--timeout", str(budget_s), str(inp), str(out)],
            "cwd": str(semanteq_dir), "result": str(out)}


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
    out = {"native_verdict": v, "elapsedMs": recs[0].get("elapsedMs"), "directions": recs[0].get("directions")}
    for t in ("A", "B"):
        out[f"track_{t}"] = outcomes.semanteq(v, t)
    return out
