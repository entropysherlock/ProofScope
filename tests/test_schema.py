import copy
import json

import pytest

from scopeledger.certificate import claim_status, statement_status
from scopeledger.cli import main
from scopeledger.records import Ledger
from scopeledger.schema import ValidationError, validate

H = "a" * 64
C = "b" * 40
HUMAN = {"kind": "human", "name": "Reviewer One"}
PIPE = {"kind": "pipeline", "name": "sl001"}
MODEL = {"kind": "model", "name": "some-llm"}
SRC = {"kind": "git", "locator": "https://example.org/r", "commit": C, "path": "X.lean"}
CERT = {"checker": "lean kernel + leanchecker", "toolchain": "Lean 4.34.1", "dependencies": "core",
        "artifact_sha256": H, "proposition_sha256": H, "replayed_at": "2026-11-11T00:00:00Z",
        "replay_log": "run-url", "kernel_replay": True, "elaborated_without_error": True,
        "sorry_free": True, "axioms": ["propext"]}


def base(t, slug, **kw):
    return {"id": f"{t}:{slug}", "type": t, "schema": "0.1", "created": "2026-11-11T00:00:00Z",
            "author": PIPE, **kw}


def claim():
    return base("claim", "c1", text="h(k) << k^2", source={"kind": "url", "locator": "https://example.org/p"})


def stmt(slug="s1"):
    return base("statement", slug, language="lean4", source=SRC, identifier="Foo.bar", text_sha256=H)


def ev(level="machine_checked", **kw):
    d = base("evidence", "e1", about="statement:s1", level=level, basis="kernel", certificate=copy.deepcopy(CERT))
    d.update(kw)
    return d


def rel(**kw):
    d = base("relation", "r1", kind="implies", subject="statement:s1", object="statement:s2",
             outcome="certified", basis="kernel", certificate=copy.deepcopy(CERT), reverse="undecided")
    d.update(kw)
    return d


def test_valid_records():
    for r in (claim(), stmt(), ev(), rel()):
        validate(r)


def test_lean_statement_needs_full_commit():
    s = stmt()
    s["source"] = {**SRC, "commit": "abc123"}
    with pytest.raises(ValidationError):
        validate(s)


@pytest.mark.parametrize("mutate", [
    lambda c: c.pop("kernel_replay"),
    lambda c: c.update(kernel_replay=False),
    lambda c: c.update(sorry_free=False),
    lambda c: c.update(elaborated_without_error=False),
    lambda c: c.update(axioms=["sorryAx"]),
    lambda c: c.update(axioms=["myAxiom"]),
    lambda c: c.pop("axioms"),
    lambda c: c.update(axiom_source="print_axioms_only"),
    lambda c: c.pop("proposition_sha256"),
])
def test_incomplete_certificate_refused(mutate):
    e = ev()
    mutate(e["certificate"])
    with pytest.raises(ValidationError):
        validate(e)


def test_model_cannot_certify_or_raise_evidence():
    with pytest.raises(ValidationError):
        validate(ev(basis="model"))
    with pytest.raises(ValidationError):
        validate(ev(level="informal", basis="model", certificate=None, author=MODEL))
    with pytest.raises(ValidationError):
        validate(rel(basis="model"))
    with pytest.raises(ValidationError):
        validate(rel(basis="model", outcome="undecided", certificate=None))
    validate(base("relation", "r9", kind="candidate_similar", subject="statement:s1", object="statement:s2",
                  outcome="observed", basis="heuristic"))


def test_model_review_capped_at_model_suggested():
    rv = base("review", "v1", about={"claim": "claim:c1", "statement": "statement:s1"},
              faithfulness="human_reviewed", basis="model", author=MODEL)
    with pytest.raises(ValidationError):
        validate(rv)
    rv["faithfulness"] = "model_suggested"
    validate(rv)


