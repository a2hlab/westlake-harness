#!/bin/zsh
set -eu

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
SERIAL=654b3a6b00000000000000000824012c
BRIDGE_ROOT=/opt/Bridge
ADAPTER=$BRIDGE_ROOT/src/adapter
RUNTIME=$ADAPTER/out/helloworld-r18-v7-ams-parent-bound-subwindow-art64-20260725T0050HKT
SYSTEM_ANDROID=$RUNTIME/systemandroid
CFG=$ADAPTER/framework/appspawn-x/config/appspawn_x.cfg
REMOTE_SYSTEM_ANDROID=/data/a64deploy/alexbridge-r18-parent-only-654b3a6b/systemandroid
RUN_ID=deploy-r18-parent-only-654b3a6b-20260725-r1
EVIDENCE=$BRIDGE_ROOT/evidence/concepts/fn08-fn12-d600-early/$RUN_ID/$SERIAL

mkdir -p "$EVIDENCE"

dev()
{
    "$HDC" -t "$SERIAL" shell "$1"
}

local_hash()
{
    /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'
}

device_hash()
{
    dev "sha256sum $1" | /usr/bin/awk '{print $1}'
}

EXPECTED_APPSPAWN=$(local_hash "$RUNTIME/bin/appspawn-x")
EXPECTED_CFG=$(local_hash "$CFG")
EXPECTED_ART=$(local_hash "$SYSTEM_ANDROID/lib64/libart.so")
EXPECTED_BRIDGE=$(local_hash "$SYSTEM_ANDROID/lib64/liboh_adapter_bridge.so")
EXPECTED_BOOT=$(local_hash "$SYSTEM_ANDROID/framework/arm64/boot.art")
EXPECTED_FONTS=$(local_hash "$SYSTEM_ANDROID/etc/fonts.xml")

[[ "$(dev 'param get const.ohos.fullname' | /usr/bin/tr -d '\r ')" == "OpenHarmony-6.1.0.31" ]]
[[ "$(dev 'getenforce' | /usr/bin/tr -d '\r ')" == "Enforcing" ]]
[[ -z "$(dev 'pidof appspawn-x || true' | /usr/bin/tr -d '\r ')" ]]
[[ "$(device_hash /system/bin/appspawn-x)" == "$EXPECTED_APPSPAWN" ]]
[[ "$(device_hash /system/etc/init/appspawn_x.cfg)" == "$EXPECTED_CFG" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/libart.so")" == "$EXPECTED_ART" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/liboh_adapter_bridge.so")" == "$EXPECTED_BRIDGE" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/framework/arm64/boot.art")" == "$EXPECTED_BOOT" ]]

"$HDC" -t "$SERIAL" target mount
dev "begetctl stop_service appspawn-x 2>/dev/null || true"
dev "mkdir -p /system/android"
dev "umount /system/android 2>/dev/null || true"
dev "mount --bind $REMOTE_SYSTEM_ANDROID /system/android"
dev "if [ -f /system/android/framework/arm64/boot.art ] && [ ! -e /system/android/framework/boot.art ]; then ln -sf arm64/boot.art /system/android/framework/boot.art; fi"

dev "find /system/android -exec chcon u:object_r:system_file:s0 {} \\;"
dev "find /system/android/lib64 -exec chcon u:object_r:system_lib_file:s0 {} \\;"
dev "for f in /system/android/framework/arm64/boot*.art /system/android/framework/arm64/boot*.oat /system/android/framework/arm64/boot*.vdex; do chcon u:object_r:system_lib_file:s0 \$f; done"
dev "chcon u:object_r:system_fonts_file:s0 /system/android/etc/fonts.xml"
dev "cp /system/android/etc/fonts.xml /system/etc/fonts.xml"
dev "chcon u:object_r:system_fonts_file:s0 /system/etc/fonts.xml"
dev "chmod -R 0755 /system/android/framework"
dev "setenforce 1"
dev "param set persist.sys.abilityms.timeout_unit_time_ratio 20"
dev "param set ro.product.cpu.abilist arm64-v8a"
dev "param set ro.product.cpu.abilist64 arm64-v8a"
dev "sync"

[[ "$(device_hash /system/android/lib64/libart.so)" == "$EXPECTED_ART" ]]
[[ "$(device_hash /system/android/lib64/liboh_adapter_bridge.so)" == "$EXPECTED_BRIDGE" ]]
[[ "$(device_hash /system/android/framework/arm64/boot.art)" == "$EXPECTED_BOOT" ]]
[[ "$(device_hash /system/etc/fonts.xml)" == "$EXPECTED_FONTS" ]]
[[ -z "$(dev 'pidof appspawn-x || true' | /usr/bin/tr -d '\r ')" ]]

dev "
cat /proc/sys/kernel/random/boot_id
getenforce
cat /proc/uptime
pidof appspawn-x || true
sha256sum \
  /system/bin/appspawn-x \
  /system/etc/init/appspawn_x.cfg \
  /system/android/lib64/libart.so \
  /system/android/lib64/liboh_adapter_bridge.so \
  /system/android/framework/arm64/boot.art \
  /system/etc/fonts.xml
ls -ldZ \
  /system/android \
  /system/android/framework \
  /system/android/framework/arm64 \
  /system/android/lib64
ls -lZ \
  /system/bin/appspawn-x \
  /system/etc/init/appspawn_x.cfg \
  /system/android/framework/arm64/boot.art \
  /system/android/framework/arm64/boot.oat \
  /system/android/framework/arm64/boot.vdex \
  /system/android/lib64/libart.so \
  /system/android/lib64/liboh_adapter_bridge.so \
  /system/android/etc/fonts.xml \
  /system/etc/fonts.xml
ls -lZ /dev/unix/socket/AppSpawnX 2>/dev/null || true
grep AppSpawnX /proc/net/unix 2>/dev/null || true
find /sys/fs/pstore -maxdepth 1 -type f -print
" >"$EVIDENCE/post-deploy-receipt.txt"

{
    print "experiment: r18-parent-only-deploy"
    print "verdict: PASS"
    print "risk: R1_REVERSIBLE_DEVICE_WRITE"
    print "device_serial: $SERIAL"
    print "appspawn_started: false"
    print "apk_installed: false"
    print "route_libraries_replaced: false"
    print "claim_boundary: HASH_AND_LABEL_CLOSED_PARENT_PREREQUISITES_ONLY"
} >"$EVIDENCE/DEPLOY-VERDICT.yaml"

print "PASS: parent-only r18 finalized without starting appspawn-x"
print "Evidence=$EVIDENCE"
