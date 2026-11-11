#!/usr/bin/env python3
"""Turn valid Stage 1 results into ledger records.  Nothing here is a certificate."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).parent))
import sl001  # noqa: E402
from scopeledger.records import Ledger  # noqa: E402

AUTHOR = {"kind": "pipeline", "name": "SL-001 Stage 1 (sl001.py), run by Claude (Anthropic) for Caleb J. Westfall"}
WHEN = "2026-11-11T00:00:00Z"
LIMITS = ["Not replayed: ScopeLedger has not built the OpenAI library.",
          "Statement text extracted by regular expression; hashes allow detection of truncation.",
          "No human has reviewed this record."]


def slug(s):
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)


def main(res_dir="experiments/SL-001/results/stage1", ledger="ledger"):
    led = Ledger(ledger)
    seen = set()

    def add(rec):
        if rec["id"] not in seen:
            seen.add(rec["id"])
            led.add(rec)

    for f in sorted(Path(res_dir).glob("SL001-*.json")):
        r = json.loads(f.read_text())
        if r.get("outcome") != "observed":
            continue
        a, b = r["A"]["linked"], r["B"]["head"]
        case = next(json.loads(l) for l in (Path(__file__).parent / "cases.jsonl").read_text().splitlines()
                    if json.loads(l)["case_id"] == r["case_id"])
        aid = "statement:oai." + slug(a["qualified_name"])
        bid = "statement:fc.erdos" + str(r["erdos_problem"]) + "." + slug(case["fc_theorem"])
        add({"id": aid, "type": "statement", "created": WHEN, "author": AUTHOR, "language": "lean4",
             "identifier": a["qualified_name"], "text_sha256": a["statement_sha256"], "text": a["statement"],
             "source": {"kind": "git", "locator": sl001.OAI_URL, "commit": a["commit"], "path": case["oai_path"],
                        "line": case["oai_line"], "sha256": a["file_sha256"], "license": "Apache-2.0"}})
        add({"id": bid, "type": "statement", "created": WHEN, "author": AUTHOR, "language": "lean4",
             "identifier": case["fc_theorem"], "text_sha256": b["statement_sha256"], "text": b["statement"],
             "source": {"kind": "git", "locator": sl001.FC_URL, "commit": b["commit"], "path": case["fc_path"],
                        "sha256": case["fc_file_sha256_head"], "license": "Apache-2.0"},
             "history": {k: {"commit": v["commit"], "statement_sha256": v["statement_sha256"],
                             "polarity": v["polarity"]} for k, v in r["B"].items()}})
        add({"id": "evidence:oai." + slug(a["qualified_name"]) + ".source", "type": "evidence", "created": WHEN,
             "author": AUTHOR, "about": aid, "level": "asserted", "basis": "source_assertion",
             "note": "openai/math presents this declaration as proved and ships a Comparator config for it: "
                     + ", ".join(c["config"] for c in r["A_comparator_challenges"]) + ". Not replayed here.",
             "permitted_axioms_in_source_config": sorted({x for c in r["A_comparator_challenges"]
                                                           for x in (c["permitted_axioms"] or [])}),
             "known_limitations": LIMITS})
        add({"id": "relation:sl001." + slug(r["case_id"]), "type": "relation", "created": WHEN, "author": AUTHOR,
             "kind": "asserted_link", "subject": aid, "object": bid, "outcome": "asserted",
             "basis": "source_assertion",
             "asserted_by": "google-deepmind/formal-conjectures PR #6898 (formal_proof attribute)",
             "assertion_source": {"kind": "git", "locator": sl001.FC_URL, "commit": sl001.FC_LINK,
                                  "path": case["fc_path"]},
             "conditional": case["link_conditional"],
             "stage1": {"independence_class": r["independence_class"],
                        "B_file_first_commit": r["B_file_first_commit"],
                        "shared_verbatim_definitions": r["defs_verbatim_identical_in_A_challenge_and_pre_release_B"],
                        "A_statement_is_named_proposition": r["A_statement_is_named_proposition"],
                        "A_and_B_statement_text_identical": r["A_and_B_statement_text_identical"],
                        "A_import_closure_modules": r["A_import_closure_modules_at_head"]},
             "comparison_results": "none; no kernel bridge attempted (PROTOCOL.md Stage 2 not launched)",
             "faithfulness": "unassessed", "reviewer_status": "no human review",
             "evidence_path": f"experiments/SL-001/results/stage1/{r['case_id']}.json",
             "known_limitations": LIMITS})
    print(len(seen), "records")


if __name__ == "__main__":
    main(*sys.argv[1:])
