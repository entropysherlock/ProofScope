"""Extract theorem/lemma signatures from a pinned Mathlib checkout (text only, no elaboration).

    python3 extract.py /path/to/mathlib4 > population.json

A declaration is a line starting (after attributes and modifiers) with `theorem` or `lemma`; its
signature is the text up to the first `:=` (or ` where` / a pattern-matching `|`) at bracket depth 0.
Declarations whose function symbol is introduced by a file-level `variable` are not recognised as
mentioning it; that is a limitation of the selection, stated in the report.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HEAD = re.compile(r"^(?:@\[[^\]]*\]\s*)*(?:(?:private|protected|nonrec|noncomputable|scoped|local)\s+)*(theorem|lemma)\s+(\S+)")
OPEN, CLOSE = "([{⟨", ")]}⟩"


def signature(lines, i, start):
    depth, buf = 0, []
    text = lines[i][start:]
    j = i
    while True:
        k = 0
        while k < len(text):
            ch = text[k]
            if ch in OPEN:
                depth += 1
            elif ch in CLOSE:
                depth -= 1
            elif depth == 0 and text.startswith(":=", k):
                return " ".join("".join(buf).split()), j
            elif depth == 0 and (text.startswith(" where", k) and text[k + 6:k + 7] in ("", " ", "\n")):
                return " ".join("".join(buf).split()), j
            elif depth == 0 and ch == "|" and not "".join(buf).strip().endswith(("|", "‖")) and text[k + 1:k + 2] == " " and buf and "".join(buf).rstrip().endswith("\n"):
                return " ".join("".join(buf).split()), j
            buf.append(ch)
            k += 1
        buf.append("\n")
        j += 1
        if j >= len(lines) or j - i > 60:
            return None, j
        text = lines[j]


def main():
    root = Path(sys.argv[1])
    rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
    decls = []
    for p in sorted((root / "Mathlib").rglob("*.lean")):
        lines = p.read_text(encoding="utf-8").split("\n")
        for i, line in enumerate(lines):
            m = HEAD.match(line)
            if not m:
                continue
            sig, _ = signature(lines, i, m.end())
            if sig is None:
                continue
            decls.append({"file": str(p.relative_to(root)), "line": i + 1, "name": m.group(2), "signature": sig})
    blob = json.dumps(decls, ensure_ascii=False, sort_keys=True)
    print(json.dumps({"mathlib_rev": rev, "count": len(decls), "sha256": hashlib.sha256(blob.encode()).hexdigest(),
                      "declarations": decls}, ensure_ascii=False))


if __name__ == "__main__":
    main()
