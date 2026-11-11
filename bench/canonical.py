"""Canonical benchmark case format, normalization and near-duplicate grouping.

A case is one (reference, candidate) pair of complete Lean *declarations* with their headers, exactly as
the source published them. Adapters may add imports or wrap namespaces; they may never edit the
declarations (protocol: "Matching inputs and resources").

    {"case_id": "c-...", "group": "g-...", "source": "epla-minif2f", "source_ref": "...",
     "ref_header": "...", "ref_decl": "theorem ... := by sorry",
     "cand_header": "...", "cand_decl": "theorem ... := by sorry",
     "toolchain_hint": "...", "provenance": {...}}

Labels never live in a case record; they are kept in a separate (sealed) file keyed by case_id.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REQUIRED = ("case_id", "group", "source", "ref_header", "ref_decl", "cand_header", "cand_decl")
FORBIDDEN_IN_CASE = ("label", "gold", "correct", "expected", "likeness", "equivalent", "adjudicated")

_COMMENT = re.compile(r"--[^\n]*|/-.*?-/", re.S)
_DECL_HEAD = re.compile(r"^\s*(?:@\[[^\]]*\]\s*)?(theorem|lemma|example)\s+([^\s(:{\[]*)", re.M)


def validate(case: dict) -> list[str]:
    errs = [f"missing {k}" for k in REQUIRED if case.get(k) is None]
    errs += [f"empty {k}" for k in ("case_id", "ref_decl", "cand_decl") if case.get(k) == ""]
    errs += [f"label-like field {k!r} in a case record" for k in case if any(f in k.lower() for f in FORBIDDEN_IN_CASE)]
    return errs


def statement_body(decl: str) -> str:
    """The declaration without its name and proof: binders and type only, comments removed,
    whitespace collapsed. Used only for duplicate detection, never as tool input."""
    d = _COMMENT.sub(" ", decl)
    d = _DECL_HEAD.sub(r"\1 _", d, count=1)
    for sep in (":= by", ":="):
        i = d.rfind(sep)
        if i > 0:
            d = d[:i]
            break
    return re.sub(r"\s+", " ", d).strip()


def tokens(s: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_][\w.']*|\d+|[^\s\w]", s))


def norm_hash(decl: str) -> str:
    return hashlib.sha256(statement_body(decl).encode()).hexdigest()[:16]


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


def group_near_duplicates(items: list[tuple[str, str]], threshold: float = 0.9) -> dict[str, str]:
    """Union-find over items (key, text): identical normalized text, or token Jaccard >= threshold,
    puts two items in one group. Quadratic, fine for a few thousand items."""
    parent = {k: k for k, _ in items}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    toks = {k: tokens(statement_body(t)) for k, t in items}
    keys = [k for k, _ in items]
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if jaccard(toks[a], toks[b]) >= threshold:
                parent[find(a)] = find(b)
    return {k: find(k) for k in keys}


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in Path(p).read_text().splitlines() if line.strip()]


def write_jsonl(p: Path, rows: list[dict]) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
