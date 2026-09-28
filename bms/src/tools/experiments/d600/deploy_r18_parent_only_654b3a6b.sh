#!/bin/zsh
set -eu

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
SERIAL=654b3a6b00000000000000000824012c
BRIDGE_ROOT=/opt/Bridge
ADAPTER=$BRIDGE_ROOT/src/adapter
RUNTIME=$ADAPTER/out/helloworld-r18-v7-ams-parent-bound-subwindow-art64-20260725T0050HKT
SYSTEM_ANDROID=$RUNTIME/systemandroid
CFG=$ADAPTER/framework/appspawn-x/config/appspawn_x.cfg
REMOTE_GENERATION=/data/a64deploy/alexbridge-r18-parent-only-654b3a6b
REMOTE_SYSTEM_ANDROID=$REMOTE_GENERATION/systemandroid
STAGE=/data/local/tmp/alexbridge-r18-parent-only-654b3a6b
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

wait_for_device()
{
    local attempt probe
    for attempt in {1..180}; do
        if "$HDC" list targets | /usr/bin/awk -v serial="$SERIAL" \
            '$1 == serial { found=1 } END { exit !found }'; then
            probe=$(dev "echo ok" 2>&1 || true)
            if [[ "$probe" == "ok" ]]; then
                return 0
            fi
        fi
        sleep 1
    done
    print -u2 "ERROR: $SERIAL did not return after reboot"
    return 1
}

EXPECTED_APPSPAWN=$(local_hash "$RUNTIME/bin/appspawn-x")
EXPECTED_CFG=$(local_hash "$CFG")
EXPECTED_ART=$(local_hash "$SYSTEM_ANDROID/lib64/libart.so")
EXPECTED_BRIDGE=$(local_hash "$SYSTEM_ANDROID/lib64/liboh_adapter_bridge.so")
EXPECTED_BOOT=$(local_hash "$SYSTEM_ANDROID/framework/arm64/boot.art")
EXPECTED_FONTS=$(local_hash "$SYSTEM_ANDROID/etc/fonts.xml")

wait_for_device
[[ "$(dev 'param get const.ohos.fullname' | /usr/bin/tr -d '\r ')" == "OpenHarmony-6.1.0.31" ]]
[[ "$(dev 'getenforce' | /usr/bin/tr -d '\r ')" == "Enforcing" ]]
[[ -z "$(dev 'pidof appspawn-x || true' | /usr/bin/tr -d '\r ')" ]]
[[ "$(dev 'test ! -e /system/bin/appspawn-x; echo $?' | /usr/bin/tr -d '\r ')" == "0" ]]
[[ "$(dev 'test ! -e /system/android; echo $?' | /usr/bin/tr -d '\r ')" == "0" ]]

(cd "$RUNTIME" && /usr/bin/shasum -a 256 -c MANIFEST.sha256 >"$EVIDENCE/host-manifest-check.txt")
{
    print "appspawn-x $EXPECTED_APPSPAWN"
    print "appspawn_x.cfg $EXPECTED_CFG"
    print "libart.so $EXPECTED_ART"
    print "liboh_adapter_bridge.so $EXPECTED_BRIDGE"
    print "boot.art $EXPECTED_BOOT"
    print "fonts.xml $EXPECTED_FONTS"
} >"$EVIDENCE/expected-hashes.txt"

dev "cat /proc/sys/kernel/random/boot_id; getenforce; cat /proc/uptime; find /sys/fs/pstore -maxdepth 1 -type f -print" \
    >"$EVIDENCE/pre-deploy-identity.txt"

"$HDC" -t "$SERIAL" target mount
dev "mkdir -p $REMOTE_GENERATION $STAGE /system/etc/init"
"$HDC" -t "$SERIAL" file send "$SYSTEM_ANDROID" "$REMOTE_GENERATION"
"$HDC" -t "$SERIAL" file send "$RUNTIME/bin/appspawn-x" "$STAGE/appspawn-x"
"$HDC" -t "$SERIAL" file send "$CFG" "$STAGE/appspawn_x.cfg"

dev "begetctl stop_service appspawn-x 2>/dev/null || true"
dev "cp $STAGE/appspawn-x /system/bin/appspawn-x"
dev "cp $STAGE/appspawn_x.cfg /system/etc/init/appspawn_x.cfg"
dev "chown root:root /system/bin/appspawn-x /system/etc/init/appspawn_x.cfg"
dev "chmod 0755 /system/bin/appspawn-x"
dev "chmod 0550 /system/etc/init/appspawn_x.cfg"
dev "chcon u:object_r:appspawn_exec:s0 /system/bin/appspawn-x"
dev "chcon u:object_r:system_etc_file:s0 /system/etc/init/appspawn_x.cfg"

[[ "$(device_hash /system/bin/appspawn-x)" == "$EXPECTED_APPSPAWN" ]]
[[ "$(device_hash /system/etc/init/appspawn_x.cfg)" == "$EXPECTED_CFG" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/libart.so")" == "$EXPECTED_ART" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/liboh_adapter_bridge.so")" == "$EXPECTED_BRIDGE" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/framework/arm64/boot.art")" == "$EXPECTED_BOOT" ]]
dev "sync"

"$HDC" -t "$SERIAL" target boot || true
wait_for_device
sleep 8

"$HDC" -t "$SERIAL" target mount
dev "begetctl stop_service appspawn-x 2>/dev/null || true"
dev "mkdir -p /system/android"
dev "umount /system/android 2>/dev/null || true"
dev "mount --bind $REMOTE_SYSTEM_ANDROID /system/android"
dev "if [ -f /system/android/framework/arm64/boot.art ] && [ ! -e /system/android/framework/boot.art ]; then ln -sf arm64/boot.art /system/android/framework/boot.art; fi"

# Reconstruct the SELinux labels that the generation would have under the
# system partition. The stock image has a lib rule but no ARM64 lib64 rule.
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

print "PASS: parent-only r18 deployed without starting appspawn-x"
print "Evidence=$EVIDENCE"
