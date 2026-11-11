#!/usr/bin/env python3
"""SL-001 shared code: frozen sources, statement extraction, Stage 1 audit.

Stage 1 is deterministic and uses no theorem prover and no language model.  It
establishes, for each asserted link "Formal Conjectures statement B is formally
proved at OpenAI declaration A", what the two sides literally are, when each was
written, and whether B can be called independent of A.  It certifies nothing.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

FC_URL = "https://github.com/google-deepmind/formal-conjectures"
OAI_URL = "https://github.com/openai/math"
# Frozen commits (see PROTOCOL.md section 3).
FC_PRE = "89294ea02bd7cd678d59984add52cb4baef3dbf4"    # last FC commit before the 2026-10-06 release
FC_LINK = "3dfd999dfe5a3a1c739d362d3189daf9e08d9fa8"   # FC PR #6898, which added the links
FC_HEAD = "da703a5f239f734a47ede2f4e99b9ccc9e644cb5"   # FC main when the protocol was frozen
OAI_LINKED = "adc7f1241b42e322a6451854ab7e4b4c146bf78a"  # commit cited by the FC links (2026-10-06)
OAI_HEAD = "4eaee87548250b2682affda7d05d947c05554bae"    # openai/math main when frozen (2026-10-29)
RELEASE_DATE = "2026-10-06"

LINK_RE = re.compile(
    r'@\[category ([^\]]*?openai/math/blob/([0-9a-f]{40})/(lean/[^"#]+)#L(\d+)[^\]]*)\]\s*\n\s*theorem\s+(\S+)')


def sh(*args: str, cwd: str | None = None) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def blob(repo: str, commit: str, path: str) -> str | None:
    r = subprocess.run(["git", "-C", repo, "show", f"{commit}:{path}"], capture_output=True)
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


def sha(text: str | None) -> str | None:
    return None if text is None else hashlib.sha256(text.encode("utf-8")).hexdigest()


def norm(text: str) -> str:
    return " ".join(text.split())


def theorem_statement(src: str, name: str) -> str | None:
    """Text between `theorem NAME` and the `:=` that starts the proof (exclusive)."""
    m = re.search(r'^\s*theorem\s+' + re.escape(name) + r'(?=[\s:({\[])', src, re.M)
    if not m:
        return None
    rest = src[m.end():]
    end = re.search(r':=', rest)
    return norm(rest[:end.start()] if end else rest[:2000])


def strip_answer(stmt: str) -> tuple[str, bool]:
    """Remove a leading `: answer(...) <->` wrapper, reporting whether one was present."""
    m = re.match(r'^:\s*answer\(\s*(sorry|True|False)\s*\)\s*↔\s*', stmt)
    return (": " + stmt[m.end():], True) if m else (stmt, False)


def core(stmt: str) -> tuple[str, str]:
    """(core proposition text, polarity) with the answer wrapper and one outer negation removed.

    Polarity is 'open' for answer(sorry), 'neg' for answer(False) or a leading ¬, else 'pos'.
    Formal Conjectures resolved `answer(sorry) <-> P` to `answer(False) <-> P` and later rewrote
    that as `¬ P` (PR #6762); all three have the same core P (amendment 1).
    """
    m = re.match(r'^:\s*answer\(\s*(sorry|True|False)\s*\)\s*↔\s*', stmt)
    if m:
        return stmt[m.end():].strip(), {"sorry": "open", "True": "pos", "False": "neg"}[m.group(1)]
    n = re.match(r'^:\s*¬\s*(.*)$', stmt)
    if n:
        inner = n.group(1).strip()
        if inner.startswith("(") and inner.endswith(")") and inner[1:-1].count("(") == inner[1:-1].count(")"):
            inner = inner[1:-1].strip()
        return inner, "neg"
    return stmt.lstrip(":").strip(), "pos"


def qualified_name(src: str, line: int, name: str) -> str:
    """Fully qualified name of a declaration from the `namespace`/`end` lines above it."""
    stack: list[str] = []
    for l in src.split("\n")[:max(0, line - 1)]:
        m = re.match(r'^\s*namespace\s+(\S+)', l)
        if m:
            stack.append(m.group(1))
            continue
        m = re.match(r'^\s*end\s+(\S+)\s*$', l)
        if m and stack and stack[-1] == m.group(1):
            stack.pop()
    return ".".join(p for p in stack + [name] if p).replace("_root_.", "")


def decl_at_line(src: str, line: int) -> tuple[str | None, str | None]:
    """(name, statement) of the theorem whose header is at or just before `line` (1-based)."""
    lines = src.split("\n")
    for i in range(min(line, len(lines)) - 1, max(-1, line - 8), -1):
        m = re.match(r'^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+)?(?:theorem|lemma)\s+(\S+)', lines[i])
        if m:
            name = m.group(1)
            return name, theorem_statement("\n".join(lines[i:]), name)
    return None, None


def defs(src: str) -> dict[str, str]:
    """Normalized bodies of top-level `def`s (name -> text up to the next blank line)."""
    out = {}
    for m in re.finditer(r'^(?:noncomputable\s+)?def\s+(\S+)(.*?)(?=\n\s*\n|\Z)', src, re.M | re.S):
        out[m.group(1)] = norm(m.group(2))
    return out


def import_closure(oai_dir: str, commit: str, path: str) -> int | None:
    """Number of OAI modules in the transitive import closure (working tree must be at `commit`)."""
    root = Path(oai_dir) / "lean"
    head = sh("git", "-C", oai_dir, "rev-parse", "HEAD").strip()
    if head != commit:
        return None
    seen, todo = set(), [path.removeprefix("lean/")]
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        f = root / p
        if not f.exists():
            continue
        seen.add(p)
        for m in re.finditer(r'^\s*(?:public\s+)?import\s+(OAI(?:\.[\w\']+)+)', f.read_text(errors="replace"), re.M):
            todo.append(m.group(1).replace(".", "/") + ".lean")
    return len(seen)


def build_cases(fc: str) -> list[dict]:
    """Enumerate every Erdős-problem theorem in FC_HEAD that links to an openai/math declaration."""
    files = sh("git", "-C", fc, "ls-tree", "-r", "--name-only", FC_HEAD, "FormalConjectures/ErdosProblems/").split()
    cases = []
    for f in sorted(files, key=lambda s: (len(s), s)):
        src = blob(fc, FC_HEAD, f)
        for m in LINK_RE.finditer(src or ""):
            num = Path(f).stem
            cases.append({
                "case_id": f"SL001-E{num}-{m.group(5)}",
                "erdos_problem": int(num),
                "fc_path": f, "fc_theorem": m.group(5),
                "fc_file_sha256_head": sha(src),
                "link_conditional": "conditional formal_proof" in m.group(1),
                "oai_commit_linked": m.group(2), "oai_path": m.group(3), "oai_line": int(m.group(4)),
            })
    return cases


def stage1(case: dict, fc: str, oai: str) -> dict:
    r = {"case_id": case["case_id"], "stage": 1, "erdos_problem": case["erdos_problem"],
         "certifies": "nothing; deterministic text and provenance observations only"}
    f, name = case["fc_path"], case["fc_theorem"]
    # --- side B: the Formal Conjectures statement at three frozen commits
    B = {}
    for tag, c in (("pre", FC_PRE), ("link", FC_LINK), ("head", FC_HEAD)):
        src = blob(fc, c, f)
        st = theorem_statement(src, name) if src else None
        body, wrapped = strip_answer(st) if st else (None, False)
        cr, pol = core(st) if st else (None, None)
        B[tag] = {"commit": c, "file_exists": src is not None, "statement": st,
                  "statement_sha256": sha(st), "body_sha256": sha(cr), "answer_wrapper": wrapped,
                  "polarity": pol}
    r["B"] = B
    first = sh("git", "-C", fc, "log", "--diff-filter=A", "--format=%H %cI %an", "--", f).strip().split("\n")[-1]
    r["B_file_first_commit"] = first
    r["B_theorem_existed_before_release"] = B["pre"]["statement"] is not None
    r["B_body_changed_pre_to_link"] = (B["pre"]["body_sha256"] != B["link"]["body_sha256"]
                                       if B["pre"]["statement"] and B["link"]["statement"] else None)
    r["B_body_changed_link_to_head"] = (B["link"]["body_sha256"] != B["head"]["body_sha256"]
                                        if B["link"]["statement"] and B["head"]["statement"] else None)
    # --- side A: the linked OpenAI declaration
    A = {}
    for tag, c in (("linked", case["oai_commit_linked"]), ("head", OAI_HEAD)):
        src = blob(oai, c, case["oai_path"])
        nm, st = decl_at_line(src, case["oai_line"]) if src else (None, None)
        if tag == "head" and src and A["linked"].get("decl"):   # line may have moved; find by name
            st2 = theorem_statement(src, A["linked"]["decl"])
            nm, st = (A["linked"]["decl"], st2) if st2 else (nm, st)
        A[tag] = {"commit": c, "file_exists": src is not None, "file_sha256": sha(src),
                  "decl": nm, "statement": st, "statement_sha256": sha(st)}
        if tag == "linked" and nm:
            hdr = max([i for i, l in enumerate(src.split("\n"), 1)
                       if re.search(r'\b(?:theorem|lemma)\s+' + re.escape(nm) + r'(?=[\s:({\[])', l)
                       and i <= case["oai_line"]] or [case["oai_line"]])
            A[tag]["qualified_name"] = qualified_name(src, hdr, nm)
    r["A"] = A
    r["A_link_resolves"] = A["linked"]["decl"] is not None
    r["A_statement_changed_linked_to_head"] = (A["linked"]["statement_sha256"] != A["head"]["statement_sha256"]
                                               if A["linked"]["statement"] and A["head"]["statement"] else None)
    # --- OpenAI's own Comparator challenge for A (if any)
    comps = []
    decl = A["linked"].get("qualified_name")
    if decl:
        listing = sh("git", "-C", oai, "ls-tree", "--name-only", OAI_HEAD, "lean/ComparatorChallenges/").split()
        for j in [x for x in listing if x.endswith(".json")]:
            txt = blob(oai, OAI_HEAD, j) or ""
            cfg = json.loads(txt) if '"' + decl + '"' in txt else None
            if cfg and decl in (cfg.get("theorem_names") or []):
                ch = blob(oai, OAI_HEAD, j[:-5] + ".lean") or ""
                comps.append({"config": j, "theorem_names": cfg.get("theorem_names"),
                              "permitted_axioms": cfg.get("permitted_axioms"),
                              "challenge_sha256": sha(ch),
                              "challenge_imports_only_mathlib": bool(re.fullmatch(r'(import Mathlib\S*\s*)+', "".join(
                                  l + "\n" for l in ch.split("\n") if l.startswith("import ")))),
                              "_challenge_defs": defs(ch)})
    # --- did A's statement text come from B?  (shared definitions, verbatim)
    fc_pre_src = blob(fc, FC_PRE, f) or ""
    fc_defs = defs(fc_pre_src)
    shared = []
    for cmp_ in comps:
        for k, v in cmp_.pop("_challenge_defs").items():
            if k in fc_defs and fc_defs[k] == v:
                shared.append(k)
    r["A_comparator_challenges"] = comps
    r["defs_verbatim_identical_in_A_challenge_and_pre_release_B"] = sorted(set(shared))
    a_st, b_body = A["linked"]["statement"], B["head"]["statement"]
    r["A_statement_is_named_proposition"] = bool(a_st and re.fullmatch(r':\s*[\w.\']+', a_st))
    r["A_and_B_statement_text_identical"] = bool(a_st and b_body and norm(a_st) == norm(b_body))
    r["A_import_closure_modules_at_head"] = import_closure(oai, OAI_HEAD, case["oai_path"])
    # --- independence classification (frozen rule, PROTOCOL.md section 6)
    if not r["B_theorem_existed_before_release"]:
        ind = "B_written_after_release"
    elif r["B_body_changed_pre_to_link"]:
        ind = "B_edited_when_linked"
    elif r["defs_verbatim_identical_in_A_challenge_and_pre_release_B"]:
        ind = "B_predates_release_but_A_shares_verbatim_definitions"
    else:
        ind = "B_predates_release_unchanged_no_verbatim_overlap_found"
    r["independence_class"] = ind
    r["outcome"] = "observed" if r["A_link_resolves"] and B["head"]["statement"] else "unsupported_input"
    return r


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build-cases", "stage1", "verify-freeze"])
    ap.add_argument("--fc", required=True)
    ap.add_argument("--oai")
    ap.add_argument("--out", default="experiments/SL-001/results/stage1")
    a = ap.parse_args()
    here = Path(__file__).parent
    if a.cmd == "build-cases":
        cases = build_cases(a.fc)
        (here / "cases.jsonl").write_text("".join(json.dumps(c, sort_keys=True) + "\n" for c in cases))
        print(len(cases), "cases")
        return 0
    cases = [json.loads(l) for l in (here / "cases.jsonl").read_text().splitlines() if l.strip()]
    if a.cmd == "verify-freeze":
        fresh = build_cases(a.fc)
        ok = fresh == cases
        print("frozen cases match sources:", ok)
        return 0 if ok else 1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = []
    for c in cases:
        try:
            r = stage1(c, a.fc, a.oai)
        except Exception as e:   # fail closed: an exception is infrastructure, never a finding
            r = {"case_id": c["case_id"], "stage": 1, "outcome": "blocked_infrastructure", "error": repr(e)}
        res.append(r)
        (out / (c["case_id"] + ".json")).write_text(json.dumps(r, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    summ = {"n_cases": len(res)}
    for key in ("outcome", "independence_class"):
        cnt = {}
        for r in res:
            cnt[r.get(key, "n/a")] = cnt.get(r.get(key, "n/a"), 0) + 1
        summ[key] = cnt
    for flag in ("A_link_resolves", "A_statement_changed_linked_to_head", "B_body_changed_link_to_head",
                 "A_statement_is_named_proposition", "A_and_B_statement_text_identical"):
        summ[flag] = sum(1 for r in res if r.get(flag) is True)
    summ["cases_with_openai_comparator_config"] = sum(1 for r in res if r.get("A_comparator_challenges"))
    cl = [r["A_import_closure_modules_at_head"] for r in res if r.get("A_import_closure_modules_at_head")]
    summ["A_import_closure_modules"] = {"min": min(cl), "max": max(cl), "sum": sum(cl)} if cl else None
    (out / "summary.json").write_text(json.dumps(summ, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summ, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
