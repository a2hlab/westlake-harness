#!/bin/bash
# run_probe_unlocked.sh — wake/unlock screen and run aonb_d600_probe.sh gates.
# Usage: D600_SERIAL=... bash run_probe_unlocked.sh [gate|all]

set -euo pipefail

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
export PATH="$(dirname "$HDC"):$PATH"

SERIAL="${D600_SERIAL:-}"
GATES="${1:-g7}"
if [ -z "$SERIAL" ]; then
    echo "Usage: D600_SERIAL=... bash $0 [g7|g13|g5|g12|all]" >&2
    exit 2
fi

TS=$(date -u +%Y%m%dT%H%M%SZ)
RUN_DIR="/opt/Bridge/evidence/runs/probe-unlocked-${SERIAL}-${TS}"
mkdir -p "$RUN_DIR"
exec > >(tee "$RUN_DIR/wrapper.log") 2>&1

echo "=== probe unlocked: serial=$SERIAL gates=$GATES ==="

# Ensure permissive SELinux and awake screen.
"$HDC" -t "$SERIAL" shell "setenforce 0; param set persist.sys.abilityms.support_anco_app true" >/dev/null 2>&1 || true
# Wake: power key-ish swipe from bottom to center.
"$HDC" -t "$SERIAL" shell "uinput -T -m 300 900 300 300 500" >/dev/null 2>&1 || true
sleep 1

export D600_SERIAL="$SERIAL"
export WORKDIR="$RUN_DIR/probes"
export APK_DIR="/opt/Bridge/.work/d600-deploy-merged-20260726"
export PROBE_DIR="/opt/Bridge/src/adapter/verification/out"

bash "/opt/Bridge/src/adapter/verification/aonb_d600_probe.sh" "$GATES"

echo "=== evidence in $RUN_DIR ==="
