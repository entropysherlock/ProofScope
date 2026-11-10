"""Paired comparison of two engines on the same sealed Pilot-25 inputs (no gold: claims and replay only)."""
import argparse
import json
from pathlib import Path

DECISIVE = {"EQUIVALENT_CLOSED", "NOT_EQUIVALENT_CLOSED", "IMPLICATION_ONE_WAY"}


def load(d: Path):
    recs = {json.loads(l)["case_id"]: json.loads(l) for l in (d / "execution" / "records.jsonl").read_text().splitlines()}
    rp = d / "replay.jsonl"
    reps = {json.loads(l)["case_id"]: json.loads(l) for l in rp.read_text().splitlines()} if rp.exists() else {}
    return recs, reps


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=Path, required=True); ap.add_argument("--b", type=Path, required=True)
    ap.add_argument("--names", nargs=2, default=["cjcs4", "sota8"]); ap.add_argument("--out", type=Path, required=True)
    x = ap.parse_args(argv)
    (ra, pa), (rb, pb) = load(x.a), load(x.b)
    rows, summ = [], {}
    for cid in sorted(ra):
        row = {"case_id": cid}
        for n, r, p in ((x.names[0], ra, pa), (x.names[1], rb, pb)):
            c = r[cid]["claim"]
            ok = c["claim"] in DECISIVE and (p.get(cid) or {}).get("replay") == "VERIFIED"
            row[n] = {"claim": c["claim"], "basis": c.get("basis") or c.get("direction"), "replay": (p.get(cid) or {}).get("replay"),
                      "certified": ok, "cpu_s": r[cid]["cpu_tree_s"], "peak_rss_mb": r[cid]["max_rss_mb"], "status": r[cid]["status"]}
            s = summ.setdefault(n, {"cases": 0, "certified": 0, "claims": {}, "cpu_s_total": 0.0, "peak_rss_mb_max": 0})
            s["cases"] += 1; s["certified"] += ok; s["claims"][c["claim"]] = s["claims"].get(c["claim"], 0) + 1
            s["cpu_s_total"] = round(s["cpu_s_total"] + r[cid]["cpu_tree_s"], 1); s["peak_rss_mb_max"] = max(s["peak_rss_mb_max"], r[cid]["max_rss_mb"])
            if ok is False and c["claim"] in DECISIVE:
                s["decisive_without_verified_certificate"] = s.get("decisive_without_verified_certificate", 0) + 1
        rows.append(row)
    for n, s in summ.items():
        s["certified_per_cpu_hour"] = round(s["certified"] / (s["cpu_s_total"] / 3600), 2) if s["cpu_s_total"] else None
    x.out.mkdir(parents=True, exist_ok=True)
    (x.out / "compare.json").write_text(json.dumps({"summary": summ, "rows": rows}, indent=1))
    md = ["| case | " + " | ".join(f"{n} claim | {n} replay | {n} CPU s | {n} peak MB" for n in x.names) + " |",
          "|---|" + "---|---|---|---|" * 2]
    for r in rows:
        md.append(f"| {r['case_id']} | " + " | ".join(f"{r[n]['claim']} {r[n]['basis'] or ''} | {r[n]['replay']} | {r[n]['cpu_s']} | {r[n]['peak_rss_mb']}" for n in x.names) + " |")
    md.append("\n```json\n" + json.dumps(summ, indent=1) + "\n```")
    (x.out / "compare.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    bad = sum(s.get("decisive_without_verified_certificate", 0) for s in summ.values())
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
