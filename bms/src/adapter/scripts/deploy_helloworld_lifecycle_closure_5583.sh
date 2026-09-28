#!/bin/zsh
set -eu

print -u2 "REFUSED: this Yue-M1 lifecycle set is quarantined after causing a boot failure on the current R6/OH6.1 image."
print -u2 "Reason: internal five-file consistency did not prove firmware/BMS/route generation compatibility."
exit 78

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
SERIAL=5583f5be00000000000000000323012c
ADAPTER=/opt/Bridge/src/adapter
CLOSURE=$ADAPTER/out/helloworld-r6-lifecycle-yue-m1-20260724/platformsdk
STAGE=/data/local/tmp/alexbridge-lifecycle-yue-m1

typeset -A EXPECTED
EXPECTED[libabilityms.z.so]=53b324d62db4c767f2e62b4362ef2e7b1165edd36cc459d366f675548727722e
EXPECTED[libmission_list.z.so]=8b17da4e24d537b9e2b71fa54590cb0ebcbb669574de7dbce0ea48bd4e27b773
EXPECTED[libscene_session.z.so]=6b855a99b5cc603f15ed005724141b6b84c3d81d6a7d746749d7ba9bf2412c54
EXPECTED[libscene_session_manager.z.so]=b5464f5fbe82e7529bc6d32c49d4f514a329336aeccfaea09d7c4d0a555c64d8
EXPECTED[libappexecfwk_common.z.so]=0230977cea0490bcab462ccf79638946ef3194076d4d91d8c1605a7baa25ebf2

FILES=(
    libabilityms.z.so
    libmission_list.z.so
    libscene_session.z.so
    libscene_session_manager.z.so
    libappexecfwk_common.z.so
)

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
    for attempt in {1..100}; do
        if require_device && dev "echo UP" 2>/dev/null | grep -q UP; then
            return 0
        fi
        sleep 3
    done
    return 1
}

check_local()
{
    local name=$1
    local actual
    actual=$(/usr/bin/shasum -a 256 "$CLOSURE/$name" | /usr/bin/awk '{print $1}')
    [[ "$actual" == "${EXPECTED[$name]}" ]] || {
        print -u2 "local hash mismatch: $name actual=$actual expected=${EXPECTED[$name]}"
        exit 1
    }
    file "$CLOSURE/$name" | grep -q "ELF 64-bit.*ARM aarch64"
}

check_device()
{
    local name=$1
    local actual
    actual=$(dev "sha256sum /system/lib64/platformsdk/$name" | awk '{print $1}')
    [[ "$actual" == "${EXPECTED[$name]}" ]] || {
        print -u2 "device hash mismatch: $name actual=$actual expected=${EXPECTED[$name]}"
        exit 1
    }
}

require_device
for name in "${FILES[@]}"; do
    check_local "$name"
done

"$HDC" -t "$SERIAL" target mount
dev "mkdir -p $STAGE"
for name in "${FILES[@]}"; do
    "$HDC" -t "$SERIAL" file send "$CLOSURE/$name" "$STAGE/$name"
    dev "sha256sum $STAGE/$name"
done

dev "begetctl stop_service foundation 2>/dev/null || true"
for name in "${FILES[@]}"; do
    dev "cp $STAGE/$name /system/lib64/platformsdk/$name"
    dev "chown root:root /system/lib64/platformsdk/$name"
    dev "chmod 0755 /system/lib64/platformsdk/$name"
    dev "restorecon /system/lib64/platformsdk/$name"
    check_device "$name"
done
dev "sync"
"$HDC" -t "$SERIAL" target boot

wait_device
sleep 15
"$HDC" -t "$SERIAL" target mount
for name in "${FILES[@]}"; do
    check_device "$name"
done

dev "cat /proc/sys/kernel/random/boot_id"
dev "sha256sum /system/lib64/platformsdk/libabilityms.z.so /system/lib64/platformsdk/libmission_list.z.so /system/lib64/platformsdk/libscene_session.z.so /system/lib64/platformsdk/libscene_session_manager.z.so /system/lib64/platformsdk/libappexecfwk_common.z.so"
