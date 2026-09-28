#!/bin/zsh
set -eu

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
SERIAL=5eab586000000000000000001123012c
ADAPTER=/opt/Bridge/src/adapter
GENERATION=$ADAPTER/out/helloworld-r6-route-hanbing-closure-20260724T202644HKT
STAGE=/data/local/tmp/alexbridge-route-hanbing-20260724
EXPECTED_APPMS=c4855744929acf4c4523e8806d4d6522a1f553a01be184878e3494784d7164d3
EXPECTED_CLIENT=f4df7769e64bf836015b5374f4f98915a1279a88e97f05714879855d55d3658f

dev()
{
    "$HDC" -t "$SERIAL" shell "$1"
}

wait_device()
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
[[ "$(dev 'param get const.ohos.fullname' | /usr/bin/tr -d '\r ')" == "OpenHarmony-6.1.0.31" ]]

[[ "$(local_hash "$GENERATION/lib64/libappms.z.so")" == "$EXPECTED_APPMS" ]]
[[ "$(local_hash "$GENERATION/lib64/libappspawn_client.z.so")" == "$EXPECTED_CLIENT" ]]
/usr/bin/file "$GENERATION/lib64/libappms.z.so" "$GENERATION/lib64/libappspawn_client.z.so" |
    /usr/bin/grep -q "ELF 64-bit.*ARM aarch64"
/usr/bin/strings "$GENERATION/lib64/libappms.z.so" |
    /usr/bin/grep -q "StartProcess: routing to appspawn-x for Android app"
/usr/bin/strings "$GENERATION/lib64/libappspawn_client.z.so" |
    /usr/bin/grep -q "AppSpawnX"

# Fail closed: the unchanged lower half must already be byte-identical.
[[ "$(device_hash /system/lib64/libappspawn_client.z.so)" == "$EXPECTED_CLIENT" ]]

"$HDC" -t "$SERIAL" target mount
dev "mkdir -p $STAGE"
"$HDC" -t "$SERIAL" file send "$GENERATION/lib64/libappms.z.so" "$STAGE/libappms.z.so"
[[ "$(device_hash "$STAGE/libappms.z.so")" == "$EXPECTED_APPMS" ]]

dev "cp $STAGE/libappms.z.so /system/lib64/libappms.z.so"
dev "chown root:root /system/lib64/libappms.z.so"
dev "chmod 0755 /system/lib64/libappms.z.so"
dev "restorecon /system/lib64/libappms.z.so"
[[ "$(device_hash /system/lib64/libappms.z.so)" == "$EXPECTED_APPMS" ]]
dev "sync"
"$HDC" -t "$SERIAL" target boot

wait_device
[[ "$(device_hash /system/lib64/libappms.z.so)" == "$EXPECTED_APPMS" ]]
[[ "$(device_hash /system/lib64/libappspawn_client.z.so)" == "$EXPECTED_CLIENT" ]]
dev "cat /proc/sys/kernel/random/boot_id"
dev "sha256sum /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so"
