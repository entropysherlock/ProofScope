"""SOTA-18 ProofScope runner (frozen engine; PROTOCOL.md sections 4-5).

    PROOFSCOPE_IMPORTS=Mathlib LEAN_PATH=<mathlib> python experiments/sota18/run_proofscope.py CASES.jsonl OUT --shard i/n

Per pair:
 1. Adapter (from SOTA-1 `bench/adapters/proofscope.py`, branch competitor-benchmark-audit): each declaration
    is elaborated in its own header and its type is printed with fully qualified names, outside the
    header's `open`s. The printed text is re-elaborated under the imports alone and checked to be
    *reducibly definitionally equal* to the declaration's type (`with_reducible rfl`). Two print
    settings are tried; the first that round-trips is used. This check is the adapter's
    meaning-preservation certificate: ProofScope is only ever given the propositions the dataset states.
 2. Frozen engines, unchanged: `python -m proofscope.adelta12` and `python -m proofscope.cmcd_v10` on
    {"id", "reference": printed ref, "lean": printed cand}.
 3. The SOTA-15/16/17 claim grammar (`proofscope.scope_expr.parse`) is applied to the printed
    propositions to count how many could enter the ScopeElim / multi-occurrence fragments at all.
All stages share one external budget of 900 s wall per pair. Nothing is retried.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import resource
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
BUDGET = 900.0
PRINT_OPTS = [
    "(((o.setBool `pp.fullNames true).setBool `pp.funBinderTypes true).setBool `pp.proofs true).setBool `pp.deepTerms true",
    "(((((o.setBool `pp.fullNames true).setBool `pp.funBinderTypes true).setBool `pp.proofs true).setBool `pp.deepTerms true)"
    ".setBool `pp.coercions false).setBool `pp.numericTypes true",
]
HEAD = re.compile(r"^(\s*(?:@\[[^\]]*\]\s*)?)(theorem|lemma)\s+([^\s(:{\[⦃]+)", re.M)


# ---------------------------------------------------------------- adapter (text plumbing, from SOTA-1)
def split_header(header: str):
    imps, rest = [], []
    for line in header.splitlines():
        (imps if line.strip().startswith("import ") else rest).append(line)
    return imps, rest


def with_sorry(decl: str) -> str:
    d = decl.rstrip()
    if d.endswith("sorry"):
        i = d.rfind(":=")
        return d[:i].rstrip() + " := sorry"
    if d.endswith(":="):
        return d + " sorry"
    return d + " := sorry"


def rename(decl: str, new: str) -> str:
    m = HEAD.search(decl)
    if not m:
        raise ValueError("no theorem/lemma head")
    return decl[:m.start()] + f"{m.group(1)}theorem {new}" + decl[m.end():]


def imports_of(case) -> list[str]:
    out = []
    for h in (case["ref_header"], case["cand_header"]):
        for line in split_header(h)[0]:
            if line.strip() not in out:
                out.append(line.strip())
    return out


def body_of(header: str) -> str:
    rest = split_header(header)[1]
    if any(l.strip().startswith(("namespace", "end ")) for l in rest):
        raise ValueError("header opens a namespace")
    return "\n".join(rest)


def print_file(case) -> str:
    src = "\n".join(["import Lean"] + imports_of(case)) + "\n"
    for side in ("ref", "cand"):
        name = f"ps_{side}_decl"
        src += f"\nsection\n{body_of(case[side + '_header'])}\n\n{rename(with_sorry(case[side + '_decl']), name)}\n\nend\n"
    for side in ("ref", "cand"):
        for k, opts in enumerate(PRINT_OPTS):
            src += (f"\nopen Lean Elab Command in\n#eval show CommandElabM Unit from do\n"
                    f"  let some ci := (← getEnv).find? `ps_{side}_decl | throwError \"PS_NO_DECL\"\n"
                    f"  let fmt ← liftTermElabM <| withOptions (fun o => {opts}) <| Meta.ppExpr ci.type\n"
                    f"  logInfo m!\"PS_CLOSED {side} {k} {{(toString fmt).replace \"\\n\" \" \"}}\"\n")
    return src


def check_file(case, printed: dict) -> tuple[str, dict]:
    src = "\n".join(imports_of(case)) + "\n"
    for side in ("ref", "cand"):
        src += f"\nsection\n{body_of(case[side + '_header'])}\n\n{rename(with_sorry(case[side + '_decl']), f'ps_{side}_decl')}\n\nend\n"
    lines = {}
    for (side, k), txt in printed.items():
        src += "\n"
        lines[(side, k)] = src.count("\n") + 1
        src += f"example : ({txt}) = type_of% @ps_{side}_decl := by with_reducible rfl\n"
    return src, lines


def run(cmd, cwd, timeout, env=None):
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=max(1.0, timeout), env=env)
        return r.returncode, (r.stdout or "") + (r.stderr or ""), time.time() - t0
    except subprocess.TimeoutExpired as e:
        txt = lambda b: b.decode("utf-8", "replace") if isinstance(b, bytes) else (b or "")
        return -9, txt(e.stdout) + txt(e.stderr) + "\nTIMEOUT", time.time() - t0


def grammar_entry(prop: str) -> str:
    from proofscope.scope_expr import Unsupported, parse
    try:
        parse(prop)
        return "parses"
    except Unsupported as e:
        return f"unsupported: {str(e)[:80]}"
    except Exception as e:  # noqa: BLE001
        return f"error: {type(e).__name__}"


def one(case, work: Path, lean: str) -> dict:
    t_start = time.time()
    left = lambda: BUDGET - (time.time() - t_start)
    row = {"case_id": case["case_id"], "stages": {}}
    work.mkdir(parents=True, exist_ok=True)
    # 1a. print
    try:
        (work / "print.lean").write_text(print_file(case))
    except ValueError as e:
        row.update(outcome="UNSUPPORTED_INPUT", reason=str(e))
        return row
    rc, out, dt = run([lean, str(work / "print.lean")], work, left())
    row["stages"]["print"] = {"rc": rc, "s": round(dt, 1)}
    if rc == -9:
        row.update(outcome="TIMEOUT", reason="adapter print")
        return row
    printed = {}
    for line in out.splitlines():
        m = re.search(r"PS_CLOSED (ref|cand) (\d) (.*)$", line)
        if m:
            printed[(m.group(1), int(m.group(2)))] = m.group(3).strip()
    if not any(s == "ref" for s, _ in printed) or not any(s == "cand" for s, _ in printed):
        errs = [l for l in out.splitlines() if "error" in l][:4]
        row.update(outcome="NON_ELABORATING", reason="declaration does not elaborate on Lean 4.34.1 / Mathlib v4.34.1",
                   side=("ref" if not any(s == "ref" for s, _ in printed) else "cand"), errors=errs)
        return row
    # 1b. round trip
    src, lines = check_file(case, printed)
    (work / "check.lean").write_text(src)
    rc, out, dt = run([lean, str(work / "check.lean")], work, left())
    row["stages"]["roundtrip"] = {"rc": rc, "s": round(dt, 1)}
    if rc == -9:
        row.update(outcome="TIMEOUT", reason="adapter round trip")
        return row
    bad = set()
    for m in re.finditer(r"check\.lean:(\d+):\d+: error", out):
        ln = int(m.group(1))
        for key, l0 in lines.items():
            if l0 == ln:
                bad.add(key)
    chosen = {}
    for side in ("ref", "cand"):
        for k in range(len(PRINT_OPTS)):
            if (side, k) in printed and (side, k) not in bad and side not in chosen:
                chosen[side] = (k, printed[(side, k)])
    row["print_setting"] = {s: v[0] for s, v in chosen.items()}
    if len(chosen) < 2:
        row.update(outcome="UNSUPPORTED_INPUT", reason="printed statement does not round-trip (adapter limitation)",
                   side=[s for s in ("ref", "cand") if s not in chosen])
        return row
    ref, cand = chosen["ref"][1], chosen["cand"][1]
    row["reference"], row["lean"] = ref, cand
    row["grammar_entry"] = {"ref": grammar_entry(ref), "cand": grammar_entry(cand)}
    # 2. frozen engines
    safe = work.name
    spec = {"id": safe, "reference": ref, "lean": cand}
    (work / f"{safe}.json").write_text(json.dumps(spec, ensure_ascii=False))
    env = dict(os.environ, PROOFSCOPE_IMPORTS="Mathlib")
    for eng, share in (("adelta12", 0.5), ("cmcd_v10", 1.0)):
        if left() <= 5:
            row["stages"][eng] = {"outcome": "TIMEOUT", "s": 0}
            continue
        limit = left() * share if share < 1 else left()
        shared = work.parent.parent / f"engine_{eng}"          # one build directory per shard
        rc, out, dt = run([sys.executable, "-m", f"proofscope.{eng}", str(work / f"{safe}.json"), "--out", str(shared),
                           "--jobs", "1"], ROOT, limit, env)
        p = shared / "rows" / f"{safe}.json"
        st = {"rc": rc, "s": round(dt, 1)}
        if p.exists():
            r = json.loads(p.read_text())
            st.update(verdict=r.get("verdict"), reason=(r.get("reason") or "")[:300],
                      certificates=sorted((r.get("certificates") or {}).keys()),
                      certify_status=r.get("certify_status"), localized_at=r.get("localized_at"),
                      symbols=r.get("symbols") or (r.get("extraction") or {}).get("symbols"),
                      detail=(r.get("detail") or "")[-400:])
        else:
            st.update(outcome="TIMEOUT" if rc == -9 else "ERROR", tail=out[-600:])
        row["stages"][eng] = st
    row["seconds"] = round(time.time() - t_start, 1)
    row["outcome"] = "ENGINES_RAN"
    return row


def main():
    cases_p, out = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
    i, n = (int(x) for x in sys.argv[sys.argv.index("--shard") + 1].split("/")) if "--shard" in sys.argv else (0, 1)
    want = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    cases = [json.loads(l) for l in cases_p.read_text().splitlines() if l.strip()]
    cases = [c for k, c in enumerate(sorted(cases, key=lambda c: c["case_id"])) if k % n == i]
    if want:
        cases = [c for c in cases if c["case_id"] in want]
    # engine freeze check
    for line in (ROOT / "experiments" / "sota18" / "ENGINE_HASHES.txt").read_text().splitlines():
        h, f = line.split("  ", 1)
        assert hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == h, f"engine file changed: {f}"
    lean = subprocess.run(["which", "lean"], capture_output=True, text=True).stdout.strip()
    (out / "rows").mkdir(parents=True, exist_ok=True)
    for c in cases:
        safe = re.sub(r"[^A-Za-z0-9_]", "_", c["case_id"])
        if (out / "rows" / f"{safe}.json").exists():
            continue
        before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        try:
            row = one(c, out / "work" / safe, lean)
        except Exception as e:  # noqa: BLE001
            row = {"case_id": c["case_id"], "outcome": "ERROR", "reason": f"runner: {type(e).__name__}: {e}"[:400]}
        row["children_maxrss_kb_so_far"] = max(before, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
        (out / "rows" / f"{safe}.json").write_text(json.dumps(row, ensure_ascii=False, indent=1))
        a = row.get("stages", {}).get("adelta12", {}).get("verdict")
        m = row.get("stages", {}).get("cmcd_v10", {}).get("verdict")
        print(c["case_id"], row["outcome"], a, m, row.get("seconds"), row.get("reason", ""), flush=True)


if __name__ == "__main__":
    main()
