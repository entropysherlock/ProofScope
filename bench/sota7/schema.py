"""Versioned case and gold-label formats (proofscope-eval/1).

Public case (what the engine may see) — one JSON file per case:
  schema, case_id (opaque: "c" + 12 hex), task ("relation" | "repair"), domain, difficulty,
  provenance {source, url, retrieved, license, upstream_revision}, environment {lean, mathlib, imports},
  reference {text, lean}, candidate {text, lean}, context (repair: [[var, type], ...]),
  repair (repair task only: reference/candidate hypothesis forms, edits, pool — the SOTA-6 spec fields).
Gold label (never given to the engine) — one JSON line per case in a separate file:
  schema, case_id, relation (EQUIVALENT | REF_STRONGER | CAND_STRONGER | INCOMPARABLE | NOT_EQUIVALENT |
  UNRESOLVED), closed_truth {reference, candidate} (TRUE | FALSE | UNKNOWN; optional), intended_repairs
  (list of sorted edit-index lists) or "NONE_IN_GRAMMAR" (repair task), evidence, reviewers (ids),
  rationales, adjudication (AGREED | ADJUDICATED | UNRESOLVED | SYNTHETIC_DEVELOPMENT), labeler_class
  (INDEPENDENT | INTERNAL | SYNTHETIC_DEVELOPMENT).
Mechanically verified facts (hashes, elaboration) and human interpretation (gold) live in different files.
"""
from __future__ import annotations

import re

SCHEMA = "proofscope-eval/1"
RELATIONS = {"EQUIVALENT", "REF_STRONGER", "CAND_STRONGER", "INCOMPARABLE", "NOT_EQUIVALENT", "UNRESOLVED"}
ADJ = {"AGREED", "ADJUDICATED", "UNRESOLVED", "SYNTHETIC_DEVELOPMENT"}
LABELER = {"INDEPENDENT", "INTERNAL", "SYNTHETIC_DEVELOPMENT"}
ID_RE = re.compile(r"^c[0-9a-f]{12}$")
# words that would disclose a label if they appeared in engine-visible metadata
LEAK = re.compile(r"(?i)\b(equivalent|non[-_ ]?equiv|not[-_ ]equiv|stronger|weaker|incomparable|differ(ence|s)?|"
                  r"gold|label|expected|correct|wrong|faithful|unfaithful|drift|repair[-_ ]?(is|=)|minimal[-_ ]repair)\b")
PUBLIC_REQ = {"schema", "case_id", "task", "domain", "difficulty", "provenance", "environment", "reference", "candidate"}
PUBLIC_ALLOWED = PUBLIC_REQ | {"context", "repair"}
META_FIELDS = ("domain", "difficulty", "provenance")


class SchemaError(ValueError):
    pass


def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)


def validate_public(c: dict) -> None:
    if c.get("schema") != SCHEMA:
        raise SchemaError(f"schema must be {SCHEMA}")
    miss = PUBLIC_REQ - set(c)
    if miss:
        raise SchemaError(f"missing fields {sorted(miss)}")
    extra = set(c) - PUBLIC_ALLOWED
    if extra:
        raise SchemaError(f"fields not allowed in a public case (possible label leak): {sorted(extra)}")
    if not ID_RE.match(c["case_id"]):
        raise SchemaError("case_id must be opaque (c + 12 hex digits)")
    if c["task"] not in ("relation", "repair"):
        raise SchemaError("task must be relation or repair")
    for k in ("reference", "candidate"):
        if not isinstance(c[k], dict) or not isinstance(c[k].get("lean"), str) or not c[k]["lean"].strip():
            raise SchemaError(f"{k}.lean must be a non-empty Lean statement")
    for p in ("source", "license", "retrieved"):
        if not c["provenance"].get(p):
            raise SchemaError(f"provenance.{p} required")
    for f in META_FIELDS:
        for s in _strings(c[f]):
            if LEAK.search(s):
                raise SchemaError(f"metadata field {f} contains label-revealing wording: {s!r}")
    if c["task"] == "repair":
        r = c.get("repair")
        if not r or not all(k in r for k in ("context", "reference", "candidate", "edits", "pool")):
            raise SchemaError("repair task needs repair.{context, reference, candidate, edits, pool}")
        for k in r:
            if k not in ("context", "reference", "candidate", "edits", "pool"):
                raise SchemaError(f"repair.{k} not allowed")


def validate_gold(g: dict, task: str) -> None:
    if g.get("schema") != SCHEMA:
        raise SchemaError("gold schema mismatch")
    if not ID_RE.match(g.get("case_id", "")):
        raise SchemaError("gold case_id must be opaque")
    if g.get("relation") not in RELATIONS:
        raise SchemaError(f"relation must be one of {sorted(RELATIONS)}")
    if g.get("adjudication") not in ADJ or g.get("labeler_class") not in LABELER:
        raise SchemaError("adjudication / labeler_class invalid")
    if g["labeler_class"] == "INDEPENDENT":
        revs = g.get("reviewers") or []
        if len(set(revs)) < 2:
            raise SchemaError("an INDEPENDENT label needs two distinct reviewers")
        if len(g.get("rationales") or []) < 2 or not all(str(r).strip() for r in g["rationales"]):
            raise SchemaError("each reviewer must give a rationale")
        if g["adjudication"] == "SYNTHETIC_DEVELOPMENT":
            raise SchemaError("INDEPENDENT labels cannot be synthetic")
    if g["labeler_class"] == "SYNTHETIC_DEVELOPMENT" and g["adjudication"] not in ("SYNTHETIC_DEVELOPMENT", "UNRESOLVED"):
        raise SchemaError("synthetic labels must be marked SYNTHETIC_DEVELOPMENT")
    if g["adjudication"] == "UNRESOLVED" and g["relation"] != "UNRESOLVED":
        raise SchemaError("unresolved adjudication must have relation UNRESOLVED")
    if task == "repair" and "intended_repairs" not in g:
        raise SchemaError("repair gold needs intended_repairs (list or NONE_IN_GRAMMAR)")
