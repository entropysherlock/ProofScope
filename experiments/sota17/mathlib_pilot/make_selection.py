"""Frozen selection for the Mathlib pilot (Track C). Deterministic given population.json.

C1  uniform sample of 200 declarations from all extracted theorems/lemmas.
C2  the declarations whose own signature binds a function `ℕ → ℕ` (the only objects the ScopeElim
    fragments talk about). They are split by the parity of sha256(file:name) into a development
    half (read while writing the translator) and a held-out half (not read before the frozen run).
"""
import hashlib
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = 20261117
FUN = re.compile(r"[({](?:[^(){}:]+) : (?:ℕ|Nat) → (?:ℕ|Nat)[)}]")


def main():
    pop = json.loads(Path(sys.argv[1]).read_text())
    decls = pop["declarations"]
    rng = random.Random(SEED)
    c1 = sorted(rng.sample(range(len(decls)), 200))
    c2 = [i for i, d in enumerate(decls) if FUN.search(d["signature"])]
    half = lambda i: int(hashlib.sha256(f"{decls[i]['file']}:{decls[i]['name']}".encode()).hexdigest(), 16) % 2
    sel = {"mathlib_rev": pop["mathlib_rev"], "population": pop["count"], "population_sha256": pop["sha256"], "seed": SEED,
           "C1": [decls[i] for i in c1],
           "C2_population": len(c2),
           "C2_dev": [decls[i] for i in c2 if half(i) == 0],
           "C2_heldout": [decls[i] for i in c2 if half(i) == 1]}
    blob = json.dumps(sel, ensure_ascii=False, sort_keys=True, indent=1)
    (HERE / "selection.json").write_text(blob + "\n")
    print({k: (len(v) if isinstance(v, list) else v) for k, v in sel.items()}, hashlib.sha256((blob + "\n").encode()).hexdigest())


if __name__ == "__main__":
    main()
