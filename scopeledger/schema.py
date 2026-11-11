"""Record schema and validation rules.

Two independent axes are kept apart on purpose:

* proof evidence  -- attached to ONE statement (formal or informal);
* faithfulness    -- attached to a LINK between an informal claim and a formal statement.

A relation between two formal statements is a third kind of object and is never
converted automatically into faithfulness evidence.

Validation is fail-closed: a record that asserts more than its evidence supports is
rejected, not downgraded.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA_VERSION = "0.1"

RECORD_TYPES = ("claim", "statement", "evidence", "relation", "review")

# Axis 1: proof evidence for a statement.
PROOF_LEVELS = (
    "asserted",          # E0 a claim exists, no public argument
    "computational",     # E1 finite checks / numerics, code available
    "informal",          # E2 informal proof is public
    "reviewed",          # E3 informal proof independently reviewed by a named human
    "machine_checked",   # E4 kernel accepted; axioms listed; no sorry
    "reproduced",        # E5 E4 replayed by a party other than the proof's author
    "suspected_false",   # R1 counterexample/gap claimed, unchecked
    "refuted",           # R2 kernel-checked refutation
)
KERNEL_PROOF_LEVELS = ("machine_checked", "reproduced", "refuted")

# Axis 2: faithfulness of an informal-claim <-> formal-statement link.
FAITHFULNESS_LEVELS = (
    "unassessed",                 # F0
    "model_suggested",            # F1 LLM opinion; never counts as evidence
    "human_reviewed",             # F2 one qualified human
    "independently_corroborated", # F3 two independent humans agree
    "formally_related",           # F4 kernel-checked relation to a reference that is itself F3
    "disputed",                   # FD
)

# Who or what produced a judgement.
BASES = ("kernel", "human", "model", "heuristic", "source_assertion")

# Relations between two FORMAL statements (or a certificate and a target statement).
RELATION_KINDS = (
    "candidate_similar",   # text/embedding similarity only; never identity
    "asserted_link",       # a third party asserts X proves/equals Y (e.g. a `formal_proof` link)
    "implies",             # A -> B
    "equivalent",          # A <-> B, both directions certified through allowed steps
    "establishes_target",  # a certificate's library yields a kernel proof of target B
    "separated",           # certified witness that A and B differ on a stated class
    "distinct_text",       # deterministic textual difference between two versions
)

# Outcome of an attempt to establish a relation.  These are kept apart because
# conflating them was the SOTA-18 "F1" defect (verdicts on unelaborated input).
OUTCOMES = (
    "certified",               # kernel replay succeeded on pinned dependencies
    "asserted",                # stated by a source, not checked by us
    "observed",                # deterministic, reproducible non-kernel observation
    "undecided",               # search ran on elaborated input and found nothing
    "timeout",                 # budget exhausted
    "unsupported_input",       # outside the declared fragment
    "compile_failure",         # a statement or proof did not elaborate
    "blocked_infrastructure",  # toolchain/network/version failure; says nothing about maths
)

DEFAULT_ALLOWED_AXIOMS = ("propext", "Classical.choice", "Quot.sound")
FORBIDDEN_AXIOMS = ("sorryAx",)

_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-z]+:[A-Za-z0-9._\-/]+$")


class ValidationError(ValueError):
    """Raised when a record is malformed or claims more than it can support."""


def _need(rec: dict, *keys: str) -> None:
    for k in keys:
        if k not in rec or rec[k] in (None, "", [], {}):
            raise ValidationError(f"{rec.get('id', '<no id>')}: missing required field '{k}'")


def _check_source(src: Any, where: str) -> None:
    if not isinstance(src, dict):
        raise ValidationError(f"{where}: source must be an object")
    _need_in(src, where, "kind", "locator")
    if src["kind"] == "git":
        _need_in(src, where, "commit", "path")
        if not _SHA1.match(src["commit"]):
            raise ValidationError(f"{where}: git source needs a full 40-character commit")
    if "sha256" in src and not _SHA256.match(src["sha256"]):
        raise ValidationError(f"{where}: sha256 must be 64 hex characters")


def _need_in(obj: dict, where: str, *keys: str) -> None:
    for k in keys:
        if not obj.get(k):
            raise ValidationError(f"{where}: missing '{k}'")


def check_certificate(cert: Any, where: str, allowed_axioms=DEFAULT_ALLOWED_AXIOMS) -> None:
    """A certificate is only accepted with a complete kernel-replay record."""
    if not isinstance(cert, dict):
        raise ValidationError(f"{where}: 'certified' requires a certificate object")
    _need_in(cert, where, "checker", "toolchain", "dependencies", "artifact_sha256",
             "proposition_sha256", "replayed_at", "replay_log")
    if cert.get("kernel_replay") is not True:
        raise ValidationError(f"{where}: certificate without kernel_replay=true is not a certificate")
    if cert.get("elaborated_without_error") is not True:
        raise ValidationError(f"{where}: certificate must record elaborated_without_error=true")
    if cert.get("sorry_free") is not True:
        raise ValidationError(f"{where}: certificate must record sorry_free=true")
    for h in ("artifact_sha256", "proposition_sha256"):
        if not _SHA256.match(cert[h]):
            raise ValidationError(f"{where}: {h} must be a sha256")
    axioms = cert.get("axioms")
    if not isinstance(axioms, list):
        raise ValidationError(f"{where}: certificate must list its axioms (may be empty)")
    bad = [a for a in axioms if a in FORBIDDEN_AXIOMS or a not in allowed_axioms]
    if bad:
        raise ValidationError(f"{where}: unapproved axioms {bad}")
    if cert.get("axiom_source") == "print_axioms_only":
        raise ValidationError(f"{where}: '#print axioms' alone is not accepted; "
                              "the proposition itself must also be checked")


def validate(rec: dict) -> dict:
    """Validate one record.  Returns it unchanged or raises ValidationError."""
    if not isinstance(rec, dict):
        raise ValidationError("record must be an object")
    _need(rec, "id", "type", "schema", "created", "author")
    if rec["type"] not in RECORD_TYPES:
        raise ValidationError(f"{rec['id']}: unknown type {rec['type']!r}")
    if not _ID.match(rec["id"]) or not rec["id"].startswith(rec["type"] + ":"):
        raise ValidationError(f"{rec['id']}: id must look like '{rec['type']}:<slug>'")
    for banned in ("trust_score", "score", "confidence"):
        if banned in rec:
            raise ValidationError(f"{rec['id']}: single numerical scores are not part of the model")
    author = rec["author"]
    if not isinstance(author, dict) or author.get("kind") not in ("human", "model", "pipeline"):
        raise ValidationError(f"{rec['id']}: author.kind must be human, model or pipeline")
    getattr(_Validators, rec["type"])(rec)
    return rec


class _Validators:
    @staticmethod
    def claim(rec):
        _need(rec, "text", "source")
        _check_source(rec["source"], rec["id"])

    @staticmethod
    def statement(rec):
        _need(rec, "language", "source", "identifier", "text_sha256")
        _check_source(rec["source"], rec["id"])
        if rec["language"] == "lean4":
            if rec["source"]["kind"] != "git":
                raise ValidationError(f"{rec['id']}: a Lean statement needs a git source with a commit")
        if not _SHA256.match(rec["text_sha256"]):
            raise ValidationError(f"{rec['id']}: text_sha256 must be a sha256")

    @staticmethod
    def evidence(rec):
        _need(rec, "about", "level", "basis")
        if rec["level"] not in PROOF_LEVELS:
            raise ValidationError(f"{rec['id']}: unknown proof level {rec['level']!r}")
        if rec["basis"] not in BASES:
            raise ValidationError(f"{rec['id']}: unknown basis {rec['basis']!r}")
        if rec["level"] in KERNEL_PROOF_LEVELS:
            if rec["basis"] != "kernel":
                raise ValidationError(f"{rec['id']}: level {rec['level']} requires basis 'kernel'")
            check_certificate(rec.get("certificate"), rec["id"],
                              tuple(rec.get("allowed_axioms", DEFAULT_ALLOWED_AXIOMS)))
        if rec["basis"] == "model" and rec["level"] != "asserted":
            raise ValidationError(f"{rec['id']}: a model's assessment cannot raise proof evidence "
                                  "above 'asserted'")
        if rec["level"] == "reviewed" and rec["author"]["kind"] != "human":
            raise ValidationError(f"{rec['id']}: 'reviewed' must be authored by a named human")
        if rec["level"] == "reproduced" and not rec.get("independent_of"):
            raise ValidationError(f"{rec['id']}: 'reproduced' must name whom it is independent of")

    @staticmethod
    def relation(rec):
        _need(rec, "kind", "subject", "object", "outcome", "basis")
        if rec["kind"] not in RELATION_KINDS:
            raise ValidationError(f"{rec['id']}: unknown relation kind {rec['kind']!r}")
        if rec["outcome"] not in OUTCOMES:
            raise ValidationError(f"{rec['id']}: unknown outcome {rec['outcome']!r}")
        if rec["basis"] not in BASES:
            raise ValidationError(f"{rec['id']}: unknown basis {rec['basis']!r}")
        kind, outcome, basis = rec["kind"], rec["outcome"], rec["basis"]
        if outcome == "certified":
            if basis != "kernel":
                raise ValidationError(f"{rec['id']}: only the kernel can certify (basis={basis})")
            if kind in ("candidate_similar", "asserted_link", "distinct_text"):
                raise ValidationError(f"{rec['id']}: {kind} cannot be 'certified'")
            if kind == "equivalent":
                certs = rec.get("certificates") or {}
                for d in ("forward", "backward"):
                    check_certificate(certs.get(d), f"{rec['id']}[{d}]")
                if not rec.get("allowed_steps"):
                    raise ValidationError(
                        f"{rec['id']}: certified equivalence must state its allowed steps; "
                        "bare logical equivalence of two proved closed propositions is trivial")
            elif kind == "separated":
                check_certificate(rec.get("certificate"), rec["id"])
                _need(rec, "witness", "structure_class")
            else:
                check_certificate(rec.get("certificate"), rec["id"])
        else:
            if rec.get("certificate") or rec.get("certificates"):
                raise ValidationError(f"{rec['id']}: a non-certified outcome must not carry a certificate")
        if basis in ("model", "heuristic") and kind not in ("candidate_similar",):
            if outcome not in ("asserted",):
                raise ValidationError(f"{rec['id']}: model/heuristic output may only be recorded as "
                                      "'candidate_similar' or as an 'asserted' opinion")
        if kind == "implies" and rec.get("reverse") not in (None, "undecided", "not_attempted",
                                                           "certified_separately"):
            raise ValidationError(f"{rec['id']}: reverse direction must be undecided, not_attempted "
                                  "or certified_separately")
        if rec.get("strict") and kind != "separated":
            raise ValidationError(f"{rec['id']}: strictness needs a 'separated' record with a witness; "
                                  "a failed reverse search is not strictness")

    @staticmethod
    def review(rec):
        _need(rec, "about", "faithfulness", "basis")
        if rec["faithfulness"] not in FAITHFULNESS_LEVELS:
            raise ValidationError(f"{rec['id']}: unknown faithfulness level")
        f, basis, kind = rec["faithfulness"], rec["basis"], rec["author"]["kind"]
        if basis == "model" or kind == "model":
            if f not in ("model_suggested", "unassessed"):
                raise ValidationError(f"{rec['id']}: a model can record at most 'model_suggested'")
        if f == "human_reviewed" and kind != "human":
            raise ValidationError(f"{rec['id']}: human_reviewed needs a human author")
        if f == "independently_corroborated":
            revs = rec.get("reviewers") or []
            if len({r.get("name") for r in revs if r.get("kind") == "human"}) < 2:
                raise ValidationError(f"{rec['id']}: independently_corroborated needs two distinct humans")
        if f == "formally_related":
            _need(rec, "relation", "reference_review")
