"""Definition-fidelity CLI: `python3 -m proofscope.fidelity control | scan | separate | benchmark`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .controls import run_controls
from .report import environment, metrics, verdict, write_reports
from .scan import scan_path
from .separate import PairSpec, run_pair
from .toolchain import Toolchain

DEFAULT_PAIRS = Path(__file__).resolve().parent / "pairs"


def _specs(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in map(Path, paths):
        out += sorted(p.glob("*.json")) if p.is_dir() else [p]
    return out


def _print_verdict(lines: list[str]) -> None:
    print("\n" + "=" * 70 + "\nVERDICT\n" + "=" * 70)
    for v in lines:
        print(" - " + v)


def cmd_control(a) -> int:
    tc = Toolchain.find(a.project)
    r = run_controls(tc)
    print(f"honest module accepted : {'PASS' if r['honest_accepted'] else 'FAIL'}")
    print(f"forged module rejected : {'PASS' if r['forged_rejected'] else 'FAIL'}")
    print(f"forged looked axiom-clean before replay: {r['forged_axioms_look_clean']}")
    write_reports(Path(a.out), environment(tc), r, [], None)
    _print_verdict(verdict(r, [], None))
    return 0 if r["passed"] else 2


def cmd_scan(a) -> int:
    scans = []
    for p in a.paths:
        scans += scan_path(p)
    for s in scans:
        sm = s.summary()
        print(f"{sm['path']}: {sum(sm['declarations'].values())} decls, {sm['definitions_flagged']} flagged defs, "
              f"{len(sm['unproved_statements'])} unproved, hazards={sm['hazards'] or '-'}")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "scan.json").write_text(json.dumps([s.as_dict() for s in scans], indent=2, ensure_ascii=False))
    print(f"\nwrote {out / 'scan.json'}")
    print("\nVERDICT\n - A scan is triage only: flags mark where to look, not errors. Nothing is certified by scanning.")
    return 0


def _run_pairs(a, tc, specs: list[Path]) -> list[dict]:
    results = []
    for i, sp in enumerate(specs, 1):
        spec = PairSpec.load(sp)
        r = run_pair(spec, tc, workdir=Path(a.out) / "work" / spec.ident, replay=not a.no_replay)
        mark = "" if not spec.expected else ("  [ok]" if r.get("correct") else f"  [expected {spec.expected}]")
        print(f"[{i}/{len(specs)}] {spec.id}: {r['classification']}  certs={len(r['certificates'])}{mark}", flush=True)
        results.append(r)
    return results


def cmd_separate(a) -> int:
    tc = Toolchain.find(a.project)
    results = _run_pairs(a, tc, _specs(a.specs))
    jp, mp = write_reports(Path(a.out), environment(tc), None, results, metrics(results))
    print(f"\nwrote {jp}\nwrote {mp}")
    _print_verdict(verdict(None, results, metrics(results)))
    return 0


def cmd_benchmark(a) -> int:
    tc = Toolchain.find(a.project)
    print(f"ProofScope {__version__} · {tc.version()}")
    print("\n[1] kernel controls")
    ctrl = run_controls(tc)
    print(f"    honest accepted: {ctrl['honest_accepted']}  forged rejected: {ctrl['forged_rejected']}")
    print("\n[2] definition pairs")
    results = _run_pairs(a, tc, _specs(a.specs or [str(DEFAULT_PAIRS)]))
    m = metrics(results)
    scans = scan_path(a.scan) if a.scan else None
    jp, mp = write_reports(Path(a.out), environment(tc), ctrl, results, m, scans)
    print(f"\nwrote {jp}\nwrote {mp}")
    _print_verdict(verdict(ctrl, results, m))
    bad = (not ctrl["passed"]) or m["inconsistent_runs"] or any(r.get("expected") and not r.get("correct") for r in results)
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python3 -m proofscope.fidelity", description="ProofScope by Caleb J. Westfall: verify the proof, validate the claim.")
    p.add_argument("--version", action="version", version=f"proofscope {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, out_default):
        sp.add_argument("--out", default=out_default, help="output directory")
        sp.add_argument("--project", default=None, help="Lake project directory (e.g. one with Mathlib) for imports")

    s = sub.add_parser("control", help="positive/negative kernel replay controls")
    common(s, "proofscope-fidelity-evidence/control")
    s.set_defaults(fn=cmd_control)

    s = sub.add_parser("scan", help="static triage of Lean files (no certification)")
    s.add_argument("paths", nargs="+")
    s.add_argument("--out", default="proofscope-fidelity-evidence/scan")
    s.set_defaults(fn=cmd_scan)

    s = sub.add_parser("separate", help="certify equivalence or difference of definition pairs")
    s.add_argument("specs", nargs="+", help="pair spec JSON files or directories")
    s.add_argument("--no-replay", action="store_true")
    common(s, "proofscope-fidelity-evidence/separate")
    s.set_defaults(fn=cmd_separate)

    s = sub.add_parser("benchmark", help="controls + all labelled pairs + metrics")
    s.add_argument("specs", nargs="*", help="pair specs (default: bundled proofscope/pairs)")
    s.add_argument("--scan", default=None, help="optionally also scan a Lean file or directory")
    s.add_argument("--no-replay", action="store_true")
    common(s, "proofscope-fidelity-evidence")
    s.set_defaults(fn=cmd_benchmark)

    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
