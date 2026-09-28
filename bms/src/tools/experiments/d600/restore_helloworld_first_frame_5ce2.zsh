#!/bin/zsh
set -euo pipefail

# Developer-only fast restore for the D600 that retains the Run28 device-local
# backups. This restores an already observed historical generation; it does not
# build a new generation from the repository and must not be used as a formal
# Journey PASS.

readonly DEFAULT_SERIAL="5ce2dcee00000000000000000923012c"
readonly SERIAL="${1:-$DEFAULT_SERIAL}"
readonly HDC_BIN="${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
readonly GENERATION="74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d"
readonly ANDROID_ROOT_BACKUP="/data/a64deploy/helloworld-f057d797f1daf51dec2d48e45be719437716f0719c75267ab7b4075fc4954e93-5ce2dcee/android"
readonly ROUTE_BACKUP="/data/local/tmp/p0-run27-old-route-a-backup/$GENERATION"
readonly RUN28L_STAGE="/data/local/tmp/p0-run28l-stage"
readonly OVERLAY="/data/local/tmp/p0-restored-helloworld-live"
readonly ROUTE_TARGET="/system/lib64/westlake/route-a/$GENERATION"
readonly APK="/data/app/el1/bundle/public/com.example.helloworld/android/base.apk"

if [[ ! -x "$HDC_BIN" ]]; then
  print -u2 "HDC executable not found: $HDC_BIN"
  exit 2
fi

dev() {
  "$HDC_BIN" -t "$SERIAL" shell "$1"
}

remote_hash() {
  dev "sha256sum '$1'" | /usr/bin/awk 'NR == 1 {gsub(/\r/, "", $1); print $1}'
}

expect_hash() {
  local path="$1"
  local expected="$2"
  local actual
  actual="$(remote_hash "$path")"
  if [[ "$actual" != "$expected" ]]; then
    print -u2 "identity mismatch: $path"
    print -u2 "  expected=$expected"
    print -u2 "  actual=$actual"
    exit 3
  fi
}

print "Preflight: serial=$SERIAL generation=$GENERATION"
dev "test -d '$ANDROID_ROOT_BACKUP' && test -d '$ROUTE_BACKUP' && test -d '$RUN28L_STAGE' && test -f '$APK'"
expect_hash "$RUN28L_STAGE/appspawn-x" "c7fd4bd6f7474841eccf93687009e79748fbd7016a208faed0a70ea580a2976e"
expect_hash "$RUN28L_STAGE/libwestlake_android_child.z.so" "f9a36217ebf8a6d08a239d8412be540d9f8cf0ebe9614bfc9486890954d8a828"
expect_hash "$RUN28L_STAGE/libwestlake_android_runtime_provider.so" "9c650fe37734d8aa29f0abe954021153f831db3c264c35aca7c02b07ce26dc1d"
expect_hash "$RUN28L_STAGE/liboh_adapter_bridge.so" "7db99e1b760cf843b1a99db1382a3299f189c8cbca786ec411b7c35a2af6ffb9"
expect_hash "$ANDROID_ROOT_BACKUP/lib64/libart.so" "59e1bb45294b9dd587dc9b81bad719b60675aa98c9c6cfced426449bcad0fe5f"
expect_hash "$ANDROID_ROOT_BACKUP/lib64/liboh_android_runtime.so" "9689ce764083b4f6db848b036ff292cdd4962ecb2e1ca26373850390efb42812"
expect_hash "$ROUTE_BACKUP/liblzma.so" "239bdf61bcc8c971ef65c6e688c87048d01781d4ab8707546668f5d5e4cc7d40"
expect_hash "$APK" "2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd"

app_uid="$(dev "bm dump -n com.example.helloworld" |
  /usr/bin/awk -F: '/^[[:space:]]*"uid": [0-9]+/ {gsub(/[ ,\r]/, "", $2); print $2; exit}')"
if [[ ! "$app_uid" =~ '^[0-9]+$' ]]; then
  print -u2 "Unable to resolve HelloWorld uid from bm dump: $app_uid"
  exit 4
fi

