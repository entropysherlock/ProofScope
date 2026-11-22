"""Declaration plumbing shared by adapters (pure text; no semantic edits)."""
from __future__ import annotations

import re

_HEAD = re.compile(r"^(\s*(?:@\[[^\]]*\]\s*)?)(theorem|lemma)\s+([^\s(:{\[]+)", re.M)


def split_header(header: str) -> tuple[list[str], list[str]]:
    """(import lines, other lines) of a source header."""
    imps, rest = [], []
    for line in header.splitlines():
        (imps if line.strip().startswith("import ") else rest).append(line)
    return imps, rest


def with_sorry(decl: str) -> str:
    """The declaration closed with `sorry`, proof text dropped. A declaration that already ends in
    `sorry` has its proof replaced at the last `:=`; one without a proof gets `:= sorry` appended
    (a `:=` inside the statement, e.g. a `let`, is therefore never cut)."""
    d = decl.rstrip()
    if d.endswith("sorry"):
        i = d.rfind(":=")
        return d[:i].rstrip() + " := sorry"
    if d.endswith(":="):
        return d + " sorry"
    return d + " := sorry"


def rename(decl: str, new: str) -> str:
    m = _HEAD.search(decl)
    if not m:
        raise ValueError("no theorem/lemma head")
    return decl[:m.start()] + f"{m.group(1)}theorem {new}" + decl[m.end():]


def merged_imports(*headers: str) -> list[str]:
    out = []
    for h in headers:
        for line in split_header(h)[0]:
            if line.strip() not in out:
                out.append(line.strip())
    return out
