"""Dataset integrity for SOTA-4 (repair of the SOTA-3 held-out checksum gate; see docs/sota4/INTEGRITY.md).

Forensic finding (docs/sota4/INTEGRITY.md): the SOTA-3 gate hashed the raw concatenation of the 14 held-out
files. The files were authored without a final newline; on the way into the repository exactly one `\\n` was
appended to each of the 24 CJCS JSON files and to nothing else. The JSON values are unchanged. Removing that
one byte from each held-out file reproduces the recorded digest bb8628b6… exactly.

Repair (only what the evidence justifies):

1. `canonical_bytes`: a file is committed by the SHA-256 of its *canonical JSON*:
     * bytes must decode as UTF-8 (strict; a byte-order mark is rejected);
     * parsed with Python's json module, rejecting duplicate object keys and NaN/Infinity;
     * re-serialized with sorted keys, separators (",", ":"), ensure_ascii=False, allow_nan=False,
       encoded as UTF-8.
   Insignificant whitespace (including any line ending) does not change the digest; any change of a
   key, value, type or array order does.
2. A manifest commits the directory: the file pattern, every file name in sorted order with its canonical
   digest, and a set digest over the ordered (name, digest) list. Verification fails on a missing file, an
   unexpected additional file, a duplicated manifest entry, a manifest that is not in sorted order, invalid
   JSON, or any digest mismatch.
3. The manifest is not derived from the checkout: it was computed from the authenticated original bytes
   (the SOTA-3 patch), and `legacy_raw_digest` ties it to the digest recorded in SOTA-3 before the first
   run: stripping at most one trailing "\\n" per file must reproduce that digest (`--require-legacy`;
   byte-level, so it holds for LF checkouts only; the canonical gate holds for any line ending).

    python -m bench.sota4.integrity verify research/cjcs/core_heldout.MANIFEST.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEME = "proofscope-canonical-json-v1"


class IntegrityError(ValueError):
    pass


def _no_dupes(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise IntegrityError(f"duplicate object key in {keys}")
    return dict(pairs)


def _no_const(c):
    raise IntegrityError(f"non-finite number {c} is not allowed")


def canonical_bytes(raw: bytes) -> bytes:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise IntegrityError("byte-order mark is not allowed")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as e:
        raise IntegrityError(f"not UTF-8: {e}") from None
    try:
        obj = json.loads(text, object_pairs_hook=_no_dupes, parse_constant=_no_const)
    except json.JSONDecodeError as e:
        raise IntegrityError(f"invalid JSON: {e}") from None
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def file_digest(raw: bytes) -> str:
    return hashlib.sha256(canonical_bytes(raw)).hexdigest()


def set_digest(entries: list[dict]) -> str:
    h = hashlib.sha256()
    for e in entries:
        h.update(f"{e['name']}\t{e['canonical_sha256']}\n".encode("utf-8"))
    return h.hexdigest()


def legacy_raw_digest(files: list[Path]) -> str:
    """SOTA-3 gate digest (`cat dir/*.json | sha256sum`) after removing at most one trailing LF per file."""
    h = hashlib.sha256()
    for f in files:
        b = f.read_bytes()
        h.update(b[:-1] if b.endswith(b"\n") else b)
    return h.hexdigest()


def build_manifest(directory: Path, pattern: str, rel: str) -> dict:
    files = sorted(directory.glob(pattern), key=lambda p: p.name)
    entries = [{"name": f.name, "canonical_sha256": file_digest(f.read_bytes())} for f in files]
    return {"scheme": SCHEME, "directory": rel, "pattern": pattern, "files": entries,
            "set_digest": set_digest(entries)}


def verify(manifest_path: Path, root: Path | None = None, require_legacy: bool = False) -> dict:
    m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if m.get("scheme") != SCHEME:
        raise IntegrityError(f"unknown scheme {m.get('scheme')}")
    root = Path(root) if root else Path(manifest_path).resolve().parents[2]
    d = root / m["directory"]
    names = [e["name"] for e in m["files"]]
    if len(names) != len(set(names)):
        raise IntegrityError("duplicated file entry in manifest")
    if names != sorted(names):
        raise IntegrityError("manifest file order is not the committed (sorted) order")
    if set_digest(m["files"]) != m["set_digest"]:
        raise IntegrityError("set digest does not match the manifest entries")
    present = sorted(p.name for p in d.glob(m["pattern"]))
    missing = sorted(set(names) - set(present))
    extra = sorted(set(present) - set(names))
    if missing:
        raise IntegrityError(f"missing files: {missing}")
    if extra:
        raise IntegrityError(f"unexpected additional files: {extra}")
    bad = []
    for e in m["files"]:
        got = file_digest((d / e["name"]).read_bytes())
        if got != e["canonical_sha256"]:
            bad.append({"name": e["name"], "expected": e["canonical_sha256"], "actual": got})
    if bad:
        raise IntegrityError(f"canonical digest mismatch: {bad}")
    res = {"manifest": str(manifest_path), "files": len(names), "set_digest": m["set_digest"], "ok": True}
    leg = m.get("legacy")
    if leg:
        got = legacy_raw_digest([d / n for n in names])
        res["legacy_expected"], res["legacy_reconstructed"] = leg["raw_sha256"], got
        res["legacy_match"] = got == leg["raw_sha256"]
        # byte-level by construction: a CRLF checkout passes the canonical gate but not this one
        if require_legacy and not res["legacy_match"]:
            raise IntegrityError(f"legacy digest not reproduced: {got} != {leg['raw_sha256']}")
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.sota4.integrity")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify")
    v.add_argument("manifests", nargs="+", type=Path)
    v.add_argument("--require-legacy", action="store_true",
                   help="also require the byte-level SOTA-3 digest (LF checkouts; used in CI)")
    a = ap.parse_args(argv)
    ok = True
    for mp in a.manifests:
        try:
            print(json.dumps(verify(mp, require_legacy=a.require_legacy)))
        except IntegrityError as e:
            ok = False
            print(json.dumps({"manifest": str(mp), "ok": False, "error": str(e)}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