local_tmp="$(mktemp -d "${TMPDIR:-/tmp}/bridge-p0-restore.XXXXXX")"
cleanup() {
  [[ -n "${local_tmp:-}" && -d "$local_tmp" ]] && rm -rf -- "$local_tmp"
}
trap cleanup EXIT INT TERM

dev "mkdir -p '$OVERLAY'"

# The retained Run28 Java adapter uses /data/app/el2/... as ApplicationInfo.dataDir,
# while the current OH sandbox only exposes the same directory at
# /data/storage/el2/base. Disable this developer sandbox layer for the display
# restore. Product reproduction must instead close the path mapping in the
# generated implementation.
"$HDC_BIN" -t "$SERIAL" file recv \
  /system/etc/sandbox/appdata-sandbox.json "$local_tmp/appdata-sandbox.json"
/usr/bin/perl -0pi -e \
  's/"top-sandbox-switch"\s*:\s*"(?:ON|OFF)"/"top-sandbox-switch": "OFF"/' \
  "$local_tmp/appdata-sandbox.json"
/usr/bin/grep -q '"top-sandbox-switch": "OFF"' "$local_tmp/appdata-sandbox.json"
"$HDC_BIN" -t "$SERIAL" file send \
  "$local_tmp/appdata-sandbox.json" "$OVERLAY/appdata-sandbox-off.json" 2>/dev/null || {
  dev "mkdir -p '$OVERLAY'"
  "$HDC_BIN" -t "$SERIAL" file send \
    "$local_tmp/appdata-sandbox.json" "$OVERLAY/appdata-sandbox-off.json"
}

