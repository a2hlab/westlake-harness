#!/bin/bash
# deploy_fn04_full_closure_d600.sh — deploy full Fn04 AMS/BMS/AppSpawn closure
# and run lifecycle/service-stubbing/graphics/input smoke probes.
#
# Usage:
#   bash deploy_fn04_full_closure_d600.sh <serial>

set -euo pipefail

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
export PATH="$(dirname "$HDC"):$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SRC=/opt/Bridge/out/alexpc-rebuild-20260726

SERIAL="${1:-}"
if [ -z "$SERIAL" ]; then
    echo "Usage: $0 <serial>" >&2
    exit 2
fi

TS=$(date -u +%Y%m%dT%H%M%SZ)
RUN_DIR="$ADAPTER_ROOT/evidence/runs/fn04-fullclosure-${SERIAL}-${TS}"
mkdir -p "$RUN_DIR"
exec > >(tee "$RUN_DIR/deploy.log") 2>&1

declare -a FILES=(
    "libabilityms.z.so.fn04.v2:/system/lib64/platformsdk/libabilityms.z.so"
    "libappms.z.so.fn04.v2:/system/lib64/platformsdk/libappms.z.so"
    "libbms.z.so:/system/lib64/platformsdk/libbms.z.so"
    "libinstalls.z.so:/system/lib64/platformsdk/libinstalls.z.so"
    "libappspawn_client.z.so.fn04.v2:/system/lib64/libappspawn_client.z.so"
)

echo "=== Fn04 full-closure deploy: serial=$SERIAL ==="
echo "RUN_DIR=$RUN_DIR"

for entry in "${FILES[@]}"; do
    srcf="${entry%%:*}"
    [ -f "$SRC/$srcf" ] || { echo "Missing artifact: $SRC/$srcf" >&2; exit 3; }
    echo " artifact $srcf sha256=$(sha256sum "$SRC/$srcf" | awk '{print $1}')"
done

TMP=/data/local/tmp/fn04-fullclosure-${TS}

echo "[*] Mount /system rw and stop foundation"
"$HDC" -t "$SERIAL" target mount
"$HDC" -t "$SERIAL" shell "begetctl stop_service foundation 2>/dev/null || true"
"$HDC" -t "$SERIAL" shell "mkdir -p $TMP"

echo "[*] Push patched binaries"
for entry in "${FILES[@]}"; do
    srcf="${entry%%:*}"
    dstf="${entry##*:}"
    name="$(basename "$dstf")"
    "$HDC" -t "$SERIAL" file send "$SRC/$srcf" "$TMP/$name"
done

echo "[*] Install files (one per shell to avoid device sh parsing issues)"
for entry in "${FILES[@]}"; do
    dstf="${entry##*:}"
    name="$(basename "$dstf")"
    "$HDC" -t "$SERIAL" shell "cp $TMP/$name $dstf && chmod 644 $dstf && restorecon $dstf"
done
"$HDC" -t "$SERIAL" shell "sync"

echo "[*] Verify on-disk identity"
for entry in "${FILES[@]}"; do
    dstf="${entry##*:}"
    "$HDC" -t "$SERIAL" shell "sha256sum $dstf"
done

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

echo "[*] Postboot setup: permissive SELinux, AMS params, unlock screen"
"$HDC" -t "$SERIAL" target mount
"$HDC" -t "$SERIAL" shell "setenforce 0"
"$HDC" -t "$SERIAL" shell "param set persist.sys.abilityms.support_anco_app true"
"$HDC" -t "$SERIAL" shell "param set persist.sys.abilityms.timeout_unit_time_ratio 20"
"$HDC" -t "$SERIAL" shell "param set ro.product.cpu.abilist arm64-v8a"
"$HDC" -t "$SERIAL" shell "param set ro.product.cpu.abilist64 arm64-v8a"
"$HDC" -t "$SERIAL" shell "uinput -T -m 300 900 300 300 500" >/dev/null 2>&1 || true
sleep 1

echo "[*] Verify identity and AppSpawnX socket"
for entry in "${FILES[@]}"; do
    dstf="${entry##*:}"
    "$HDC" -t "$SERIAL" shell "sha256sum $dstf"
done
"$HDC" -t "$SERIAL" shell "ls -l /dev/unix/socket/AppSpawnX 2>/dev/null || echo 'AppSpawnX socket MISSING'; getenforce"

echo "[*] Run AonB smoke probes (with screen kept awake)"
export D600_SERIAL="$SERIAL"
export WORKDIR="$RUN_DIR/probes"
export APK_DIR="/opt/Bridge/.work/d600-deploy-merged-20260726"
export PROBE_DIR="$ADAPTER_ROOT/src/adapter/verification/out"

wake_screen() {
    "$HDC" -t "$SERIAL" shell "uinput -T -m 300 900 300 300 500" >/dev/null 2>&1 || true
    sleep 1
}

for gate in g7 g13 g5 g12; do
    wake_screen
    bash "$ADAPTER_ROOT/src/adapter/verification/aonb_d600_probe.sh" "$gate" || true
done

echo "=== Done: evidence in $RUN_DIR ==="
