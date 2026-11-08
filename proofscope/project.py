"""ProofScope v0.2: audit a pinned public Lean project.

    python3 -m proofscope.project --repo https://github.com/OWNER/REPO --commit <40-hex sha> \
        [--subdir lean] [--modules A.B C.D] [--decls X.y] [--catalog] [--build] --output DIR

Stages (each produces findings labelled VERIFIED / WARNING / INCONCLUSIVE / HUMAN_REVIEW / FAIL / INFO):

  S1  fetch     exactly one commit; verify HEAD == requested SHA; record tree hash
  S2  pins      Lean toolchain, Lake requirements, lake-manifest dependency revisions
  S3  closure   local import closure of every target module, SHA-256 of each file
  S4  hazards   sorry/admit/axiom/native_decide/kernel-check bypass/... inside the closure
  S5  catalog   formalization.yaml main results vs files, declarations and comparator configs
  S6  build     (opt-in) lake build, `#print axioms` per declaration, leanchecker replay

S1-S5 never execute code from the audited project. S6 does (Lake configuration and Lean
elaboration are programs): run it only in a sandbox without credentials, such as the
bundled GitHub workflow, which has read-only permissions and no secrets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .scan import HAZARDS, scan_text

STD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
REPO_RE = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?(\.git)?/?$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SUBDIR_RE = re.compile(r"^[A-Za-z0-9_.\-/]*$")
NAME_RE = re.compile(r"^[A-Za-z_\u00ab][A-Za-z0-9_'!?\u00ab\u00bb\u2080-\u2089]*(\.[A-Za-z0-9_'!?\u00ab\u00bb\u2080-\u2089]+)*$")
IMPORT_RE = re.compile(r"^\s*(?:public\s+)?(?:meta\s+)?import\s+(?:all\s+)?([^\s-][^\n]*)$", re.M)

VERIFIED, WARNING, INCONCLUSIVE, HUMAN_REVIEW, FAIL, INFO = (
    "VERIFIED", "WARNING", "INCONCLUSIVE", "HUMAN_REVIEW", "FAIL", "INFO")
ORDER = [FAIL, WARNING, HUMAN_REVIEW, INCONCLUSIVE, VERIFIED, INFO]


class InputError(ValueError):
    pass


@dataclass
class Finding:
    stage: str
    check: str
    subject: str
    status: str
    detail: str = ""
    data: dict = field(default_factory=dict)


@dataclass
class Audit:
    out: Path
    findings: list[Finding] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    logs: list[dict] = field(default_factory=list)

    def add(self, stage, check, subject, status, detail="", **data):
        f = Finding(stage, check, subject, status, detail, data)
        self.findings.append(f)
        print(f"[{stage}] {status:<12} {check}: {subject}" + (f" - {detail}" if detail else ""), flush=True)
        return f

    def run(self, argv, cwd=None, timeout=None, name="cmd", env=None):
        t0 = time.time()
        try:
            p = subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True, text=True,
                               timeout=timeout, env=env)
            rec = {"name": name, "command": [str(a) for a in argv], "cwd": str(cwd) if cwd else None,
                   "exit_code": p.returncode, "seconds": round(time.time() - t0, 1),
                   "stdout": p.stdout[-40000:], "stderr": p.stderr[-40000:], "execution_error": None}
        except (OSError, subprocess.TimeoutExpired) as e:
            rec = {"name": name, "command": [str(a) for a in argv], "cwd": str(cwd) if cwd else None,
                   "exit_code": None, "seconds": round(time.time() - t0, 1), "stdout": "", "stderr": "",
                   "execution_error": repr(e)}
        logdir = self.out / "logs"
        logdir.mkdir(parents=True, exist_ok=True)
        (logdir / f"{len(self.logs) + 1:02d}_{re.sub(r'[^A-Za-z0-9_.-]', '_', name)[:60]}.json").write_text(
            json.dumps(rec, indent=2))
        self.logs.append({k: rec[k] for k in ("name", "command", "exit_code", "seconds", "execution_error")})
        return rec


# ----------------------------------------------------------------------------- helpers

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def validate(repo: str, commit: str, subdir: str, names: list[str], allow_local: bool = False) -> None:
    if not (REPO_RE.match(repo) or (allow_local and repo.startswith(("file://", "/")))):
        raise InputError(f"repo must look like https://github.com/OWNER/REPO, got {repo!r}")
    if not SHA_RE.match(commit):
        raise InputError("commit must be a full 40-character lowercase hexadecimal SHA (no branches or tags)")
    if not SUBDIR_RE.match(subdir) or ".." in subdir.split("/") or subdir.startswith("/"):
        raise InputError(f"invalid subdir {subdir!r}")
    for n in names:
        if not NAME_RE.match(n):
            raise InputError(f"invalid Lean name {n!r}")


def module_file(root: Path, mod: str) -> Path:
    return root / (mod.replace(".", "/") + ".lean")


def imports_of(text: str) -> list[str]:
    # Only the header (before the first non-import, non-comment command) can contain imports.
    out = []
    for m in IMPORT_RE.finditer(text):
        out += m.group(1).split()
    return [i for i in out if NAME_RE.match(i)]


def strip_comments(src: str) -> str:
    src = re.sub(r"/-.*?-/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), src, flags=re.S)
    return re.sub(r"--[^\n]*", "", src)


def closure(root: Path, mods: list[str]) -> tuple[dict[str, Path], set[str]]:
    """Local import closure. Returns local module -> file, and the set of external imports."""
    local: dict[str, Path] = {}
    external: set[str] = set()
    stack = list(mods)
    while stack:
        m = stack.pop()
        if m in local:
            continue
        f = module_file(root, m)
        if not f.is_file():
            external.add(m)
            continue
        local[m] = f
        for i in imports_of(strip_comments(f.read_text(errors="replace"))):
            if i not in local:
                stack.append(i)
    return local, external


def decl_present(text: str, full: str) -> str:
    """'exact' if the fully-qualified name is declared, 'suffix' if only the last component matches."""
    scan = scan_text(text)
    names = {d.full_name for d in scan.decls}
    if full in names:
        return "exact"
    last = full.split(".")[-1]
    if any(n.split(".")[-1] == last for n in names):
        return "suffix"
    return "missing"


# ----------------------------------------------------------------------------- stages

def s1_fetch(A: Audit, repo: str, commit: str, dest: Path) -> bool:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    git = ["git", "-c", "advice.detachedHead=false", "-c", "protocol.version=2"]
    A.run(git + ["init", "-q"], cwd=dest, name="git_init")
    A.run(git + ["remote", "add", "origin", repo], cwd=dest, name="git_remote")
    f = A.run(git + ["fetch", "-q", "--depth", "1", "origin", commit], cwd=dest, timeout=1800, name="git_fetch")
    if f["exit_code"] != 0:
        A.add("S1", "fetch pinned commit", commit, FAIL, (f["stderr"] or f["execution_error"] or "")[-300:])
        return False
    A.run(git + ["checkout", "-q", "FETCH_HEAD"], cwd=dest, name="git_checkout")
    head = A.run(git + ["rev-parse", "HEAD"], cwd=dest, name="git_head")["stdout"].strip()
    tree = A.run(git + ["rev-parse", "HEAD^{tree}"], cwd=dest, name="git_tree")["stdout"].strip()
    dirty = A.run(git + ["status", "--porcelain"], cwd=dest, name="git_status")["stdout"].strip()
    A.meta["source"] = {"repo": repo, "commit": commit, "head": head, "tree": tree}
    if head == commit and not dirty:
        A.add("S1", "fetch pinned commit", commit, VERIFIED, f"HEAD matches; tree {tree}")
        return True
    A.add("S1", "fetch pinned commit", commit, FAIL, f"HEAD={head} dirty={bool(dirty)}")
    return False


def s2_pins(A: Audit, root: Path) -> dict:
    info: dict = {}
    tc = root / "lean-toolchain"
    if tc.is_file():
        info["toolchain"] = tc.read_text().strip()
        A.add("S2", "Lean toolchain pinned", info["toolchain"],
              VERIFIED if re.search(r":v\d+\.\d+\.\d+", info["toolchain"]) else WARNING,
              "" if re.search(r":v\d+\.\d+\.\d+", info["toolchain"]) else "not an exact release version")
    else:
        A.add("S2", "Lean toolchain pinned", "lean-toolchain", FAIL, "file missing")
    for cfg in ("lakefile.lean", "lakefile.toml"):
        p = root / cfg
        if p.is_file():
            info["lakefile"] = {"path": cfg, "sha256": sha256(p)}
            reqs = re.findall(r'require\s+([^\s]+)\s+from\s+git\s+"([^"]+)"(?:\s*@\s*"([^"]+)")?', p.read_text())
            info["requires"] = [{"name": n, "url": u, "rev": r} for n, u, r in reqs]
            floating = [n for n, _, r in reqs if not SHA_RE.match(r or "")]
            if reqs:
                A.add("S2", "lakefile requirements pinned to commits", cfg,
                      VERIFIED if not floating else WARNING,
                      f"{len(reqs)} requirements" + (f"; not pinned to a SHA: {', '.join(floating)}" if floating else ""))
    man = root / "lake-manifest.json"
    if man.is_file():
        m = json.loads(man.read_text())
        pk = m.get("packages", [])
        info["manifest"] = {"sha256": sha256(man),
                            "packages": [{"name": p.get("name"), "url": p.get("url"), "rev": p.get("rev"),
                                          "inputRev": p.get("inputRev")} for p in pk]}
        bad = [p.get("name") for p in pk if p.get("type", "git") == "git" and not SHA_RE.match(p.get("rev") or "")]
        A.add("S2", "lake-manifest dependency revisions", f"{len(pk)} packages",
              VERIFIED if not bad else FAIL,
              ("no external dependencies" if not pk else "all pinned to exact commits") if not bad else f"unpinned: {bad}")
        moving = [p.get("name") for p in pk if p.get("inputRev") and not SHA_RE.match(p["inputRev"])]
        if moving:
            A.add("S2", "dependencies tracking a branch or tag", f"{len(moving)} packages", INFO,
                  "the manifest pins exact commits, but `lake update` would move these: " + ", ".join(map(str, moving[:12]))
                  + (" ..." if len(moving) > 12 else ""))
    else:
        A.add("S2", "lake-manifest dependency revisions", "lake-manifest.json",
              WARNING if (root / "lakefile.lean").exists() or (root / "lakefile.toml").exists() else INFO,
              "no manifest: dependency revisions are not locked")
    A.meta["pins"] = info
    return info


def s3_closure(A: Audit, root: Path, modules: list[str]) -> dict[str, Path]:
    local, external = closure(root, modules)
    for m in modules:
        if m in local:
            A.add("S3", "target module present", m, VERIFIED, str(module_file(root, m).relative_to(root)))
        else:
            A.add("S3", "target module present", m, FAIL, "no such file in the project")
    manifest = {m: {"path": str(p.relative_to(root)), "sha256": sha256(p)} for m, p in sorted(local.items())}
    (A.out / "SOURCE_MANIFEST.json").write_text(json.dumps(
        {"source": A.meta.get("source"), "local_closure": manifest,
         "external_imports": sorted(external)}, indent=2))
    roots = sorted({e.split(".")[0] for e in external})
    A.add("S3", "local import closure hashed", f"{len(local)} files", VERIFIED if local else INCONCLUSIVE,
          f"external import roots: {', '.join(roots) or 'none'} (pinned by the manifest, not re-hashed here)")
    A.meta["closure"] = {"local_files": len(local), "external_roots": roots}
    return local


def s4_hazards(A: Audit, root: Path, local: dict[str, Path]) -> None:
    counts: dict[str, list[str]] = {}
    axioms: list[str] = []
    for m, p in sorted(local.items()):
        code = strip_comments(p.read_text(errors="replace"))
        for label, rx in HAZARDS:
            for mt in rx.finditer(code):
                line = code.count("\n", 0, mt.start()) + 1
                counts.setdefault(label, []).append(f"{p.relative_to(root)}:{line}")
        for mt in re.finditer(r"^\s*(?:private\s+|protected\s+)?axiom\s+([^\s:({\[]+)", code, re.M):
            axioms.append(f"{mt.group(1)} ({p.relative_to(root)})")
    severity = {"sorry": FAIL, "admit": FAIL, "axiom declaration": WARNING, "kernel type-check bypass": FAIL,
                "implemented_by / extern": WARNING, "unsafe": WARNING, "native_decide (trusts compiler)": WARNING,
                "debug / trust options": WARNING}
    if not counts:
        A.add("S4", "trust hazards in import closure", f"{len(local)} files", VERIFIED,
              "no sorry, admit, axiom, native_decide, unsafe, implemented_by or kernel-check bypass found (text scan)")
    for label, where in sorted(counts.items()):
        A.add("S4", "trust hazard in import closure", label, severity.get(label, WARNING),
              f"{len(where)} occurrence(s): " + ", ".join(where[:6]) + (" ..." if len(where) > 6 else ""),
              locations=where)
    if axioms:
        A.add("S4", "axioms declared in closure", f"{len(axioms)}", HUMAN_REVIEW,
              "an expert must decide whether each is acceptable: " + "; ".join(axioms[:6]))


def s5_catalog(A: Audit, root: Path, limit: int | None) -> list[dict]:
    cat = root / "formalization.yaml"
    if not cat.is_file():
        A.add("S5", "formalization.yaml catalog", "absent", INFO, "no paper-to-Lean catalog to check")
        return []
    try:
        import yaml  # optional dependency, only needed for catalogs
    except ImportError:
        A.add("S5", "formalization.yaml catalog", "present", INCONCLUSIVE, "PyYAML is not installed")
        return []
    data = yaml.safe_load(cat.read_text())
    entries = ((data or {}).get("status") or {}).get("main_results") or []
    A.meta["catalog"] = {"sha256": sha256(cat), "schema_version": (data or {}).get("version"),
                         "main_results": len(entries), "sources": len((data or {}).get("sources") or [])}
    A.add("S5", "formalization.yaml catalog", f"{len(entries)} main results, "
          f"{len((data or {}).get('sources') or [])} sources", INFO)
    if limit:
        entries = entries[:limit]
    counts = {VERIFIED: 0, WARNING: 0, FAIL: 0, HUMAN_REVIEW: 0}
    rows = []
    closure_cache: dict[str, dict[str, Path]] = {}
    for e in entries:
        decl, fpath, cpath = e.get("declaration", ""), e.get("file", ""), e.get("comparator_config")
        row = {"declaration": decl, "file": fpath, "comparator_config": cpath, "checks": {}}
        f = root / fpath
        if not f.is_file():
            row["checks"]["file_exists"] = FAIL
        else:
            row["checks"]["file_exists"] = VERIFIED
            pres = decl_present(f.read_text(errors="replace"), decl)
            row["checks"]["declaration_in_file"] = {"exact": VERIFIED, "suffix": HUMAN_REVIEW, "missing": FAIL}[pres]
        if cpath:
            c = root / cpath
            if not c.is_file():
                row["checks"]["comparator_config"] = FAIL
            else:
                cfg = json.loads(c.read_text())
                listed = decl in (cfg.get("theorem_names") or []) + (cfg.get("definition_names") or [])
                row["checks"]["comparator_lists_declaration"] = VERIFIED if listed else FAIL
                extra = sorted(set(cfg.get("permitted_axioms") or []) - STD_AXIOMS)
                row["checks"]["comparator_permitted_axioms_standard"] = VERIFIED if not extra else WARNING
                if extra:
                    row["extra_permitted_axioms"] = extra
                ch = module_file(root, cfg.get("challenge_module", ""))
                row["checks"]["challenge_module_exists"] = VERIFIED if ch.is_file() else FAIL
                sol = cfg.get("solution_module", "")
                if module_file(root, sol).is_file():
                    if sol not in closure_cache:
                        closure_cache[sol] = closure(root, [sol])[0]
                    in_closure = any(p.resolve() == f.resolve() for p in closure_cache[sol].values()) if f.is_file() else False
                    row["checks"]["solution_module_imports_catalog_file"] = VERIFIED if in_closure else WARNING
                else:
                    row["checks"]["solution_module_imports_catalog_file"] = FAIL
        row["checks"]["statement_matches_paper"] = HUMAN_REVIEW
        worst = min((v for v in row["checks"].values()), key=ORDER.index)
        row["status"] = worst if worst != HUMAN_REVIEW or list(row["checks"].values()).count(HUMAN_REVIEW) > 1 else VERIFIED
        counts[row["status"]] = counts.get(row["status"], 0) + 1
        rows.append(row)
    (A.out / "catalog_audit.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    mech_fail = [r for r in rows if r["status"] == FAIL]
    mech_warn = [r for r in rows if r["status"] == WARNING]
    A.add("S5", "catalog entries mechanically consistent", f"{len(rows)} checked",
          VERIFIED if not mech_fail and not mech_warn else (FAIL if mech_fail else WARNING),
          f"{len(rows) - len(mech_fail) - len(mech_warn)} consistent, {len(mech_warn)} warning, {len(mech_fail)} failing "
          "(file exists, declaration found, comparator config lists it and the solution module imports it)")
    for r in (mech_fail + mech_warn)[:25]:
        bad = {k: v for k, v in r["checks"].items() if v in (FAIL, WARNING)}
        A.add("S5", "catalog entry", r["declaration"], r["status"], json.dumps(bad))
    A.add("S5", "paper-to-Lean statement fidelity", f"{len(rows)} entries", HUMAN_REVIEW,
          "not decidable mechanically: each statement must be compared with its paper by a qualified reviewer")
    cfg_dir = root / "ComparatorChallenges"
    if cfg_dir.is_dir():
        used = {Path(e.get("comparator_config", "")).stem for e in (data.get("status") or {}).get("main_results") or []}
        allcfg = {p.stem for p in cfg_dir.glob("*.json")}
        A.add("S5", "comparator challenges outside the catalog", f"{len(allcfg - used)} of {len(allcfg)}", INFO,
              "these challenges have no main-result catalog entry linking them to a paper")
    return rows


def s6_build(A: Audit, root: Path, modules: list[str], decls: list[str], timeout: int) -> None:
    lake = shutil.which("lake")
    if not lake:
        A.add("S6", "build", "lake", INCONCLUSIVE, "lake not found on PATH")
        return
    v = A.run(["lean", "--version"], cwd=root, name="lean_version")
    A.meta["lean_version"] = v["stdout"].strip()
    manifest = root / "lake-manifest.json"
    uses_mathlib = manifest.is_file() and '"mathlib"' in manifest.read_text()
    if uses_mathlib:
        c = A.run([lake, "exe", "cache", "get"], cwd=root, timeout=timeout, name="lake_cache_get")
        A.add("S6", "Mathlib binary cache", "lake exe cache get", VERIFIED if c["exit_code"] == 0 else WARNING,
              "official cache used (trust assumption)" if c["exit_code"] == 0 else "cache unavailable; building from source")
    b = A.run([lake, "build"] + modules, cwd=root, timeout=timeout, name="lake_build")
    if b["exit_code"] != 0:
        A.add("S6", "lake build", " ".join(modules), FAIL if b["execution_error"] is None else INCONCLUSIVE,
              ((b["stderr"] or b["stdout"])[-400:] or b["execution_error"] or "").strip())
        return
    A.add("S6", "lake build", " ".join(modules), VERIFIED, f"{b['seconds']} s")
    if decls:
        audit_file = root / "ProofScopeAxiomAudit.lean"
        audit_file.write_text("".join(f"import {m}\n" for m in modules) + "\n"
                              + "".join(f"#print axioms {d}\n" for d in decls))
        r = A.run([lake, "env", "lean", str(audit_file)], cwd=root, timeout=timeout, name="axiom_audit")
        out = r["stdout"] + r["stderr"]
        for d in decls:
            m = re.search(r"'%s' depends on axioms: \[([^\]]*)\]" % re.escape(d), out)
            none = re.search(r"'%s' does not depend on any axioms" % re.escape(d), out)
            if none:
                A.add("S6", "axioms of declaration", d, VERIFIED, "no axioms")
            elif m:
                ax = [a.strip() for a in m.group(1).split(",") if a.strip()]
                if "sorryAx" in ax:
                    A.add("S6", "axioms of declaration", d, FAIL, "depends on sorryAx: not proved", axioms=ax)
                elif set(ax) <= STD_AXIOMS:
                    A.add("S6", "axioms of declaration", d, VERIFIED, ", ".join(ax), axioms=ax)
                else:
                    A.add("S6", "axioms of declaration", d, WARNING, "non-standard: " + ", ".join(sorted(set(ax) - STD_AXIOMS)), axioms=ax)
            else:
                err = next((ln.strip() for ln in out.splitlines() if d in ln and "error" in ln), "")
                A.add("S6", "axioms of declaration", d, FAIL if r["exit_code"] != 0 else INCONCLUSIVE,
                      "declaration not found or audit failed" + (f": {err[-240:]}" if err else ""))
    for m in modules:
        rp = A.run([lake, "env", "leanchecker", m], cwd=root, timeout=timeout, name=f"replay_{m}")
        if rp["execution_error"] or "leanchecker" in (rp["stderr"] or "") and "not found" in (rp["stderr"] or ""):
            A.add("S6", "kernel replay (leanchecker, non-fresh)", m, INCONCLUSIVE, "leanchecker unavailable")
        else:
            A.add("S6", "kernel replay (leanchecker, non-fresh)", m, VERIFIED if rp["exit_code"] == 0 else FAIL,
                  "module declarations re-checked by the kernel" if rp["exit_code"] == 0 else (rp["stderr"] or rp["stdout"])[-300:])


# ----------------------------------------------------------------------------- report

def write(A: Audit, args) -> int:
    tally: dict[str, int] = {}
    for f in A.findings:
        tally[f.status] = tally.get(f.status, 0) + 1
    if tally.get(FAIL):
        overall = "FAIL"
    elif tally.get(WARNING) or tally.get(INCONCLUSIVE):
        overall = "PASS_WITH_WARNINGS"
    else:
        overall = "PASS"
    report = {
        "project": "ProofScope by Caleb J. Westfall", "version": __version__, "mode": "project_audit",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(),
        "inputs": {"repo": args.repo, "commit": args.commit, "subdir": args.subdir, "modules": args.modules,
                   "decls": args.decls, "catalog": args.catalog, "build": args.build},
        "meta": A.meta, "overall": overall, "tally": tally,
        "findings": [asdict(f) for f in A.findings], "commands": A.logs,
        "scope": ("Mechanical audit of provenance, trust hazards and catalog consistency"
                  + ("; build, axiom audit and kernel replay of the target modules" if args.build else "; no code from the project was executed")
                  + ". It does not establish that any Lean statement matches its paper."),
    }
    (A.out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

    L = ["# ProofScope project audit", "",
         f"ProofScope {__version__} · {report['timestamp_utc']}", "",
         f"- Repository: {args.repo}", f"- Commit: `{args.commit}`" + (f" (subdir `{args.subdir}`)" if args.subdir else ""),
         f"- Targets: {', '.join(args.modules) or '—'}" + (f"; declarations: {', '.join(args.decls)}" if args.decls else ""),
         f"- Build stage: {'run' if args.build else 'not run (no project code executed)'}", "",
         f"Overall: **{overall}** · " + " · ".join(f"{k}: {v}" for k, v in sorted(tally.items(), key=lambda kv: ORDER.index(kv[0]))), "",
         "## Findings", "", "| Stage | Status | Check | Subject | Detail |", "|---|---|---|---|---|"]
    for f in A.findings:
        d = f.detail.replace("|", "\\|").replace("\n", " ")
        L.append(f"| {f.stage} | **{f.status}** | {f.check} | `{f.subject}` | {d[:300]} |")
    L += ["", "## What the labels mean", "",
          "- **VERIFIED**: established mechanically in this run (see logs).",
          "- **WARNING**: established, but weakens trust or needs a second look.",
          "- **FAIL**: a check that should hold does not.",
          "- **INCONCLUSIVE**: the check could not be completed; never counted as a pass.",
          "- **HUMAN_REVIEW**: cannot be decided mechanically; needs a qualified reviewer.",
          "- **INFO**: context only.", "",
          "## VERDICT", ""]
    L += [f"- {v}" for v in verdict(A, args, overall, tally)]
    L += ["", "## Trust and limits", "",
          "- Text-level scans (S3-S5) can miss hazards hidden behind macros or produced by metaprograms; S6 is the semantic check.",
          "- `leanchecker` uses the same kernel implementation as Lean; replay is an anti-tampering check, not an independent kernel.",
          "- When S6 uses the official Mathlib binary cache, those compiled files are trusted, not rebuilt.",
          "- No finding here says that a formal statement means what the paper claims; that is labelled HUMAN_REVIEW.", ""]
    (A.out / "REPORT.md").write_text("\n".join(L))
    print("\n" + "=" * 70 + "\nVERDICT\n" + "=" * 70)
    for v in verdict(A, args, overall, tally):
        print(" - " + v)
    return 0 if overall != "FAIL" else 1


def verdict(A: Audit, args, overall: str, tally: dict) -> list[str]:
    v = []
    stopped = next((f for f in A.findings if f.stage in ("S0", "S1") and f.status == FAIL), None)
    if stopped:
        return [f"The audit stopped at {stopped.stage} ({stopped.check}): {stopped.detail}",
                "Nothing was scanned, built or certified in this run."]
    src = A.meta.get("source", {})
    if src.get("head") == args.commit:
        v.append(f"The audited source is exactly commit {args.commit[:12]} of {args.repo}.")
    cl = A.meta.get("closure")
    if cl:
        v.append(f"{cl['local_files']} project files in the targets' import closure were hashed.")
    if any(f.stage == "S4" for f in A.findings):
        haz = [f for f in A.findings if f.stage == "S4" and f.status in (FAIL, WARNING)]
        v.append("No trust hazards were found in that closure by text scan." if not haz else
                 f"{len(haz)} trust-hazard type(s) were found in that closure; see S4.")
    else:
        v.append("No target modules were given, so no import closure was hashed or scanned for trust hazards.")
    cat = A.meta.get("catalog")
    if cat:
        row = next((f for f in A.findings if f.check == "catalog entries mechanically consistent"), None)
        if row:
            v.append(f"Catalog: {row.detail}.")
    if args.build:
        ax = [f for f in A.findings if f.check == "axioms of declaration"]
        ok = [f for f in ax if f.status == VERIFIED]
        if ax:
            v.append(f"{len(ok)} of {len(ax)} audited declarations depend only on standard axioms.")
    else:
        v.append("The build stage was not run, so nothing here says the proofs compile.")
    v.append(f"Overall status {overall}. Whether each Lean statement matches its paper remains a human judgement.")
    return v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m proofscope.project", description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--subdir", default="")
    ap.add_argument("--modules", nargs="*", default=[], help="target Lean modules")
    ap.add_argument("--decls", nargs="*", default=[], help="declarations to axiom-audit (needs --build)")
    ap.add_argument("--catalog", action="store_true", help="check formalization.yaml main results")
    ap.add_argument("--catalog-limit", type=int, default=0)
    ap.add_argument("--catalog-targets", type=int, default=0,
                    help="also add the first N catalog main results as module/declaration targets")
    ap.add_argument("--build", action="store_true", help="run lake build, axiom audit and replay (executes project code)")
    ap.add_argument("--build-timeout", type=int, default=3600)
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--output", default="proofscope-project-evidence")
    ap.add_argument("--allow-local", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    # Inputs may arrive through environment variables as whitespace-separated strings.
    a.modules = [m for x in a.modules for m in x.split()]
    a.decls = [d for x in a.decls for d in x.split()]
    a.subdir = a.subdir.strip().strip("/")
    out = Path(a.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    A = Audit(out)
    try:
        validate(a.repo, a.commit, a.subdir, a.modules + a.decls, a.allow_local)
    except InputError as e:
        A.add("S0", "input validation", "arguments", FAIL, str(e))
        return write(A, a)
    A.add("S0", "input validation", "arguments", VERIFIED, "repository URL, 40-hex commit and Lean names accepted")

    work = Path(a.workdir or (out.parent / "proofscope-project-src")).resolve()
    if not s1_fetch(A, a.repo, a.commit, work):
        return write(A, a)
    root = (work / a.subdir) if a.subdir else work
    if not root.is_dir():
        A.add("S1", "subdir present", a.subdir, FAIL)
        return write(A, a)
    s2_pins(A, root)
    rows = s5_catalog(A, root, a.catalog_limit or None) if a.catalog else []
    if a.catalog_targets and rows:
        for r in rows[:a.catalog_targets]:
            mod = r["file"][:-5].replace("/", ".") if r["file"].endswith(".lean") else None
            if mod and mod not in a.modules:
                a.modules.append(mod)
            if r["declaration"] not in a.decls:
                a.decls.append(r["declaration"])
    if a.modules:
        local = s3_closure(A, root, a.modules)
        s4_hazards(A, root, local)
    if a.build:
        if a.modules:
            s6_build(A, root, a.modules, a.decls, a.build_timeout)
        else:
            A.add("S6", "build", "no targets", INCONCLUSIVE, "give --modules or --catalog-targets")
    return write(A, a)


if __name__ == "__main__":
    sys.exit(main())
