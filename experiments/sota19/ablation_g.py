"""SOTA-19 pilot A0 (ABLATION_PROTOCOL.md): apply-the-other-statement + ProofScope's portfolio, no extraction.

    LEAN_PATH=<mathlib> python experiments/sota19/ablation_g.py SOTA18_RUN_DIR OUT --shard i/n
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OK_AX = {"propext", "Classical.choice", "Quot.sound"}


def closers():
    import os
    os.environ["PROOFSCOPE_IMPORTS"] = "Mathlib"
    import importlib
    a = importlib.import_module("proofscope.adelta12")
    out = ["assumption"]
    for t in a.REDUNDANT:
        if t not in out:
            out.append(t)
    return out


def lean_file(row, cl):
    lv = sorted({x for v in (row.get("levels") or {}).values() for x in v} | {f"u_{k}" for k in range(1, 10)})
    src = "import Mathlib\n\nuniverse " + " ".join(lv) + "\n\n"
    R, L = row["reference"], row["lean"]
    names = []
    for d, (a, b) in (("fwd", (R, L)), ("bwd", (L, R))):
        for k, t in enumerate(cl):
            n = f"g_{d}_{k}"
            names.append(n)
            body = "assumption" if t == "assumption" else f"first | assumption | {t}"
            src += (f"set_option maxHeartbeats 100000 in\ntheorem {n} : ({a}) → ({b}) := by\n"
                    f"  intro hR; intros; apply hR <;> {body}\n\n")
    src += "".join(f"#print axioms {n}\n" for n in names)
    return src, names


def main():
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    i, n = (int(x) for x in sys.argv[sys.argv.index("--shard") + 1].split("/"))
    rows = [json.loads(p.read_text()) for p in sorted((run / "proofscope").glob("*.json"))]
    rows = [r for r in rows if r.get("outcome") == "ENGINES_RAN"]
    rows = [r for k, r in enumerate(rows) if k % n == i]
    cl = closers()
    out.mkdir(parents=True, exist_ok=True)
    (out / "closers.json").write_text(json.dumps(cl, ensure_ascii=False, indent=0))
    lean = subprocess.run(["which", "lean"], capture_output=True, text=True).stdout.strip()
    for r in rows:
        safe = re.sub(r"[^A-Za-z0-9_]", "_", r["case_id"])
        src, names = lean_file(r, cl)
        f = out / f"{safe}.lean"
        f.write_text(src)
        t0 = time.time()
        try:
            p = subprocess.run([lean, str(f)], capture_output=True, text=True, timeout=600)
            txt, to = p.stdout + p.stderr, False
        except subprocess.TimeoutExpired as e:
            txt, to = (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or ""), True
        proved = {}
        for m in re.finditer(r"'(g_(fwd|bwd)_(\d+))' (depends on axioms: \[([^\]]*)\]|does not depend on any axioms)", txt):
            ax = set(a.strip() for a in (m.group(5) or "").split(",") if a.strip())
            if ax <= OK_AX:
                proved.setdefault(m.group(2), []).append(cl[int(m.group(3))])
        row = {"case_id": r["case_id"], "fwd": proved.get("fwd", []), "bwd": proved.get("bwd", []),
               "equiv": bool(proved.get("fwd")) and bool(proved.get("bwd")), "timeout": to,
               "seconds": round(time.time() - t0, 1)}
        (out / f"{safe}.json").write_text(json.dumps(row, ensure_ascii=False))
        f.unlink()
        print(r["case_id"], row["equiv"], len(row["fwd"]), len(row["bwd"]), row["seconds"], "TIMEOUT" if to else "", flush=True)


if __name__ == "__main__":
    main()
