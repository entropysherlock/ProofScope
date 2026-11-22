"""Sealing: blinded case files, label commitments and a group-disjoint pilot/primary split.

Run by the independent custodian, not by a tool developer:

    python -m bench.seal build --pool pool/ --sources epla,pnv-test --primary 480 --pilot 48 \
        --seed <custodian-chosen> --out sealed/

Writes
    sealed/pilot.cases.jsonl, sealed/primary.cases.jsonl   blinded (opaque ids, shuffled, no labels)
    sealed/manifest.json                                   counts, strata, file SHA-256s, label commitment
    sealed/custodian/labels.jsonl + salt.txt                NEVER committed; held by the custodian

Commitment: SHA-256(salt || canonical JSON of the label file). Publishing the commitment before any
prediction run and the salt + labels after the runs are locked lets anyone verify that labels were not
changed after seeing predictions. Selection is by whole group (all siblings of a source theorem go to the
same split) so near-duplicates cannot straddle pilot and primary. Stratification uses source labels only
to balance the sample; gold labels are the adjudicators' votes, recorded later against the same ids.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import secrets
from collections import defaultdict
from pathlib import Path

from .canonical import group_near_duplicates, read_jsonl, sha256_file, write_jsonl


def commitment(labels: list[dict], salt: str) -> str:
    payload = json.dumps(sorted(labels, key=lambda r: r["case_id"]), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((salt + payload).encode()).hexdigest()


def verify(labels: list[dict], salt: str, published: str) -> bool:
    return commitment(labels, salt) == published


def build(pool: Path, sources: list[str], n_primary: int, n_pilot: int, seed: int, out: Path) -> dict:
    cases, src_labels = [], {}
    for s in sources:
        cases += read_jsonl(pool / f"{s}.cases.jsonl")
        for r in read_jsonl(pool / f"{s}.source_labels.jsonl"):
            src_labels[r["case_id"]] = r["source_label_equivalent"]
    # near-duplicate grouping on top of the source's own theorem grouping
    near = group_near_duplicates([(c["case_id"], c["cand_decl"]) for c in cases])
    by_ref = group_near_duplicates([(c["case_id"], c["ref_decl"]) for c in cases])
    # final group: union of source group, candidate near-dup and reference near-dup relations
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    for c in cases:
        k = c["case_id"]
        union(k, "G:" + c["group"])
        union(k, "N:" + near[k])
        union(k, "R:" + by_ref[k])
    groups = defaultdict(list)
    for c in cases:
        groups[find(c["case_id"])].append(c)
    rng = random.Random(seed)
    order = sorted(groups)
    rng.shuffle(order)
    # pilot: first groups until n_pilot cases; primary: balanced by source label, whole groups only
    pilot, primary, used = [], [], set()
    for g in order:
        if len(pilot) >= n_pilot:
            break
        pilot += groups[g]
        used.add(g)
    want = {True: n_primary // 2, False: n_primary - n_primary // 2}
    have = {True: 0, False: 0}
    for g in order:
        if g in used:
            continue
        members = groups[g]
        pos = sum(bool(src_labels.get(c["case_id"])) for c in members)
        neg = len(members) - pos
        if have[True] + pos <= want[True] and have[False] + neg <= want[False]:
            primary += members
            have[True] += pos
            have[False] += neg
            used.add(g)
        if have == want:
            break
    salt = secrets.token_hex(32)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"seed": seed, "sources": sources, "groups_total": len(groups), "notes": []}
    for name, part in (("pilot", pilot), ("primary", primary)):
        rng.shuffle(part)
        blinded, labels = [], []
        for i, c in enumerate(part):
            bid = f"{name}-{i:04d}-" + hashlib.sha256((str(seed) + c["case_id"]).encode()).hexdigest()[:6]
            b = {k: v for k, v in c.items() if k not in ("generator",)}
            b["case_id"], b["origin_case_id_hash"] = bid, hashlib.sha256(c["case_id"].encode()).hexdigest()[:16]
            b["group"] = "grp-" + hashlib.sha256(find(c["case_id"]).encode()).hexdigest()[:10]
            blinded.append(b)
            labels.append({"case_id": bid, "origin_case_id": c["case_id"], "source": c["source"],
                           "source_label_equivalent": src_labels.get(c["case_id"])})
        write_jsonl(out / f"{name}.cases.jsonl", blinded)
        write_jsonl(out / "custodian" / f"{name}.labels.jsonl", labels)
        manifest[name] = {"cases": len(part), "groups": len({b['group'] for b in blinded}),
                          "by_source": {s: sum(c["source"] == s for c in part) for s in sources_of(part)},
                          "cases_sha256": sha256_file(out / f"{name}.cases.jsonl"),
                          "label_commitment": commitment(labels, salt)}
    if have != want:
        manifest["notes"].append(f"primary balance not reached with whole groups: positives {have[True]}/{want[True]}, "
                                 f"negatives {have[False]}/{want[False]}; the shortfall is reported, not padded")
    (out / "custodian" / "salt.txt").write_text(salt + "\n")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest


def sources_of(part):
    return sorted({c["source"] for c in part})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bench.seal")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--pool", type=Path, required=True)
    b.add_argument("--sources", required=True)
    b.add_argument("--primary", type=int, default=480)
    b.add_argument("--pilot", type=int, default=48)
    b.add_argument("--seed", type=int, required=True)
    b.add_argument("--out", type=Path, required=True)
    v = sub.add_parser("verify")
    v.add_argument("--labels", type=Path, required=True)
    v.add_argument("--salt", required=True)
    v.add_argument("--commitment", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        print(json.dumps(build(a.pool, a.sources.split(","), a.primary, a.pilot, a.seed, a.out), indent=1))
        return 0
    ok = verify(read_jsonl(a.labels), a.salt.strip(), a.commitment)
    print("COMMITMENT_OK" if ok else "COMMITMENT_MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
