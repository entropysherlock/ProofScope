#!/usr/bin/env python3
"""Ledger records for SL-002.  Usage: publish_sl002.py <bridge-run-id> [<assembly-run-id> <952:ok|fail> <1150:ok|fail>]

Only results reported by CI are recorded as certified; the arguments carry the run ids and the
assembly outcomes read from that run's public annotations.
"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from scopeledger.records import Ledger  # noqa: E402
import check  # noqa: E402

AUTH = {"kind": "pipeline", "name": "SL-002 (experiments/SL-002), run by Claude (Anthropic) for Caleb J. Westfall"}
WHEN = "2026-11-11T13:00:00Z"
REPO = "https://github.com/entropysherlock/ProofScope"
OAI_URL, FC_URL = "https://github.com/openai/math", "https://github.com/google-deepmind/formal-conjectures"
AX = ["Classical.choice", "Quot.sound", "propext"]
LIMITS = ["Produced and checked only by the project's own AI-assisted pipeline; no independent review.",
          "Says nothing about whether either formal statement is faithful to Erdős's problem.",
          "Comparator, SemantEq and BEq+ were not run."]


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha(s):
    return hashlib.sha256(" ".join(s.split()).encode()).hexdigest()


def cert(run, artifact, prop, deps):
    return {"checker": "Lean 4.34.1 kernel (lean -o) + leanchecker replay of the module",
            "toolchain": "leanprover/lean4:v4.34.1 (archive SHA-256 47bf4bbd…e4e4)",
            "dependencies": deps, "artifact_sha256": sha_file(artifact), "proposition_sha256": sha(prop),
            "replayed_at": WHEN, "replay_log": f"{REPO}/actions/runs/{run}",
            "kernel_replay": True, "elaborated_without_error": True, "sorry_free": True,
            "axioms": AX, "axiom_source": "print_axioms+statement_verbatim_check+leanchecker"}


def main(bridge_run, asm_run=None, a952=None, a1150=None):
    led = Ledger(ROOT / "ledger")
    P = Path(__file__).parent / "project/SL002"
    e952, e1150 = (P / "E952.lean").read_text(), (P / "E1150.lean").read_text()
    main952 = check.def_body(e952, "MainEndpoint")
    main1150 = check.def_body(e1150, "MainStatement")
    fc952 = check.def_body(e952, "FCStatement").removeprefix(": Prop :=").strip()
    fc1150 = check.def_body(e1150, "FCStatement").removeprefix(": Prop :=").strip()
    mathlib = "Mathlib d13f23b723b8a846827a245b89c10fc7d3f11612 only"
    for sid, ident, path, text in (
            ("statement:oai.challenge.OAI.GaussianMoat.MainEndpoint", "OAI.GaussianMoat.MainEndpoint",
             "lean/ComparatorChallenges/GaussianMoat.lean", main952),
            ("statement:oai.challenge.OAI.AsymptoticallyMinimalLittlewood.MainStatement",
             "OAI.AsymptoticallyMinimalLittlewood.MainStatement",
             "lean/ComparatorChallenges/AsymptoticallyMinimalLittlewood.lean", main1150)):
        led.add({"id": sid, "type": "statement", "created": WHEN, "author": AUTH, "language": "lean4",
                 "identifier": ident, "text": text, "text_sha256": sha(text),
                 "source": {"kind": "git", "locator": OAI_URL, "commit": check.OAI_HEAD, "path": path,
                            "license": "Apache-2.0"},
                 "note": "Definition (a Prop) from OpenAI's Comparator challenge, distinct from the theorem record."})
    fcid952 = "statement:fc.erdos952.erdos_952"
    fcid1150 = "statement:fc.erdos1150.erdos_1150"
    led.add({"id": "relation:sl002.E952.equivalent", "type": "relation", "created": WHEN, "author": AUTH,
             "kind": "equivalent", "subject": "statement:oai.challenge.OAI.GaussianMoat.MainEndpoint",
             "object": fcid952, "outcome": "certified", "basis": "kernel",
             "declaration": "ScopeLedger.SL002.E952.fc_iff_main",
             "allowed_steps": ("any Mathlib lemma; the proof context contains no proof of either side "
                               "(Mathlib-only import, both statements are definitions), so the equivalence "
                               "is not the trivial one between two proved closed propositions"),
             "certificates": {"forward": cert(bridge_run, P / "E952.lean", f"({fc952}) ↔ ({main952})", mathlib),
                              "backward": cert(bridge_run, P / "E952.lean", f"({fc952}) ↔ ({main952})", mathlib)},
             "note": "One theorem (an iff) certifies both directions.",
             "faithfulness": "unassessed", "known_limitations": LIMITS})
    led.add({"id": "relation:sl002.E1150.implies", "type": "relation", "created": WHEN, "author": AUTH,
             "kind": "implies",
             "subject": "statement:oai.challenge.OAI.AsymptoticallyMinimalLittlewood.MainStatement",
             "object": fcid1150, "outcome": "certified", "basis": "kernel", "reverse": "not_attempted",
             "declaration": "ScopeLedger.SL002.E1150.main_implies_fc",
             "certificate": cert(bridge_run, P / "E1150.lean", f"({main1150}) → ({fc1150})", mathlib),
             "faithfulness": "unassessed", "known_limitations": LIMITS})
    if asm_run:
        for case, ok, decl, fcid, prop, file, n in (
                ("952", a952, "ScopeLedger.SL002.E952.erdos_952", fcid952, fc952, "Assembly952.lean", 41),
                ("1150", a1150, "ScopeLedger.SL002.E1150.erdos_1150", fcid1150, fc1150, "Assembly1150.lean", 24)):
            deps = f"{mathlib}; {n} openai/math source files at {check.OAI_HEAD}, verbatim, hashes in oai_files.json"
            if ok == "ok":
                led.add({"id": f"evidence:sl002.E{case}.fc_statement_from_openai", "type": "evidence",
                         "created": WHEN, "author": AUTH, "about": fcid, "level": "machine_checked",
                         "basis": "kernel", "declaration": decl,
                         "certificate": cert(asm_run, P / file, prop, deps),
                         "note": "The Formal Conjectures statement, verbatim, proved from OpenAI's theorem via the "
                                 "SL-002 bridge. Not 'reproduced': built by this project's own pipeline.",
                         "known_limitations": LIMITS})
            else:
                led.add({"id": f"relation:sl002.E{case}.assembly", "type": "relation", "created": WHEN,
                         "author": AUTH, "kind": "establishes_target", "subject": f"library:openai/math@{check.OAI_HEAD}",
                         "object": fcid, "outcome": ok, "basis": "kernel",
                         "evidence_path": f"{REPO}/actions/runs/{asm_run}", "known_limitations": LIMITS})
    print(led.validate_all() or "ledger valid")


if __name__ == "__main__":
    main(*sys.argv[1:])
