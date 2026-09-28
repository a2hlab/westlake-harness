#!/usr/bin/env zsh
set -eu

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
TARGET="${1:-5583f5be00000000000000000323012c}"
ROOT=/opt/Bridge
SHORT="${TARGET:0:4}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

RUN=/opt/Bridge/evidence/runs/helloworld-hanbing-v2-cfi-resource-r6-20260724
CLOSURE=$RUN/runtime-closure-winning-art64
SYSTEM_ANDROID=$CLOSURE/systemandroid
ARTIFACTS=$RUN/artifacts
CFG=$ROOT/src/adapter/framework/appspawn-x/config/appspawn_x.cfg

REMOTE_GENERATION="/data/a64deploy/fn0103-appspawnx-$SHORT"
REMOTE_SYSTEM_ANDROID="$REMOTE_GENERATION/systemandroid"
STAGE="/data/local/tmp/fn0103-appspawnx-$SHORT-$TS"
EVIDENCE="$ROOT/evidence/runs/fn01-fn03-appspawnx-recover-$SHORT-$TS"

mkdir -p "$EVIDENCE"

dev()
{
    "$HDC" -t "$TARGET" shell "$1"
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
        if "$HDC" list targets | /usr/bin/awk -v serial="$TARGET" \
            '$1 == serial { found=1 } END { exit !found }'; then
            probe=$(dev "echo ok" 2>&1 || true)
            if [[ "$probe" == "ok" ]]; then
                return 0
            fi
        fi
        sleep 1
    done
    print -u2 "ERROR: $TARGET did not return"
    return 1
}

EXPECTED_INSTALLER=a015fb78185b6490041e5ac8187ed87363e79517ccba7040c51f06a926d3e30c
EXPECTED_BMS=f8ef078df8a0fa483b60c1a997831a8190448545e141b9568fb14eacaf9da105
EXPECTED_INSTALLS=2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0
EXPECTED_ART=69096c9e3ea9b6b376c11fd5a77705792698a80fa2f66b0242e633eef8b8ecdc
EXPECTED_APPSPAWN=2987e27fd0bbcf7df35d4a1c67054765fcc95ca08b424d1fdde96d50ba30253a
EXPECTED_CFG=f50ae8fbf36ccbd6c0ba2ce36489b9dfb0aadc5f848fb421d184e866a15605a0
EXPECTED_MUSL=fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2

{
    print "target=$TARGET"
    print "run_dir=$EVIDENCE"
    print "remote_generation=$REMOTE_GENERATION"
    print "cfg=$CFG"
    print "system_android=$SYSTEM_ANDROID"
    date -u
} >"$EVIDENCE/METADATA.txt"

[[ "$(local_hash "$ARTIFACTS/libapk_installer.so")" == "$EXPECTED_INSTALLER" ]]
[[ "$(local_hash "$ARTIFACTS/libbms.z.so")" == "$EXPECTED_BMS" ]]
[[ "$(local_hash "$ARTIFACTS/libinstalls.z.so")" == "$EXPECTED_INSTALLS" ]]
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libart.so")" == "$EXPECTED_ART" ]]
[[ "$(local_hash "$CLOSURE/bin/appspawn-x")" == "$EXPECTED_APPSPAWN" ]]
[[ "$(local_hash "$CFG")" == "$EXPECTED_CFG" ]]

boot_file_count=$(/usr/bin/find "$SYSTEM_ANDROID/framework/arm64" -maxdepth 1 -type f | /usr/bin/wc -l | /usr/bin/tr -d ' ')
[[ "$boot_file_count" == "27" ]]

wait_for_device
dev "cat /proc/sys/kernel/random/boot_id; param get const.ohos.fullname; getenforce; cat /proc/uptime; find /sys/fs/pstore -maxdepth 1 -type f -print" \
    >"$EVIDENCE/pre-recover-identity.txt"

