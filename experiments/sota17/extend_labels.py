"""Second labelling attempt, with long solver limits, for directions the engine certified but
`labels.py` left unlabelled. Same independent method (uninterpreted-function refutation only).

    python3 experiments/sota17/extend_labels.py SUMMARY.json OUT.json
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import labels  # noqa: E402


def main():
    summ = json.loads(Path(sys.argv[1]).read_text())
    out = {}
    for cid, tag, st in summ["unlabelled_certified"]:
        spec = json.loads((HERE / "cases" / f"{cid}.json").read_text())
        R, F = labels.claim(spec["reference"]), labels.claim(spec["formal"])
        H, C = (R, F) if tag == "fwd" else (F, R)
        res = None
        for name, m in (("z3", labels.z3), ("cvc5", labels.cv)):
            if m is None:
                continue
            try:
                if labels.uf_refute(m, H, C, 60000):
                    res = name
                    break
            except Exception:  # noqa: BLE001
                pass
        out[f"{cid}:{tag}"] = {"engine": st, "label": "ENTAILS" if res else None, "method": res}
        print(cid, tag, st, res, flush=True)
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
