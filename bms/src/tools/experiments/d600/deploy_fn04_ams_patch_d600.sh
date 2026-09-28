#!/bin/bash
# deploy_fn04_ams_patch_d600.sh — deploy patched AMS/AppSpawn-client to a D600
# and run a minimal AonB smoke probe (lifecycle + service-stubbing + graphics + input).
#
# Usage:
#   bash deploy_fn04_ams_patch_d600.sh <serial> <variant>
# where <variant> is one of:
#   patched   — use libabilityms.z.so.patched + libappms.z.so.patched2
#   fn04v2    — use libabilityms.z.so.fn04.v2 + libappms.z.so.fn04.v2
#
# Example:
#   bash deploy_fn04_ams_patch_d600.sh 5583f5be00000000000000000323012c patched

set -euo pipefail

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
export PATH="$(dirname "$HDC"):$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SRC=/opt/Bridge/out/alexpc-rebuild-20260726

SERIAL="${1:-}"
VARIANT="${2:-}"

if [ -z "$SERIAL" ] || [ -z "$VARIANT" ]; then
    echo "Usage: $0 <serial> <patched|fn04v2>" >&2
    exit 2
fi

TS=$(date -u +%Y%m%dT%H%M%SZ)
RUN_DIR="$ADAPTER_ROOT/evidence/runs/fn04-ams-${VARIANT}-${SERIAL}-${TS}"
mkdir -p "$RUN_DIR"
exec > >(tee "$RUN_DIR/deploy.log") 2>&1

case "$VARIANT" in
    patched)
        ABILITY_SRC=libabilityms.z.so.patched
        APPMS_SRC=libappms.z.so.patched2
        CLIENT_SRC=libappspawn_client.z.so
        ;;
    fn04v2)
        ABILITY_SRC=libabilityms.z.so.fn04.v2
        APPMS_SRC=libappms.z.so.fn04.v2
        CLIENT_SRC=libappspawn_client.z.so.fn04.v2
        ;;
    *)
        echo "Unknown variant: $VARIANT (choose patched or fn04v2)" >&2
        exit 2
        ;;
esac

echo "=== Fn04 AMS patch deploy: serial=$SERIAL variant=$VARIANT ==="
echo "RUN_DIR=$RUN_DIR"

for f in "$SRC/$ABILITY_SRC" "$SRC/$APPMS_SRC" "$SRC/$CLIENT_SRC"; do
    if [ ! -f "$f" ]; then
        echo "Missing artifact: $f" >&2
        exit 3
    fi
    echo " artifact $(basename "$f") sha256=$(sha256sum "$f" | awk '{print $1}')"
done

TMP=/data/local/tmp/fn04-ams-patch-${VARIANT}

echo "[*] Mount /system rw and stop foundation"
"$HDC" -t "$SERIAL" target mount
"$HDC" -t "$SERIAL" shell "begetctl stop_service foundation 2>/dev/null || true"
"$HDC" -t "$SERIAL" shell "mkdir -p $TMP"

echo "[*] Push patched binaries"
"$HDC" -t "$SERIAL" file send "$SRC/$ABILITY_SRC" "$TMP/libabilityms.z.so"
"$HDC" -t "$SERIAL" file send "$SRC/$APPMS_SRC"      "$TMP/libappms.z.so"
"$HDC" -t "$SERIAL" file send "$SRC/$CLIENT_SRC"    "$TMP/libappspawn_client.z.so"

echo "[*] Install and verify on-disk identity"
"$HDC" -t "$SERIAL" shell "
set -e
cp $TMP/libabilityms.z.so    /system/lib64/platformsdk/libabilityms.z.so
cp $TMP/libappms.z.so        /system/lib64/platformsdk/libappms.z.so
cp $TMP/libappspawn_client.z.so /system/lib64/libappspawn_client.z.so
chmod 644 /system/lib64/platformsdk/libabilityms.z.so
chmod 644 /system/lib64/platformsdk/libappms.z.so
chmod 644 /system/lib64/libappspawn_client.z.so
restorecon /system/lib64/platformsdk/libabilityms.z.so
restorecon /system/lib64/platformsdk/libappms.z.so
restorecon /system/lib64/libappspawn_client.z.so
sync
sha256sum /system/lib64/platformsdk/libabilityms.z.so /system/lib64/platformsdk/libappms.z.so /system/lib64/libappspawn_client.z.so
"

echo "[*] Reboot"
"$HDC" -t "$SERIAL" target boot

echo "[*] Wait for device"
for i in $(seq 1 90); do
    if "$HDC" -t "$SERIAL" shell "echo UP" 2>/dev/null | grep -q UP; then
        echo "device back after $((i*3))s"
        break
    fi
    sleep 3
done

echo "[*] Postboot mount, identity and AppSpawnX socket check"
"$HDC" -t "$SERIAL" target mount
"$HDC" -t "$SERIAL" shell "
sha256sum /system/lib64/platformsdk/libabilityms.z.so /system/lib64/platformsdk/libappms.z.so /system/lib64/libappspawn_client.z.so
ls -l /dev/unix/socket/AppSpawnX 2>/dev/null || echo 'AppSpawnX socket MISSING'
getenforce
"

echo "[*] Set AMS tuning parameters"
"$HDC" -t "$SERIAL" shell "
param set persist.sys.abilityms.support_anco_app true
param set persist.sys.abilityms.timeout_unit_time_ratio 20
param set ro.product.cpu.abilist arm64-v8a
param set ro.product.cpu.abilist64 arm64-v8a
"

echo "[*] Run AonB smoke probes"
export D600_SERIAL="$SERIAL"
export WORKDIR="$RUN_DIR/probes"
export APK_DIR="/opt/Bridge/.work/d600-deploy-merged-20260726"
export PROBE_DIR="$ADAPTER_ROOT/src/adapter/verification/out"

bash "$ADAPTER_ROOT/src/adapter/verification/aonb_d600_probe.sh" g7 || true
bash "$ADAPTER_ROOT/src/adapter/verification/aonb_d600_probe.sh" g13 || true
bash "$ADAPTER_ROOT/src/adapter/verification/aonb_d600_probe.sh" g5 || true
bash "$ADAPTER_ROOT/src/adapter/verification/aonb_d600_probe.sh" g12 || true

echo "=== Done: evidence in $RUN_DIR ==="
