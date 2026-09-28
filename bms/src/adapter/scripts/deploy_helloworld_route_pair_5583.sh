#!/bin/zsh
set -eu

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
SERIAL=5583f5be00000000000000000323012c
ADAPTER=/opt/Bridge/src/adapter
ROUTE=$ADAPTER/out/helloworld-r6-route-684cb313
RUN=/opt/Bridge/evidence/runs/helloworld-hanbing-v2-cfi-resource-r6-20260724
EVIDENCE=$RUN/init-route-pair-run-5583
REMOTE_SYSTEM_ANDROID=/data/a64deploy/winning-art64-69096c9e/systemandroid
STAGE=/data/local/tmp/alexbridge-route-pair-684cb313

EXPECTED_APPMS=d75f1a484d40deb2736702f766ea2520351140bdb559b0d5282d1b988bf85bb0
EXPECTED_APPSPAWN_CLIENT=d8643ea487f02d21af232bee782b9de90db8e1523386a573e26c8efe2ccea78e
EXPECTED_INSTALLER=a015fb78185b6490041e5ac8187ed87363e79517ccba7040c51f06a926d3e30c
EXPECTED_BMS=f8ef078df8a0fa483b60c1a997831a8190448545e141b9568fb14eacaf9da105
EXPECTED_INSTALLS=2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0
EXPECTED_ART=69096c9e3ea9b6b376c11fd5a77705792698a80fa2f66b0242e633eef8b8ecdc
EXPECTED_APPSPAWN=2987e27fd0bbcf7df35d4a1c67054765fcc95ca08b424d1fdde96d50ba30253a

mkdir -p "$EVIDENCE"

dev()
{
    "$HDC" -t "$SERIAL" shell "$1"
}

require_device()
{
    "$HDC" list targets | grep -q "$SERIAL"
}

wait_device()
{
    local attempt
    for attempt in {1..80}; do
        if require_device; then
            return 0
        fi
        sleep 3
    done
    return 1
}

wait_shell()
{
    local attempt
    local probe
    for attempt in {1..80}; do
        probe=$(dev "cat /proc/sys/kernel/random/boot_id" 2>&1 || true)
        if [[ -n "$probe" && "$probe" != *"[Fail]"* ]]; then
            return 0
        fi
        sleep 3
    done
    return 1
}

check_local_hash()
{
    local artifact_path=$1
    local expected=$2
    local actual
    actual=$(/usr/bin/shasum -a 256 "$artifact_path" | /usr/bin/awk '{print $1}')
    if [[ "$actual" != "$expected" ]]; then
        print -u2 "local hash mismatch: $artifact_path expected=$expected actual=$actual"
        exit 1
    fi
}

check_device_hash()
{
    local artifact_path=$1
    local expected=$2
    local actual
    actual=$(dev "sha256sum $artifact_path" | awk '{print $1}')
    if [[ "$actual" != "$expected" ]]; then
        print -u2 "device hash mismatch: $artifact_path expected=$expected actual=$actual"
        exit 1
    fi
}

require_device
check_local_hash "$ROUTE/libappms.z.so" "$EXPECTED_APPMS"
check_local_hash "$ROUTE/libappspawn_client.z.so" "$EXPECTED_APPSPAWN_CLIENT"
file "$ROUTE/libappms.z.so" "$ROUTE/libappspawn_client.z.so" | grep -q "ARM aarch64"
strings "$ROUTE/libappms.z.so" | grep -q "StartProcess: routing to appspawn-x for Android app"
strings "$ROUTE/libappspawn_client.z.so" | grep -q "AppSpawnX"

"$HDC" -t "$SERIAL" target mount
dev "mkdir -p $STAGE"
"$HDC" -t "$SERIAL" file send "$ROUTE/libappms.z.so" "$STAGE/libappms.z.so"
"$HDC" -t "$SERIAL" file send "$ROUTE/libappspawn_client.z.so" "$STAGE/libappspawn_client.z.so"
dev "cp $STAGE/libappms.z.so /system/lib64/libappms.z.so"
dev "cp $STAGE/libappspawn_client.z.so /system/lib64/libappspawn_client.z.so"
dev "chown root:root /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so"
dev "chmod 0755 /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so"
dev "restorecon -F /system/lib64/libappms.z.so"
dev "restorecon -F /system/lib64/libappspawn_client.z.so"
check_device_hash /system/lib64/libappms.z.so "$EXPECTED_APPMS"
check_device_hash /system/lib64/libappspawn_client.z.so "$EXPECTED_APPSPAWN_CLIENT"
dev "sync"