print "Restore: materialize identity-checked overlay and bind exact targets"
dev "begetctl stop_service appspawn-x 2>/dev/null || true
mkdir -p '$OVERLAY' '$ROUTE_TARGET'
cp '$RUN28L_STAGE/appspawn-x' '$OVERLAY/appspawn-x'
cp '$RUN28L_STAGE/libwestlake_android_child.z.so' '$OVERLAY/libwestlake_android_child.z.so'
cp '$RUN28L_STAGE/libwestlake_android_runtime_provider.so' '$OVERLAY/libwestlake_android_runtime_provider.so'
cp '$RUN28L_STAGE/liboh_adapter_bridge.so' '$OVERLAY/liboh_adapter_bridge.so'
chown root:root '$OVERLAY/appspawn-x' '$OVERLAY/libwestlake_android_child.z.so' '$OVERLAY/libwestlake_android_runtime_provider.so' '$OVERLAY/liboh_adapter_bridge.so' '$OVERLAY/appdata-sandbox-off.json'
chmod 0755 '$OVERLAY/appspawn-x' '$OVERLAY/libwestlake_android_child.z.so'
chmod 0644 '$OVERLAY/libwestlake_android_runtime_provider.so' '$OVERLAY/liboh_adapter_bridge.so' '$OVERLAY/appdata-sandbox-off.json'
chcon u:object_r:appspawn_exec:s0 '$OVERLAY/appspawn-x'
chcon u:object_r:system_lib_file:s0 '$OVERLAY/libwestlake_android_child.z.so' '$OVERLAY/libwestlake_android_runtime_provider.so' '$OVERLAY/liboh_adapter_bridge.so'
chcon u:object_r:system_file:s0 '$OVERLAY/appdata-sandbox-off.json'
umount /system/android/lib64/liblzma.so 2>/dev/null || true
umount /system/android/lib64/liboh_adapter_bridge.so 2>/dev/null || true
umount '$ROUTE_TARGET/libwestlake_android_runtime_provider.so' 2>/dev/null || true
umount '$ROUTE_TARGET' 2>/dev/null || true
umount /system/lib64/appspawn/libwestlake_android_child.z.so 2>/dev/null || true
umount /system/bin/appspawn-x 2>/dev/null || true
umount /system/etc/sandbox/appdata-sandbox.json 2>/dev/null || true
umount /system/android 2>/dev/null || true
mount --bind '$ANDROID_ROOT_BACKUP' /system/android
mount --bind '$ROUTE_BACKUP' '$ROUTE_TARGET'
mount --bind '$OVERLAY/libwestlake_android_runtime_provider.so' '$ROUTE_TARGET/libwestlake_android_runtime_provider.so'
mount --bind '$OVERLAY/liboh_adapter_bridge.so' /system/android/lib64/liboh_adapter_bridge.so
mount --bind '$ROUTE_TARGET/liblzma.so' /system/android/lib64/liblzma.so
mount --bind '$OVERLAY/libwestlake_android_child.z.so' /system/lib64/appspawn/libwestlake_android_child.z.so
mount --bind '$OVERLAY/appspawn-x' /system/bin/appspawn-x
mount --bind '$OVERLAY/appdata-sandbox-off.json' /system/etc/sandbox/appdata-sandbox.json
mkdir -p /data/app/el2/100/base/com.example.helloworld/cache /data/app/el2/100/base/com.example.helloworld/code_cache /data/app/el2/100/base/com.example.helloworld/files /data/app/el2/100/base/com.example.helloworld/databases /data/app/el2/100/base/com.example.helloworld/shared_prefs /data/app/el2/100/base/com.example.helloworld/no_backup
chown -R '$app_uid:$app_uid' /data/app/el2/100/base/com.example.helloworld
chmod 0700 /data/app/el2/100/base/com.example.helloworld /data/app/el2/100/base/com.example.helloworld/*
chcon -R u:object_r:appdat:s0 /data/app/el2/100/base/com.example.helloworld
param set persist.sys.abilityms.support_anco_app true
param set persist.sys.abilityms.timeout_unit_time_ratio 20
param set persist.sys.prefork.enable false
param set ro.product.cpu.abilist arm64-v8a
param set ro.product.cpu.abilist64 arm64-v8a
chmod 0666 /dev/mali0
power-shell timeout -o 86400000
power-shell wakeup
begetctl start_service appspawn-x
sleep 2
chown root:appspawn /dev/unix/socket/AppSpawnX
chmod 0660 /dev/unix/socket/AppSpawnX
chcon u:object_r:appspawn_socket:s0 /dev/unix/socket/AppSpawnX
hilog -r
aa start -a com.example.helloworld.MainActivity -b com.example.helloworld -W"

sleep 4
readonly OUTPUT_DIR="${OUTPUT_DIR:-/tmp/bridge-p0-restored-$(date -u +%Y%m%dT%H%M%SZ)-$SERIAL}"
mkdir -p "$OUTPUT_DIR"
dev "snapshot_display -f '$OVERLAY/first-frame.jpeg'
echo serial='$SERIAL' > '$OVERLAY/final-receipt.txt'
echo generation='$GENERATION' >> '$OVERLAY/final-receipt.txt'
echo boot_id=\$(cat /proc/sys/kernel/random/boot_id) >> '$OVERLAY/final-receipt.txt'
echo app_uid='$app_uid' >> '$OVERLAY/final-receipt.txt'
param get ro.product.cpu.abilist >> '$OVERLAY/final-receipt.txt'
param get ro.product.cpu.abilist64 >> '$OVERLAY/final-receipt.txt'
ps -A -o PID,PPID,UID,NAME,CMDLINE | grep ' $app_uid ' >> '$OVERLAY/final-receipt.txt'
sha256sum /system/bin/appspawn-x /system/lib64/appspawn/libwestlake_android_child.z.so '$ROUTE_TARGET/libwestlake_android_runtime_provider.so' /system/android/lib64/liboh_adapter_bridge.so /system/android/lib64/liboh_android_runtime.so /system/android/lib64/libart.so /system/android/lib64/liblzma.so '$APK' >> '$OVERLAY/final-receipt.txt'
hilog -x > '$OVERLAY/hilog.txt'"
"$HDC_BIN" -t "$SERIAL" file recv "$OVERLAY/first-frame.jpeg" "$OUTPUT_DIR/first-frame.jpeg"
"$HDC_BIN" -t "$SERIAL" file recv "$OVERLAY/final-receipt.txt" "$OUTPUT_DIR/final-receipt.txt"
"$HDC_BIN" -t "$SERIAL" file recv "$OVERLAY/hilog.txt" "$OUTPUT_DIR/hilog.txt"
test -s "$OUTPUT_DIR/first-frame.jpeg"

print "HelloWorld restored and left in foreground on $SERIAL"
print "Developer evidence: $OUTPUT_DIR"
print "Boundary: historical device-local generation; not a clean PR build or independent PASS"
