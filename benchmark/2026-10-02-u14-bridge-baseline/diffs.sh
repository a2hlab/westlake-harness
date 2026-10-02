#!/bin/bash
# Difference artifacts of a U14 bridge build vs the deployed 84695d62: abi_diff (+ runtime consumers ac59dec0 and U13
# 18763dd4, call-set diff), NEEDED/undefined diff, deployed_strings_diff.   diffs.sh <generation dir> <out dir>
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd); repo=$(cd "$here/../.." && pwd); WS=${WORKSPACES:-$(cd "$repo/.." && pwd)}
GEN=$1; OUTD=$2; mkdir -p "$OUTD"
I=$WS/westlake-inputs/generations
OLD=$I/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/native/payload/android/lib64/liboh_adapter_bridge.so
RT0=$I/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/native/payload/android/lib64/liboh_android_runtime.so
RT=$I/u13-runtime-m1-v1/liboh_android_runtime-u13-18763dd4.so
NEW=$GEN/out/liboh_adapter_bridge.so
RE=$(xcrun -f llvm-readelf); NM=$(xcrun -f llvm-nm)
set +e
python3 "$repo/scripts/lab/abi_diff.py" --old "$OLD" --new "$NEW" --consumer "$RT0" --consumer "$RT" --calls \
    --json "$OUTD/abi-diff-846-vs-u14.json" > "$OUTD/abi-diff-846-vs-u14.txt" 2>&1
echo "abi_diff rc=$?" >> "$OUTD/abi-diff-846-vs-u14.txt"
python3 "$repo/scripts/lab/deployed_strings_diff.py" "$NEW" --deployed "$OLD" > "$OUTD/strings-846-vs-u14.txt" 2>&1
set -e
{ echo "## NEEDED (846 vs U14)"; /usr/bin/diff <($RE -d "$OLD" | grep NEEDED | sed 's/.*\[//;s/\]//' | sort) <($RE -d "$NEW" | grep NEEDED | sed 's/.*\[//;s/\]//' | sort) || true
  echo "## undefined (846 -> U14)"
  /usr/bin/diff <($NM -D --undefined-only "$OLD" | awk '{print $NF}' | sort -u) <($NM -D --undefined-only "$NEW" | awk '{print $NF}' | sort -u) | grep '^[<>]' | sed 's/^</- /;s/^>/+ /' || true
} > "$OUTD/needed-undefined.txt"
sed -i '' "s|$WS|\$WORKSPACES|g" "$OUTD"/*.txt
head -1 "$OUTD/abi-diff-846-vs-u14.txt"; tail -1 "$OUTD/strings-846-vs-u14.txt"
