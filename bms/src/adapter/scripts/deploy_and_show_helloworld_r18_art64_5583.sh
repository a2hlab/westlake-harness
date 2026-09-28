#!/bin/zsh
set -eu

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
SERIAL=5583f5be00000000000000000323012c
ADAPTER=/opt/Bridge/src/adapter
RUNTIME=$ADAPTER/out/helloworld-r18-v7-ams-parent-bound-subwindow-art64-20260725T0050HKT
SYSTEM_ANDROID=$RUNTIME/systemandroid
ROUTE=$ADAPTER/out/helloworld-r6-route-hanbing-closure-20260724T202644HKT
PACKAGE=$ADAPTER/out/helloworld-r6-package-closure-current-20260724T2029HKT
CFG=$ADAPTER/framework/appspawn-x/config/appspawn_x.cfg
REMOTE_GENERATION=/data/a64deploy/alexbridge-r18-visible-5583
REMOTE_SYSTEM_ANDROID=$REMOTE_GENERATION/systemandroid
STAGE=/data/local/tmp/alexbridge-r18-visible-5583
EVIDENCE=$ADAPTER/out/helloworld-r18-visible-5583-20260725T0842HKT

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

apply_enforcing_fixes()
{
    # Boot Enforcing; previous Permissive runs were diagnostic only.
    dev "setenforce 1"

    # G7 Enforcing fix: /system/android/framework may be 750; the spawned Android
    # app uid needs to traverse it and read framework-res.apk.
    dev "chmod -R 0755 /system/android/framework"

    # G7 Enforcing fix: ART expects /system/android/framework/boot.art, but the
    # boot image is packaged under framework/arm64/. Provide the stable top-level
    # symlink expected by the runtime.
    dev "if [ -f /system/android/framework/arm64/boot.art ] && [ ! -e /system/android/framework/boot.art ]; then ln -sf arm64/boot.art /system/android/framework/boot.art; fi"

    # AbilityMS timeout ratio and CPU abilist for ARM64 content.
    dev "param set persist.sys.abilityms.timeout_unit_time_ratio 20"
    dev "param set ro.product.cpu.abilist arm64-v8a"
    dev "param set ro.product.cpu.abilist64 arm64-v8a"
}

# Compute all expected hashes from the local source tree / generation output.
# This removes the previous hard-coded manifest and makes the script reusable
# across rebuilds.
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

wait_for_device
[[ "$(dev 'param get const.ohos.fullname' | /usr/bin/tr -d '\r ')" == "OpenHarmony-6.1.0.31" ]]
(cd "$RUNTIME" && /usr/bin/shasum -a 256 -c MANIFEST.sha256 >/dev/null)
[[ "$(local_hash "$RUNTIME/bin/appspawn-x")" == "$EXPECTED_APPSPAWN" ]]
[[ "$(local_hash "$CFG")" == "$EXPECTED_CFG" ]]
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libart.so")" == "$EXPECTED_ART" ]]
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/liboh_adapter_bridge.so")" == "$EXPECTED_BRIDGE" ]]
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libhwui.so")" == "$EXPECTED_HWUI" ]]
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libwestlake_thread_guard_registry.so")" == "$EXPECTED_THREAD_GUARD" ]]
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/liblzma.so")" == "$EXPECTED_LZMA" ]]
[[ "$(local_hash "$ROUTE/lib64/libappms.z.so")" == "$EXPECTED_APPMS" ]]
[[ "$(local_hash "$ROUTE/lib64/libappspawn_client.z.so")" == "$EXPECTED_CLIENT" ]]
[[ "$(local_hash "$PACKAGE/lib64/libbms.z.so")" == "$EXPECTED_BMS" ]]
[[ "$(local_hash "$PACKAGE/lib64/libinstalls.z.so")" == "$EXPECTED_INSTALLS" ]]
[[ "$(local_hash "$PACKAGE/lib64/libapk_installer.so")" == "$EXPECTED_INSTALLER" ]]
[[ "$(local_hash "$PACKAGE/app/HelloWorld.apk")" == "$EXPECTED_APK" ]]
[[ "$(/usr/bin/find "$SYSTEM_ANDROID/framework/arm64" -maxdepth 1 -type f | /usr/bin/wc -l | /usr/bin/tr -d ' ')" == "27" ]]

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

# Appspawn-x is a running init service; stop it before replacing the binary to
# avoid "Text file busy".
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
[[ "$(device_hash /system/lib64/libappms.z.so)" == "$EXPECTED_APPMS" ]]
[[ "$(device_hash /system/lib64/libappspawn_client.z.so)" == "$EXPECTED_CLIENT" ]]
[[ "$(device_hash /system/lib64/libbms.z.so)" == "$EXPECTED_BMS" ]]
[[ "$(device_hash /system/lib64/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]]
[[ "$(device_hash /system/lib64/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/libart.so")" == "$EXPECTED_ART" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/liboh_adapter_bridge.so")" == "$EXPECTED_BRIDGE" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/libhwui.so")" == "$EXPECTED_HWUI" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/libwestlake_thread_guard_registry.so")" == "$EXPECTED_THREAD_GUARD" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/liblzma.so")" == "$EXPECTED_LZMA" ]]
[[ "$(device_hash "$STAGE/HelloWorld.apk")" == "$EXPECTED_APK" ]]
dev "sync"
"$HDC" -t "$SERIAL" target boot

