"""CJCS one-process engine (SOTA-4, experimental).

Same algorithm, same obligations, same tactic portfolios, same verdict mapping and the same certificate
acceptance standard as SOTA-3 (`proofscope/experimental/cjcs.py`, imported unchanged). What changes is
where the work happens:

    SOTA-3 (per pair): extract (1 lean) -> stage-1 probe (1 lean) -> certify probe (1 lean) ->
                       certify compile (1 lean) -> leanchecker (1) -> witness readout (1 lean)
                       = 6 processes, 5 environment loads (each one imports Mathlib in Mathlib mode)

    SOTA-4 (per pair): SEARCH  one Lean REPL process (leanprover-community/repl, pinned) with ONE
                               environment load: extraction, stage-1 refutation, stage-2 search and witness
                               readout all run in it; the search command (`lean/ProofScope/CJCSSearch.lean`)
                               is elaborated in the same session after the imports. UNTRUSTED.
                       VERIFY  one clean `lean -o` compile of a certificate module that contains, for each
                               proposed obligation, exactly the one tactic alternative the search proposed,
                               then `#print axioms` and an independent `leanchecker` replay.
                       = 3 Lean processes, 1 search environment load + 2 verification loads
                       (+ the per-case extractor build that SOTA-3 also performs in the benchmark shape)

Trust boundary. The REPL process proposes; it never certifies. A declaration is a certificate only if the
clean verification module compiles (return code 0, no error), its `#print axioms` shows only propext,
Classical.choice and Quot.sound (never sorryAx), and leanchecker replays the module: the unchanged rule of
`proofscope/certify.py` (`STD_AXIOMS`). If any proposed declaration fails in verification the module does
not compile and every proposal is rejected (fail closed; status VERIFY_REJECTED). Verdicts are computed
only from the certified set, with the SOTA-3 mapping.

Witness models are read in the search process from the search declarations, whose statements and tactic
scripts are exactly those that were then certified. They are explanatory only; no verdict reads them, and a
witness is reported only for a declaration that was certified.

Removed redundancy (each counted in `stats`): repeated environment loads (5 -> 1 search), duplicate
elaboration of stage-1 obligations in stage 2 (kept in the search environment instead of re-elaborated),
the certify probe (the search already established which alternative elaborates), giant `first` blocks in
the certificate (one alternative per declaration), and the separate witness-readout process.

No result cache: per-pair CPU must stay comparable with SOTA-3 and the competitors, and a cached verdict
would not be a certificate. (`point pools` are reset per case; SOTA-3 leaked them across cases in a worker,
see docs/sota4/README.md, finding F2.)
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import select
import shutil
import signal
import subprocess
import time
from pathlib import Path

from .. import adelta12 as A
from ..certify import STD_AXIOMS, _axioms, _module
from ..toolchain import Toolchain
from . import cjcs as S3   # SOTA-3 obligations, portfolios and constants, imported unchanged

SEARCH_TIMEOUT_S = 900.0     # per REPL request; the SOTA-3 per-process timeouts were 600-900 s
VERIFY_TIMEOUT_S = 900.0
BUDGET = 200000              # S3.HEADER: maxHeartbeats 200000 per declaration


class ReplError(RuntimeError):
    pass


class Repl:
    """One leanprover-community/repl process. Started in its own session so close() can kill the whole
    group; the benchmark limiter tracks it by ancestry regardless (bench/limits.py)."""

    def __init__(self, exe: str, lean_path: str, cwd: Path):
        env = dict(os.environ)
        env["LEAN_PATH"] = lean_path
        self.p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  cwd=str(cwd), env=env, start_new_session=True)
        self.requests = 0

    def send(self, cmd: str, env: int | None, timeout: float | None = None) -> dict:
        req = {"cmd": cmd} if env is None else {"cmd": cmd, "env": env}
        self.p.stdin.write((json.dumps(req, ensure_ascii=False) + "\n\n").encode())
        self.p.stdin.flush()
        self.requests += 1
        buf, deadline = b"", time.monotonic() + (SEARCH_TIMEOUT_S if timeout is None else timeout)
        fd = self.p.stdout.fileno()
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                raise ReplError("REPL request timed out")
            r, _, _ = select.select([fd], [], [], min(left, 1.0))
            if not r:
                if self.p.poll() is not None:
                    raise ReplError(f"REPL exited with {self.p.returncode}: {self.p.stderr.read()[-2000:]!r}")
                continue
            chunk = os.read(fd, 1 << 16)
            if not chunk:
                raise ReplError(f"REPL closed its output (exit {self.p.poll()})")
            buf += chunk
            if b"\n\n" in buf:
                head = buf[:buf.rindex(b"\n\n")]
                try:
                    return json.loads(head.decode())
                except json.JSONDecodeError:
                    continue

    def close(self) -> None:
        try:
            os.killpg(self.p.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            self.p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        for s in (self.p.stdin, self.p.stdout, self.p.stderr):
            try:
                s.close()
            except Exception:
                pass


def find_repl() -> str:
    exe = os.environ.get("PROOFSCOPE_REPL") or shutil.which("repl")
    if not exe or not Path(exe).exists():
        raise FileNotFoundError("Lean REPL not found: set PROOFSCOPE_REPL (leanprover-community/repl v4.34.0, "
                                "commit 193cf4bb9a22bb3fc6d25774f0fe6a70db1fd6ee, built with Lean 4.34.1)")
    return exe


SEARCH_SRC = A.SRC / "ProofScope" / "CJCSSearch.lean"


def build(tc: Toolchain, out: Path) -> dict:
    """Exactly the SOTA-3 build: the frozen extractor as an .olean under out/. The search metaprogram is not
    compiled to a module; its source is elaborated inside the REPL session after the imports (one process
    fewer per pair; it is a few dozen lines of command elaborator)."""
    return A.build(tc, out)


def search_source() -> str:
    src = SEARCH_SRC.read_text()
    head, sep, body = src.partition("\nimport Lean\n") if not src.startswith("import Lean\n") else ("", "", src[len("import Lean\n"):])
    return body


def _infos(resp: dict, tag: str) -> list:
    out = []
    for m in sorted(resp.get("messages", []), key=lambda m: (m["pos"]["line"], m["pos"]["column"])):
        d = m.get("data", "")
        i = d.find(tag + " ")
        if m.get("severity") == "info" and i >= 0:
            out.append(json.loads(d[i + len(tag) + 1:]))
    return out


def _errors(resp: dict) -> list[str]:
    return [m.get("data", "")[:600] for m in resp.get("messages", []) if m.get("severity") == "error"]


def _lean_str(s: str) -> str:
    """A Lean string literal for `s` (JSON escapes \\" \\\\ \\n \\t \\r \\uXXXX are Lean escapes too)."""
    j = json.dumps(s, ensure_ascii=True)
    if re.search(r"\\[bf/]", j):
        raise ValueError("unsupported escape")
    return j


DEPS = {"false_R": ["link_R", "wit_R"], "false_L": ["link_L", "wit_L"], "diff_RL": ["false_R", "true_L"],
        "diff_LR": ["false_L", "true_R"], "equiv_both_false": ["false_R", "false_L"],
        "equiv_both_true": ["true_R", "true_L"]}


def search(repl: Repl, env: int, ns: str, obligations: dict) -> tuple[int, dict]:
    req = {"budget": BUDGET, "obligations": [
        {"name": k, "stmt": st, "alts": list(tacs), "deps": DEPS.get(k, [])} for k, (st, tacs) in obligations.items()]}
    cmd = f"namespace {ns}\n#cjcs_search {_lean_str(json.dumps(req, ensure_ascii=False))}\nend {ns}"
    r = repl.send(cmd, env)
    rows = _infos(r, "CJCS_SEARCH")
    if len(rows) != 1:
        raise ReplError("search returned no result: " + " | ".join(_errors(r))[:1500])
    return r["env"], {row["name"]: row for row in rows[0]}


def verify(ident: str, header: str, proposals: dict, tc: Toolchain, workdir: Path) -> dict:
    """Independent verification of the proposed declarations: a fresh `lean` compiles a clean module
    (one alternative each), `#print axioms`, then `leanchecker` replays it. Acceptance rule identical to
    proofscope/certify.py (which is frozen and not modified)."""
    root = Path(workdir).resolve()
    src_root, build_root = root / "src", root / "build"
    (src_root / "ProofScopeCert").mkdir(parents=True, exist_ok=True)
    ns = f"ProofScopeCert.{ident}"
    res = {"certificates": {}, "rejected": {}, "status": "OK", "statements": {k: v[0] for k, v in proposals.items()}}
    if not proposals:
        return res
    src, _ = _module(ns, header, proposals, set(proposals))
    f = src_root / "ProofScopeCert" / f"{ident}.lean"
    f.write_text(src)
    res["certificate_source"] = src
    cc = tc.compile(f, build_root / "ProofScopeCert" / f"{ident}.olean", src_root, timeout=VERIFY_TIMEOUT_S)
    res["certify_compile"] = cc.as_dict()
    if cc.returncode != 0 or re.search(r": error", cc.output):
        res["status"] = "VERIFY_REJECTED"
        for k in proposals:
            res["rejected"][k] = "certificate module failed to compile (a search proposal did not verify)"
        return res
    ax = _axioms(cc.output, ns)
    rp = tc.replay(f"ProofScopeCert.{ident}", build_root, timeout=VERIFY_TIMEOUT_S)
    res["replay"] = rp.as_dict()
    for k in proposals:
        a = ax.get(k)
        if a is None:
            res["rejected"][k] = "axiom report missing"
        elif "sorryAx" in a:
            res["rejected"][k] = "depends on sorryAx"
        elif not set(a) <= STD_AXIOMS:
            res["rejected"][k] = f"non-standard axioms {a}"
        elif rp.returncode != 0:
            res["rejected"][k] = "leanchecker replay failed"
        else:
            res["certificates"][k] = {"declaration": f"{ns}.{k}", "statement": proposals[k][0], "axioms": a}
    if res["rejected"] and not res["certificates"]:
        res["status"] = "VERIFY_REJECTED"
    return res


def verdict(out: dict, certs: set) -> None:
    """The SOTA-3 mapping (proofscope/experimental/cjcs.py, run_case), unchanged."""
    if "equiv_defeq" in certs and ({"diff_RL", "diff_LR"} & certs):
        out.update(verdict="INCONSISTENT", reason="definitional equality and a logical difference were both certified")
    elif "equiv_defeq" in certs:
        out.update(verdict="CERTIFIED_LOGICAL_EQUIVALENCE", direction="definitional", theorem="Iff.rfl")
    elif "diff_RL" in certs:
        out.update(verdict="CERTIFIED_LOGICAL_DIFFERENCE", direction="reference_false_formalization_true",
                   theorem="CJCS.cjcs_sound")
    elif "diff_LR" in certs:
        out.update(verdict="CERTIFIED_LOGICAL_DIFFERENCE", direction="reference_true_formalization_false",
                   theorem="CJCS.cjcs_sound")
    elif "equiv_both_false" in certs:
        out.update(verdict="CERTIFIED_LOGICAL_EQUIVALENCE", direction="both_false", theorem="CJCS.both_false_equiv")
    elif "equiv_both_true" in certs:
        out.update(verdict="CERTIFIED_LOGICAL_EQUIVALENCE", direction="both_true", theorem="CJCS.both_true_equiv")
    else:
        one = sorted(k for k in certs if k.startswith(("false_", "true_")))
        out.update(verdict="ABSTAIN", partial=one,
                   reason="no certified countermodel for one side together with a certified proof of the other")


def run_case(spec: dict, tc: Toolchain, buildp: Path, work: Path, repl_exe: str | None = None) -> dict:
    R, L = spec["reference"], spec["lean"]
    out = {"id": spec["id"], "reference": R, "lean": L, "engine": "cjcs-sota4-oneprocess"}
    stats = {"search_processes": 1, "search_env_loads": 1, "verify_processes": 0, "repl_requests": 0}
    out["stats"] = stats
    work = Path(work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    saved_pools = copy.deepcopy(A.POINT_POOLS)          # per-case point pools (SOTA-3 leaked them; F2)
    t0 = time.monotonic()
    repl = Repl(repl_exe or find_repl(), os.pathsep.join(p for p in [str(buildp), os.environ.get("LEAN_PATH", "")] if p), work)
    try:
        init = (A.import_lines() + "import ProofScope.AssumptionExtract11\nimport Lean\n"
                + search_source() + "\nset_option linter.unusedVariables false")
        r0 = repl.send(init, None)
        if "env" not in r0 or _errors(r0):
            out.update(verdict="INCONCLUSIVE", reason="search environment failed to load", detail=_errors(r0)[:3])
            out["failure_class"] = "SEARCH_ENV_LOAD"
            return out
        stats["env_load_s"] = round(time.monotonic() - t0, 2)
        env0 = r0["env"]
        rx = repl.send("".join(f"#proofscope_assumptions11 ({a}) ({b})\n" for a, b in [(R, R), (L, L), (R, L)]), env0)
        ex = _infos(rx, "PROOFSCOPE_ASSUMPTIONS11")
        if len(ex) != 3:
            out.update(verdict="INCONCLUSIVE", reason="extraction failed", detail=" | ".join(_errors(rx))[-600:])
            out["failure_class"] = "EXTRACTION"
            return out
        dR, dL, e = ex
        ident = "CJ_" + re.sub(r"[^A-Za-z0-9_]", "_", spec["id"])
        ns = f"ProofScopeCert.{ident}"
        S3.with_literal_points(R, L)
        sides = {**S3.side_obligations("R", R, dR), **S3.side_obligations("L", L, dL)}
        t1 = time.monotonic()
        env1, s1 = search(repl, env0, ns, sides)
        ok1 = {k for k, v in s1.items() if v["status"] == "proposed"}
        refuted = {t for t in ("R", "L") if {f"link_{t}", f"wit_{t}", f"false_{t}"} <= ok1}
        out["stage1_refuted"] = sorted(refuted)
        # stage 2: the SOTA-3 stage-2 obligation set minus the stage-1 obligations already in the environment
        stmts = {"R": R, "L": L}
        ob2 = {"equiv_defeq": (f"({R}) ↔ ({L})", ["exact Iff.rfl"])}
        for t in ("R", "L"):
            if t not in refuted:
                ob2[f"true_{t}"] = (stmts[t], S3.prove_tactics())
        if "R" in refuted and "L" not in refuted:
            ob2["diff_RL"] = (f"¬ (({R}) ↔ ({L}))", ["exact fun h => false_R (h.mpr true_L)"])
        if "L" in refuted and "R" not in refuted:
            ob2["diff_LR"] = (f"¬ (({R}) ↔ ({L}))", ["exact fun h => false_L (h.mp true_R)"])
        if refuted == {"R", "L"}:
            ob2["equiv_both_false"] = (f"({R}) ↔ ({L})", ["exact ⟨fun h => absurd h false_R, fun h => absurd h false_L⟩"])
        if not refuted:
            ob2["equiv_both_true"] = (f"({R}) ↔ ({L})", ["exact ⟨fun _ => true_L, fun _ => true_R⟩"])
        ob2.update(S3.region_obligations(e))
        # SOTA-3 kept false_X only for refuted sides; link/wit whenever they elaborated
        keep1 = {k: sides[k] for k in sides if k in ok1 and (not k.startswith("false_") or k[-1] in refuted)}
        env2, s2 = search(repl, env1, ns, ob2)
        stats["search_s"] = round(time.monotonic() - t1, 2)
        ok2 = {k for k, v in s2.items() if v["status"] == "proposed"}
        out["search"] = {"stage1": s1, "stage2": s2}
        proposals = {k: (st, [tacs[s1[k]["alt"]]]) for k, (st, tacs) in keep1.items()}
        proposals.update({k: (st, [tacs[s2[k]["alt"]]]) for k, (st, tacs) in ob2.items() if k in ok2})
        wit_names = [k for k in proposals if k.startswith(("wit_", "region_"))]
        witnesses = {}
        if wit_names:
            rw = repl.send("".join(f"#proofscope_witness11 {ns}.{n}\n" for n in wit_names), env2)
            got = _infos(rw, "PROOFSCOPE_WITNESS11")
            witnesses = dict(zip(wit_names, got)) if len(got) == len(wit_names) else {}
    except ReplError as err:
        out.update(verdict="INCONCLUSIVE", reason=f"search process failure: {err}"[:800])
        out["failure_class"] = "SEARCH_TIMEOUT" if "timed out" in str(err) else "SEARCH_PROCESS"
        return out
    finally:
        stats["repl_requests"] = repl.requests
        repl.close()
        A.POINT_POOLS.clear()
        A.POINT_POOLS.update(saved_pools)
    # ---- independent verification (fresh processes; the search process is gone) ----
    t2 = time.monotonic()
    v = verify(ident, A.import_lines() + S3.HEADER, proposals, tc, work / "certify")
    stats["verify_processes"] = 0 if not proposals else (1 if "replay" not in v else 2)
    stats["verify_s"] = round(time.monotonic() - t2, 2)
    certs = set(v["certificates"])
    out["certify_status"] = v["status"]
    out["certificates"] = v["certificates"]
    out["rejected"] = v["rejected"]
    out["certificate_source"] = v.get("certificate_source")
    out["proposed_not_certified"] = sorted(set(proposals) - certs)
    out["witnesses"] = {k: w for k, w in witnesses.items() if k in certs}
    out["regions"] = sorted(k for k in certs if k.startswith("region_"))
    if v["status"] == "VERIFY_REJECTED":
        out["failure_class"] = "VERIFY_REJECTED"
    verdict(out, certs)
    return out


def _one(a):
    p, buildp, out = a
    spec = json.loads(Path(p).read_text())
    row = run_case(spec, Toolchain.find(), buildp, out / "work" / Path(p).stem)
    for k in ("expected", "domain", "family", "split", "must_not_be"):
        row[k] = spec.get(k)
    (out / "rows").mkdir(parents=True, exist_ok=True)
    (out / "rows" / (Path(p).stem + ".json")).write_text(json.dumps(row, ensure_ascii=False, indent=1))
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m proofscope.experimental.cjcs4")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("specs", nargs="+")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args(argv)
    out = a.out.resolve()
    find_repl()
    b = build(Toolchain.find(), out / "build")
    if not b["ok"]:
        print(json.dumps(b, indent=2)[:3000])
        return 2
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        rows = list(ex.map(_one, [(p, out / "build", out) for p in a.specs]))
    for row in rows:
        ok = "" if not row.get("expected") else ("OK" if row["verdict"] == row["expected"] else f"MISS(expected {row['expected']})")
        print(row["id"], row["verdict"], row.get("direction"), row.get("regions"), ok, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
