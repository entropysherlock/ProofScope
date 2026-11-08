"""Scope-fidelity review worksheets (v0.3).

For a project that documents the scope of its formalization in prose (openai/math does this in
`lean/docs/*.md`, one file per result family, each linking the papers and the comparator challenge
statements), build one worksheet per scope document that puts side by side:

  * the scope document's own claims,
  * the exact Lean statement(s) it links to (comments stripped, nothing else changed),
  * junk-value exposure flags: operators whose Lean meaning silently changes off their natural domain
    (`sInf`/`sSup` of empty or unbounded sets, `tsum` of non-summable families, `limUnder` without a
    limit, `limsup`/`liminf` over a conditionally complete lattice, `deriv` without differentiability,
    Bochner integrals without integrability) when the statement asserts no matching guard,
  * any recorded review verdicts from a ledger.

Nothing here is certified. A worksheet is where a qualified reviewer records whether the Lean statement
says what the scope document and paper claim. Verdicts are attributed and typed: HUMAN (named reviewer)
or AI_PRELIMINARY (machine-assisted, must be confirmed by a person).

    python3 -m proofscope.review --lean-dir path/to/openai-math/lean --out worksheets [--ledger reviews.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

VERDICTS = {"FAITHFUL", "FAITHFUL_WITH_NOTE", "DISCREPANCY", "NEEDS_EXPERT", "UNREVIEWED"}
REVIEWER_TYPES = {"HUMAN", "AI_PRELIMINARY"}

# operator regex, guard regex (a guard anywhere in the statement suppresses the flag)
JUNK = {
    "sInf/iInf (empty or unbounded set gives a junk value)": (r"\bsInf\b|⨅|\biInf\b", r"Nonempty|BddBelow"),
    "sSup/iSup (empty or unbounded set gives a junk value)": (r"\bsSup\b|⨆|\biSup\b", r"Nonempty|BddAbove"),
    "tsum (non-summable family sums to 0)": (r"∑'|\btsum\b", r"Summable|HasSum"),
    "limUnder/lim (no limit gives an unspecified value)": (r"\blimUnder\b|\blim\b", r"Tendsto"),
    "limsup/liminf (unbounded sequence gives a junk value in ℝ)": (
        r"\blimsup\b|\bliminf\b", r"IsBoundedUnder|IsCoboundedUnder|EReal|ℝ≥0∞|ENNReal"),
    "deriv/fderiv (non-differentiable point gives 0)": (
        r"\bderiv\b|\bfderiv\b", r"Differentiable|HasDerivAt|HasFDerivAt|ContDiff"),
    "Bochner integral (non-integrable function integrates to 0)": (r"∫(?!⁻)", r"Integrable"),
}


def strip_comments(src: str) -> str:
    src = re.sub(r"/-.*?-/", "", src, flags=re.S)
    return "\n".join(l for l in re.sub(r"--[^\n]*", "", src).split("\n") if l.strip())


def junk_exposure(statement: str) -> list[str]:
    out = []
    for label, (op, guard) in JUNK.items():
        n = len(re.findall(op, statement))
        if n and not re.search(guard, statement):
            out.append(f"{label}: {n} occurrence(s), no guard in the statement")
    return out


def parse_doc(text: str) -> dict:
    title = (re.search(r"^#\s+(.+)$", text, re.M) or [None, ""])[1].strip()
    scope = text.split("## Scope", 1)[1].split("## Comparator", 1)[0].strip() if "## Scope" in text else ""
    papers = re.findall(r"\[([^\]]+)\]\((\.\./\.\./preprints/[^)]+)\)", text)
    links = re.findall(r"\|\s*([^|\n]+?)\s*\|\s*\[[^\]]+\]\((\.\./ComparatorChallenges/[\w]+\.lean)(?:#L\d+(?:-L\d+)?)?\)", text)
    return {"title": title, "scope": scope, "papers": [{"title": t, "path": p} for t, p in papers],
            "challenges": [{"result": r.strip(), "path": p} for r, p in links]}


def load_ledger(path: Path | None, commit: str | None = None) -> dict[str, list[dict]]:
    """Review records apply only to the exact commit they were made against."""
    if not path:
        return {}
    data = json.loads(path.read_text())
    if commit and data.get("commit") != commit:
        return {}
    by: dict[str, list[dict]] = {}
    for r in data.get("reviews", []):
        if r.get("verdict") not in VERDICTS or r.get("reviewer_type") not in REVIEWER_TYPES:
            raise ValueError(f"invalid review record: {r}")
        by.setdefault(r["challenge"], []).append(r)
    return by


def build(lean_dir: Path, out: Path, ledger: Path | None = None, commit: str | None = None) -> dict:
    docs_dir = lean_dir / "docs"
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"no scope documents at {docs_dir}")
    reviews = load_ledger(ledger, commit)
    out.mkdir(parents=True, exist_ok=True)
    (out / "worksheets").mkdir(exist_ok=True)
    index = []
    for d in sorted(docs_dir.glob("*.md")):
        info = parse_doc(d.read_text(errors="replace"))
        ws = [f"# Scope-fidelity worksheet: {info['title']}", "",
              f"Scope document: `{d.relative_to(lean_dir)}` (sha256 `{hashlib.sha256(d.read_bytes()).hexdigest()[:16]}…`)", ""]
        ws += ["## Papers", ""] + [f"- {p['title']} (`{p['path']}`)" for p in info["papers"]] + [""]
        ws += ["## Scope document claims", "", info["scope"] or "_no Scope section_", ""]
        entries = []
        for c in info["challenges"]:
            p = (docs_dir / c["path"]).resolve()
            name = p.stem
            entry = {"challenge": name, "result": c["result"], "exists": p.is_file()}
            ws += [f"## Lean statement: `{name}` ({c['result']})", ""]
            if p.is_file():
                stmt = strip_comments(p.read_text(errors="replace"))
                entry["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
                entry["junk_exposure"] = junk_exposure(stmt)
                ws += ["```lean", stmt, "```", ""]
                ws += ["**Junk-value exposure (triage, not errors):** "
                       + ("; ".join(entry["junk_exposure"]) if entry["junk_exposure"] else "none detected"), ""]
            else:
                ws += ["_linked file missing_", ""]
            recs = reviews.get(name, [])
            entry["reviews"] = recs
            entry["status"] = (recs[-1]["verdict"] + (" (AI_PRELIMINARY)" if recs[-1]["reviewer_type"] == "AI_PRELIMINARY" else ""))\
                if recs else "UNREVIEWED"
            ws += ["**Review record:**", ""]
            if recs:
                for r in recs:
                    ws.append(f"- {r['verdict']} by {r['reviewer']} ({r['reviewer_type']}, {r['date']}): {r['notes']}")
            else:
                ws.append("- UNREVIEWED. Reviewer: compare the statement with the scope document and the paper; "
                          "record FAITHFUL, FAITHFUL_WITH_NOTE, DISCREPANCY (with a Lean-checkable witness if possible) or NEEDS_EXPERT.")
            ws.append("")
            entries.append(entry)
        (out / "worksheets" / f"{d.stem}.md").write_text("\n".join(ws))
        index.append({"doc": d.name, "title": info["title"], "papers": len(info["papers"]), "challenges": entries})
    flat = [c for i in index for c in i["challenges"]]
    summary = {
        "scope_documents": len(index),
        "linked_challenges": len(flat),
        "missing_links": sum(1 for c in flat if not c["exists"]),
        "with_junk_exposure_flags": sum(1 for c in flat if c.get("junk_exposure")),
        "reviewed": sum(1 for c in flat if c["reviews"]),
        "verdicts": {v: sum(1 for c in flat if c["reviews"] and c["reviews"][-1]["verdict"] == v) for v in sorted(VERDICTS)},
        "human_reviewed": sum(1 for c in flat if any(r["reviewer_type"] == "HUMAN" for r in c["reviews"])),
    }
    linked = {c["challenge"] for c in flat}
    cdir = lean_dir / "ComparatorChallenges"
    if cdir.is_dir():
        allc = {p.stem for p in cdir.glob("*.lean")}
        summary["challenge_files"] = len(allc)
        summary["challenges_without_scope_document"] = sorted(allc - linked)
    (out / "worksheet_index.json").write_text(json.dumps({"summary": summary, "documents": index}, indent=2, ensure_ascii=False))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m proofscope.review", description=__doc__.split("\n\n")[0])
    ap.add_argument("--lean-dir", required=True)
    ap.add_argument("--out", default="proofscope-review")
    ap.add_argument("--ledger", default=None, help="JSON review ledger to merge")
    a = ap.parse_args(argv)
    s = build(Path(a.lean_dir), Path(a.out), Path(a.ledger) if a.ledger else None)
    print(json.dumps(s, indent=2))
    print("\nVERDICT\n - Worksheets are review aids. No statement is certified faithful or unfaithful by this tool; "
          "AI_PRELIMINARY verdicts must be confirmed by a qualified person.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
