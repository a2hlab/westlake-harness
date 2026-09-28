#!/bin/zsh
set -eu

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
SERIAL=5eab586000000000000000001123012c
ADAPTER=/opt/Bridge/src/adapter
GENERATION=$ADAPTER/out/helloworld-r6-package-closure-current-20260724T2029HKT
STAGE=/data/local/tmp/alexbridge-package-current-20260724

EXPECTED_ROUTE=c4855744929acf4c4523e8806d4d6522a1f553a01be184878e3494784d7164d3
EXPECTED_STOCK_BMS=92ae61bd98c2dc6411f76a9c8bb1632c745ebe84782eb70fe676990b54e878ce
EXPECTED_BMS=f8ef078df8a0fa483b60c1a997831a8190448545e141b9568fb14eacaf9da105
EXPECTED_INSTALLS=2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0
EXPECTED_INSTALLER=184d40a56a9116ab87d079413ba31d92e3d45c86a2f9b1088ffc97725ec650f9
EXPECTED_APK=2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd

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
[[ "$(device_hash /system/lib64/libappms.z.so)" == "$EXPECTED_ROUTE" ]]
[[ "$(device_hash /system/lib64/libbms.z.so)" == "$EXPECTED_STOCK_BMS" ]]
[[ "$(device_hash /system/lib64/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]]

[[ "$(local_hash "$GENERATION/lib64/libbms.z.so")" == "$EXPECTED_BMS" ]]
[[ "$(local_hash "$GENERATION/lib64/libinstalls.z.so")" == "$EXPECTED_INSTALLS" ]]
[[ "$(local_hash "$GENERATION/lib64/libapk_installer.so")" == "$EXPECTED_INSTALLER" ]]
[[ "$(local_hash "$GENERATION/app/HelloWorld.apk")" == "$EXPECTED_APK" ]]
/usr/bin/file "$GENERATION"/lib64/* | /usr/bin/grep -q "ELF 64-bit.*ARM aarch64"

"$HDC" -t "$SERIAL" target mount
dev "mkdir -p $STAGE"
"$HDC" -t "$SERIAL" file send "$GENERATION/lib64/libbms.z.so" "$STAGE/libbms.z.so"
"$HDC" -t "$SERIAL" file send "$GENERATION/lib64/libapk_installer.so" "$STAGE/libapk_installer.so"
"$HDC" -t "$SERIAL" file send "$GENERATION/app/HelloWorld.apk" "$STAGE/HelloWorld.apk"
[[ "$(device_hash "$STAGE/libbms.z.so")" == "$EXPECTED_BMS" ]]
[[ "$(device_hash "$STAGE/libapk_installer.so")" == "$EXPECTED_INSTALLER" ]]
[[ "$(device_hash "$STAGE/HelloWorld.apk")" == "$EXPECTED_APK" ]]

dev "cp $STAGE/libbms.z.so /system/lib64/libbms.z.so"
dev "cp $STAGE/libapk_installer.so /system/lib64/libapk_installer.so"
dev "chown root:root /system/lib64/libbms.z.so /system/lib64/libapk_installer.so"
dev "chmod 0755 /system/lib64/libbms.z.so /system/lib64/libapk_installer.so"
dev "restorecon /system/lib64/libbms.z.so"
dev "restorecon /system/lib64/libapk_installer.so"
[[ "$(device_hash /system/lib64/libbms.z.so)" == "$EXPECTED_BMS" ]]
[[ "$(device_hash /system/lib64/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]]
dev "sync"
"$HDC" -t "$SERIAL" target boot

wait_device
[[ "$(device_hash /system/lib64/libappms.z.so)" == "$EXPECTED_ROUTE" ]]
[[ "$(device_hash /system/lib64/libbms.z.so)" == "$EXPECTED_BMS" ]]
[[ "$(device_hash /system/lib64/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]]
[[ "$(device_hash /system/lib64/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]]

dev "hilog -r"
dev "bm install -p $STAGE/HelloWorld.apk"
dev "bm dump -n com.example.helloworld"
dev "cat /proc/sys/kernel/random/boot_id"
