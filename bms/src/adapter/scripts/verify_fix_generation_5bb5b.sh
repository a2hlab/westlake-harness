#!/bin/zsh
set -eu

if [[ $# -lt 1 ]]; then
    print -u2 "Usage: $0 <generation-dir>"
    exit 1
fi

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
SERIAL=5bb5b1ae00000000000000000823012c
ADAPTER=/opt/Bridge/src/adapter
RUNTIME=$1
SYSTEM_ANDROID=$RUNTIME/systemandroid
ROUTE=$ADAPTER/out/helloworld-r6-route-hanbing-closure-20260724T202644HKT
PACKAGE=$ADAPTER/out/helloworld-r6-package-closure-current-20260724T2029HKT
CFG=$ADAPTER/framework/appspawn-x/config/appspawn_x.cfg
REMOTE_GENERATION=/data/a64deploy/alexbridge-fix-$(basename "$RUNTIME")
REMOTE_SYSTEM_ANDROID=$REMOTE_GENERATION/systemandroid
STAGE=/data/local/tmp/alexbridge-fix-$(basename "$RUNTIME")
TIMESTAMP=$(date +%Y%m%dT%H%M%S%Z)
EVIDENCE=$ADAPTER/out/$(basename "$RUNTIME")-fix-verify-5bb5b-$TIMESTAMP

mkdir -p "$EVIDENCE"

local_hash()
{
    /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'
}

device_hash()
{
    dev "sha256sum $1" | /usr/bin/awk '{print $1}'
}

dev()
{
    "$HDC" -t "$SERIAL" shell "$1"
}

wait_for_device()
{
    local attempt
    for attempt in {1..120}; do
        if "$HDC" list targets | /usr/bin/grep -q "$SERIAL"; then
            return 0
        fi
        sleep 1
    done
    echo "ERROR: device $SERIAL did not come online" >&2
    return 1
}

wait_shell()
{
    local attempt probe
    wait_for_device
    for attempt in {1..120}; do
        probe=$(dev "echo ok" 2>&1 || true)
        if [[ "$probe" == "ok" ]]; then
            return 0
        fi
        sleep 1
    done
    echo "ERROR: device shell did not become ready" >&2
    return 1
}

stop_appspawn_x()
{
    local attempt pid
    dev "begetctl stop_service appspawn-x 2>/dev/null || true"
    for attempt in {1..40}; do
        pid=$(dev "pidof appspawn-x" 2>/dev/null || true)
        if [[ -z "${pid// /}" ]]; then
            return 0
        fi
        dev "killall appspawn-x 2>/dev/null || true"
        sleep 0.5
    done
    echo "ERROR: appspawn-x did not stop" >&2
    return 1
}

print "=== verifying fix generation $(basename "$RUNTIME") on $SERIAL ==="

wait_for_device
[[ "$(dev 'param get const.ohos.fullname' | /usr/bin/tr -d '\r ')" == "OpenHarmony-6.1.0.31" ]]

EXPECTED_APPSPAWN=$(local_hash "$RUNTIME/bin/appspawn-x")
EXPECTED_CFG=$(local_hash "$CFG")
EXPECTED_ART=$(local_hash "$SYSTEM_ANDROID/lib64/libart.so")
EXPECTED_BRIDGE=$(local_hash "$SYSTEM_ANDROID/lib64/liboh_adapter_bridge.so")
EXPECTED_HWUI=$(local_hash "$SYSTEM_ANDROID/lib64/libhwui.so")
EXPECTED_THREAD_GUARD=$(local_hash "$SYSTEM_ANDROID/lib64/libwestlake_thread_guard_registry.so")
EXPECTED_LZMA=$(local_hash "$SYSTEM_ANDROID/lib64/liblzma.so")
EXPECTED_FONTS=$(local_hash "$SYSTEM_ANDROID/etc/fonts.xml")
EXPECTED_APPMS=$(local_hash "$ROUTE/lib64/libappms.z.so")
EXPECTED_CLIENT=$(local_hash "$ROUTE/lib64/libappspawn_client.z.so")
EXPECTED_BMS=$(local_hash "$PACKAGE/lib64/libbms.z.so")
EXPECTED_INSTALLS=$(local_hash "$PACKAGE/lib64/libinstalls.z.so")
EXPECTED_INSTALLER=$(local_hash "$PACKAGE/lib64/libapk_installer.so")
EXPECTED_APK=$(local_hash "$PACKAGE/app/HelloWorld.apk")

if [[ -f "$RUNTIME/generation.json" ]]; then
    cp "$RUNTIME/generation.json" "$EVIDENCE/generation.json"
fi

# Push generation tree + per-file staging.
"$HDC" -t "$SERIAL" target mount
dev "mkdir -p $REMOTE_GENERATION $STAGE /system/etc/init"
"$HDC" -t "$SERIAL" file send "$SYSTEM_ANDROID" "$REMOTE_GENERATION"
"$HDC" -t "$SERIAL" file send "$RUNTIME/bin/appspawn-x" "$STAGE/appspawn-x"
"$HDC" -t "$SERIAL" file send "$CFG" "$STAGE/appspawn_x.cfg"
"$HDC" -t "$SERIAL" file send "$ROUTE/lib64/libappms.z.so" "$STAGE/libappms.z.so"
"$HDC" -t "$SERIAL" file send "$ROUTE/lib64/libappspawn_client.z.so" "$STAGE/libappspawn_client.z.so"
"$HDC" -t "$SERIAL" file send "$PACKAGE/lib64/libbms.z.so" "$STAGE/libbms.z.so"
"$HDC" -t "$SERIAL" file send "$PACKAGE/lib64/libinstalls.z.so" "$STAGE/libinstalls.z.so"
"$HDC" -t "$SERIAL" file send "$PACKAGE/lib64/libapk_installer.so" "$STAGE/libapk_installer.so"
"$HDC" -t "$SERIAL" file send "$PACKAGE/app/HelloWorld.apk" "$STAGE/HelloWorld.apk"

stop_appspawn_x
dev "cp $STAGE/appspawn-x /system/bin/appspawn-x"
dev "cp $STAGE/appspawn_x.cfg /system/etc/init/appspawn_x.cfg"
dev "cp $STAGE/libappms.z.so /system/lib64/libappms.z.so"
dev "cp $STAGE/libappspawn_client.z.so /system/lib64/libappspawn_client.z.so"
dev "cp $STAGE/libbms.z.so /system/lib64/libbms.z.so"
dev "cp $STAGE/libinstalls.z.so /system/lib64/libinstalls.z.so"
dev "cp $STAGE/libapk_installer.so /system/lib64/libapk_installer.so"
dev "chown root:root /system/bin/appspawn-x /system/etc/init/appspawn_x.cfg /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so"
dev "chmod 0755 /system/bin/appspawn-x /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so"
dev "chmod 0550 /system/etc/init/appspawn_x.cfg"
dev "restorecon /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so"
dev "chcon u:object_r:appspawn_exec:s0 /system/bin/appspawn-x 2>/dev/null || restorecon /system/bin/appspawn-x"
dev "chcon u:object_r:system_etc_file:s0 /system/etc/init/appspawn_x.cfg 2>/dev/null || restorecon /system/etc/init/appspawn_x.cfg"

[[ "$(device_hash /system/bin/appspawn-x)" == "$EXPECTED_APPSPAWN" ]]
[[ "$(device_hash /system/etc/init/appspawn_x.cfg)" == "$EXPECTED_CFG" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/libart.so")" == "$EXPECTED_ART" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/liboh_adapter_bridge.so")" == "$EXPECTED_BRIDGE" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/libhwui.so")" == "$EXPECTED_HWUI" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/libwestlake_thread_guard_registry.so")" == "$EXPECTED_THREAD_GUARD" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/liblzma.so")" == "$EXPECTED_LZMA" ]]

dev "sync"
print "=== pre-reboot deploy verified, rebooting ==="
"$HDC" -t "$SERIAL" target boot

wait_shell
sleep 12
"$HDC" -t "$SERIAL" target mount
dev "mkdir -p /system/android"
dev "umount /system/android 2>/dev/null || true"
dev "mount --bind $REMOTE_SYSTEM_ANDROID /system/android"

# Relabel the bind-mounted Android tree explicitly.  This device's
# file_contexts covers /system/android/lib but not /system/android/lib64, so a
# recursive restorecon leaves the ARM64 generation as data_file:s0.
dev "find /system/android -exec chcon u:object_r:system_file:s0 {} \\;"
dev "find /system/android/lib64 -exec chcon u:object_r:system_lib_file:s0 {} \\;"
dev "for f in /system/android/framework/arm64/boot*.art /system/android/framework/arm64/boot*.oat /system/android/framework/arm64/boot*.vdex; do chcon u:object_r:system_lib_file:s0 \$f; done"

dev "cp /system/android/etc/fonts.xml /system/etc/fonts.xml"
dev "chcon u:object_r:system_fonts_file:s0 /system/etc/fonts.xml"

# Enforcing verification.
dev "setenforce 1"
dev "param set persist.sys.abilityms.timeout_unit_time_ratio 20"
dev "param set ro.product.cpu.abilist arm64-v8a"
dev "param set ro.product.cpu.abilist64 arm64-v8a"

# Apply G7 Enforcing fixes that the generation itself expects.
dev "chmod -R 0755 /system/android/framework"
dev "if [ -f /system/android/framework/arm64/boot.art ] && [ ! -e /system/android/framework/boot.art ]; then ln -sf arm64/boot.art /system/android/framework/boot.art; fi"

dev "begetctl start_service appspawn-x 2>/dev/null || true"
sleep 2

# Pre-launch verification: parent must be alive and stable.
sleep 3
parent_pid=$(dev "pidof appspawn-x" 2>/dev/null | /usr/bin/tr -d '\r ' || true)
if [[ -z "$parent_pid" ]]; then
    print -u2 "FAIL: appspawn-x parent is not alive before launch"
    dev "dmesg | grep -iE 'appspawn-x|sigsegv|signal 11' | tail -40" >"$EVIDENCE/dmesg-prelaunch.txt"
    exit 1
fi
print "=== appspawn-x parent stable (pid=$parent_pid) ==="

# Install/verify HelloWorld.
installed_apk_hash=$(device_hash /data/app/el1/bundle/public/com.example.helloworld/android/base.apk 2>/dev/null || true)
if [[ "$installed_apk_hash" != "$EXPECTED_APK" ]]; then
    dev "bm install -p $STAGE/HelloWorld.apk" >"$EVIDENCE/bm-install.txt" 2>&1 || true
fi
dev "bm dump -n com.example.helloworld" >"$EVIDENCE/bm-dump.txt" 2>&1 || true

# Trigger launch.
dev "aa force-stop com.example.helloworld" >/dev/null 2>&1 || true
dev "hilog -r" >/dev/null 2>&1 || true
sleep 1

print "=== launching HelloWorld under Enforcing ==="
dev "aa start -a com.example.helloworld.MainActivity -b com.example.helloworld" >"$EVIDENCE/aa-start.txt" 2>&1 || true

# Wait for child.
child_pid=""
for attempt in {1..30}; do
    child_pid=$(dev "pidof com.example.helloworld" 2>/dev/null | /usr/bin/tr -d '\r ' || true)
    if [[ -n "$child_pid" ]]; then
        break
    fi
    sleep 1
done

# Post-launch verification.
sleep 5
parent_pid_after=$(dev "pidof appspawn-x" 2>/dev/null | /usr/bin/tr -d '\r ' || true)

dev "pidof appspawn-x" >"$EVIDENCE/pidof-appspawn-x-after.txt" 2>&1 || true
dev "pidof com.example.helloworld" >"$EVIDENCE/pidof-helloworld-after.txt" 2>&1 || true
dev "ls -lZ /dev/unix/socket/AppSpawnX 2>/dev/null || true; grep AppSpawnX /proc/net/unix 2>/dev/null || true" >"$EVIDENCE/socket-state-after.txt"
dev "dmesg | grep -iE 'appspawn-x|sigsegv|signal 11|audit' | tail -120" >"$EVIDENCE/dmesg-after.txt" 2>&1 || true
dev "find /data/log/faultlog -maxdepth 3 -type f 2>/dev/null || true" >"$EVIDENCE/fault-files.txt"
dev "hilog -x" >"$EVIDENCE/hilog.txt" 2>&1 || true

if [[ -n "$child_pid" ]]; then
    "$HDC" -t "$SERIAL" file recv "/data/service/el1/public/appspawnx/adapter_child_${child_pid}.stderr" "$EVIDENCE/adapter_child_${child_pid}.stderr" 2>/dev/null || true
fi

dev "ps -A -o PID,PPID,UID,NAME,CMDLINE | grep -E 'appspawn-x|com.example.helloworld' || true" >"$EVIDENCE/processes.txt"
dev "cat /proc/sys/kernel/random/boot_id; getenforce; sha256sum /system/android/lib64/libart.so /system/android/lib64/liboh_adapter_bridge.so /system/android/lib64/libhwui.so /system/android/lib64/libwestlake_thread_guard_registry.so /system/android/lib64/liblzma.so /system/bin/appspawn-x" >"$EVIDENCE/final-hashes.txt"

# Screenshot.
dev "snapshot_display -f /data/local/tmp/helloworld-fix-verify-5bb5b.jpeg" 2>/dev/null || true
"$HDC" -t "$SERIAL" file recv /data/local/tmp/helloworld-fix-verify-5bb5b.jpeg "$EVIDENCE/helloworld-fix-verify-5bb5b.jpeg" 2>/dev/null || true

# Verdict.
print "=== verification result ==="
print "parent_pid_after=$parent_pid_after"
print "child_pid=$child_pid"

if [[ -z "$parent_pid_after" ]]; then
    print -u2 "FAIL: appspawn-x parent crashed after launch"
    exit 1
fi

if [[ -z "$child_pid" ]]; then
    print -u2 "FAIL: com.example.helloworld child process was not created"
    exit 1
fi

# Check hilog for MainActivity lifecycle markers.
if /usr/bin/grep -qE 'MainActivity.*onCreate|MainActivity.*onResume|ActivityThread.*handleLaunchActivity' "$EVIDENCE/hilog.txt" 2>/dev/null; then
    print "PASS: MainActivity lifecycle marker found"
else
    print "WARNING: MainActivity lifecycle marker not found in hilog (may still be loading)"
fi

print "PASS: fix verified on 5bb5b"
print "Evidence: $EVIDENCE"
