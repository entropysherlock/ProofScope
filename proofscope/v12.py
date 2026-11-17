"""ProofScope v1.2 runner: Assumption Delta v1.2 (`adelta12`) with sharding and a domain-coverage matrix.

    python -m proofscope.v12 run SPEC.json ... --out DIR [--jobs N] [--shard i/n]
    python -m proofscope.v12 aggregate DIR ... --out coverage.json [--markdown coverage.md]

Coverage separates three things per domain: the statements **elaborate** (Lean accepted both and the
telescope was extracted), the engine reached a **certified** decisive verdict (every decisive verdict is
backed by kernel-checked certificates through the unchanged certify gate), and the verdict **matches**
the pre-registered label. A verdict listed in a case's `must_not_be` is counted as **unsound**.
Conclusion changes are reported as `CONCLUSION_ONLY_CHANGE` and are not scored as decisive here.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from . import adelta12 as AD

DECISIVE = {"ASSUMPTION_EQUIVALENT", "LEAN_WEAKER_BY_ASSUMPTION", "LEAN_STRONGER_BY_ASSUMPTION",
            "ASSUMPTION_INCOMPARABLE", "REFERENCE_NEEDS_ASSUMPTION", "LEAN_CLAIM_FALSE", "BOTH_CLAIMS_FALSE",
            "INCLUSION_MINIMAL", "HAS_REDUNDANT_ASSUMPTIONS", "NO_ASSUMPTION_DELTA", "INCONSISTENT"}


def matches(verdict: str, expected: str | None) -> bool:
    if not expected:
        return False
    if expected.startswith("INCONCLUSIVE"):
        return verdict.startswith("INCONCLUSIVE")
    return verdict == expected


def score_row(r: dict) -> dict:
    v = r.get("verdict", "INCONCLUSIVE")
    elaborated = r.get("reason") != "extraction failed"
    return {"elaborated": elaborated, "certified": v in DECISIVE and v != "INCONSISTENT",
            "conditional": v == "INCLUSION_MINIMAL_IF_THEOREM_HOLDS", "match": matches(v, r.get("expected")),
            "unsound": v in (r.get("must_not_be") or []), "inconsistent": v == "INCONSISTENT"}


def coverage(rows: list[dict]) -> dict:
    by = defaultdict(lambda: defaultdict(int))
    for r in rows:
        s = score_row(r)
        for key in (r.get("domain") or "?", "ALL"):
            d = by[key]
            d["cases"] += 1
            for k, v in s.items():
                d[k] += int(v)
    return {"domains": {k: dict(v) for k, v in sorted(by.items())},
            "unsound_cases": [r["id"] for r in rows if score_row(r)["unsound"]],
            "rows": [{"id": r["id"], "domain": r.get("domain"), "expected": r.get("expected"),
                      "verdict": r.get("verdict"), **score_row(r)} for r in rows]}


def markdown(cov: dict) -> str:
    out = ["| Domain | Cases | Elaborates | Certified decisive | Conditional | Matches label | Unsound |",
           "|---|---|---|---|---|---|---|"]
    for k, d in cov["domains"].items():
        out.append(f"| {k} | {d['cases']} | {d.get('elaborated', 0)} | {d.get('certified', 0)} | "
                   f"{d.get('conditional', 0)} | {d.get('match', 0)} | {d.get('unsound', 0)} |")
    out.append("")
    out.append("Unsound decisive verdicts: " + (", ".join(cov["unsound_cases"]) or "none"))
    return "\n".join(out) + "\n"


def _shard(paths: list[str], spec: str | None) -> list[str]:
    if not spec:
        return paths
    i, n = (int(x) for x in spec.split("/"))
    return [p for k, p in enumerate(sorted(paths)) if k % n == i]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m proofscope.v12")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("specs", nargs="+")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--jobs", type=int, default=1)
    r.add_argument("--shard")
    g = sub.add_parser("aggregate")
    g.add_argument("dirs", nargs="+", type=Path)
    g.add_argument("--out", type=Path, required=True)
    g.add_argument("--markdown", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        specs = _shard(a.specs, a.shard)
        rc = AD.main(specs + ["--out", str(a.out), "--jobs", str(a.jobs)]) if specs else 0
        return rc
    rows = []
    for d in a.dirs:
        rows += [json.loads(p.read_text()) for p in sorted(d.rglob("rows/*.json"))]
    seen = {}
    for row in rows:
        seen[row["id"]] = row
    cov = coverage(list(seen.values()))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(cov, indent=1, ensure_ascii=False))
    md = markdown(cov)
    if a.markdown:
        a.markdown.write_text(md)
    print(md)
    return 1 if cov["unsound_cases"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
