"""Run telemetry for a shard of the 23 adapted cases with a given engine checkout (frozen or recovered)."""
import json
import subprocess
import sys
from pathlib import Path

from bench.pilot25r.cases import adapted

if __name__ == "__main__":
    engine_root, label, shard, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
    i, n = map(int, shard.split("/"))
    out.mkdir(parents=True, exist_ok=True)
    for k, d in enumerate(adapted()):
        if k % n != i:
            continue
        spec = out / f"{d['id']}.spec.json"
        spec.write_text(json.dumps({"id": d["id"], "reference": d["R"], "lean": d["F"]}, ensure_ascii=False))
        subprocess.run([sys.executable, "-m", "bench.pilot25r.telemetry", "--engine-root", str(engine_root), "--spec", str(spec),
                        "--out", str(out / f"{d['id']}.{label}.json")])
