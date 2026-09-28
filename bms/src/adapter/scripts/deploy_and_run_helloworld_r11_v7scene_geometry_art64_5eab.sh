#!/bin/zsh
set -eu

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
SERIAL=5eab586000000000000000001123012c
ADAPTER=/opt/Bridge/src/adapter
GENERATION=$ADAPTER/out/helloworld-r11-v7scene-geometry-art64-20260724T2254HKT
SYSTEM_ANDROID=$GENERATION/systemandroid
REMOTE_GENERATION=/data/a64deploy/alexbridge-r11-v7scene-geometry-art64-98241dca
REMOTE_SYSTEM_ANDROID=$REMOTE_GENERATION/systemandroid
EVIDENCE=$ADAPTER/out/helloworld-r11-v7scene-geometry-run1-5eab-20260724T2254HKT

EXPECTED_ROUTE=c4855744929acf4c4523e8806d4d6522a1f553a01be184878e3494784d7164d3
EXPECTED_BMS=f8ef078df8a0fa483b60c1a997831a8190448545e141b9568fb14eacaf9da105
EXPECTED_INSTALLS=2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0
EXPECTED_INSTALLER=184d40a56a9116ab87d079413ba31d92e3d45c86a2f9b1088ffc97725ec650f9
EXPECTED_ART=69096c9e3ea9b6b376c11fd5a77705792698a80fa2f66b0242e633eef8b8ecdc
EXPECTED_APPSPAWN=2987e27fd0bbcf7df35d4a1c67054765fcc95ca08b424d1fdde96d50ba30253a
EXPECTED_BRIDGE=98241dca87a1497c364f009cac072a38c66eb9489fdb14ee91848ae15113fb6b
EXPECTED_FONTS=7818e8a9ef1fb951b085b521317007a8324f8ec872d848d1b4f82321883db093
EXPECTED_CFG=f4340210a0e5f6826e5990b2546a02600556aa15465c5972500d20f4751ab6b2

mkdir -p "$EVIDENCE"

dev()
{
    "$HDC" -t "$SERIAL" shell "$1"
}

wait_shell()
{
    local attempt probe
    for attempt in {1..100}; do
        probe=$(dev "cat /proc/sys/kernel/random/boot_id" 2>&1 || true)
        if [[ -n "$probe" && "$probe" != *"[Fail]"* ]]; then
            return 0
        fi
        sleep 3
    done
    return 1
}

local_hash()
{
    /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'
}

device_hash()
{
    dev "sha256sum $1" | /usr/bin/awk '{print $1}'
}

"$HDC" list targets | /usr/bin/grep -q "$SERIAL"
(cd "$GENERATION" && /usr/bin/shasum -a 256 -c MANIFEST.sha256 >/dev/null)
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libart.so")" == "$EXPECTED_ART" ]]
[[ "$(local_hash "$GENERATION/bin/appspawn-x")" == "$EXPECTED_APPSPAWN" ]]
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/liboh_adapter_bridge.so")" == "$EXPECTED_BRIDGE" ]]
[[ "$(local_hash "$ADAPTER/framework/appspawn-x/config/appspawn_x.cfg")" == "$EXPECTED_CFG" ]]
[[ "$(/usr/bin/find "$SYSTEM_ANDROID/framework/arm64" -maxdepth 1 -type f | /usr/bin/wc -l | /usr/bin/tr -d ' ')" == "27" ]]
[[ -z "$(/usr/bin/find "$GENERATION" -type f \( -name '*.bak*' -o -name '*pre-proxy-bak' \) -print)" ]]

