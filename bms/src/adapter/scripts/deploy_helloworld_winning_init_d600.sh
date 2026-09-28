#!/bin/zsh
set -eu

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
SERIAL=5583f5be00000000000000000323012c
ADAPTER=/opt/Bridge/src/adapter
RUN=/opt/Bridge/evidence/runs/helloworld-hanbing-v2-cfi-resource-r6-20260724
CLOSURE=$RUN/runtime-closure-winning-art64
SYSTEM_ANDROID=$CLOSURE/systemandroid
ARTIFACTS=$RUN/artifacts
EVIDENCE=$RUN/init-owned-run-5583
REMOTE_GENERATION=/data/a64deploy/winning-art64-69096c9e
REMOTE_SYSTEM_ANDROID=$REMOTE_GENERATION/systemandroid
STAGE=/data/local/tmp/alexbridge-winning-art64-r6

EXPECTED_INSTALLER=a015fb78185b6490041e5ac8187ed87363e79517ccba7040c51f06a926d3e30c
EXPECTED_BMS=f8ef078df8a0fa483b60c1a997831a8190448545e141b9568fb14eacaf9da105
EXPECTED_INSTALLS=2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0
EXPECTED_ART=69096c9e3ea9b6b376c11fd5a77705792698a80fa2f66b0242e633eef8b8ecdc
EXPECTED_APPSPAWN=2987e27fd0bbcf7df35d4a1c67054765fcc95ca08b424d1fdde96d50ba30253a
EXPECTED_APK=2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd

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
        print -u2 "hash mismatch: $artifact_path expected=$expected actual=$actual"
        exit 1
    fi
}

require_device

check_local_hash "$ARTIFACTS/libapk_installer.so" "$EXPECTED_INSTALLER"
check_local_hash "$ARTIFACTS/libbms.z.so" "$EXPECTED_BMS"
check_local_hash "$ARTIFACTS/libinstalls.z.so" "$EXPECTED_INSTALLS"
check_local_hash "$ARTIFACTS/HelloWorld.apk" "$EXPECTED_APK"
check_local_hash "$SYSTEM_ANDROID/lib64/libart.so" "$EXPECTED_ART"
check_local_hash "$CLOSURE/bin/appspawn-x" "$EXPECTED_APPSPAWN"

boot_file_count=$(/usr/bin/find "$SYSTEM_ANDROID/framework/arm64" -maxdepth 1 -type f | /usr/bin/wc -l | /usr/bin/tr -d ' ')
if [[ "$boot_file_count" != 27 ]]; then
    print -u2 "boot closure mismatch: expected 27 files, actual=$boot_file_count"
    exit 1
fi

"$HDC" -t "$SERIAL" target mount
dev "mkdir -p $STAGE $REMOTE_GENERATION /system/etc/init"
"$HDC" -t "$SERIAL" file send \
    "$SYSTEM_ANDROID" \
    "$REMOTE_GENERATION"
"$HDC" -t "$SERIAL" file send \
    "$CLOSURE/bin/appspawn-x" \
    "$STAGE/appspawn-x"
"$HDC" -t "$SERIAL" file send \
    "$ADAPTER/framework/appspawn-x/config/appspawn_x.cfg" \
    "$STAGE/appspawn_x.cfg"
"$HDC" -t "$SERIAL" file send \
    "$ARTIFACTS/libapk_installer.so" \
    "$STAGE/libapk_installer.so"
"$HDC" -t "$SERIAL" file send \
    "$ARTIFACTS/libbms.z.so" \
    "$STAGE/libbms.z.so"
"$HDC" -t "$SERIAL" file send \
    "$ARTIFACTS/libinstalls.z.so" \
    "$STAGE/libinstalls.z.so"
"$HDC" -t "$SERIAL" file send \
    "$ARTIFACTS/HelloWorld.apk" \
    "$STAGE/HelloWorld.apk"

