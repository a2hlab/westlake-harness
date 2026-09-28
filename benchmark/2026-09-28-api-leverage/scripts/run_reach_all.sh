#!/bin/bash
# Entry #12: run harness startup-reach for every app that has a static scan, on the VM (APKs live there).
# Usage: bash run_reach_all.sh <out-root-on-vm>   (run inside: orb -m a2hlab bash -lc '...')
set -uo pipefail
OUT_ROOT="${1:?usage: run_reach_all.sh <out-root>}"
SCANS=/home/zhaoyue/a2hlab/static/scans
INPUTS=/home/zhaoyue/a2hlab/app-inputs
RUNTIME=/home/zhaoyue/a2hlab/static/runtime-index.json
REPO=/home/zhaoyue/a2hlab/lev/westlake-harness-lev   # copied from the Mac worktree by the caller
mkdir -p "$OUT_ROOT"
ok=0; fail=0
for scan_json in "$SCANS"/*.json; do
  key=$(basename "$scan_json" .json)
  apk=$(ls "$INPUTS/$key"/*.apk "$INPUTS/$key"/*.xapk "$INPUTS/$key"/*.apkm 2>/dev/null | head -1)
  if [ -z "$apk" ]; then echo "SKIP $key (no apk)"; continue; fi
  out="$OUT_ROOT/$key.reach.json"
  if [ -s "$out" ]; then echo "CACHED $key"; ok=$((ok+1)); continue; fi
  if PYTHONPATH="$REPO/harness" python3 -m westlake_gap.cli startup-reach "$apk" \
      --runtime "$RUNTIME" --scan "$scan_json" --out "$out" >/dev/null 2>"$OUT_ROOT/$key.reach.err"; then
    echo "OK $key"; ok=$((ok+1))
  else
    echo "FAIL $key (see $OUT_ROOT/$key.reach.err)"; fail=$((fail+1))
  fi
done
echo "=== reach-all done: ok=$ok fail=$fail out=$OUT_ROOT ==="
