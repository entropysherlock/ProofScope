"""CMCD v1.0: the frozen v0.9 drift-localization engine plus boundary witness synthesis.

`proofscope/cmcd.py` (v0.9) is unchanged and still frozen. This module wraps it: before a case runs,
`lean/ProofScope/BoundarySynth.lean` reads every abstracted chain statement and proposes, for each
abstracted operator, interpretations that place it exactly on a comparison boundary
(`x a a < a + 2` gives `fun b0 _ => b0 + 2`, and the ±1 neighbours). They are added to the front of
the witness pool for that operator's type. Proposals carry no authority: they only enter Lean-checked
separation certificates through the unchanged `certify` gate.

General principle (not case-specific): a strict/non-strict, `=`/`≤` or constant change at an atom
`x ts ⋈ e` is separated exactly by interpretations of `x` on the boundary `e`.
"""

from __future__ import annotations

import argparse
import os
import json
from pathlib import Path

from . import cmcd as V9
from .toolchain import Toolchain

SRC = V9.SRC
IMPORTS = [m for m in os.environ.get("PROOFSCOPE_IMPORTS", "").split(",") if m.strip()]
_v9_extract, _v9_certify = V9.extract, V9.certify


def import_lines() -> str:
    return "".join(f"import {m.strip()}\n" for m in IMPORTS)


def _extract_with_imports(ref, lean, tc, buildp, work):
    work.mkdir(parents=True, exist_ok=True)
    f = work / "Drift_input.lean"
    f.write_text(f"{import_lines()}import ProofScope.DriftExtract\n\n#proofscope_drift ({ref}) ({lean})\n")
    r = tc.run([tc.lean, str(f)], cwd=work, extra_path=buildp, timeout=600)
    for line in r.output.splitlines():
        i = line.find("PROOFSCOPE_DRIFT ")
        if i >= 0:
            return json.loads(line[i + len("PROOFSCOPE_DRIFT "):])
    return {"error": r.output[-3000:]}


def _certify_with_imports(ident, header, *a, **k):
    return _v9_certify(ident, import_lines() + header, *a, **k)


REAL_POOLS = {"ℝ": ["(0 : ℝ)", "(1 : ℝ)", "(-1 : ℝ)", "(1 / 2 : ℝ)", "(2 : ℝ)"],
              "ℝ → ℝ": ["fun x => x", "fun _ => 0", "fun x => x + 1", "fun x => -x", "fun x => x ^ 2"],
              "ℝ → ℝ → ℝ": ["fun a _ => a", "fun _ b => b", "fun a b => a + b", "fun _ _ => 0", "fun a b => a - b"]}
_EXTRA: dict[str, list[str]] = {}
_v9_pool = V9.pool


def pool(typ: str, ls: list[int]) -> list[str]:
    t = " ".join(typ.split())
    extra = _EXTRA.get(t, []) + (REAL_POOLS.get(t, []) if IMPORTS else [])
    return extra + [p for p in _v9_pool(typ, ls) if p not in extra]


def build(tc: Toolchain, out: Path) -> dict:
    b = V9.build(tc, out)
    o = out / "ProofScope" / "BoundarySynth.olean"
    if b["ok"] and not o.exists():
        r = tc.compile(SRC / "ProofScope" / "BoundarySynth.lean", o, SRC, timeout=900)
        return {"ok": r.returncode == 0 and o.exists(), "log": r.as_dict()}
    return b


def synthesize(chain: list[str], symbols: list[dict], tc: Toolchain, buildp: Path, work: Path) -> dict[str, list[str]]:
    work.mkdir(parents=True, exist_ok=True)
    binders = " ".join(f"(x{i + 1} : {s['type']})" for i, s in enumerate(symbols))
    f = work / "Boundary_input.lean"
    f.write_text(import_lines() + "import ProofScope.BoundarySynth\n\n" + "".join(f"#proofscope_boundary (fun {binders} => {S})\n" for S in chain))
    r = tc.run([tc.lean, str(f)], cwd=work, extra_path=buildp, timeout=600)
    per: dict[str, list[str]] = {}
    for line in r.output.splitlines():
        if "PROOFSCOPE_BOUNDARY " not in line:
            continue
        for i, cands in enumerate(json.loads(line[line.index("PROOFSCOPE_BOUNDARY ") + 20:])):
            t = " ".join(symbols[i]["type"].split())
            for c in cands:
                head, _, body = c.partition("=>")
                for v in (c, f"{head}=> ({body.strip()}) + 1", f"{head}=> ({body.strip()}) - 1"):
                    per.setdefault(t, [])
                    if v not in per[t]:
                        per[t].append(v)
    return per


def run_case(spec: dict, tc: Toolchain, buildp: Path, work: Path) -> dict:
    if IMPORTS:
        V9.extract, V9.certify = _extract_with_imports, _certify_with_imports
    d = V9.extract(spec["reference"], spec["lean"], tc, buildp, work / "pre")
    extra = {}
    if "error" not in d and d.get("symbols") and d.get("edits"):
        extra = synthesize([c["abstract"] for c in d["chain"]], d["symbols"], tc, buildp, work / "boundary")
    _EXTRA.clear()
    _EXTRA.update(extra)
    V9.pool = pool
    try:
        row = V9.run_case(spec, tc, buildp, work)
    finally:
        V9.pool = _v9_pool
        V9.extract, V9.certify = _v9_extract, _v9_certify
        _EXTRA.clear()
    row["engine"] = "cmcd_v10"
    row["boundary_candidates"] = extra
    return row


def _one(a):
    p, buildp, out = a
    spec = json.loads(Path(p).read_text())
    row = run_case(spec, Toolchain.find(), buildp, out / "work" / Path(p).stem)
    for k in ("expected", "expected_localized_at", "domain", "family", "split", "must_not_be"):
        row[k] = spec.get(k)
    (out / "rows").mkdir(parents=True, exist_ok=True)
    (out / "rows" / (Path(p).stem + ".json")).write_text(json.dumps(row, ensure_ascii=False, indent=1))
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m proofscope.cmcd_v10")
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args(argv)
    out = a.out.resolve()
    b = build(Toolchain.find(), out / "build")
    if not b["ok"]:
        print(json.dumps(b, indent=2)[:3000])
        return 2
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        rows = list(ex.map(_one, [(p, out / "build", out) for p in a.specs]))
    for r in rows:
        ok = "" if not r.get("expected") else ("OK" if r["verdict"] == r["expected"] else f"MISS(expected {r['expected']})")
        print(r["id"], r["verdict"], r.get("localized_at"), ok, flush=True)
    (out / "cmcd_results.json").write_text(json.dumps({"engine": "cmcd_v10", "rows": rows}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
