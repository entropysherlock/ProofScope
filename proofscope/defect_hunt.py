"""Certified defect hunt for formal math benchmarks (SOTA-9 discovery track).

For each benchmark statement T (compiled unchanged, proof left as `sorry`), try to certify:
  FALSE    — `¬ (type_of% @T)`: the formal statement is refutable (usually by instantiating its variables
             at concrete values, including rationals like 1/2 for real variables, then `norm_num`).
  VACUOUS  — `vacuous_of% @T`: every binder kept, conclusion replaced by `False`; i.e. the hypotheses are
             contradictory (or a domain is empty), so the statement is true for a trivial reason.
A finding is reported only after a clean Lean file re-proves it from the unchanged statement, `#print axioms`
shows only {propext, Classical.choice, Quot.sound}, and leanchecker replays the module. A search that finds
nothing is not evidence that a statement is correct.

Input: JSONL rows {"id", "source", "lean_code", "informal"?}. Imports must be Mathlib/Aesop (or none in core
mode). Statements whose type mentions a `sorry` placeholder (e.g. an unfilled answer) are skipped.

    python -m proofscope.defect_hunt --data problems.jsonl --out DIR --minutes 3.5 [--workers 2] [--core]

Prior art: Ammanmanchi & Bhat, "Faults in Our Formal Benchmarking" (ICML 2026) certified counterexamples by
`decide` over small finite/integer domains and vacuity by omega/grind on miniF2F, ProofNet, FormalMath,
CombiBench, ProverBench. Each finding here records how it was found so overlap can be judged.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import threading
import time
from pathlib import Path

from .experimental import cjcs4 as E
from .toolchain import Toolchain

STD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}

HELPER = r'''open Lean Elab Term Meta in
elab "vacuous_of% " e:term : term => do
  let e ← elabTerm e none
  let ty ← instantiateMVars (← inferType e)
  forallTelescope ty fun xs _ => mkForallFVars xs (mkConst ``False)
'''

PROBE = r'''open Lean Meta in
#eval show MetaM Unit from do
  let ci ← getConstInfo `{name}
  let mut sorryDeps : Array String := #[]
  for c in ci.type.getUsedConstants do
    if (← collectAxioms c).contains ``sorryAx then sorryDeps := sorryDeps.push c.toString
  let info ← forallTelescope ci.type fun xs body => do
    let mut arr : Array Json := #[]
    for x in xs do
      let d ← x.fvarId!.getDecl
      let ty ← instantiateMVars d.type
      let isP ← isProp ty
      let kind := if ty.isConstOf `Nat then "nat" else if ty.isConstOf `Int then "int"
        else if ty.isConstOf `Real then "real" else if ty.isConstOf `Rat then "rat" else "other"
      let bi := if d.binderInfo.isInstImplicit then "inst" else if d.binderInfo.isExplicit then "explicit" else "implicit"
      arr := arr.push (Json.mkObj [("isProp", toJson isP), ("kind", toJson kind), ("bi", toJson bi),
                                   ("type", toJson (toString (← ppExpr ty)))])
    return Json.mkObj [("binders", Json.arr arr), ("bodyFalse", toJson (body.isConstOf ``False)),
                       ("goal", toJson (toString (← ppExpr body)))]
  IO.println ("PSPROBE " ++ (Json.mkObj [("levelParams", toJson (ci.levelParams.map toString)),
    ("sorryDeps", toJson sorryDeps.toList), ("info", info)]).compress)
'''

VALUES = {"nat": ["0", "1", "2", "3", "4", "5", "10"],
          "int": ["0", "1", "-1", "2", "-2", "3", "-3", "10"],
          "real": ["0", "1", "-1", "2", "-2", "1/2", "-1/2", "3", "1/3", "10"],
          "rat": ["0", "1", "-1", "2", "-2", "1/2", "-1/2", "3", "1/3", "10"]}
LEAN_TYPE = {"nat": "Nat", "int": "Int", "real": "Real", "rat": "Rat"}


class Tactics:
    """Alternatives never contain `by` blocks nested inside terms: Lean logs (rather than throws) errors there, so a
    failed side condition would not make the enclosing `first` alternative fail."""
    def __init__(self, mathlib: bool):
        self.mathlib = mathlib
        if mathlib:
            self.close = ("first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) "
                          "| (norm_num at *; done) | (simp at *; done)")
            self.direct = ["(intro h; norm_num at h; done)", "(intro h; simp at h; done)", "(norm_num; done)", "decide"]
            self.vacuous = ["(intros; omega)", "(intros; linarith)", "(intros; nlinarith)", "(intros; norm_num at *; done)",
                            "(intros; simp_all; done)", "(intros; contradiction)"]
        else:
            self.close = "first | decide | omega | (simp; done) | (simp at *; done)"
            self.direct = ["(intro h; simp at h; done)", "decide", "(intro h; omega)"]
            self.vacuous = ["(intros; omega)", "(intros; simp_all; done)", "(intros; contradiction)"]


def grid_alts(binders: list[dict], tac: Tactics, cap: int = 40) -> list[str]:
    """`absurd (@h v₁ … ?_ …) ?_`: instantiate every numeric variable (smallest values first), then each
    hypothesis instance and the negated conclusion instance must close; only when every data binder is numeric."""
    num = [i for i, b in enumerate(binders) if not b["isProp"] and b["bi"] != "inst"]
    if not num or any(binders[i]["kind"] == "other" for i in num):
        return []
    pools = [VALUES[binders[i]["kind"]] for i in num]
    combos = sorted(itertools.product(*[range(len(p)) for p in pools]), key=lambda c: (sum(c), c))[:cap]
    alts = []
    for c in combos:
        val = dict(zip(num, (f"(({pools[k][j]}) : {LEAN_TYPE[binders[num[k]]['kind']]})" for k, j in enumerate(c))))
        args = [val[i] if i in val else ("_" if b["bi"] == "inst" else "?_") for i, b in enumerate(binders)]
        alts.append(f"(intro h; refine absurd (@h {' '.join(args)}) ?_ <;> {tac.close})")
    return alts


def block(alts: list[str]) -> str:
    return "by\n  first\n" + "".join(f"    | {a}\n" for a in alts)


def split_code(code: str, mathlib: bool) -> tuple[list[str], str] | None:
    imports = [l.split()[1] for l in code.splitlines() if l.startswith("import ")]
    ok = all(m == "Mathlib" or m.startswith("Mathlib.") or m == "Aesop" for m in imports) if mathlib else not imports
    if not ok:
        return None
    return imports, "\n".join(l for l in code.splitlines() if not l.startswith("import "))


def theorem_name(body: str) -> str | None:
    names = re.findall(r"^\s*(?:@\[[^\]]*\]\s*)?(?:theorem|lemma)\s+([^\s(:{\[]+)", body, re.M)
    return names[-1] if names else None


def _infos(resp: dict, tag: str) -> list[str]:
    return [l[len(tag) + 1:] for m in resp.get("messages", []) for l in m.get("data", "").splitlines() if l.startswith(tag + " ")]


class Worker:
    def __init__(self, tc: Toolchain, work: Path, mathlib: bool, hb: int):
        self.work, self.mathlib, self.hb = work, mathlib, hb
        self.tac = Tactics(mathlib)
        self.repl = None
        self.env0 = None

    def start(self):
        self.work.mkdir(parents=True, exist_ok=True)
        self.repl = E.Repl(E.find_repl(), os.environ.get("LEAN_PATH", ""), self.work)
        r = self.repl.send(("import Mathlib\n" if self.mathlib else "") + "import Lean\n" + HELPER, None, timeout=600)
        if "env" not in r or E._errors(r):
            raise RuntimeError(f"helper environment failed: {E._errors(r)[:3]}")
        self.env0 = r["env"]

    def restart(self):
        if self.repl:
            self.repl.close()
        self.start()

    def try_(self, stmt: str, alts: list[str], env: int) -> str | None:
        if not alts:
            return None
        cmd = f"set_option maxHeartbeats {self.hb} in\nexample : {stmt} := {block(alts)}"
        try:
            r = self.repl.send(cmd, env, timeout=60)
        except E.ReplError:
            self.restart()
            return None
        return None if E._errors(r) or "env" not in r else block(alts)

    def check(self, row: dict) -> dict:
        out = {"id": row["id"], "source": row.get("source")}
        sp = split_code(row["lean_code"], self.mathlib)
        if sp is None:
            return {**out, "status": "SKIP_IMPORTS"}
        _, body = sp
        name = theorem_name(body)
        if not name:
            return {**out, "status": "SKIP_NO_THEOREM"}
        out["theorem"] = name
        try:
            r1 = self.repl.send(body, self.env0, timeout=120)
        except E.ReplError as e:
            self.restart()
            return {**out, "status": "COMPILE_TIMEOUT", "detail": str(e)[:200]}
        if "env" not in r1 or E._errors(r1):
            return {**out, "status": "COMPILE_FAIL", "detail": (E._errors(r1) or ["no env"])[0][:300]}
        try:
            r_ai = self.repl.send("set_option autoImplicit false\n" + body, self.env0, timeout=120)
            ai_err = E._errors(r_ai)
        except E.ReplError:
            ai_err = []
        if ai_err:      # compiles only because an unknown identifier was silently bound as a variable
            out["autobound"] = ai_err[0][:300]
        env1 = r1["env"]
        out["_env"] = env1
        try:
            rp = self.repl.send(PROBE.replace("{name}", name), env1, timeout=60)
            probe = json.loads(_infos(rp, "PSPROBE")[0])
        except (E.ReplError, IndexError, json.JSONDecodeError) as e:
            return {**out, "status": "PROBE_FAIL", "detail": str(e)[:200]}
        out["probe"] = probe
        if probe["sorryDeps"]:
            return {**out, "status": "SKIP_PLACEHOLDER", "detail": probe["sorryDeps"]}
        if probe["levelParams"]:
            return {**out, "status": "SKIP_UNIVERSE_POLY"}
        info = probe["info"]
        cands = []
        if not info["bodyFalse"]:
            b = self.try_(f"vacuous_of% @{name}", self.tac.vacuous, env1)
            if b:
                cands.append({"kind": "VACUOUS", "stmt": f"vacuous_of% @{name}", "proof": b})
        grid = grid_alts(info["binders"], self.tac)
        b = self.try_(f"¬ (type_of% @{name})", self.tac.direct + grid, env1)
        if b:
            cands.append({"kind": "FALSE", "stmt": f"¬ (type_of% @{name})", "proof": b})
        out["status"] = "CANDIDATE" if cands else "NO_DEFECT_FOUND"
        out["candidates"] = cands
        out["body"] = body
        return out


def winning_alt(src: str, proof: str, stmt: str, worker: Worker, env: int) -> str:
    """Shrink a successful `first` block to the single alternative that works (shorter certificate, witness shown)."""
    alts = [l.strip()[2:] for l in proof.splitlines() if l.strip().startswith("| ")]
    for a in alts:
        if worker.try_(stmt, [a], env):
            return a
    return proof


def verify(tc: Toolchain, cands: list[dict], work: Path, mathlib: bool, hb: int) -> list[dict]:
    """Clean certificate module: unchanged statements (proof `sorry`), certificates, axioms, leanchecker replay."""
    if not cands:
        return []
    root = work / "verify"
    root.mkdir(parents=True, exist_ok=True)
    for attempt in range(2):
        mod = f"PSHuntCert{int(time.time())}"
        parts = [("import Mathlib\n" if mathlib else "") + "import Lean\n" + HELPER]
        ranges = []
        for k, c in enumerate(cands):
            ns = f"PSH{k}"
            start = sum(p.count("\n") + 1 for p in parts) + 1
            parts.append(f"namespace {ns}\n{c['body']}\nset_option maxHeartbeats {hb} in\n"
                         f"theorem ps_cert : {c['stmt']} := by\n  first\n    | {c['alt']}\nend {ns}\n")
            ranges.append((start, sum(p.count("\n") + 1 for p in parts)))
        parts += [f"#print axioms PSH{k}.ps_cert\n" for k in range(len(cands))]
        f = root / f"{mod}.lean"
        f.write_text("\n".join(parts))
        cc = tc.compile(f, root / "build" / f"{mod}.olean", root, timeout=1200)
        ax = {}
        for m in re.finditer(r"'PSH(\d+)\.ps_cert' (?:depends on axioms: \[([^\]]*)\]|does not depend on any axioms)", cc.output):
            ax[int(m.group(1))] = [a.strip() for a in (m.group(2) or "").split(",") if a.strip()]
        errs = [l for l in cc.output.splitlines() if ": error" in l]
        err_lines = [int(m.group(1)) for l in errs for m in [re.search(r":(\d+):\d+: error", l)] if m]
        bad_ns = {k for k, (a, b) in enumerate(ranges) for L in err_lines if a - 2 <= L <= b + 2}
        if errs and attempt == 0:
            keep = [c for k, c in enumerate(cands) if k in ax and k not in bad_ns and set(ax[k]) <= STD_AXIOMS]
            if not keep:
                return []
            cands = keep
            continue
        if errs:
            return []
        rp = tc.replay(mod, root / "build", timeout=1200)
        out = []
        for k, c in enumerate(cands):
            a = ax.get(k)
            if a is not None and set(a) <= STD_AXIOMS and rp.returncode == 0:
                out.append({**c, "axioms": a, "certificate_module": f.name, "replay": "leanchecker OK"})
        (root / "certificate_source.lean").write_text(f.read_text())
        return out
    return []


def novelty(c: dict, row: dict) -> str:
    alt = c.get("alt", "")
    kinds = {b["kind"] for b in row["probe"]["info"]["binders"] if not b["isProp"] and b["bi"] != "inst"}
    if c["kind"] == "FALSE":
        if kinds & {"real", "rat"} or "/" in alt:
            return "real/rational witness — outside the prior audit's decide-over-integers counterexample search"
        return "integer/natural witness — may overlap the prior audit's small-domain search"
    if any(t in alt for t in ("nlinarith", "linarith", "norm_num", "positivity")):
        return f"contradiction found by `{alt}` — prior audit used omega/grind"
    return "contradiction found by omega/simp — may overlap the prior audit"


def run(rows: list[dict], out: Path, minutes: float, workers: int, mathlib: bool, hb: int = 200000) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    tc = Toolchain.find()
    done_f, res_f = out / "done_ids.txt", out / "results.jsonl"
    done = set(done_f.read_text().split("\n")) if done_f.exists() else set()
    todo = [r for r in rows if r["id"] not in done]
    t_end = time.monotonic() + minutes * 60 - (75 if mathlib else 15)
    lock, results, ws = threading.Lock(), [], []
    it = iter(todo)

    def loop(w: Worker):
        w.start()
        while time.monotonic() < t_end:
            with lock:
                row = next(it, None)
            if row is None:
                return
            res = w.check(row)
            if res["status"] == "CANDIDATE":
                for c in res["candidates"]:
                    c["alt"] = winning_alt("", c["proof"], c["stmt"], w, res["_env"])
            with lock:
                results.append((row, res))
                with res_f.open("a") as fh:
                    fh.write(json.dumps({k: v for k, v in res.items() if k not in ("body", "_env")}, ensure_ascii=False) + "\n")
                with done_f.open("a") as fh:
                    fh.write(row["id"] + "\n")

    for i in range(workers):
        w = Worker(tc, out / f"w{i}", mathlib, hb)
        ws.append(w)
    threads = [threading.Thread(target=loop, args=(w,), daemon=True) for w in ws]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for w in ws:
        if w.repl:
            w.repl.close()
    cands = [{**c, "id": row["id"], "theorem": res["theorem"], "body": res["body"], "row": row, "res": res}
             for row, res in results if res["status"] == "CANDIDATE" for c in res["candidates"]]
    verified = verify(tc, [{k: v for k, v in c.items()} for c in cands], out, mathlib, hb)
    findings = []
    for v in verified:
        f = {"id": v["id"], "source": v["row"].get("source"), "theorem": v["theorem"], "kind": v["kind"],
             "certificate_statement": v["stmt"], "proof": v["alt"], "axioms": v["axioms"], "replay": v["replay"],
             "formal_goal": v["res"]["probe"]["info"]["goal"],
             "hypotheses": [b["type"] for b in v["res"]["probe"]["info"]["binders"] if b["isProp"]],
             "informal": (v["row"].get("informal") or "")[:1500], "novelty": novelty(v, v["res"]),
             "autobound": v["res"].get("autobound")}
        findings.append(f)
    with (out / "findings.jsonl").open("a") as fh:
        for f in findings:
            fh.write(json.dumps(f, ensure_ascii=False) + "\n")
    counts = {}
    for _, res in results:
        counts[res["status"]] = counts.get(res["status"], 0) + 1
    return {"scanned_this_run": len(results), "remaining": len(todo) - len(results), "status_counts": counts,
            "candidates": len(cands), "verified_findings": findings}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m proofscope.defect_hunt")
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("proofscope_hunt"))
    ap.add_argument("--minutes", type=float, default=3.5)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--core", action="store_true", help="core Lean only (no Mathlib)")
    a = ap.parse_args(argv)
    rows = [json.loads(l) for l in a.data.read_text().splitlines() if l.strip()]
    s = run(rows, a.out, a.minutes, a.workers, not a.core)
    (a.out / "last_run_summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1, default=str))
    print(json.dumps({k: v for k, v in s.items() if k != "verified_findings"}, indent=1))
    for f in s["verified_findings"]:
        print(f"FINDING {f['kind']} {f['id']}: {f['proof']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
