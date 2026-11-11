"""Append-only record store: one JSON file per record, history kept in Git.

Records are never edited in place.  A correction is a new record that names the
record it supersedes; a dispute is a new record that names what it disputes.
"""
from __future__ import annotations

import json
from pathlib import Path

from .schema import SCHEMA_VERSION, ValidationError, validate

DIRS = {"claim": "claims", "statement": "statements", "evidence": "evidence",
        "relation": "relations", "review": "reviews"}


class Ledger:
    def __init__(self, root: str | Path = "ledger"):
        self.root = Path(root)

    def path_for(self, rec_id: str) -> Path:
        rtype, slug = rec_id.split(":", 1)
        return self.root / DIRS[rtype] / (slug.replace("/", "__") + ".json")

    def add(self, rec: dict) -> Path:
        rec.setdefault("schema", SCHEMA_VERSION)
        validate(rec)
        p = self.path_for(rec["id"])
        if p.exists():
            raise ValidationError(f"{rec['id']} already exists; records are immutable. "
                                  "Write a new record with 'supersedes'.")
        for ref in ("supersedes", "disputes"):
            if rec.get(ref) and not self.path_for(rec[ref]).exists():
                raise ValidationError(f"{rec['id']}: {ref} target {rec[ref]} not in ledger")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        return p

    def all(self) -> list[dict]:
        out = []
        for d in DIRS.values():
            for f in sorted((self.root / d).glob("*.json")):
                out.append(json.loads(f.read_text(encoding="utf-8")))
        return out

    def get(self, rec_id: str) -> dict:
        return json.loads(self.path_for(rec_id).read_text(encoding="utf-8"))

    def validate_all(self) -> list[str]:
        errors, ids = [], set()
        recs = self.all()
        for r in recs:
            try:
                validate(r)
            except ValidationError as e:
                errors.append(str(e))
            ids.add(r.get("id"))
        for r in recs:
            for ref in ("supersedes", "disputes"):
                if r.get(ref) and r[ref] not in ids:
                    errors.append(f"{r['id']}: dangling {ref} -> {r[ref]}")
        return errors

    def superseded(self) -> set[str]:
        return {r["supersedes"] for r in self.all() if r.get("supersedes")}

    def disputed(self) -> set[str]:
        return {r["disputes"] for r in self.all() if r.get("disputes")}

    def active(self) -> list[dict]:
        gone = self.superseded()
        return [r for r in self.all() if r["id"] not in gone]
