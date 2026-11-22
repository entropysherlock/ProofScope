"""SOTA-18 BEq+ runner: the unmodified upstream `beq_plus` (LeanInteract @768e18e, examples/beq_plus.py),
driven exactly as upstream's own `proofnetverif()` driver does: one REPL server with
`TempRequireProject(lean_version="v4.8.0", require="mathlib")`, `timeout_per_proof=DEFAULT_TIMEOUT` (60 s).

    python run_beqplus.py LEANINTERACT_DIR CASES.jsonl OUT --shard i/n

Additions that do not change the method:
* the two headers are merged (imports and `open`s, de-duplicated) into BEq+'s single `src_header`
  argument (identical for ProofNetVerif rows, where both sides share one header);
* a type-check probe of both declarations (with `sorry`) so a pair BEq+ skips as ill-typed is reported as
  NON_ELABORATING instead of being folded into "not equivalent";
* wall time per pair; a pair over the protocol's 900 s cap is reclassified TIMEOUT afterwards.
"""
import importlib.util
import json
import re
import sys
import time
import traceback
from pathlib import Path

CAP = 900.0


def merge_headers(h1, h2):
    seen, imps, rest = set(), [], []
    for line in (h1 + "\n" + h2).splitlines():
        s = line.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        (imps if s.startswith("import ") else rest).append(s)
    return "\n".join(imps + rest) + "\n"


def main():
    li, cases_p, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    i, n = (int(x) for x in sys.argv[sys.argv.index("--shard") + 1].split("/")) if "--shard" in sys.argv else (0, 1)
    cases = [json.loads(l) for l in cases_p.read_text().splitlines() if l.strip()]
    cases = [c for k, c in enumerate(sorted(cases, key=lambda c: c["case_id"])) if k % n == i]
    spec = importlib.util.spec_from_file_location("beq_plus_mod", str(li / "examples" / "beq_plus.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    from lean_interact import AutoLeanServer, LeanREPLConfig, TempRequireProject
    from lean_interact.interface import Command
    t0 = time.time()
    server = AutoLeanServer(config=LeanREPLConfig(project=TempRequireProject(lean_version="v4.8.0", require="mathlib")))
    out.mkdir(parents=True, exist_ok=True)
    (out / "setup.json").write_text(json.dumps({"startup_s": round(time.time() - t0, 1), "per_proof_timeout_s": m.DEFAULT_TIMEOUT}))
    for c in cases:
        safe = re.sub(r"[^A-Za-z0-9_]", "_", c["case_id"])
        p = out / f"{safe}.json"
        if p.exists():
            continue
        header = merge_headers(c["ref_header"], c["cand_header"])
        row = {"case_id": c["case_id"]}
        t1 = time.time()
        try:
            probe = {}
            for side in ("ref", "cand"):
                code = header + "\n\n" + m.clean_last_theorem_string(c[side + "_decl"], f"ps_probe_{side}", add_sorry=True)
                r = server.run(Command(cmd=code), timeout=m.DEFAULT_TIMEOUT * 5)
                msgs = getattr(r, "messages", []) or []
                probe[side] = not any(getattr(x, "severity", "") == "error" for x in msgs)
            row["typechecks"] = probe
            row["beq_plus"] = bool(m.beq_plus(c["ref_decl"], c["cand_decl"], header, server, timeout_per_proof=m.DEFAULT_TIMEOUT))
        except Exception as e:  # noqa: BLE001
            row["error"] = f"{type(e).__name__}: {e}"[:400]
            row["trace"] = traceback.format_exc()[-800:]
        row["seconds"] = round(time.time() - t1, 1)
        if row["seconds"] > CAP:
            row["over_cap"] = True
        p.write_text(json.dumps(row, ensure_ascii=False))
        print(c["case_id"], row.get("beq_plus"), row.get("typechecks"), row["seconds"], row.get("error", ""), flush=True)


if __name__ == "__main__":
    main()