def test_one_way_is_not_strict_and_failure_is_not_inequivalence():
    with pytest.raises(ValidationError):
        validate(rel(strict=True))                 # strictness needs a separating witness
    with pytest.raises(ValidationError):
        validate(rel(reverse="false"))             # a failed search proves nothing
    with pytest.raises(ValidationError):
        validate(rel(outcome="undecided"))         # non-certified outcome carrying a certificate
    validate(rel(outcome="undecided", certificate=None))
    sep = rel(kind="separated", witness="n = 2", structure_class="natural numbers")
    sep.pop("reverse")
    validate(sep)


def test_equivalence_needs_both_directions_and_allowed_steps():
    r = rel(kind="equivalent")
    r.pop("certificate")
    r["certificates"] = {"forward": copy.deepcopy(CERT)}
    with pytest.raises(ValidationError):
        validate(r)
    r["certificates"]["backward"] = copy.deepcopy(CERT)
    with pytest.raises(ValidationError):
        validate(r)                                # closed-proposition trap: steps must be stated
    r["allowed_steps"] = "identity"
    validate(r)


def test_similarity_and_assertions_cannot_be_certified():
    for kind in ("candidate_similar", "asserted_link", "distinct_text"):
        with pytest.raises(ValidationError):
            validate(rel(kind=kind))


def test_no_single_score():
    c = claim()
    c["trust_score"] = 0.9
    with pytest.raises(ValidationError):
        validate(c)


def test_corroboration_needs_two_humans():
    rv = base("review", "v2", about={"claim": "claim:c1", "statement": "statement:s1"},
              faithfulness="independently_corroborated", basis="human", author=HUMAN,
              reviewers=[HUMAN, HUMAN])
    with pytest.raises(ValidationError):
        validate(rv)
    rv["reviewers"] = [HUMAN, {"kind": "human", "name": "Reviewer Two"}]
    validate(rv)


def test_ledger_immutability_supersede_and_status(tmp_path):
    led = Ledger(tmp_path)
    led.add(claim()); led.add(stmt()); led.add(ev())
    with pytest.raises(ValidationError):
        led.add(ev())                               # same id: immutable
    assert statement_status(led, "statement:s1")["level"] == "machine_checked"
    # kernel proof + no review: the claim is not verified
    assert claim_status(led, "claim:c1")["outcome"] == "asserted"
    led.add(base("review", "v1", about={"claim": "claim:c1", "statement": "statement:s1"},
                 faithfulness="model_suggested", basis="model", author=MODEL))
    assert claim_status(led, "claim:c1")["outcome"] == "supported"
    led.add(base("review", "v2", about={"claim": "claim:c1", "statement": "statement:s1"},
                 faithfulness="independently_corroborated", basis="human", author=HUMAN,
                 reviewers=[HUMAN, {"kind": "human", "name": "Reviewer Two"}]))
    assert claim_status(led, "claim:c1")["outcome"] == "verified"
    # retraction: a superseding record removes the kernel evidence and the label follows
    e2 = ev(level="informal", basis="human", author=HUMAN)
    e2.pop("certificate"); e2["id"] = "evidence:e2"; e2["supersedes"] = "evidence:e1"
    led.add(e2)
    assert statement_status(led, "statement:s1")["level"] == "informal"
    assert claim_status(led, "claim:c1")["outcome"] == "supported"
    assert led.validate_all() == []
    bad = ev(); bad["id"] = "evidence:e3"; bad["supersedes"] = "evidence:nope"
    with pytest.raises(ValidationError):
        led.add(bad)


def test_cli_refuses_and_accepts(tmp_path, capsys):
    good, bad = tmp_path / "g.json", tmp_path / "b.json"
    good.write_text(json.dumps(claim()))
    b = ev(); b["certificate"]["kernel_replay"] = False
    bad.write_text(json.dumps(b))
    led = str(tmp_path / "ledger")
    assert main(["--ledger", led, "add", str(good)]) == 0
    assert main(["--ledger", led, "add", str(bad)]) == 2
    assert main(["--ledger", led, "validate"]) == 0
    assert main(["--ledger", led, "status", "claim:c1"]) == 0
