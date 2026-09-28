#!/bin/zsh
set -eu

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
SERIAL=5eab586000000000000000001123012c
EVIDENCE=/opt/Bridge/src/adapter/out/helloworld-r6-on-screen-5eab-20260724T2100HKT

EXPECTED_ROUTE=c4855744929acf4c4523e8806d4d6522a1f553a01be184878e3494784d7164d3
EXPECTED_BMS=f8ef078df8a0fa483b60c1a997831a8190448545e141b9568fb14eacaf9da105
EXPECTED_INSTALLS=2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0
EXPECTED_INSTALLER=184d40a56a9116ab87d079413ba31d92e3d45c86a2f9b1088ffc97725ec650f9
EXPECTED_ART=69096c9e3ea9b6b376c11fd5a77705792698a80fa2f66b0242e633eef8b8ecdc
EXPECTED_APPSPAWN=2987e27fd0bbcf7df35d4a1c67054765fcc95ca08b424d1fdde96d50ba30253a

mkdir -p "$EVIDENCE"

dev()
{
    "$HDC" -t "$SERIAL" shell "$1"
}

device_hash()
{
    dev "sha256sum $1" | /usr/bin/awk '{print $1}'
}

[[ "$(device_hash /system/android/lib64/libart.so)" == "$EXPECTED_ART" ]]
[[ "$(device_hash /system/bin/appspawn-x)" == "$EXPECTED_APPSPAWN" ]]
[[ "$(device_hash /system/lib64/libappms.z.so)" == "$EXPECTED_ROUTE" ]]
[[ "$(device_hash /system/lib64/libbms.z.so)" == "$EXPECTED_BMS" ]]
[[ "$(device_hash /system/lib64/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]]
[[ "$(device_hash /system/lib64/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]]

ready=0
for attempt in {1..30}; do
    if dev "bm dump -n com.example.helloworld" | /usr/bin/grep -q "com.example.helloworld.MainActivity"; then
        ready=1
        break
    fi
    sleep 1
done
[[ "$ready" == "1" ]]

dev "cat /proc/sys/kernel/random/boot_id; sha256sum /system/android/lib64/libart.so /system/bin/appspawn-x /system/lib64/libappms.z.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so; ls -lZ /dev/unix/socket/AppSpawnX; grep AppSpawnX /proc/net/unix" >"$EVIDENCE/pre-launch.txt"
dev "aa force-stop com.example.helloworld"
dev "hilog -r"
dev "aa start -a com.example.helloworld.MainActivity -b com.example.helloworld -W" >"$EVIDENCE/aa-start.txt" 2>&1 || true

child_seen=0
: >"$EVIDENCE/process-samples.txt"
for attempt in {1..30}; do
    child_pid=$(dev "pidof com.example.helloworld" | /usr/bin/tr -d '\r')
    dev "date +%s; pidof appspawn-x; pidof com.example.helloworld" >>"$EVIDENCE/process-samples.txt"
    if [[ -n "$child_pid" ]]; then
        child_seen=1
    fi
    sleep 1
done

dev "hilog -x" >"$EVIDENCE/hilog.txt"
dev "ps -A -o PID,PPID,UID,NAME,CMDLINE | grep -E 'appspawn-x|com.example.helloworld' || true; ls -lZ /dev/unix/socket/AppSpawnX; grep AppSpawnX /proc/net/unix" >"$EVIDENCE/final-state.txt"
dev "find /data/log/faultlog -maxdepth 3 -type f" >"$EVIDENCE/fault-files.txt"
dev "snapshot_display -f /data/local/tmp/helloworld-art64-5eab.jpeg"
"$HDC" -t "$SERIAL" file recv /data/local/tmp/helloworld-art64-5eab.jpeg "$EVIDENCE/helloworld-art64-5eab.jpeg"

print "child_seen=$child_seen"
print "final_pid=$(dev 'pidof com.example.helloworld' | /usr/bin/tr -d '\r')"
print "evidence=$EVIDENCE"
