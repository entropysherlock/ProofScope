"""Static scan of Lean source files: declarations, unproved statements, trust hazards, and definition flags.

This is a text-level triage pass. It never certifies anything. Its job is to tell a reviewer where to
look first: custom definitions whose behaviour depends on Lean conventions (division by zero, truncated
natural subtraction, ...) and constructs that weaken trust (axioms, sorry, kernel-check bypasses).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

DECL_RE = re.compile(
    r"^[ \t]*(?P<attrs>(?:@\[[^\]]*\]\s*)*)"
    r"(?P<mods>(?:(?:private|protected|public|noncomputable|partial|unsafe|nonrec|meta)\s+)*)"
    r"(?P<kind>theorem|lemma|def|abbrev|instance|structure|inductive|class|axiom|opaque|example)\b[ \t]*"
    r"(?P<name>[^\s:(\[{]*(?:\.\{[^}]*\})?)",
    re.M)
NS_RE = re.compile(r"^\s*(?:(?:noncomputable|public|private|meta)\s+)*(namespace|end|section)\b[ \t]*([A-Za-z0-9_.'\u00ab\u00bb]*)", re.M)

# Definition-level flags: Lean conventions that can silently change a definition's meaning off-domain.
DEF_FLAGS = [
    ("division (x/0 = 0)", re.compile(r"(?<![/\-])/(?![/\-])")),
    ("subtraction (truncates at 0 if natural)", re.compile(r"(?<![<\-])-(?![>\-])")),
    ("modulo (x % 0 = x)", re.compile(r"%")),
    ("floor/ceil/sqrt rounding", re.compile(r"\b(Nat\.sqrt|Int\.sqrt|floor|ceil|⌊|⌈|toNat|natAbs)\b")),
    ("log/sqrt/rpow junk values", re.compile(r"\b(Real\.log|Real\.sqrt|Real\.rpow|log|rpow)\b|(?<!Nat\.)(?<!Int\.)\bsqrt\b")),
    ("if-then-else case split", re.compile(r"\bif\b")),
    ("classical choice in definition", re.compile(r"\b(Classical\.|choose|Exists\.choose|epsilon)\b")),
]
# File-level trust hazards.
HAZARDS = [
    ("sorry", re.compile(r"\bsorry\b")),
    ("admit", re.compile(r"\badmit\b")),
    ("axiom declaration", re.compile(r"^\s*axiom\b", re.M)),
    ("kernel type-check bypass", re.compile(r"skipKernelTC")),
    ("implemented_by / extern", re.compile(r"implemented_by|@\[extern")),
    ("unsafe", re.compile(r"\bunsafe\b")),
    ("native_decide (trusts compiler)", re.compile(r"native_decide|Lean\.ofReduceBool")),
    ("debug / trust options", re.compile(r"set_option\s+(debug\.|trust)")),
]


@dataclass
class Decl:
    kind: str
    name: str
    full_name: str
    line: int
    text: str
    flags: list[str] = field(default_factory=list)
    unproved: bool = False


@dataclass
class FileScan:
    path: str
    decls: list[Decl]
    hazards: dict[str, int]

    def summary(self) -> dict:
        kinds: dict[str, int] = {}
        for d in self.decls:
            kinds[d.kind] = kinds.get(d.kind, 0) + 1
        return {"path": self.path, "declarations": kinds,
                "definitions_flagged": sum(1 for d in self.decls if d.kind in ("def", "abbrev") and d.flags),
                "unproved_statements": [d.full_name for d in self.decls if d.unproved],
                "hazards": self.hazards}

    def as_dict(self) -> dict:
        return {"summary": self.summary(), "decls": [asdict(d) for d in self.decls]}


def _strip_comments(src: str) -> str:
    src = re.sub(r"/-.*?-/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), src, flags=re.S)
    return re.sub(r"--[^\n]*", "", src)


def scan_text(src: str, path: str = "<string>") -> FileScan:
    code = _strip_comments(src)
    lines = code.split("\n")
    # namespace tracking by line
    ns_at: list[str] = []
    stack: list[tuple[str, str]] = []
    for ln in lines:
        m = NS_RE.match(ln)
        if m:
            kw, nm = m.groups()
            parts = [x for x in nm.split(".") if x] if nm else []
            if kw == "namespace":
                stack += [("namespace", x) for x in parts]       # `namespace A.B` opens two scopes
            elif kw == "section":
                stack.append(("section", nm))
            else:                                                # `end A.B` closes two, bare `end` one
                for _ in range(max(1, len(parts))):
                    if stack:
                        stack.pop()
        ns_at.append(".".join(n for k, n in stack if k == "namespace" and n))
    starts = [(m.start(), m) for m in DECL_RE.finditer(code)]
    decls: list[Decl] = []
    for i, (pos, m) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(code)
        body = code[pos:end]
        # stop the body at the next namespace/end/section line
        cut = re.search(r"^\s*(namespace|end|section|open|variable)\b", body[1:], re.M)
        if cut:
            body = body[:cut.start() + 1]
        line = code.count("\n", 0, pos) + 1
        kind = m.group("kind")
        name = re.sub(r"\.\{[^}]*\}$", "", m.group("name") or "").rstrip(".") or "(anonymous)"
        ns = ns_at[line - 1] if line - 1 < len(ns_at) else ""
        full = f"{ns}.{name}" if ns and not name.startswith("_root_") else name
        d = Decl(kind=kind, name=name, full_name=full, line=line, text=body.strip()[:2000])
        if kind in ("def", "abbrev"):
            rhs = body.split(":=", 1)[1] if ":=" in body else body
            d.flags = [label for label, rx in DEF_FLAGS if rx.search(rhs)]
        if kind in ("theorem", "lemma", "example") and re.search(r"\bsorry\b", body):
            d.unproved = True
        decls.append(d)
    hazards = {label: len(rx.findall(code)) for label, rx in HAZARDS}
    return FileScan(path=path, decls=decls, hazards={k: v for k, v in hazards.items() if v})


def scan_path(path: str | Path) -> list[FileScan]:
    p = Path(path)
    files = sorted(p.rglob("*.lean")) if p.is_dir() else [p]
    return [scan_text(f.read_text(errors="replace"), str(f)) for f in files]
