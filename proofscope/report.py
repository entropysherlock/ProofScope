"""Markdown/JSON reports and benchmark metrics."""

from __future__ import annotations

import json
import platform
import time
from pathlib import Path

from . import __version__
from .separate import IN_DOMAIN, INCONSISTENT


def metrics(results: list[dict]) -> dict:
    labelled = [r for r in results if r.get("expected")]
    tp = fp = fn = tn = 0
    for r in labelled:
        exp = r["expected"] == IN_DOMAIN
        got = r["classification"] == IN_DOMAIN
        tp += exp and got
        fp += (not exp) and got
        fn += exp and not got
        tn += (not exp) and not got
    exact = sum(1 for r in labelled if r["classification"] == r["expected"])
    return {
        "labelled_cases": len(labelled),
        "exact_label_accuracy": f"{exact}/{len(labelled)}",
        "in_domain_discrepancy": {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                                  "precision": round(tp / (tp + fp), 3) if tp + fp else None,
                                  "recall": round(tp / (tp + fn), 3) if tp + fn else None},
        "certificates_replayed": sum(len(r.get("certificates", {})) for r in results),
        "inconsistent_runs": sum(1 for r in results if r["classification"] == INCONSISTENT),
        "note": "Controls and mutants are constructed by the project itself: they show the engine behaves as "
                "designed, not that it generalises to unseen formalizations.",
    }


def environment(tc) -> dict:
    return {"proofscope": __version__, "lean": tc.version(), "python": platform.python_version(),
            "platform": platform.platform(), "utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "lake_project": str(tc.project) if tc.project else None}


def verdict(control: dict | None, results: list[dict], m: dict | None) -> list[str]:
    out = []
    if control is not None:
        out.append("Kernel controls PASSED: this machine's checker accepts an honest module and rejects a forged one."
                   if control["passed"] else
                   "Kernel controls FAILED: do not trust any certificate from this machine until this is fixed.")
    if m:
        out.append(f"Labelled benchmark: {m['exact_label_accuracy']} cases got the expected label; "
                   f"{m['certificates_replayed']} certificates passed kernel replay.")
        if m["inconsistent_runs"]:
            out.append("WARNING: contradictory certificates were produced. Treat this run as unsound.")
    real = [r for r in results if r.get("group") == "real"]
    if real:
        found = [r["id"] for r in real if r["classification"] == IN_DOMAIN]
        out.append("Real definition pairs: " + (
            f"{len(found)} certified in-domain discrepancy candidate(s) needing expert review: {', '.join(found)}."
            if found else "no theorem-relevant discrepancy was certified. That is a negative result, reported as such."))
    out.append("Nothing here is a peer-reviewed finding. A certified difference shows two formal notions disagree; "
               "whether that changes the paper's claim is a human judgement.")
    return out


def write_reports(out: Path, env: dict, control: dict | None, results: list[dict], m: dict | None,
                  scans: list | None = None) -> tuple[Path, Path]:
    out.mkdir(parents=True, exist_ok=True)
    data = {"environment": env, "control": control, "results": results, "metrics": m,
            "scans": [s.summary() for s in scans] if scans else None,
            "verdict": verdict(control, results, m)}
    jp = out / "proofscope_report.json"
    jp.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    L = [f"# ProofScope report", "",
         f"ProofScope {env['proofscope']} · {env['lean']} · {env['utc']} UTC", ""]
    if control is not None:
        L += ["## Kernel controls", "",
              f"- honest module accepted: **{'PASS' if control['honest_accepted'] else 'FAIL'}**",
              f"- forged module rejected by replay: **{'PASS' if control['forged_rejected'] else 'FAIL'}**",
              f"- forged declaration looked axiom-clean before replay: {control['forged_axioms_look_clean']}", ""]
    if results:
        L += ["## Definition pairs", "",
              "| Case | Group | Expected | Classification | Certificates (replayed) |",
              "|---|---|---|---|---|"]
        for r in results:
            exp = r.get("expected") or "—"
            mark = "" if not r.get("expected") else (" ✓" if r.get("correct") else " ✗")
            certs = ", ".join(sorted(r.get("certificates", {}))) or "none"
            L.append(f"| `{r['id']}` | {r.get('group','')} | {exp} | **{r['classification']}**{mark} | {certs} |")
        L += ["", "### Interpretations", ""]
        for r in results:
            extra = " (uses pair-specific tactics/lemmas)" if r.get("pair_specific_tactics") or r.get("pair_specific_lemmas") else ""
            L.append(f"- `{r['id']}`: {r['interpretation']}{extra}")
            if r.get("rejected"):
                L.append(f"  - rejected candidates: {r['rejected']}")
        L.append("")
    if m:
        L += ["## Metrics", "", "```", json.dumps(m, indent=1), "```", ""]
    if scans:
        L += ["## Static scan", "", "| File | Defs flagged | Unproved statements | Hazards |", "|---|---|---|---|"]
        for s in scans:
            sm = s.summary()
            L.append(f"| `{Path(sm['path']).name}` | {sm['definitions_flagged']} | {len(sm['unproved_statements'])} | "
                     f"{', '.join(f'{k}: {v}' for k, v in sm['hazards'].items()) or '—'} |")
        L.append("")
    L += ["## VERDICT", ""] + [f"- {v}" for v in data["verdict"]] + [
        "", "## Limits", "",
        "- leanchecker replay uses the same kernel implementation as Lean; it is an anti-tampering replay, not an independent kernel.",
        "- Reference definitions and theorem domains are supplied by a person or AI and must be reviewed independently.",
        "- Bounded agreement is certified only on the stated finite box.",
        "- INCONCLUSIVE means the search failed; it is never counted as a pass.", ""]
    mp = out / "proofscope_report.md"
    mp.write_text("\n".join(L))
    return jp, mp
