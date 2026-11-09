"""Generic certificate engine (v0.7).

`certify(ident, header, obligations, tc, workdir)` takes named Lean propositions, each with a tactic portfolio,
and returns which of them are **certificates**: a declaration counts only if

  1. it elaborates with one of its tactic alternatives (each alternative must close the goal: `(tac); done`),
  2. it recompiles in a clean module written to an `.olean`,
  3. `#print axioms` shows only propext, Classical.choice, Quot.sound (anything with `sorryAx` or another
     axiom is rejected), and
  4. `leanchecker` replays the module.

Anything else is reported with the reason it was rejected. A tool failure can only remove certificates,
never add one.
"""

from __future__ import annotations

import re
from pathlib import Path

from .toolchain import Toolchain

STD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
_ERR = re.compile(r":(\d+):\d+: error", re.M)


def _theorem(name: str, stmt: str, tactics: list[str]) -> str:
    alts = "\n".join(f"    | (({t}); done)" for t in tactics) or "    | done"
    return f"theorem {name} : {stmt} := by\n  first\n{alts}\n"


def _module(ns: str, header: str, obligations: dict, keep: set | None) -> tuple[str, dict]:
    src = header.rstrip() + "\n\n" + f"namespace {ns}\n\n"
    spans = {}
    for k, (stmt, tacs) in obligations.items():
        if keep is not None and k not in keep:
            continue
        a = src.count("\n") + 1
        src += _theorem(k, stmt, tacs) + "\n"
        spans[k] = (a, src.count("\n"))
    src += f"end {ns}\n"
    if keep:
        src += "\n" + "".join(f"#print axioms {ns}.{k}\n" for k in spans)
    return src, spans


def _failed(output: str, spans: dict) -> tuple[set, bool]:
    bad, outside = set(), False
    for m in _ERR.finditer(output):
        line = int(m.group(1))
        hit = [k for k, (a, b) in spans.items() if a <= line <= b]
        bad.update(hit)
        outside |= not hit
    return bad, outside


def _axioms(output: str, ns: str) -> dict:
    res = {}
    for m in re.finditer(r"'%s\.(\w+)' depends on axioms: \[([^\]]*)\]" % re.escape(ns), output):
        res[m.group(1)] = [a.strip() for a in m.group(2).split(",") if a.strip()]
    for m in re.finditer(r"'%s\.(\w+)' does not depend on any axioms" % re.escape(ns), output):
        res[m.group(1)] = []
    return res


def certify(ident: str, header: str, obligations: dict[str, tuple[str, list[str]]], tc: Toolchain,
            workdir: Path, replay: bool = True, timeout: float = 900) -> dict:
    root = Path(workdir).resolve()
    src_root, build = root / "src", root / "build"
    mod_dir = src_root / "ProofScopeCert"
    mod_dir.mkdir(parents=True, exist_ok=True)
    ns = f"ProofScopeCert.{ident}"
    res: dict = {"certificates": {}, "rejected": {}, "status": "OK", "statements": {k: v[0] for k, v in obligations.items()}}

    probe_src, spans = _module(ns, header, obligations, None)
    (mod_dir / f"{ident}Probe.lean").write_text(probe_src)
    probe = tc.compile(mod_dir / f"{ident}Probe.lean", None, src_root, timeout=timeout)
    res["probe"] = probe.as_dict()
    failed, outside = _failed(probe.output, spans)
    if probe.returncode not in (0, 1) or outside:
        res["status"] = "INFRASTRUCTURE_ERROR" if probe.returncode not in (0, 1) else "PREAMBLE_ERROR"
        return res
    for k in failed:
        res["rejected"][k] = "no tactic alternative closed the goal"
    cands = set(spans) - failed
    if not cands:
        return res
    cert_src, _ = _module(ns, header, obligations, cands)
    cf = mod_dir / f"{ident}.lean"
    cf.write_text(cert_src)
    res["certificate_source"] = cert_src
    cc = tc.compile(cf, build / "ProofScopeCert" / f"{ident}.olean", src_root, timeout=timeout)
    res["certify_compile"] = cc.as_dict()
    if cc.returncode != 0:
        for k in cands:
            res["rejected"][k] = "certificate module failed to compile"
        return res
    ax = _axioms(cc.output, ns)
    rp = tc.replay(f"ProofScopeCert.{ident}", build, timeout=timeout) if replay else None
    res["replay"] = rp.as_dict() if rp else {"skipped": True}
    for k in cands:
        a = ax.get(k)
        if a is None:
            res["rejected"][k] = "axiom report missing"
        elif "sorryAx" in a:
            res["rejected"][k] = "depends on sorryAx"
        elif not set(a) <= STD_AXIOMS:
            res["rejected"][k] = f"non-standard axioms {a}"
        elif rp is not None and rp.returncode != 0:
            res["rejected"][k] = "leanchecker replay failed"
        else:
            res["certificates"][k] = {"declaration": f"{ns}.{k}", "statement": obligations[k][0], "axioms": a}
    return res
