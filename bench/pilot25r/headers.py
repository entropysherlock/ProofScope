"""Recover the source elaboration context for Pilot-25 from the ORIGINAL public archive (PILOT50_PUBLIC_v2.zip).

Only lines that occur verbatim in the original case files and are `open …`, `open scoped …` or `universe …`
are taken (the same whitelist the engine enforces). Nothing is invented: a case whose original file carries no
such line gets an empty preamble. The archive digest and each original file digest are recorded.

    python -m bench.pilot25r.headers --zip PILOT50_PUBLIC_v2.zip --out bench/pilot25r/source_headers.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

from bench.pilot25r.cases import load

LINE = re.compile(r"^(open( scoped)? (?!in\b)[A-Za-z_][A-Za-z0-9_.]*( (?!in\b)[A-Za-z_][A-Za-z0-9_.]*)*|universe [a-z][A-Za-z0-9_]*( [a-z][A-Za-z0-9_]*)*)$")


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.pilot25r.headers")
    ap.add_argument("--zip", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    zb = a.zip.read_bytes()
    want = {d["original_sha256"]: d["id"] for d in load()}
    out = {"archive_sha256": hashlib.sha256(zb).hexdigest(), "cases": {}}
    with zipfile.ZipFile(a.zip) as z:
        for n in z.namelist():
            if n.endswith("/"):
                continue
            b = z.read(n)
            h = hashlib.sha256(b).hexdigest()
            if h not in want:
                continue
            try:
                obj = json.loads(b)
            except json.JSONDecodeError:
                obj = b.decode(errors="replace")
            lines = []
            for s in strings(obj):
                for l in s.splitlines():
                    l = l.strip()
                    if LINE.match(l) and l not in lines:
                        lines.append(l)
            out["cases"][want[h]] = {"original_file": n, "original_sha256": h, "preamble": lines}
    missing = sorted(set(want.values()) - set(out["cases"]))
    out["unmatched_cases"] = missing
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"matched": len(out["cases"]), "unmatched": missing,
                      "with_preamble": sum(bool(c["preamble"]) for c in out["cases"].values())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