"$HDC" -t "$TARGET" target mount >"$EVIDENCE/target-mount-1.txt" 2>&1
dev "mkdir -p $STAGE $REMOTE_GENERATION /system/etc/init"
"$HDC" -t "$TARGET" file send "$SYSTEM_ANDROID" "$REMOTE_GENERATION" >"$EVIDENCE/send-systemandroid.txt" 2>&1
"$HDC" -t "$TARGET" file send "$CLOSURE/bin/appspawn-x" "$STAGE/appspawn-x" >"$EVIDENCE/send-appspawn-x.txt" 2>&1
"$HDC" -t "$TARGET" file send "$CFG" "$STAGE/appspawn_x.cfg" >"$EVIDENCE/send-appspawn-cfg.txt" 2>&1
"$HDC" -t "$TARGET" file send "$ARTIFACTS/libapk_installer.so" "$STAGE/libapk_installer.so" >"$EVIDENCE/send-libapk-installer.txt" 2>&1
"$HDC" -t "$TARGET" file send "$ARTIFACTS/libbms.z.so" "$STAGE/libbms.z.so" >"$EVIDENCE/send-libbms.txt" 2>&1
"$HDC" -t "$TARGET" file send "$ARTIFACTS/libinstalls.z.so" "$STAGE/libinstalls.z.so" >"$EVIDENCE/send-libinstalls.txt" 2>&1

dev "begetctl stop_service appspawn-x 2>/dev/null || true"
dev "cp $STAGE/libapk_installer.so /system/lib64/libapk_installer.so"
dev "cp $STAGE/libbms.z.so /system/lib64/libbms.z.so"
dev "cp $STAGE/libinstalls.z.so /system/lib64/libinstalls.z.so"
dev "cp $STAGE/appspawn-x /system/bin/appspawn-x"
dev "cp $STAGE/appspawn_x.cfg /system/etc/init/appspawn_x.cfg"
dev "ln -sf /lib/ld-musl-aarch64.so.1 /system/lib/libc_musl.so"
dev "chown root:root /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/bin/appspawn-x /system/etc/init/appspawn_x.cfg"
dev "chmod 0755 /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/bin/appspawn-x"
dev "chmod 0550 /system/etc/init/appspawn_x.cfg"
dev "restorecon -F /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so 2>/dev/null || true"
dev "chcon u:object_r:appspawn_exec:s0 /system/bin/appspawn-x 2>/dev/null || restorecon -F /system/bin/appspawn-x"
dev "chcon u:object_r:system_etc_file:s0 /system/etc/init/appspawn_x.cfg 2>/dev/null || restorecon -F /system/etc/init/appspawn_x.cfg"
dev "chcon -h u:object_r:system_lib_file:s0 /system/lib/libc_musl.so 2>/dev/null || true"