"$HDC" -t "$SERIAL" target boot
wait_device
wait_shell
sleep 12

"$HDC" -t "$SERIAL" target mount
dev "mkdir -p /system/android"
dev "umount /system/android 2>/dev/null || true"
dev "mount --bind $REMOTE_SYSTEM_ANDROID /system/android"
dev "setenforce 0"

check_device_hash /system/lib64/libappms.z.so "$EXPECTED_APPMS"
check_device_hash /system/lib64/libappspawn_client.z.so "$EXPECTED_APPSPAWN_CLIENT"
check_device_hash /system/lib64/libapk_installer.so "$EXPECTED_INSTALLER"
check_device_hash /system/lib64/libbms.z.so "$EXPECTED_BMS"
check_device_hash /system/lib64/libinstalls.z.so "$EXPECTED_INSTALLS"
check_device_hash /system/android/lib64/libart.so "$EXPECTED_ART"
check_device_hash /system/bin/appspawn-x "$EXPECTED_APPSPAWN"

dev "cat /proc/sys/kernel/random/boot_id; sha256sum /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libbms.z.so /system/android/lib64/libart.so /system/bin/appspawn-x; ls -lZ /dev/unix/socket/AppSpawnX; grep AppSpawnX /proc/net/unix" \
    >"$EVIDENCE/pre-launch-closure.txt"
dev "bm dump -n com.example.helloworld" >"$EVIDENCE/bm-dump.txt"
if ! grep -q "com.example.helloworld.MainActivity" "$EVIDENCE/bm-dump.txt"; then
    print -u2 "HelloWorld package/activity is absent after reboot"
    exit 1
fi

dev "aa force-stop com.example.helloworld 2>/dev/null || true"
dev "hilog -r"
dev "aa start -a com.example.helloworld.MainActivity -b com.example.helloworld -W" \
    >"$EVIDENCE/aa-start.txt"

appspawn_pid=""
child_pid=""
for attempt in {1..40}; do
    appspawn_pid=$(dev "pidof appspawn-x" | tr -d '\r')
    child_pid=$(dev "pidof com.example.helloworld" | tr -d '\r')
    if [[ -n "$child_pid" ]]; then
        break
    fi
    sleep 1
done

dev "hilog -x" >"$EVIDENCE/hilog.txt"
dev "ps -A -o PID,PPID,UID,NAME,CMDLINE | grep -E 'appspawn-x|com.example.helloworld' || true; ls -lZ /dev/unix/socket/AppSpawnX; grep AppSpawnX /proc/net/unix; param get init.svc.appspawn-x 2>&1 || true" \
    >"$EVIDENCE/process-and-socket.txt"
dev "find /data/log/faultlog /data/log/reliability -maxdepth 4 -type f 2>/dev/null | sort" \
    >"$EVIDENCE/fault-files.txt"

if [[ -z "$appspawn_pid" ]]; then
    print -u2 "routing did not activate appspawn-x"
    exit 2
fi
if [[ -z "$child_pid" ]]; then
    print -u2 "appspawn-x activated, but HelloWorld child was not created"
    exit 3
fi

sleep 3
dev "snapshot_display -f /data/local/tmp/helloworld-route-pair-5583.jpeg"
"$HDC" -t "$SERIAL" file recv \
    /data/local/tmp/helloworld-route-pair-5583.jpeg \
    "$EVIDENCE/helloworld-route-pair-5583.jpeg"

print "appspawn-x pid=$appspawn_pid"
print "HelloWorld pid=$child_pid"
print "Screenshot: $EVIDENCE/helloworld-route-pair-5583.jpeg"
