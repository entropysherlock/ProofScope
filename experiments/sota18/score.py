"""SOTA-18 scoring, exactly as pre-registered in PROTOCOL.md sections 4, 6 and 7.

    python experiments/sota18/score.py RESULTS_DIR [--cases CASES.jsonl] [--out summary.json]

RESULTS_DIR holds proofscope/, semanteq/, beqplus/ per-pair records (as committed by the collect job).
"""
from __future__ import annotations

import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
EQ_K = {"ASSUMPTION_EQUIVALENT", "IDENTICAL", "SCHEMA_EQUIVALENT", "EQUIVALENT_BY_LAWS"}
EQ_S = {"NO_ASSUMPTION_DELTA"}
NE = {"LEAN_WEAKER_BY_ASSUMPTION", "LEAN_STRONGER_BY_ASSUMPTION", "ASSUMPTION_INCOMPARABLE", "REFERENCE_NEEDS_ASSUMPTION",
      "LEAN_CLAIM_FALSE", "CLAIM_LEAN_WEAKER", "CLAIM_LEAN_STRONGER", "CLAIM_INCOMPARABLE"}
SE_EQ = {"ExactMatch", "DefEq", "EquivalentRestricted"}
INFRA = {"NON_ELABORATING", "UNSUPPORTED_INPUT", "TIMEOUT", "ERROR", "MISSING"}


def safe(cid):
    return re.sub(r"[^A-Za-z0-9_]", "_", cid)


def load(d: Path):
    return {p.stem: json.loads(p.read_text()) for p in d.glob("*.json")} if d.exists() else {}


# ------------------------------------------------------------------ per-tool classification
def ps_engine_class(v):
    if v in EQ_K:
        return "EQUIV", "kernel"
    if v in EQ_S:
        return "EQUIV", "structural"
    if v in NE:
        return "NONEQUIV", "kernel"
    if v == "INCONSISTENT":
        return "INCONSISTENT", None
    return None, None


def sorry_extraction(erow):
    return bool(erow) and "sorry" in json.dumps(erow.get("extraction") or {}, ensure_ascii=False)


def proofscope(row, erow=None, mode="H0"):
    if row is None:
        return {"cls": "MISSING", "why": "no record"}
    if row.get("outcome") != "ENGINES_RAN":
        return {"cls": row.get("outcome", "ERROR"), "why": row.get("reason")}
    st = row["stages"]
    v = {e: st.get(e, {}).get("verdict") for e in ("adelta12", "cmcd_v10")}
    cl = {e: ps_engine_class(v[e]) for e in v}
    f1 = sorry_extraction(erow)
    if mode == "H1" and f1:
        cl["adelta12"] = (None, None)
    dec = {e: c for e, c in cl.items() if c[0]}
    out = {"verdicts": v, "seconds": row.get("seconds"), "F1_sorry_extraction": f1}
    if any(c[0] == "INCONSISTENT" for c in dec.values()):
        out.update(cls="INCONSISTENT", kind=None)
    elif not dec:
        both_failed = all(st.get(e, {}).get("reason") == "extraction failed" for e in v) or (mode == "H1" and f1)
        timed = [e for e in v if st.get(e, {}).get("outcome") == "TIMEOUT"]
        out.update(cls="TIMEOUT" if timed and len(timed) == 2 else "ABSTAIN",
                   why="ENGINE_EXTRACTION_FAILED" if both_failed else ",".join(f"{e}={v[e]}" for e in v))
    else:
        classes = {c[0] for c in dec.values()}
        if len(classes) > 1:
            out.update(cls="INCONSISTENT", kind=None, why="engines disagree")
        else:
            c = classes.pop()
            kinds = {k for _, k in dec.values()}
            out.update(cls=c, kind="kernel" if "kernel" in kinds else "structural", engines=sorted(dec))
    return out


def semanteq(row):
    if row is None:
        return {"cls": "MISSING"}
    rec = row.get("record")
    if not rec:
        return {"cls": "ERROR", "why": row.get("error")}
    v = rec.get("verdict", "")
    o = {"verdict": v, "seconds": (rec.get("elapsedMs") or 0) / 1000}
    if row.get("over_cap") or v == "Timeout":
        o["cls"] = "TIMEOUT"
    elif v.endswith("CompileError") or v.endswith("NoStatement") or v == "NotAProposition":
        o["cls"] = "NON_ELABORATING"
    elif v in ("MalformedInput", "ContextMergeError"):
        o["cls"] = "UNSUPPORTED_INPUT"
    elif v == "InternalError":
        o["cls"] = "ERROR"
    elif v in SE_EQ:
        o["cls"] = "EQUIV"
    else:
        o["cls"] = "ABSTAIN"
    return o


