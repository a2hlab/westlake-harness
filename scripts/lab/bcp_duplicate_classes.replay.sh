#!/usr/bin/env bash
# Replay for the G3 gate bcp_duplicate_classes.py (board #95, T7C-CHECKSYSTEMCLASS.md).
# Reproduces the T7c class-comparison conclusion and demonstrates the gate both ways:
#   1) unit tests pass
#   2) a real v3c BCP set is clean (only the 7 allowed *Initializer duplicates, exit 0)
#   3) a synthetic collision (a stub class that also lives in framework) is caught (exit 1)
# No board, no network. Deterministic.
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
GATE="$HERE/bcp_duplicate_classes.py"
WS=$(cd -- "$HERE/../../.." && pwd)   # .../orca/workspaces

echo "== 1. unit tests =="
( cd "$HERE" && python3 test_bcp_duplicate_classes.py ) 2>&1 | grep -E '^(Ran|OK|FAILED)' | tail -3

echo
echo "== 2. real v3c BCP set (auto-discovered generation package) =="
FDIR=""
for p in "$WS"/westlake-generation-*/payload/android/framework/adapter-mainline-stubs.jar; do
  [ -f "$p" ] && { FDIR=$(dirname "$p"); break; }
done
if [ -n "$FDIR" ]; then
  echo "framework-dir: $FDIR"
  python3 "$GATE" --framework-dir "$FDIR"; rc=$?
  echo "exit=$rc (expect 0: only the 7 allowed *Initializer duplicates)"
else
  echo "no generation package on disk; skipping the real-jar replay"
fi

echo
echo "== 3. synthetic collision is caught =="
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
cat > "$TMP/classmap.json" <<'JSON'
{
  "framework": ["android/net/NetworkInfo", "android/app/Activity"],
  "adapter-mainline-stubs": ["android/net/NetworkInfo", "org/ccil/cowan/tagsoup/Parser"],
  "core-oj": ["java/lang/Object"]
}
JSON
set +e
python3 "$GATE" --classmap "$TMP/classmap.json"; rc=$?
set -e
echo "exit=$rc (expect 1: android/net/NetworkInfo duplicated across framework + stubs)"
[ "$rc" = 1 ] || { echo "REPLAY FAIL: gate did not flag the synthetic collision"; exit 1; }
echo
echo "replay OK"
