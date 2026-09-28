#!/bin/bash
# Entry #12 worker: parallel startup-reach over every app with a static scan.
# Runs ON THE VM (orb -m a2hlab). APKs/scans/runtime are VM-local paths; the repo
# copy is VM-local too (~/reach-repo) so no OrbStack path translation can bite.
# Claims keys via mkdir locks -> idempotent, resumable, safe to run N copies.
W=${1:-?}
PY=~/reachenv/bin/python3
OUT=~/a2hlab/static/reach-20260928
SCANS=~/a2hlab/static/scans
INPUTS=~/a2hlab/app-inputs
RUNTIME=~/a2hlab/static/runtime-index.json
LOCKD=$OUT/.locks
mkdir -p "$LOCKD"
for scan_json in "$SCANS"/*.json; do
  key=$(basename "$scan_json" .json)
  out="$OUT/$key.reach.json"
  [ -s "$out" ] && continue
  mkdir "$LOCKD/$key" 2>/dev/null || continue   # claim; another worker owns it
  apk=$(ls "$INPUTS/$key"/*.apk "$INPUTS/$key"/*.xapk "$INPUTS/$key"/*.apkm 2>/dev/null | head -1)
  if [ -z "$apk" ]; then echo "W$W SKIP $key (no apk)"; continue; fi
  if PYTHONPATH=~/reach-repo/harness timeout 900 $PY -m westlake_gap.cli startup-reach "$apk" \
      --runtime "$RUNTIME" --scan "$scan_json" --out "$out" >/dev/null 2>"$OUT/$key.reach.err"; then
    echo "W$W OK $key"
  else
    echo "W$W FAIL $key"
  fi
done
echo "W$W DONE"
