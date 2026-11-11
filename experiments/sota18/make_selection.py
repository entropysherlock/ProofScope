"""SOTA-18 frozen case selection (runs on a GitHub runner; text only, no tool is run).

    python experiments/sota18/make_selection.py SEMANTEQ_DIR ASSESS_DIR OUTDIR

Writes OUTDIR/manifest.json (ids, gold labels, track membership, provenance, hashes) and
OUTDIR/cases.jsonl (the statements). See PROTOCOL.md sections 2-3.
"""
import hashlib
import json
import random
import re
import sys
from pathlib import Path

SEED_A_PNV, SEED_A_EPLA, SEED_B = 20261118, 20261119, 20261120
N_A_PNV, N_A_EPLA, CAP_B, MIN_B = 200, 100, 200, 30
OPEN, CLOSE = "([{⦃⟨", ")]}⦄⟩"
HEAD = re.compile(r"(?:^|\n)\s*(?:@\[[^\]]*\]\s*)?(?:theorem|lemma)\s+([^\s(:{\[⦃]+)")
TOK = re.compile(r"\d+|[A-Za-z_Ͱ-Ͽᴀ-ᶿ℀-⅏][\w.'Ͱ-Ͽ₀-ₜ]*|∃!|\S")
CLASS = set("< ≤ > ≥ = ≠ ∣ ∀ ∃ ∃! ∧ ∨ → ↔ ¬".split())


def norm(s):
    return " ".join(s.split())


def signature(decl):
    """(binders, conclusion) of a theorem/lemma declaration, text only; None if not parseable."""
    m = HEAD.search(decl)
    if not m:
        return None
    rest = decl[m.end():]
    depth, colon = 0, None
    for i, ch in enumerate(rest):
        if ch in OPEN:
            depth += 1
        elif ch in CLOSE:
            depth -= 1
        elif depth == 0 and ch == ":" and not rest.startswith(":=", i):
            colon = i
            break
    if colon is None:
        return None
    body = rest[colon + 1:]
    depth, end = 0, len(body)
    for i, ch in enumerate(body):
        if ch in OPEN:
            depth += 1
        elif ch in CLOSE:
            depth -= 1
        elif depth == 0 and body.startswith(":=", i):
            end = i
            break
    return norm(rest[:colon]), norm(body[:end])


def track_b(ref_decl, cand_decl):
    a, b = signature(ref_decl), signature(cand_decl)
    if not a or not b:
        return None
    (rb, rc), (cb, cc) = a, b
    if rc == cc and rb != cb:
        return "B1"
    if rb == cb and rc != cc:
        x, y = TOK.findall(rc), TOK.findall(cc)
        if len(x) == len(y):
            diff = [(p, q) for p, q in zip(x, y) if p != q]
            if len(diff) == 1:
                p, q = diff[0]
                if (p in CLASS or p.isdigit()) and (q in CLASS or q.isdigit()):
                    return "B2"
    return None


def sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def main():
    semanteq, assess, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    from datasets import load_dataset
    from huggingface_hub import HfApi
    info = HfApi().dataset_info("PAug/ProofNetVerif")
    card = getattr(info, "card_data", None) or {}
    prov = {"pnv_dataset": "PAug/ProofNetVerif", "pnv_revision": info.sha,
            "pnv_license": (card.get("license") if hasattr(card, "get") else None) or str(card)[:200]}
    ds = load_dataset("PAug/ProofNetVerif", split="test", revision=info.sha)
    adj = {}
    for line in (semanteq / "test" / "pnv_test_adjudicated_labels.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            adj[r["id"]] = r["correct"]
    cases = []
    for idx, r in enumerate(ds):
        cid = f"pnv:test:{idx:04d}:{r['id']}"
        cases.append({"case_id": cid, "source": "PNV", "ref_header": r["lean4_src_header"], "cand_header": r["lean4_src_header"],
                      "ref_decl": r["lean4_formalization"], "cand_decl": r["lean4_prediction"],
                      "nl": r.get("nl_statement"), "gold": {"G1": bool(r["correct"]), "G2": adj.get(cid)}})
    n_pnv = len(cases)
    for split in ("ProofNet", "miniF2F"):
        data = json.loads((assess / "benchmark" / f"EPLA-{split}.json").read_text())
        for it in data:
            for k, sq in enumerate(it["sub_questions"]):
                if sq.get("compiler_check") != "success":
                    continue
                cases.append({"case_id": f"epla:{split}:{it['id']}:{k}", "source": "EPLA", "ref_header": it["header"],
                              "cand_header": sq["header"], "ref_decl": it["FL (Label)"], "cand_decl": sq["FL (Prediction)"],
                              "nl": it.get("NL"), "gold": {"G3": bool(sq["likeness after transformation"])}})
    pnv = [c["case_id"] for c in cases if c["source"] == "PNV"]
    epla = [c["case_id"] for c in cases if c["source"] == "EPLA"]
    a = sorted(random.Random(SEED_A_PNV).sample(pnv, N_A_PNV)) + sorted(random.Random(SEED_A_EPLA).sample(epla, N_A_EPLA))
    btag = {c["case_id"]: track_b(c["ref_decl"], c["cand_decl"]) for c in cases}
    bq = sorted(k for k, v in btag.items() if v)
    b = bq if len(bq) <= CAP_B else sorted(random.Random(SEED_B).sample(bq, CAP_B))
    keep = set(a) | set(b)
    sel = [c for c in cases if c["case_id"] in keep]
    for c in sel:
        c["tracks"] = (["A"] if c["case_id"] in a else []) + (["B"] if c["case_id"] in b else [])
        c["track_b_class"] = btag[c["case_id"]]
    with (out / "cases.jsonl").open("w") as f:
        for c in sel:
            f.write(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n")
    unparsed = sum(1 for c in cases if signature(c["ref_decl"]) is None or signature(c["cand_decl"]) is None)
    man = {"provenance": {**prov, "semanteq_labels": "hlxr89/SemantEq@f92767000e14 test/pnv_test_adjudicated_labels.jsonl",
                          "epla": "XiaoyangLiu-sjtu/ASSESS@bc7933547d8a benchmark/EPLA-*.json (compiler_check == success)"},
           "population": {"PNV_test_rows": n_pnv, "PNV_rows_with_G2": sum(1 for c in cases if c["source"] == "PNV" and c["gold"]["G2"] is not None),
                          "EPLA_rows": len(epla), "signature_unparsed": unparsed,
                          "track_b_qualifying": {"B1": sum(1 for v in btag.values() if v == "B1"), "B2": sum(1 for v in btag.values() if v == "B2"),
                                                 "by_source": {s: sum(1 for c in cases if btag[c["case_id"]] and c["source"] == s) for s in ("PNV", "EPLA")}},
                          "track_b_scarce": len(bq) < MIN_B},
           "seeds": {"A_PNV": SEED_A_PNV, "A_EPLA": SEED_A_EPLA, "B": SEED_B},
           "track_A": a, "track_B": b,
           "gold": {c["case_id"]: c["gold"] for c in sel},
           "cases_sha256": hashlib.sha256((out / "cases.jsonl").read_bytes()).hexdigest(),
           "population_sha256": sha([[c["case_id"], c["ref_decl"], c["cand_decl"]] for c in cases])}
    (out / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in man.items() if k not in ("track_A", "track_B", "gold")}, indent=1, ensure_ascii=False))
    print("track A", len(a), "track B", len(b), "union", len(keep))


if __name__ == "__main__":
    main()