dev "cp $STAGE/libapk_installer.so /system/lib64/libapk_installer.so"
dev "cp $STAGE/libbms.z.so /system/lib64/libbms.z.so"
dev "cp $STAGE/libinstalls.z.so /system/lib64/libinstalls.z.so"
dev "cp $STAGE/appspawn-x /system/bin/appspawn-x"
dev "cp $STAGE/appspawn_x.cfg /system/etc/init/appspawn_x.cfg"
dev "chown root:root /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so"
dev "chmod 0755 /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so"
dev "chown root:root /system/bin/appspawn-x /system/etc/init/appspawn_x.cfg"
dev "chmod 0755 /system/bin/appspawn-x"
dev "chmod 0550 /system/etc/init/appspawn_x.cfg"
dev "restorecon -F /system/lib64/libapk_installer.so"
dev "restorecon -F /system/lib64/libbms.z.so"
dev "restorecon -F /system/lib64/libinstalls.z.so"
dev "chcon u:object_r:appspawn_exec:s0 /system/bin/appspawn-x 2>/dev/null || restorecon -F /system/bin/appspawn-x"
dev "chcon u:object_r:system_etc_file:s0 /system/etc/init/appspawn_x.cfg 2>/dev/null || restorecon -F /system/etc/init/appspawn_x.cfg"

check_device_hash /system/lib64/libapk_installer.so "$EXPECTED_INSTALLER"
check_device_hash /system/lib64/libbms.z.so "$EXPECTED_BMS"
check_device_hash /system/lib64/libinstalls.z.so "$EXPECTED_INSTALLS"
check_device_hash /system/bin/appspawn-x "$EXPECTED_APPSPAWN"
check_device_hash "$REMOTE_SYSTEM_ANDROID/lib64/libart.so" "$EXPECTED_ART"
check_device_hash "$STAGE/HelloWorld.apk" "$EXPECTED_APK"
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

check_device_hash /system/android/lib64/libart.so "$EXPECTED_ART"
check_device_hash /system/lib64/libapk_installer.so "$EXPECTED_INSTALLER"
check_device_hash /system/lib64/libbms.z.so "$EXPECTED_BMS"
check_device_hash /system/lib64/libinstalls.z.so "$EXPECTED_INSTALLS"

dev "ls -lZ /dev/unix/socket/AppSpawnX; grep AppSpawnX /proc/net/unix" \
    >"$EVIDENCE/init-socket-before-start.txt"
dev "bm install -p $STAGE/HelloWorld.apk" \
    >"$EVIDENCE/bm-install.txt"
dev "bm dump -n com.example.helloworld" \
    >"$EVIDENCE/bm-dump.txt"
if ! grep -q "com.example.helloworld.MainActivity" "$EVIDENCE/bm-dump.txt"; then
    print -u2 "HelloWorld package/activity was not registered"
    exit 1
fi

dev "aa force-stop com.example.helloworld"
dev "hilog -r"
dev "aa start -a com.example.helloworld.MainActivity -b com.example.helloworld -W" \
    >"$EVIDENCE/aa-start.txt"

child_pid=""
for attempt in {1..30}; do
    child_pid=$(dev "pidof com.example.helloworld" | tr -d '\r')
    if [[ -n "$child_pid" ]]; then
        break
    fi
    sleep 1
done

dev "hilog -x" >"$EVIDENCE/hilog.txt"
dev "pidof appspawn-x; pidof com.example.helloworld; ls -lZ /dev/unix/socket/AppSpawnX; grep AppSpawnX /proc/net/unix" \
    >"$EVIDENCE/process-and-socket.txt"
dev "find /data/log/faultlog -maxdepth 3 -type f" \
    >"$EVIDENCE/fault-files.txt"

if [[ -z "$child_pid" ]]; then
    print -u2 "HelloWorld process was not created"
    exit 1
fi

dev "snapshot_display -f /data/local/tmp/helloworld-winning-init.jpeg"
"$HDC" -t "$SERIAL" file recv \
    /data/local/tmp/helloworld-winning-init.jpeg \
    "$EVIDENCE/helloworld-winning-init.jpeg"

print "HelloWorld pid=$child_pid"
print "Screenshot: $EVIDENCE/helloworld-winning-init.jpeg"