def beqplus(row):
    if row is None:
        return {"cls": "MISSING"}
    if "error" in row:
        return {"cls": "ERROR", "why": row["error"], "seconds": row.get("seconds")}
    o = {"verdict": row.get("beq_plus"), "seconds": row.get("seconds")}
    tc = row.get("typechecks") or {}
    if row.get("over_cap"):
        o["cls"] = "TIMEOUT"
    elif tc and not all(tc.values()):
        o["cls"] = "NON_ELABORATING"
    else:
        o["cls"] = "EQUIV" if row.get("beq_plus") else "ABSTAIN"
    return o


def native(tool, c):
    """Native reading: the tool's own accept/reject. Infrastructure outcomes stay as they are."""
    if c in INFRA or c == "INCONSISTENT":
        return c
    if tool in ("semanteq", "beqplus"):
        return "EQUIV" if c == "EQUIV" else "NONEQUIV"
    return c


# ------------------------------------------------------------------ statistics
def cp(k, n, a=0.05):
    """Exact Clopper-Pearson interval by bisection on the binomial tail (no scipy needed)."""
    if n == 0:
        return None
    def tail_ge(p):  # P[X >= k]
        return sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k, n + 1))
    def tail_le(p):  # P[X <= k]
        return sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(0, k + 1))
    def solve(f, target, increasing):
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if (f(mid) < target) == increasing:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(tail_ge, a / 2, True)
    upper = 1.0 if k == n else solve(tail_le, a / 2, False)
    return [round(lower, 4), round(upper, 4)]


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return round(min(1.0, 2 * sum(math.comb(n, j) for j in range(0, k + 1)) / 2 ** n), 6)


def pct(xs, q):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    return round(xs[min(len(xs) - 1, int(math.ceil(q * len(xs))) - 1)], 1)


# ------------------------------------------------------------------ main
def gold_of(case, which):
    g = case["gold"]
    if case["source"] == "EPLA":
        return g.get("G3")
    return g.get(which)


def metrics(rows, tool, reading, which):
    s = Counter()
    secs = []
    for case, res in rows:
        c = res[tool]["cls"]
        if reading == "native":
            c = native(tool, c)
        g = gold_of(case, which)
        s["total"] += 1
        secs.append(res[tool].get("seconds"))
        if c in INFRA:
            s[c] += 1
            if c != "TIMEOUT":
                s["ineligible_or_failed"] += 1
            continue
        s["processed"] += 1
        if c in ("EQUIV", "NONEQUIV", "INCONSISTENT"):
            if g is None:
                s["decisive_no_gold"] += 1
                continue
            s["decisive"] += 1
            ok = (c == "EQUIV" and g) or (c == "NONEQUIV" and not g)
            s["correct" if ok else "incorrect"] += 1
            s[f"{c}_{'ok' if ok else 'wrong'}"] += 1
        else:
            s["abstain"] += 1
        if g is not None:
            s["gold_true" if g else "gold_false"] += 1
    t = s["total"]
    out = dict(s)
    out["coverage"] = round(s["decisive"] / t, 4) if t else None
    out["correct_decisive_rate"] = round(s["correct"] / t, 4) if t else None
    out["correct_decisive_ci"] = cp(s["correct"], t)
    for c in ("EQUIV", "NONEQUIV"):
        k, n = s[f"{c}_ok"], s[f"{c}_ok"] + s[f"{c}_wrong"]
        out[f"precision_{c}"] = round(k / n, 4) if n else None
        out[f"precision_{c}_ci"] = cp(k, n)
    out["recall_EQUIV"] = round(s["EQUIV_ok"] / s["gold_true"], 4) if s["gold_true"] else None
    out["recall_NONEQUIV"] = round(s["NONEQUIV_ok"] / s["gold_false"], 4) if s["gold_false"] else None
    out["seconds_median"] = round(statistics.median([x for x in secs if x is not None]), 1) if any(x is not None for x in secs) else None
    out["seconds_p90"] = pct(secs, 0.9)
    return out


def correct_decisive(case, res, tool, reading, which):
    c = res[tool]["cls"]
    if reading == "native":
        c = native(tool, c)
    g = gold_of(case, which)
    return g is not None and ((c == "EQUIV" and g) or (c == "NONEQUIV" and not g))


