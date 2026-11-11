"""SOTA-18 SemantEq runner (hlxr89/SemantEq@f92767000e14, v1.4.0, native toolchain v4.30.0-rc1).

    python run_semanteq.py SEMANTEQ_DIR CASES.jsonl OUT --shard i/n

Input is SemantEq's documented pair format: each side is its source header followed by the declaration
closed with `sorry` (as in SemantEq's own `test/pnv_fetch.py`). Batch mode (one process, environments
cached), `--raw --timeout 300` (PROTOCOL.md section 5). If the process dies, the first pair without a
record is recorded as ERROR and the batch resumes on the remaining pairs. A pair whose `elapsedMs`
exceeds the 900 s cap is reclassified TIMEOUT afterwards.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def with_sorry(decl):
    d = decl.rstrip()
    if d.endswith("sorry"):
        return d[:d.rfind(":=")].rstrip() + " := sorry"
    return d + " sorry" if d.endswith(":=") else d + " := sorry"


def side(header, decl):
    return f"{header.rstrip()}\n\n{with_sorry(decl)}\n"


def main():
    sdir, cases_p, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), Path(sys.argv[3]).resolve()
    i, n = (int(x) for x in sys.argv[sys.argv.index("--shard") + 1].split("/")) if "--shard" in sys.argv else (0, 1)
    cases = [json.loads(l) for l in cases_p.read_text().splitlines() if l.strip()]
    cases = [c for k, c in enumerate(sorted(cases, key=lambda c: c["case_id"])) if k % n == i]
    out.mkdir(parents=True, exist_ok=True)
    done = {}
    attempt = 0
    while True:
        todo = [c for c in cases if c["case_id"] not in done]
        if not todo:
            break
        attempt += 1
        inp, res = out / f"pairs_{attempt}.jsonl", out / f"results_{attempt}.jsonl"
        inp.write_text("".join(json.dumps({"id": c["case_id"], "reference": side(c["ref_header"], c["ref_decl"]),
                                           "candidate": side(c["cand_header"], c["cand_decl"])}, ensure_ascii=False) + "\n"
                               for c in todo))
        t0 = time.time()
        try:
            r = subprocess.run(["lake", "exe", "semanteq", "--raw", "--timeout", "300", str(inp), str(res)], cwd=sdir,
                               capture_output=True, text=True, timeout=900 * len(todo) + 600)
            rc, tail = r.returncode, (r.stdout + r.stderr)[-1500:]
        except subprocess.TimeoutExpired:
            rc, tail = -9, "batch timeout"
        got = 0
        if res.exists():
            for line in res.read_text().splitlines():
                if line.strip():
                    rec = json.loads(line)
                    if "id" in rec and rec["id"] not in done:
                        done[rec["id"]] = {"record": rec}
                        got += 1
        print(f"attempt {attempt}: rc={rc} records={got} of {len(todo)} in {time.time() - t0:.0f}s", flush=True)
        missing = [c for c in todo if c["case_id"] not in done]
        if missing:
            done[missing[0]["case_id"]] = {"record": None, "error": f"process ended rc={rc} without a record", "tail": tail}
    for cid, d in done.items():
        rec = d.get("record") or {}
        if rec.get("elapsedMs") and rec["elapsedMs"] > 900_000:
            d["over_cap"] = True
        (out / (re.sub(r"[^A-Za-z0-9_]", "_", cid) + ".json")).write_text(json.dumps({"case_id": cid, **d}, ensure_ascii=False))
        print(cid, rec.get("verdict"), rec.get("elapsedMs"), d.get("error", ""), flush=True)


if __name__ == "__main__":
    main()
