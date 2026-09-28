#!/usr/bin/env zsh
set -eu

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
TARGET="${1:?Usage: $0 <device-serial>}"
ROOT=/opt/Bridge
SRC=/opt/Bridge/.work/d600-deploy-no-hardcode-20260726T230022Z
SYSTEM_ANDROID=$SRC/system/android
CFG=/opt/Bridge/src/adapter/framework/appspawn-x/config/appspawn_x.cfg
APK=$SRC/HelloWorld.apk
SHORT="${TARGET:0:8}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
REMOTE_GENERATION="/data/a64deploy/fn0103-r18-merged-$SHORT"
REMOTE_SYSTEM_ANDROID="$REMOTE_GENERATION/android"
EVIDENCE="$ROOT/evidence/runs/fn01-fn03-r18-runtime-recover-$SHORT-$TS"

dev() { "$HDC" -t "$TARGET" shell "$1"; }

mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/script.log")
exec 2>&1

{
    print "target=$TARGET"
    print "timestamp=$TS"
    print "src=$SRC"
} >"$EVIDENCE/METADATA.txt"

print "[*] Mount /system rw and push runtime overlay"
"$HDC" -t "$TARGET" target mount

# Ensure SELinux permissive for AonB bring-up
dev "setenforce 0"

# Parameters needed for AMS to route Android apps to appspawn-x
dev "param set persist.sys.abilityms.support_anco_app true"
dev "param set persist.sys.abilityms.timeout_unit_time_ratio 20"
dev "param set ro.product.cpu.abilist arm64-v8a"
dev "param set ro.product.cpu.abilist64 arm64-v8a"

# Push runtime overlay to /data if not present, then bind-mount
STAGE="/data/local/tmp/fn0103-recover-$SHORT-$TS"
dev "mkdir -p $STAGE $REMOTE_GENERATION /system/android"
"$HDC" -t "$TARGET" file send "$SYSTEM_ANDROID" "$REMOTE_GENERATION" >"$EVIDENCE/send-systemandroid.txt" 2>&1
"$HDC" -t "$TARGET" file send "$ROOT/src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/frozen/runtime_provider/provider-v12/providers/liblzma.so" "$STAGE/liblzma.so" >"$EVIDENCE/send-liblzma.txt" 2>&1
dev "mkdir -p $REMOTE_GENERATION/android/lib64"
dev "cp $STAGE/liblzma.so $REMOTE_GENERATION/android/lib64/liblzma.so"
dev "umount /system/android 2>/dev/null || true"
dev "mount --bind $REMOTE_SYSTEM_ANDROID /system/android"
dev "if [ -f /system/android/framework/arm64/boot.art ] && [ ! -e /system/android/framework/boot.art ]; then ln -sf arm64/boot.art /system/android/framework/boot.art; fi"

# Permissions / contexts
dev "find /system/android -exec chcon u:object_r:system_file:s0 {} \;"
dev "find /system/android/lib64 -exec chcon u:object_r:system_lib_file:s0 {} \;"
dev "for f in /system/android/framework/arm64/boot*.art /system/android/framework/arm64/boot*.oat /system/android/framework/arm64/boot*.vdex; do chcon u:object_r:system_lib_file:s0 \$f; done"
dev "chcon u:object_r:system_fonts_file:s0 /system/android/etc/fonts.xml"
dev "cp /system/android/etc/fonts.xml /system/etc/fonts.xml"
dev "chcon u:object_r:system_fonts_file:s0 /system/etc/fonts.xml 2>/dev/null || true"
dev "ln -sf /lib/ld-musl-aarch64.so.1 /system/lib/libc_musl.so"
dev "chcon -h u:object_r:system_lib_file:s0 /system/lib/libc_musl.so 2>/dev/null || true"

print "[*] Restart appspawn-x with updated cfg"
dev "cp $CFG /system/etc/init/appspawn_x.cfg"
dev "chmod 0550 /system/etc/init/appspawn_x.cfg"
dev "chcon u:object_r:system_etc_file:s0 /system/etc/init/appspawn_x.cfg 2>/dev/null || restorecon -F /system/etc/init/appspawn_x.cfg"
dev "begetctl stop_service appspawn-x >/dev/null 2>&1 || true"
dev "begetctl start_service appspawn-x >/dev/null 2>&1 || true"
sleep 3
APP_SPAWN_PID=$(dev "pidof appspawn-x" | tr -d '\r' || true)
print "appspawn-x pid=$APP_SPAWN_PID"

print "[*] Install and launch HelloWorld"
"$HDC" -t "$TARGET" file send "$APK" "$STAGE/HelloWorld.apk" >"$EVIDENCE/send-apk.txt" 2>&1
dev "bm install -p $STAGE/HelloWorld.apk" >"$EVIDENCE/bm-install.txt" 2>&1 || { print "bm install failed"; }
dev "aa force-stop com.example.helloworld 2>/dev/null || true"
dev "hilog -r >/dev/null 2>&1 || true"
sleep 1
dev "power-shell wakeup; power-shell timeout -o 86400000; power-shell display -o 230" >/dev/null 2>&1 || true
dev "uinput -T -m 300 900 300 300 500" >/dev/null 2>&1 || true
dev "aa start -a com.example.helloworld.MainActivity -b com.example.helloworld" >"$EVIDENCE/aa-start.txt" 2>&1 || true
sleep 12
dev "hilog -x" >"$EVIDENCE/hilog.txt" 2>&1 || true
dev "ps -A -o PID,PPID,UID,NAME,CMDLINE | grep -E 'appspawn-x|com.example.helloworld'" >"$EVIDENCE/processes.txt" 2>&1 || true

hello_pid=$(dev "pidof com.example.helloworld" | tr -d '\r' || true)
activity_thread=$(grep -c "ActivityThread" "$EVIDENCE/hilog.txt" 2>/dev/null || true)
android_runtime=$(grep -c "AndroidRuntime" "$EVIDENCE/hilog.txt" 2>/dev/null || true)
oncreate=$(grep -c "onCreate" "$EVIDENCE/hilog.txt" 2>/dev/null || true)
appspawn_accept=$(grep -c "AppSpawnX" "$EVIDENCE/hilog.txt" 2>/dev/null || true)

{
    print "experiment: fn01-fn03-r18-runtime-recover"
    print "target: $TARGET"
    print "timestamp: $TS"
    print "appspawn_x_pid: $APP_SPAWN_PID"
    print "hello_world_pid: $hello_pid"
    print "activity_thread_hits: ${activity_thread:-0}"
    print "android_runtime_hits: ${android_runtime:-0}"
    print "oncreate_hits: ${oncreate:-0}"
    print "appspawnx_hits: ${appspawn_accept:-0}"
    print "verdict: $([[ -n "$hello_pid" && "$activity_thread" -gt 0 && "$android_runtime" -gt 0 ]] && echo PASS || echo FAIL)"
} >"$EVIDENCE/RECOVER-VERDICT.yaml"

print "Verdict: $(grep '^verdict:' "$EVIDENCE/RECOVER-VERDICT.yaml")"
print "Evidence=$EVIDENCE"