[[ "$(device_hash /system/lib64/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]]
[[ "$(device_hash /system/lib64/libbms.z.so)" == "$EXPECTED_BMS" ]]
[[ "$(device_hash /system/lib64/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]]
[[ "$(device_hash /system/bin/appspawn-x)" == "$EXPECTED_APPSPAWN" ]]
[[ "$(device_hash /system/etc/init/appspawn_x.cfg)" == "$EXPECTED_CFG" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/libart.so")" == "$EXPECTED_ART" ]]
[[ "$(device_hash /system/lib/ld-musl-aarch64.so.1)" == "$EXPECTED_MUSL" ]]
dev "readlink -f /system/lib/libc_musl.so; sha256sum /system/lib/libc_musl.so /system/lib/ld-musl-aarch64.so.1" \
    >"$EVIDENCE/pre-reboot-musl-receipt.txt"
dev "sync"

"$HDC" -t "$TARGET" target boot >"$EVIDENCE/target-boot.txt" 2>&1 || true
wait_for_device
sleep 12

"$HDC" -t "$TARGET" target mount >"$EVIDENCE/target-mount-2.txt" 2>&1
dev "mkdir -p /system/android"
dev "umount /system/android 2>/dev/null || true"
dev "mount --bind $REMOTE_SYSTEM_ANDROID /system/android"
dev "if [ -f /system/android/framework/arm64/boot.art ] && [ ! -e /system/android/framework/boot.art ]; then ln -sf arm64/boot.art /system/android/framework/boot.art; fi"
dev "find /system/android -exec chcon u:object_r:system_file:s0 {} \\;"
dev "find /system/android/lib64 -exec chcon u:object_r:system_lib_file:s0 {} \\;"
dev "for f in /system/android/framework/arm64/boot*.art /system/android/framework/arm64/boot*.oat /system/android/framework/arm64/boot*.vdex; do chcon u:object_r:system_lib_file:s0 \$f; done"
dev "cp /system/android/etc/fonts.xml /system/etc/fonts.xml"
dev "chcon u:object_r:system_fonts_file:s0 /system/android/etc/fonts.xml /system/etc/fonts.xml 2>/dev/null || true"
dev "ln -sf /lib/ld-musl-aarch64.so.1 /system/lib/libc_musl.so"
dev "chcon -h u:object_r:system_lib_file:s0 /system/lib/libc_musl.so 2>/dev/null || true"
dev "setenforce 0"
dev "power-shell wakeup; power-shell timeout -o 86400000; power-shell display -o 230"
dev "sync"

dev "
cat /proc/sys/kernel/random/boot_id
param get const.ohos.fullname
getenforce
cat /proc/uptime
pidof appspawn-x || true
sha256sum \
  /system/bin/appspawn-x \
  /system/etc/init/appspawn_x.cfg \
  /system/android/lib64/libart.so \
  /system/lib64/libapk_installer.so \
  /system/lib64/libbms.z.so \
  /system/lib64/libinstalls.z.so \
  /system/lib/ld-musl-aarch64.so.1 \
  /system/lib/libc_musl.so
readlink -f /system/lib/libc_musl.so
grep -n cgroup /system/etc/init/appspawn_x.cfg
ls -ldZ /system/android /system/android/framework /system/android/framework/arm64 /system/android/lib64
ls -lZ /system/bin/appspawn-x /system/etc/init/appspawn_x.cfg /system/lib/libc_musl.so /dev/unix/socket/AppSpawnX 2>/dev/null || true
grep AppSpawnX /proc/net/unix 2>/dev/null || true
cat /proc/cgroups
mount | grep cgroup
find /sys/fs/pstore -maxdepth 1 -type f -print
" >"$EVIDENCE/post-recover-receipt.txt"

[[ "$(device_hash /system/bin/appspawn-x)" == "$EXPECTED_APPSPAWN" ]]
[[ "$(device_hash /system/etc/init/appspawn_x.cfg)" == "$EXPECTED_CFG" ]]
[[ "$(device_hash /system/android/lib64/libart.so)" == "$EXPECTED_ART" ]]
[[ "$(device_hash /system/lib64/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]]
[[ "$(device_hash /system/lib64/libbms.z.so)" == "$EXPECTED_BMS" ]]
[[ "$(device_hash /system/lib64/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]]
[[ "$(device_hash /system/lib/libc_musl.so)" == "$EXPECTED_MUSL" ]]

socket_receipt=$(dev "ls -lZ /dev/unix/socket/AppSpawnX 2>/dev/null || true")
{
    print "experiment: fn01-fn03-appspawnx-recover"
    print "target: $TARGET"
    print "device_write: true"
    print "rebooted: true"
    print "cfg_cgroup_false: true"
    print "libc_musl_symlink_arm64: true"
    if [[ -n "$socket_receipt" ]]; then
        print "appspawnx_socket_present: true"
    else
        print "appspawnx_socket_present: false"
    fi
    print "verdict: PASS"
    print "claim_boundary: APP_SPAWN_X_PARENT_PREREQS_ONLY"
} >"$EVIDENCE/RECOVER-VERDICT.yaml"

print "PASS: fn01-fn03 appspawn-x prerequisites recovered"
print "Evidence=$EVIDENCE"
