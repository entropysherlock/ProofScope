"""Mathlib pilot (Track C): how many real declarations reach each stage of the SOTA-17 pipeline.

    python3 pilot.py SPLIT OUT      # SPLIT in C1, C2_dev, C2_heldout (from selection.json)

Stages (every declaration is counted at the first stage it fails; nothing is dropped):
  extracted     signature text found by extract.py (all selected declarations)
  binders       binder list understood: one function `ℕ → ℕ`, natural-number variables, hypotheses
  abstracted    hypotheses and conclusion translated into the claim grammar, exactly one hypothesis
                on the function
  in_fragment   that hypothesis is in a supported class (step / lower / pointwise)
  certified     'hypothesis entails conclusion' certified by Lean (ENTAILS expected: it is a theorem)

There is no Mathlib build in this pipeline, so statements are *not elaborated*; translation is
syntactic. The only definitions unfolded are a fixed dictionary of two (on `ℕ → ℕ`):
  StrictMono f  ↦  ∀ n, f n < f (n + 1)        (Mathlib: strictMono_nat_of_lt_succ and its converse)
  Monotone f    ↦  ∀ n, f n ≤ f (n + 1)        (Mathlib: monotone_nat_of_le_succ and its converse)
The certified statement is therefore about the abstracted claim, not about the Mathlib constant.

Synthetic track (labelled as such): for each certified declaration the hypothesis is weakened
(`<` to `≤`) and the comparison is repeated; the expected outcome is whatever is true.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from proofscope import multiocc  # noqa: E402
from proofscope.scope_expr import Unsupported  # noqa: E402
from proofscope.scopeelim import lib_toolchain  # noqa: E402
from proofscope.toolchain import Toolchain  # noqa: E402

OPEN, CLOSE = "({[⦃", ")}]⦄"
NAT = {"ℕ", "Nat"}
FUN = {"ℕ → ℕ", "Nat → Nat"}
DICT = {"StrictMono": "f n < f (n + 1)", "Monotone": "f n ≤ f (n + 1)"}


class Fail(Exception):
    def __init__(self, stage, reason):
        self.stage, self.reason = stage, reason


def split_signature(sig):
    groups, i = [], 0
    while i < len(sig):
        ch = sig[i]
        if ch.isspace():
            i += 1
        elif ch in OPEN:
            depth, j = 0, i
            while j < len(sig):
                depth += sig[j] in OPEN
                depth -= sig[j] in CLOSE
                if depth == 0:
                    break
                j += 1
            if depth:
                raise Fail("binders", "unbalanced binder")
            groups.append((ch, sig[i + 1:j].strip()))
            i = j + 1
        elif ch == ":":
            return groups, sig[i + 1:].strip()
        else:
            raise Fail("binders", "binder without brackets")
    raise Fail("binders", "no conclusion")


def rename(text, fsym):
    if fsym != "f" and re.search(r"(?<![\w.'])f(?![\w.'])", text):
        raise Fail("abstracted", "name clash with f")
    return re.sub(r"(?<![\w.'])%s(?![\w.'])" % re.escape(fsym), "f", text)


def prop(text, fsym, outer_vars):
    """(vars, body) for a proposition; vars are the variables it binds itself."""
    text = text.strip()
    m = re.fullmatch(r"(StrictMono|Monotone) (\S+)", text)
    if m:
        if m.group(2) != fsym:
            raise Fail("abstracted", "law about another object")
        v = next(x for x in ("n", "k", "i", "j", "t") if x not in outer_vars)
        return [v], re.sub(r"\bn\b", v, DICT[m.group(1)])
    m = re.fullmatch(r"∀ \(?([A-Za-z_ ]+?)(?: : (?:ℕ|Nat))?\)?, (.*)", text)
    if m:
        vs = m.group(1).split()
        return vs, rename(m.group(2), fsym)
    return [], rename(text, fsym)


def translate(decl):
    groups, concl = split_signature(decl["signature"])
    fsyms, nats, hyps = [], [], []
    for br, body in groups:
        if br == "[":
            raise Fail("binders", "typeclass binder")
        if " : " not in body:
            raise Fail("binders", "untyped binder")
        names, typ = body.split(" : ", 1)
        names, typ = names.split(), typ.strip()
        if typ in FUN:
            fsyms += names
        elif typ in NAT:
            nats += names
        elif len(names) == 1:
            hyps.append(typ)
        else:
            raise Fail("binders", "variables of another type")
    if len(fsyms) != 1:
        raise Fail("binders", "several function symbols" if fsyms else "no function symbol in the binders")
    fsym = fsyms[0]
    has = lambda t: re.search(r"(?<![\w.'])%s(?![\w.'])" % re.escape(fsym), t) is not None
    on_f = [h for h in hyps if has(h)]
    side = [h for h in hyps if not has(h)]
    if not has(concl):
        raise Fail("abstracted", "conclusion does not mention the function")
    if len(on_f) != 1:
        raise Fail("abstracted", "no hypothesis on the function" if not on_f else "several hypotheses on the function")
    try:
        hv, hb = prop(on_f[0], fsym, nats)
        if len(hv) != 1:
            raise Fail("abstracted", "hypothesis on the function is neither a single ∀ over ℕ nor a dictionary law")
        H = multiocc.Claim.from_json({"var": hv[0], "body": hb})
        cv, cb = prop(concl, fsym, nats)
        guard = " ∧ ".join(f"({rename(s, fsym)})" for s in side) or "True"
        C = multiocc.Claim.from_json({"vars": nats + cv, "guard": guard, "body": cb})
    except Unsupported as e:
        raise Fail("abstracted", f"outside the claim grammar: {e}")
    return {"reference": {"var": hv[0], "body": hb}, "formal": {"vars": nats + cv, "guard": guard, "body": cb}}, H, C


def main():
    split, out = sys.argv[1], Path(sys.argv[2]).resolve()
    sel = json.loads((HERE / "selection.json").read_text())
    base = Toolchain.find()
    b = multiocc.build_lib(base, out / "lib")
    assert b["ok"], b
    tc = lib_toolchain(base, out / "lib")
    rows, stages = [], Counter()
    for k, decl in enumerate(sel[split]):
        row = {"name": decl["name"], "file": decl["file"], "line": decl["line"]}
        try:
            spec, H, C = translate(decl)
            row["abstraction"] = spec
            try:
                row["class"] = {a: b_ for a, b_ in multiocc.classify(H).items() if a != "fc"}
            except Unsupported as e:
                raise Fail("in_fragment", str(e))
            res = multiocc.compare({"id": f"{split}_{k}", "kind": "multi", **spec}, tc, out / "work" / f"{split}_{k}")
            row["fwd"], row["seconds"] = res["directions"]["fwd"], res["seconds"]
            row["axioms"] = res.get("axioms", {})
            if res["directions"]["fwd"] != "ENTAILS":
                raise Fail("certified", f"engine returned {res['directions']['fwd']}")
            row["stage"] = "certified"
            if "<" in spec["reference"]["body"]:                      # synthetic perturbation
                weak = dict(spec, reference={"var": spec["reference"]["var"],
                                             "body": spec["reference"]["body"].replace("<", "≤")})
                r2 = multiocc.compare({"id": f"{split}_{k}_weak", "kind": "multi", **weak}, tc, out / "work" / f"{split}_{k}_weak")
                row["synthetic_weakened_hypothesis"] = {"reference": weak["reference"], "fwd": r2["directions"]["fwd"],
                                                        "witness": r2.get("info", {}).get("fwd", {}).get("witnesses", [])[:1]}
        except Fail as e:
            row["stage"], row["reason"] = "failed_at_" + e.stage, e.reason
        stages[row["stage"]] += 1
        rows.append(row)
    order = ["binders", "abstracted", "in_fragment", "certified"]
    n = len(rows)
    reached, left = {"extracted": n}, n
    for st in order:
        left -= stages.get("failed_at_" + st, 0)
        reached[st] = left
    summ = {"split": split, "mathlib_rev": sel["mathlib_rev"], "declarations": n, "reached": reached,
            "failure_reasons": dict(Counter(f"{r['stage']}: {r['reason']}" for r in rows if "reason" in r).most_common()),
            "certified": [r["name"] for r in rows if r["stage"] == "certified"],
            "seconds_total": round(sum(r.get("seconds", 0) for r in rows), 1)}
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{split}_results.json").write_text(json.dumps({"summary": summ, "rows": rows}, indent=1, ensure_ascii=False))
    print(json.dumps(summ, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