[[ "$(device_hash /system/lib64/libappms.z.so)" == "$EXPECTED_ROUTE" ]]
[[ "$(device_hash /system/lib64/libbms.z.so)" == "$EXPECTED_BMS" ]]
[[ "$(device_hash /system/lib64/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]]
[[ "$(device_hash /system/lib64/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]]
dev "bm dump -n com.example.helloworld" | /usr/bin/grep -q "com.example.helloworld.MainActivity"

"$HDC" -t "$SERIAL" target mount
dev "mkdir -p $REMOTE_GENERATION"
"$HDC" -t "$SERIAL" file send "$SYSTEM_ANDROID" "$REMOTE_GENERATION"

[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/libart.so")" == "$EXPECTED_ART" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/liboh_adapter_bridge.so")" == "$EXPECTED_BRIDGE" ]]
[[ "$(device_hash /system/bin/appspawn-x)" == "$EXPECTED_APPSPAWN" ]]
[[ "$(device_hash /system/etc/init/appspawn_x.cfg)" == "$EXPECTED_CFG" ]]
dev "sync"
"$HDC" -t "$SERIAL" target boot

wait_shell
"$HDC" -t "$SERIAL" target mount
dev "mkdir -p /system/android"
dev "umount /system/android 2>/dev/null || true"
dev "mount --bind $REMOTE_SYSTEM_ANDROID /system/android"
# AOSP SystemFonts hardcodes /system/etc/fonts.xml. Materialize the exact file
# from this frozen generation and give it OH's native system-font label.
dev "cp /system/android/etc/fonts.xml /system/etc/fonts.xml"
dev "chcon u:object_r:system_fonts_file:s0 /system/etc/fonts.xml"
dev "setenforce 0"
dev "param set persist.sys.abilityms.timeout_unit_time_ratio 20"
dev "param set ro.product.cpu.abilist arm64-v8a"
dev "param set ro.product.cpu.abilist64 arm64-v8a"
dev "power-shell timeout -o 86400000; power-shell wakeup"
sleep 3
dev "uitest uiInput swipe 600 1700 600 300 1000" || true
dev "uitest uiInput swipe 600 1700 600 250 1500" || true
sleep 2
dev "uitest uiInput click 600 1180" || true
dev "hilog -p off"

[[ "$(device_hash /system/android/lib64/libart.so)" == "$EXPECTED_ART" ]]
[[ "$(device_hash /system/android/lib64/liboh_adapter_bridge.so)" == "$EXPECTED_BRIDGE" ]]
[[ "$(device_hash /system/etc/fonts.xml)" == "$EXPECTED_FONTS" ]]
dev "ls -lZ /system/etc/fonts.xml" | /usr/bin/grep -q "u:object_r:system_fonts_file:s0"
[[ "$(device_hash /system/bin/appspawn-x)" == "$EXPECTED_APPSPAWN" ]]
[[ "$(device_hash /system/lib64/libappms.z.so)" == "$EXPECTED_ROUTE" ]]
[[ "$(device_hash /system/lib64/libbms.z.so)" == "$EXPECTED_BMS" ]]
[[ "$(device_hash /system/lib64/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]]
[[ "$(device_hash /system/lib64/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]]
dev "bm dump -n com.example.helloworld" | /usr/bin/grep -q "com.example.helloworld.MainActivity"

dev "cat /proc/sys/kernel/random/boot_id; param get persist.sys.abilityms.timeout_unit_time_ratio; param get ro.product.cpu.abilist; param get ro.product.cpu.abilist64; sha256sum /system/android/lib64/libart.so /system/android/lib64/liboh_adapter_bridge.so /system/bin/appspawn-x /system/lib64/libappms.z.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so; ls -lZ /dev/unix/socket/AppSpawnX 2>/dev/null || true; grep AppSpawnX /proc/net/unix || true" >"$EVIDENCE/pre-launch.txt"
dev "aa force-stop com.example.helloworld"
dev "hilog -r"
dev "aa start -a com.example.helloworld.MainActivity -b com.example.helloworld -W" >"$EVIDENCE/aa-start.txt" 2>&1 || true

child_pid=""
for attempt in {1..30}; do
    child_pid=$(dev "pidof com.example.helloworld" | /usr/bin/tr -d '\r')
    dev "date +%s; pidof appspawn-x; pidof com.example.helloworld" >>"$EVIDENCE/process-samples.txt"
    if [[ -n "$child_pid" ]]; then
        break
    fi
    sleep 1
done

sleep 5
dev "hilog -x" >"$EVIDENCE/hilog.txt"
dev "ps -A -o PID,PPID,UID,NAME,CMDLINE | grep -E 'appspawn-x|com.example.helloworld' || true; ls -lZ /dev/unix/socket/AppSpawnX 2>/dev/null || true; grep AppSpawnX /proc/net/unix || true" >"$EVIDENCE/final-state.txt"
dev "find /data/log/faultlog -maxdepth 3 -type f" >"$EVIDENCE/fault-files.txt"
dev "snapshot_display -f /data/local/tmp/helloworld-r11-art64-5eab.jpeg"
"$HDC" -t "$SERIAL" file recv /data/local/tmp/helloworld-r11-art64-5eab.jpeg "$EVIDENCE/helloworld-r11-art64-5eab.jpeg"

print "HelloWorld pid=$child_pid"
print "Evidence=$EVIDENCE"
[[ -n "$child_pid" ]]