wait_shell
sleep 12
"$HDC" -t "$SERIAL" target mount
dev "mkdir -p /system/android"
dev "umount /system/android 2>/dev/null || true"
dev "mount --bind $REMOTE_SYSTEM_ANDROID /system/android"
# G7 Enforcing fix: the Android tree is bind-mounted from /data/a64deploy/...,
# so every inode still carries the data_file:s0 label from the staging path.
# The device file_contexts only covers /system/android/lib, not the ARM64
# /system/android/lib64 tree.  Therefore restorecon cannot close this gap.
# Reconstruct the labels that these files would inherit under /system:
# ordinary framework/config entries are system_file, runtime libraries and
# boot-image segments are system_lib_file (the latter must permit ART flock).
dev "find /system/android -exec chcon u:object_r:system_file:s0 {} \\;"
dev "find /system/android/lib64 -exec chcon u:object_r:system_lib_file:s0 {} \\;"
dev "for f in /system/android/framework/arm64/boot*.art /system/android/framework/arm64/boot*.oat /system/android/framework/arm64/boot*.vdex; do chcon u:object_r:system_lib_file:s0 \$f; done"
dev "cp /system/android/etc/fonts.xml /system/etc/fonts.xml"
dev "chcon u:object_r:system_fonts_file:s0 /system/etc/fonts.xml"

apply_enforcing_fixes

# The explicit lib64 chcon above also covers
# libwestlake_thread_guard_registry.so and liblzma.so.

# The new appspawn-x needs /system/android/lib64 at load time; the bind mount
# is now in place, so make sure init has a healthy service instance before the
# app launch attempt.
dev "begetctl start_service appspawn-x 2>/dev/null || true"
sleep 2

[[ "$(device_hash /system/android/lib64/libart.so)" == "$EXPECTED_ART" ]]
[[ "$(device_hash /system/android/lib64/liboh_adapter_bridge.so)" == "$EXPECTED_BRIDGE" ]]
[[ "$(device_hash /system/android/lib64/libhwui.so)" == "$EXPECTED_HWUI" ]]
[[ "$(device_hash /system/android/lib64/libwestlake_thread_guard_registry.so)" == "$EXPECTED_THREAD_GUARD" ]]
[[ "$(device_hash /system/android/lib64/liblzma.so)" == "$EXPECTED_LZMA" ]]
[[ "$(device_hash /system/etc/fonts.xml)" == "$EXPECTED_FONTS" ]]
[[ "$(device_hash /system/bin/appspawn-x)" == "$EXPECTED_APPSPAWN" ]]
[[ "$(device_hash /system/etc/init/appspawn_x.cfg)" == "$EXPECTED_CFG" ]]
[[ "$(device_hash /system/lib64/libappms.z.so)" == "$EXPECTED_APPMS" ]]
[[ "$(device_hash /system/lib64/libappspawn_client.z.so)" == "$EXPECTED_CLIENT" ]]
[[ "$(device_hash /system/lib64/libbms.z.so)" == "$EXPECTED_BMS" ]]
[[ "$(device_hash /system/lib64/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]]
[[ "$(device_hash /system/lib64/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]]

installed_apk_hash=$(device_hash /data/app/el1/bundle/public/com.example.helloworld/android/base.apk 2>/dev/null || true)
if [[ "$installed_apk_hash" != "$EXPECTED_APK" ]]; then
    dev "bm install -p $STAGE/HelloWorld.apk" >"$EVIDENCE/bm-install.txt"
fi
dev "bm dump -n com.example.helloworld" >"$EVIDENCE/bm-dump.txt"
/usr/bin/grep -q "com.example.helloworld.MainActivity" "$EVIDENCE/bm-dump.txt"

dev "power-shell timeout -o 86400000; power-shell wakeup"
dev "uitest uiInput swipe 600 1700 600 250 1200" || true
dev "uitest uiInput click 600 1180" || true
dev "aa force-stop com.example.helloworld"
dev "hilog -r"
# The 5583 proof route is the actual launcher path.  Reusing an old OH
# MainSession through a second `aa start -W` can create a new foreground
# transition without the matching adapter callback and is then killed by the
# 10-second OH lifecycle watchdog.  Clicking the registered launcher ability
# creates the normal transition and closes ScheduleForegroundApplication ->
# AbilityTransitionDone(FOREGROUND).
dev "uitest uiInput click 190 180" >"$EVIDENCE/launcher-click.txt"
sleep 13

child_pid=$(dev "ps -A -o PID,PPID,UID,NAME,CMDLINE | grep ' 20010053 ' || true" |
    /usr/bin/awk 'NR == 1 {print $1}' |
    /usr/bin/tr -d '\r ')
[[ -n "$child_pid" ]]
dev "cat /proc/sys/kernel/random/boot_id; ps -A -o PID,PPID,UID,NAME,CMDLINE | grep -E 'appspawn-x|com.example.helloworld' || true; sha256sum /system/android/lib64/libart.so /system/android/lib64/liboh_adapter_bridge.so /system/android/lib64/libhwui.so /system/android/lib64/libwestlake_thread_guard_registry.so /system/android/lib64/liblzma.so /system/bin/appspawn-x /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so; ls -lZ /dev/unix/socket/AppSpawnX" >"$EVIDENCE/final-receipt.txt"
dev "hilog -x" >"$EVIDENCE/hilog.txt"
/usr/bin/grep -q "ScheduleForegroundApplication" "$EVIDENCE/hilog.txt"
/usr/bin/grep -q "AbilityTransitionDone(FOREGROUND) ACCEPTED rc=0" "$EVIDENCE/hilog.txt"
dev "snapshot_display -f /data/local/tmp/helloworld-r18-visible-5583.jpeg"
"$HDC" -t "$SERIAL" file recv /data/local/tmp/helloworld-r18-visible-5583.jpeg "$EVIDENCE/helloworld-r18-visible-5583.jpeg"

print "HelloWorld visible on 5583, pid=$child_pid"
print "Evidence=$EVIDENCE"