def main():
    rd = Path(sys.argv[1])
    cases_p = Path(sys.argv[sys.argv.index("--cases") + 1]) if "--cases" in sys.argv else HERE / "frozen" / "cases.jsonl"
    cases = {c["case_id"]: c for c in (json.loads(l) for l in cases_p.read_text().splitlines() if l.strip())}
    ps, se, bq = load(rd / "proofscope"), load(rd / "semanteq"), load(rd / "beqplus")
    ea = load(rd / "engine_adelta12")
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "H0"
    res = {}
    for cid in cases:
        k = safe(cid)
        res[cid] = {"proofscope": proofscope(ps.get(k), ea.get(k), mode), "semanteq": semanteq(se.get(k)), "beqplus": beqplus(bq.get(k))}
    tracks = {"A": [c for c in cases.values() if "A" in c.get("tracks", [])],
              "B": [c for c in cases.values() if "B" in c.get("tracks", [])],
              "C": [c for c in cases.values() if "C" in c.get("tracks", [])]}
    out = {"mode": mode, "tables": {}, "proofscope": {}, "gate": {}}
    for tr, cs in tracks.items():
        if not cs:
            continue
        for src in ("PNV", "EPLA", "SYNTHETIC", "ALL"):
            sub = [c for c in cs if src == "ALL" or c["source"] == src]
            if not sub:
                continue
            golds = ["G1", "G2"] if src == "PNV" else ["G1"]
            for which in golds:
                for tool in ("proofscope", "semanteq", "beqplus"):
                    for reading in ("certified", "native"):
                        key = f"{tr}|{src}|{which if src != 'EPLA' else 'G3'}|{tool}|{reading}"
                        if src == "ALL" and which != "G1":
                            continue
                        out["tables"][key] = metrics([(c, res[c["case_id"]]) for c in sub], tool, reading, which)
    # ProofScope detail
    allc = list(cases.values())
    d = out["proofscope"]
    d["outcome_counts"] = dict(Counter(res[c["case_id"]]["proofscope"]["cls"] for c in allc))
    d["abstain_reasons"] = dict(Counter(res[c["case_id"]]["proofscope"].get("why") for c in allc
                                        if res[c["case_id"]]["proofscope"]["cls"] == "ABSTAIN").most_common(30))
    d["engine_verdicts"] = {e: dict(Counter((ps.get(safe(c["case_id"])) or {}).get("stages", {}).get(e, {}).get("verdict")
                                            for c in allc)) for e in ("adelta12", "cmcd_v10")}
    d["failure_reasons"] = dict(Counter(f"{res[c['case_id']]['proofscope']['cls']}: {res[c['case_id']]['proofscope'].get('why')}"
                                        for c in allc if res[c["case_id"]]["proofscope"]["cls"] in INFRA).most_common(30))
    d["kind"] = dict(Counter(res[c["case_id"]]["proofscope"].get("kind") for c in allc
                             if res[c["case_id"]]["proofscope"]["cls"] in ("EQUIV", "NONEQUIV")))
    d["grammar_entry"] = dict(Counter(
        "both parse" if all(v == "parses" for v in ((ps.get(safe(c["case_id"])) or {}).get("grammar_entry") or {"x": "-"}).values())
        else ("not reached" if not (ps.get(safe(c["case_id"])) or {}).get("grammar_entry") else "outside grammar")
        for c in allc))
    d["decisive_pairs"] = {c["case_id"]: {**res[c["case_id"]]["proofscope"], "gold": c["gold"], "tracks": c.get("tracks"),
                                          "semanteq": res[c["case_id"]]["semanteq"].get("verdict"),
                                          "beqplus": res[c["case_id"]]["beqplus"].get("verdict")}
                           for c in allc if res[c["case_id"]]["proofscope"]["cls"] in ("EQUIV", "NONEQUIV", "INCONSISTENT")}
    # T2: pairs with at least one machine-checked one-way implication between R and L
    eng = {e: load(rd / f"engine_{e}") for e in ("adelta12", "cmcd_v10")}
    def ps_one_way(cid):
        r = eng["cmcd_v10"].get(safe(cid)) or {}
        g = set((r.get("global_certificates") or {}).keys())
        dirs = {"R=>L" for k in g if k.startswith("fwd")} | {"L=>R" for k in g if k.startswith("bwd")}
        v = (eng["adelta12"].get(safe(cid)) or {}).get("verdict")
        if v in ("LEAN_WEAKER_BY_ASSUMPTION", "ASSUMPTION_EQUIVALENT"):
            dirs.add("R=>L")
        if v in ("LEAN_STRONGER_BY_ASSUMPTION", "ASSUMPTION_EQUIVALENT"):
            dirs.add("L=>R")
        return dirs
    t2 = {c["case_id"]: ps_one_way(c["case_id"]) for c in allc}
    d["T2_pairs_with_certified_one_way_implication"] = sum(1 for v in t2.values() if v)
    d["T2_pairs_with_both_directions"] = sum(1 for v in t2.values() if len(v) == 2)
    d["T2_one_way_only_and_gold_unfaithful"] = sum(1 for c in allc if len(t2[c["case_id"]]) == 1 and gold_of(c, "G1") is False)
    # T2 / T3 counts
    d["T3_concrete_or_conditional_inequivalence"] = sum(1 for c in allc if "LEAN_CLAIM_FALSE" in (res[c["case_id"]]["proofscope"].get("verdicts") or {}).values()
                                                        or "BOTH_CLAIMS_FALSE" in (res[c["case_id"]]["proofscope"].get("verdicts") or {}).values())
    out["semanteq_one_direction"] = sum(1 for c in allc if res[c["case_id"]]["semanteq"].get("verdict") in ("LikelyTooStrong", "LikelyTooWeak"))
    out["semanteq_verdicts"] = dict(Counter(res[c["case_id"]]["semanteq"].get("verdict") for c in allc))
    out["beqplus_outcomes"] = dict(Counter(res[c["case_id"]]["beqplus"]["cls"] for c in allc))
    # head to head (certified reading for ProofScope, native for competitors as pre-registered for X)
    for tr in ("A", "B"):
        cs = tracks[tr]
        if not cs:
            continue
        h = {}
        for comp in ("semanteq", "beqplus"):
            b = sum(1 for c in cs if correct_decisive(c, res[c["case_id"]], "proofscope", "certified", "G1")
                    and not correct_decisive(c, res[c["case_id"]], comp, "certified", "G1"))
            cc = sum(1 for c in cs if not correct_decisive(c, res[c["case_id"]], "proofscope", "certified", "G1")
                     and correct_decisive(c, res[c["case_id"]], comp, "certified", "G1"))
            h[comp] = {"proofscope_only": b, f"{comp}_only": cc, "mcnemar_p": mcnemar(b, cc)}
        out.setdefault("head_to_head_certified_G1", {})[tr] = h
    # gate
    A, B = tracks["A"], tracks["B"]
    if A:
        UA = sum(correct_decisive(c, res[c["case_id"]], "proofscope", "certified", "G1") for c in A) / len(A)
        UB = sum(correct_decisive(c, res[c["case_id"]], "proofscope", "certified", "G1") for c in B) / len(B) if B else 0
        AB = {c["case_id"]: c for c in A + B}.values()
        ne = [c for c in AB if res[c["case_id"]]["proofscope"]["cls"] == "NONEQUIV" and gold_of(c, "G1") is not None]
        PN = sum(1 for c in ne if not gold_of(c, "G1")) / len(ne) if ne else None
        X = [c["case_id"] for c in AB if correct_decisive(c, res[c["case_id"]], "proofscope", "certified", "G1")
             and not correct_decisive(c, res[c["case_id"]], "semanteq", "native", "G1")
             and not correct_decisive(c, res[c["case_id"]], "beqplus", "native", "G1")]
        Xr = [c["case_id"] for c in AB if not correct_decisive(c, res[c["case_id"]], "proofscope", "certified", "G1")
              and (correct_decisive(c, res[c["case_id"]], "semanteq", "native", "G1")
                   or correct_decisive(c, res[c["case_id"]], "beqplus", "native", "G1"))]
        S_F1 = [c["case_id"] for c in allc if res[c["case_id"]]["proofscope"].get("F1_sorry_extraction")
                and (res[c["case_id"]]["proofscope"].get("verdicts") or {}).get("adelta12") == "NO_ASSUMPTION_DELTA"]
        out["gate"] = {"S_F1_unsound_no_assumption_delta_H0": len(S_F1), "S_F1_cases": S_F1,
                       "U_A": round(UA, 4), "U_B": round(UB, 4), "P_N": None if PN is None else round(PN, 4),
                       "P_N_count": len(ne), "X": len(X), "X_cases": X, "competitor_only_count": len(Xr),
                       "S": "set by the soundness audit (section 11 of the report)"}
    o = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else rd / "summary.json"
    o.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    print(json.dumps({"gate": out.get("gate"), "proofscope": {k: v for k, v in d.items() if k != "decisive_pairs"},
                      "semanteq_verdicts": out["semanteq_verdicts"], "beqplus_outcomes": out["beqplus_outcomes"]},
                     indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
