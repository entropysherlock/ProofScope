#!/usr/bin/env bash
# Usage: verify.sh <dir-with-.lean-certificates> <out-dir> [leanchecker]
# Requires `lean` on PATH and LEAN_PATH pointing at a built Mathlib. For each certificate:
#   1. the verbatim block is re-hashed against index.json (dataset text unchanged),
#   2. the file compiles with no errors,
#   3. `#print axioms` for the certificate lists only propext / Classical.choice / Quot.sound (no sorryAx),
#   4. optionally, leanchecker replays the compiled module.
set -uo pipefail
D="$1"; OUT="$2"; CHECKER="${3:-}"
mkdir -p "$OUT/build"; : > "$OUT/summary.tsv"; fail=0
python3 - "$D" <<'PY' || fail=1
import hashlib, json, sys
from pathlib import Path
d = Path(sys.argv[1]); idx = json.loads((d / "index.json").read_text())
for c in idx["certificates"]:
    t = (d / c["file"]).read_text()
    body = t[t.index("-/\n") + 3: t.index("\n  sorry\n")]
    ok = hashlib.sha256(body.encode()).hexdigest() == c["autoformalization_sha256"]
    print(("VERBATIM_OK  " if ok else "VERBATIM_MISMATCH ") + c["row"]); assert ok
PY
i=0
for f in "$D"/*.lean; do
  i=$((i+1)); m="Cert$i"; cp "$f" "$OUT/build/$m.lean"
  ( cd "$OUT/build" && lean -o "$m.olean" "$m.lean" ) > "$OUT/$m.log" 2>&1; rc=$?
  ax=$(grep -o "depends on axioms: \[[^]]*\]" "$OUT/$m.log" | tail -1)
  errs=$(grep -c ": error" "$OUT/$m.log")
  axok=no; [ -n "$ax" ] && ! grep -q sorryAx <<<"$ax" && axok=yes
  rep=skipped
  if [ -n "$CHECKER" ] && [ $rc -eq 0 ]; then
    ( cd "$OUT/build" && LEAN_PATH="$OUT/build:$LEAN_PATH" "$CHECKER" "$m" ) > "$OUT/$m.replay.log" 2>&1 && rep=ok || rep=FAIL
  fi
  status=PASS; { [ $rc -ne 0 ] || [ "$errs" != 0 ] || [ "$axok" != yes ] || [ "$rep" = FAIL ]; } && status=FAIL && fail=1
  if [ "$status" = FAIL ] && [ "$i" -le 2 ]; then echo "--- $m compile log"; tail -c 1500 "$OUT/$m.log"; [ -f "$OUT/$m.replay.log" ] && { echo "--- $m replay log"; tail -c 1500 "$OUT/$m.replay.log"; }; fi
  printf "%s\t%s\tcompile_rc=%s\terrors=%s\taxioms=%s\treplay=%s\n" "$status" "$(basename "$f")" "$rc" "$errs" "${ax:-none}" "$rep" | tee -a "$OUT/summary.tsv"
done
exit $fail
