"""Theorem Intelligence (v0.5): elaborator-based theorem dossiers.

    python3 -m proofscope.dossier --imports Mod1 Mod2 [--decls A.b C.d] [--modules Mod1] \
        [--module-limit N] [--project LAKE_DIR] [--commit SHA] [--replay] --out DIR

Runs the Lean metaprogram `lean/ProofScope/Dossier.lean` inside Lean itself, so every field comes from the
elaborated declaration in the environment, not from source text. Adds provenance (toolchain, commit) and a
kernel status per declaration:

  REPLAYED            the declaring project module was re-checked by `leanchecker` in this run
  REPLAY_FAILED       `leanchecker` rejected the declaring module
  TOOLCHAIN_LIBRARY   declared in the Lean toolchain's own library; trusted with the toolchain, not replayed
  NOT_REPLAYED        not replayed in this run (replay disabled, beyond --replay-limit, or no project)

Axiom status: STANDARD (subset of propext, Classical.choice, Quot.sound), NONE, SORRY (depends on sorryAx),
NONSTANDARD (any other axiom).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .toolchain import Toolchain

SRC = Path(__file__).resolve().parents[1] / "lean"
STD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
REQUIRED = ["theorem_id", "kind", "module", "elaborated_type", "binders", "hypotheses", "conclusion",
            "conclusion_shape", "statement_dependencies", "proof_dependencies", "axioms",
            "source_locations", "unresolved_items"]
TOOLCHAIN_ROOTS = ("Init", "Lean", "Std", "Lake")
NAME_RE = re.compile(r"^[A-Za-z_«][A-Za-z0-9_'!?«».₀-₉]*$")


def build_metaprogram(tc: Toolchain, build: Path) -> dict:
    out = build / "ProofScope" / "Dossier.olean"
    r = tc.compile(SRC / "ProofScope" / "Dossier.lean", out, SRC, timeout=900)
    return {"ok": r.returncode == 0 and out.exists(), "log": r.as_dict()}


def axiom_status(axioms: list[str]) -> str:
    if "sorryAx" in axioms:
        return "SORRY"
    if not axioms:
        return "NONE"
    return "STANDARD" if set(axioms) <= STD_AXIOMS else "NONSTANDARD"


def to_markdown(d: dict) -> str:
    L = [f"# Theorem dossier: `{d['theorem_id']}`", "",
         f"- Kind: {d['kind']} · Module: `{d['module']}` · Lines: {d.get('source_locations') or '—'}",
         f"- Source commit: `{d.get('source_commit') or '—'}` · Toolchain: {d.get('lean_toolchain', '—')}",
         f"- Kernel status: **{d['kernel_status']}** · Axioms: **{d['axiom_status']}** ({', '.join(d['axioms']) or 'none'})",
         "", "## Elaborated statement", "", "```lean", d["elaborated_type"], "```", "",
         f"Conclusion shape: `{d['conclusion_shape']}`", "", "## Binders", "",
         "| Name | Binder | Role | Type |", "|---|---|---|---|"]
    for b in d["binders"]:
        L.append(f"| `{b['name']}` | {b['binder']} | {b['role']} | `{b['type']}` |")
    L += ["", "## Definitions the statement depends on (review these)", ""]
    defs = [x for x in d["statement_dependencies"] if x["role"] == "definition"]
    L += [f"- `{x['name']}` ({x['module']})" for x in defs] or ["- none beyond logic, types and notation"]
    L += ["", f"Other statement dependencies: {len(d['statement_dependencies']) - len(defs)} "
          "(logic, types, notation and typeclass machinery).",
          f"Direct proof dependencies: {len(d['proof_dependencies'])}.", "", "## Unresolved", ""]
    L += [f"- {u}" for u in d["unresolved_items"]]
    L += ["", "_A dossier describes what Lean elaborated. It does not say the statement matches any paper._", ""]
    return "\n".join(L)


def run(imports: list[str], decls: list[str], modules: list[str], out: Path, project: str | None = None,
        commit: str | None = None, module_limit: int | None = None, replay: bool = True,
        replay_limit: int | None = None, isolated_modules: bool = False) -> dict:
    for n in imports + decls + modules:
        if not NAME_RE.match(n):
            raise ValueError(f"invalid Lean name {n!r}")
    out = out.resolve()
    tc = Toolchain.find(project)
    build = out / "_build"
    meta = build_metaprogram(tc, build)
    summary: dict = {"toolchain": tc.version(), "source_commit": commit, "project": project,
                     "metaprogram_built": meta["ok"], "dossiers": 0, "errors": []}
    if not meta["ok"]:
        summary["errors"].append("INFRASTRUCTURE_ERROR: metaprogram failed to compile: "
                                 + meta["log"]["output_tail"][-600:])
        (out / "dossier_index.json").write_text(json.dumps(summary, indent=2))
        return summary
    driver = build / "ProofScopeDriver.lean"
    lim = f" {module_limit}" if module_limit else ""
    outputs: list[str] = []
    failures: list[str] = []
    if isolated_modules:
        # Some individually valid research modules declare identically named
        # constants and CANNOT be imported into one Lean environment.
        # One Lean process per module preserves each elaborated declaration.
        if decls:
            raise ValueError("--isolated-modules is incompatible with --decls")
        if not modules:
            raise ValueError("--isolated-modules requires --modules")
        for number, module in enumerate(dict.fromkeys(modules), 1):
            driver.write_text(f"import {module}\nimport ProofScope.Dossier\n\n"
                              f"#proofscope_dossier_module {module}{lim}\n")
            result = tc.run([tc.lean, str(driver)], cwd=project or build,
                            extra_path=build, timeout=3600)
            outputs.append(f"### ISOLATED MODULE {number}/{len(set(modules))}: {module}\n" + result.output)
            if result.returncode != 0:
                failures.append(f"MODULE_ELABORATION_FAILED: {module} (exit {result.returncode})")
    else:
        driver.write_text("".join(f"import {m}\n" for m in dict.fromkeys(imports + modules)) + "import ProofScope.Dossier\n\n"
                          + (f"#proofscope_dossier {' '.join(decls)}\n" if decls else "")
                          + "".join(f"#proofscope_dossier_module {m}{lim}\n" for m in modules))
        result = tc.run([tc.lean, str(driver)], cwd=project or build,
                        extra_path=build, timeout=3600)
        outputs.append(result.output)
        if result.returncode != 0:
            failures.append(f"ELABORATION_PROCESS_FAILED: exit {result.returncode}")
    output_text = "\n".join(outputs)
    (out / "elaboration.log").write_text(output_text)
    rows = []
    for line in output_text.splitlines():
        i = line.find("PROOFSCOPE_DOSSIER ")
        if i >= 0:
            rows.append(json.loads(line[i + len("PROOFSCOPE_DOSSIER "):]))
    errs = [l for l in output_text.splitlines() if ": error" in l]
    summary["errors"] += failures
    summary["errors"] += [f"ELABORATION_ERROR: {e}" for e in errs[:20]]

    replayed: dict[str, str] = {}
    if replay and project:
        for m in sorted({d["module"] for d in rows if "error" not in d}):
            if m.split(".")[0] in TOOLCHAIN_ROOTS or m.startswith("("):
                continue
            if replay_limit is not None and len(replayed) >= replay_limit:
                break
            rp = tc.run([tc.leanchecker, m] if tc.leanchecker else ["false"], cwd=project, timeout=3600)
            replayed[m] = "REPLAYED" if rp.returncode == 0 else "REPLAY_FAILED"
            (out / "replay").mkdir(exist_ok=True)
            (out / "replay" / f"{m}.log").write_text(rp.output)
    (out / "dossiers").mkdir(parents=True, exist_ok=True)
    kept = []
    for d in rows:
        if "error" in d:
            summary["errors"].append(f"UNKNOWN_CONSTANT: {d['theorem_id']}")
            continue
        missing = [k for k in REQUIRED if k not in d]
        if missing:
            d.setdefault("unresolved_items", []).append(f"fields missing from extraction: {missing}")
        d["source_commit"] = commit
        d["lean_toolchain"] = summary["toolchain"]
        d["axiom_status"] = axiom_status(d["axioms"])
        root = d["module"].split(".")[0]
        if d["module"] in replayed:
            d["kernel_status"] = replayed[d["module"]]
        elif root in TOOLCHAIN_ROOTS:
            d["kernel_status"] = "TOOLCHAIN_LIBRARY"
        else:
            d["kernel_status"] = "NOT_REPLAYED"
        d["verification_evidence"] = {"elaboration_log": "elaboration.log",
                                      "replay_log": f"replay/{d['module']}.log" if d["module"] in replayed else None}
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", d["theorem_id"])[:150]
        (out / "dossiers" / f"{safe}.json").write_text(json.dumps(d, indent=2, ensure_ascii=False))
        (out / "dossiers" / f"{safe}.md").write_text(to_markdown(d))
        kept.append(d)
    summary["dossiers"] = len(kept)
    summary["by_axiom_status"] = {s: sum(1 for d in kept if d["axiom_status"] == s)
                                  for s in ("NONE", "STANDARD", "NONSTANDARD", "SORRY")}
    summary["by_kernel_status"] = {s: sum(1 for d in kept if d["kernel_status"] == s)
                                   for s in ("REPLAYED", "REPLAY_FAILED", "TOOLCHAIN_LIBRARY", "NOT_REPLAYED")}
    summary["with_hypotheses"] = sum(1 for d in kept if d["hypotheses"])
    summary["with_definition_dependencies"] = sum(
        1 for d in kept if any(x["role"] == "definition" for x in d["statement_dependencies"]))
    summary["incomplete_extractions"] = sum(1 for d in kept if any("fields missing" in u for u in d["unresolved_items"]))
    (out / "dossier_index.json").write_text(json.dumps(
        {"summary": summary, "theorems": [{k: d[k] for k in ("theorem_id", "module", "kernel_status", "axiom_status")}
                                           for d in kept]}, indent=2, ensure_ascii=False))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m proofscope.dossier", description=__doc__.split("\n\n")[0])
    ap.add_argument("--imports", nargs="*", default=[])
    ap.add_argument("--decls", nargs="*", default=[])
    ap.add_argument("--modules", nargs="*", default=[], help="dossier every theorem declared in these modules")
    ap.add_argument("--module-limit", type=int, default=None)
    ap.add_argument("--isolated-modules", action="store_true",
                    help="elaborate each module in its own Lean environment to avoid collisions")
    ap.add_argument("--project", default=None, help="Lake project directory (already built)")
    ap.add_argument("--commit", default=None)
    ap.add_argument("--no-replay", action="store_true")
    ap.add_argument("--replay-limit", type=int, default=None, help="replay at most this many project modules")
    ap.add_argument("--out", default="proofscope-dossiers")
    a = ap.parse_args(argv)
    s = run(a.imports, a.decls, a.modules, Path(a.out), a.project, a.commit, a.module_limit, not a.no_replay,
            a.replay_limit, a.isolated_modules)
    print(json.dumps(s, indent=2, ensure_ascii=False))
    ok = s["metaprogram_built"] and s["dossiers"] > 0
    print("\nVERDICT\n - " + (f"{s['dossiers']} theorem dossiers were extracted from Lean's elaborated declarations. "
                              "They describe what was stated and which axioms it uses; they say nothing about whether "
                              "a statement matches a paper." if ok else "No dossiers were produced; see errors."))
    return 0 if ok and not s["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
