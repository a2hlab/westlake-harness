#!/usr/bin/env zsh
set -eu

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
TARGET="${1:-5583f5be00000000000000000323012c}"
ROOT=/opt/Bridge
SHORT="${TARGET:0:4}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

SRC=/opt/Bridge/.work/d600-deploy-merged-20260726
SYSTEM_ANDROID=$SRC/system/android
CFG=/opt/Bridge/src/adapter/framework/appspawn-x/config/appspawn_x.cfg
REMOTE_GENERATION="/data/a64deploy/fn0103-r18-merged-$SHORT"
REMOTE_SYSTEM_ANDROID="$REMOTE_GENERATION/android"
STAGE="/data/local/tmp/fn0103-r18-merged-$SHORT-$TS"
EVIDENCE="$ROOT/evidence/runs/fn01-fn03-r18-runtime-deploy-$SHORT-$TS"

EXPECTED_ART=69096c9e3ea9b6b376c11fd5a77705792698a80fa2f66b0242e633eef8b8ecdc
EXPECTED_BRIDGE=578a39778cbc94e694e074671f28cbf29933482daaa06ec085b51feb695daed4
EXPECTED_HWUI=f7e6350122e18a53d0110e366ddeec3660f5cdc1f26db5fbab45546d838a2112
EXPECTED_HWUI_SHIM=e97315493ba9edffc638bf25f65e559d7af647af3905b938a636e398cda9ce53
EXPECTED_RTTI=ba12b45ad5c957e57731a15ba8bba6c623282cd02c50c8b1d860f45cbaf78515
EXPECTED_ANDROIDFW=14b51c422c5d41231c29515e7ac16e492bed0a988c69150e068031fbbf8bff73
EXPECTED_MINIKIN=1d688d8f6829bbb3a63ab83234791a9a1436c37731a4aaebd8c277d278401d2a
EXPECTED_FONTS=7818e8a9ef1fb951b085b521317007a8324f8ec872d848d1b4f82321883db093
EXPECTED_APPSPAWN=2987e27fd0bbcf7df35d4a1c67054765fcc95ca08b424d1fdde96d50ba30253a
EXPECTED_CFG=f50ae8fbf36ccbd6c0ba2ce36489b9dfb0aadc5f848fb421d184e866a15605a0
EXPECTED_APPMS=c4855744929acf4c4523e8806d4d6522a1f553a01be184878e3494784d7164d3
EXPECTED_CLIENT=f4df7769e64bf836015b5374f4f98915a1279a88e97f05714879855d55d3658f
EXPECTED_BMS=f8ef078df8a0fa483b60c1a997831a8190448545e141b9568fb14eacaf9da105
EXPECTED_INSTALLS=2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0
EXPECTED_INSTALLER=184d40a56a9116ab87d079413ba31d92e3d45c86a2f9b1088ffc97725ec650f9
EXPECTED_MUSL=fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2

mkdir -p "$EVIDENCE"

dev()
{
    "$HDC" -t "$TARGET" shell "$1"
}

local_hash()
{
    /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'
}

device_hash()
{
    dev "sha256sum $1" | /usr/bin/awk '{print $1}'
}

wait_for_device()
{
    local attempt probe
    for attempt in {1..180}; do
        if "$HDC" list targets | /usr/bin/awk -v serial="$TARGET" \
            '$1 == serial { found=1 } END { exit !found }'; then
            probe=$(dev "echo ok" 2>&1 || true)
            if [[ "$probe" == "ok" ]]; then
                return 0
            fi
        fi
        sleep 1
    done
    print -u2 "ERROR: $TARGET did not return"
    return 1
}

{
    print "target=$TARGET"
    print "run_dir=$EVIDENCE"
    print "src=$SRC"
    print "system_android=$SYSTEM_ANDROID"
    print "cfg=$CFG"
    print "remote_generation=$REMOTE_GENERATION"
    date -u
} >"$EVIDENCE/METADATA.txt"

[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libart.so")" == "$EXPECTED_ART" ]]
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/liboh_adapter_bridge.so")" == "$EXPECTED_BRIDGE" ]]
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libhwui.so")" == "$EXPECTED_HWUI" ]]
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/liboh_hwui_shim.so")" == "$EXPECTED_HWUI_SHIM" ]]
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/liboh_skia_rtti_shim.so")" == "$EXPECTED_RTTI" ]]
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libandroidfw.so")" == "$EXPECTED_ANDROIDFW" ]]
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libminikin.so")" == "$EXPECTED_MINIKIN" ]]
[[ "$(local_hash "$SYSTEM_ANDROID/etc/fonts.xml")" == "$EXPECTED_FONTS" ]]
[[ "$(local_hash "$CFG")" == "$EXPECTED_CFG" ]]
[[ "$(local_hash "$SRC/system/lib64/libappms.z.so")" == "$EXPECTED_APPMS" ]]
[[ "$(local_hash "$SRC/system/lib64/libappspawn_client.z.so")" == "$EXPECTED_CLIENT" ]]
[[ "$(local_hash "$SRC/system/lib64/libbms.z.so")" == "$EXPECTED_BMS" ]]
[[ "$(local_hash "$SRC/system/lib64/libinstalls.z.so")" == "$EXPECTED_INSTALLS" ]]
[[ "$(local_hash "$SRC/system/lib64/libapk_installer.so")" == "$EXPECTED_INSTALLER" ]]
[[ "$(device_hash /system/bin/appspawn-x)" == "$EXPECTED_APPSPAWN" ]]
[[ "$(/usr/bin/find "$SYSTEM_ANDROID/framework/arm64" -maxdepth 1 -type f | /usr/bin/wc -l | /usr/bin/tr -d ' ')" == "27" ]]

wait_for_device
dev "cat /proc/sys/kernel/random/boot_id; param get const.ohos.fullname; getenforce; cat /proc/uptime" \
    >"$EVIDENCE/pre-deploy-identity.txt"

"$HDC" -t "$TARGET" target mount >"$EVIDENCE/target-mount-1.txt" 2>&1
dev "aa force-stop com.a2hlab.bridge.fn0103.alpha 2>/dev/null || true; aa force-stop com.a2hlab.bridge.fn0103.beta 2>/dev/null || true; aa force-stop com.a2hlab.bridge.fn0103.gamma 2>/dev/null || true"
dev "mkdir -p $STAGE $REMOTE_GENERATION /system/etc/init"
"$HDC" -t "$TARGET" file send "$SYSTEM_ANDROID" "$REMOTE_GENERATION" >"$EVIDENCE/send-systemandroid.txt" 2>&1
"$HDC" -t "$TARGET" file send "$CFG" "$STAGE/appspawn_x.cfg" >"$EVIDENCE/send-appspawn-cfg.txt" 2>&1
"$HDC" -t "$TARGET" file send "$SRC/system/lib64/libappms.z.so" "$STAGE/libappms.z.so" >"$EVIDENCE/send-libappms.txt" 2>&1
"$HDC" -t "$TARGET" file send "$SRC/system/lib64/libappspawn_client.z.so" "$STAGE/libappspawn_client.z.so" >"$EVIDENCE/send-libappspawn-client.txt" 2>&1
"$HDC" -t "$TARGET" file send "$SRC/system/lib64/libbms.z.so" "$STAGE/libbms.z.so" >"$EVIDENCE/send-libbms.txt" 2>&1
"$HDC" -t "$TARGET" file send "$SRC/system/lib64/libinstalls.z.so" "$STAGE/libinstalls.z.so" >"$EVIDENCE/send-libinstalls.txt" 2>&1
"$HDC" -t "$TARGET" file send "$SRC/system/lib64/libapk_installer.so" "$STAGE/libapk_installer.so" >"$EVIDENCE/send-libapk-installer.txt" 2>&1

dev "begetctl stop_service appspawn-x >/dev/null 2>&1 || true"
dev "cp $STAGE/libappms.z.so /system/lib64/libappms.z.so"
dev "cp $STAGE/libappspawn_client.z.so /system/lib64/libappspawn_client.z.so"
dev "cp $STAGE/libbms.z.so /system/lib64/libbms.z.so"
dev "cp $STAGE/libinstalls.z.so /system/lib64/libinstalls.z.so"
dev "cp $STAGE/libapk_installer.so /system/lib64/libapk_installer.so"
dev "cp $STAGE/appspawn_x.cfg /system/etc/init/appspawn_x.cfg"
dev "ln -sf /lib/ld-musl-aarch64.so.1 /system/lib/libc_musl.so"
dev "chown root:root /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so /system/etc/init/appspawn_x.cfg"
dev "chmod 0755 /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so"
dev "chmod 0550 /system/etc/init/appspawn_x.cfg"
dev "restorecon -F /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so 2>/dev/null || true"
dev "chcon u:object_r:system_etc_file:s0 /system/etc/init/appspawn_x.cfg 2>/dev/null || restorecon -F /system/etc/init/appspawn_x.cfg"
dev "chcon -h u:object_r:system_lib_file:s0 /system/lib/libc_musl.so 2>/dev/null || true"

[[ "$(device_hash /system/bin/appspawn-x)" == "$EXPECTED_APPSPAWN" ]]
[[ "$(device_hash /system/etc/init/appspawn_x.cfg)" == "$EXPECTED_CFG" ]]
[[ "$(device_hash /system/lib64/libappms.z.so)" == "$EXPECTED_APPMS" ]]
[[ "$(device_hash /system/lib64/libappspawn_client.z.so)" == "$EXPECTED_CLIENT" ]]
[[ "$(device_hash /system/lib64/libbms.z.so)" == "$EXPECTED_BMS" ]]
[[ "$(device_hash /system/lib64/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]]
[[ "$(device_hash /system/lib64/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]]
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/libart.so")" == "$EXPECTED_ART" ]]
[[ "$(device_hash /system/lib/libc_musl.so)" == "$EXPECTED_MUSL" ]]
dev "sync"

"$HDC" -t "$TARGET" target boot >"$EVIDENCE/target-boot.txt" 2>&1 || true
wait_for_device
sleep 12

"$HDC" -t "$TARGET" target mount >"$EVIDENCE/target-mount-2.txt" 2>&1
dev "mkdir -p /system/android"
dev "umount /system/android 2>/dev/null || true"
dev "mount --bind $REMOTE_SYSTEM_ANDROID /system/android"
dev "if [ -f /system/android/framework/arm64/boot.art ] && [ ! -e /system/android/framework/boot.art ]; then ln -sf arm64/boot.art /system/android/framework/boot.art; fi"
dev "find /system/android -exec chcon u:object_r:system_file:s0 {} \\;"
dev "find /system/android/lib64 -exec chcon u:object_r:system_lib_file:s0 {} \\;"
dev "for f in /system/android/framework/arm64/boot*.art /system/android/framework/arm64/boot*.oat /system/android/framework/arm64/boot*.vdex; do chcon u:object_r:system_lib_file:s0 \$f; done"
dev "cp /system/android/etc/fonts.xml /system/etc/fonts.xml"
dev "chcon u:object_r:system_fonts_file:s0 /system/android/etc/fonts.xml /system/etc/fonts.xml 2>/dev/null || true"
dev "ln -sf /lib/ld-musl-aarch64.so.1 /system/lib/libc_musl.so"
dev "chcon -h u:object_r:system_lib_file:s0 /system/lib/libc_musl.so 2>/dev/null || true"
dev "setenforce 0"
dev "param set persist.sys.abilityms.timeout_unit_time_ratio 20"
dev "param set ro.product.cpu.abilist arm64-v8a"
dev "param set ro.product.cpu.abilist64 arm64-v8a"
dev "power-shell wakeup; power-shell timeout -o 86400000; power-shell display -o 230"
dev "sync"

dev "
cat /proc/sys/kernel/random/boot_id
param get const.ohos.fullname
getenforce
cat /proc/uptime
param get persist.sys.abilityms.timeout_unit_time_ratio
sha256sum \
  /system/bin/appspawn-x \
  /system/etc/init/appspawn_x.cfg \
  /system/android/lib64/libart.so \
  /system/android/lib64/liboh_adapter_bridge.so \
  /system/android/lib64/libhwui.so \
  /system/android/lib64/liboh_hwui_shim.so \
  /system/android/lib64/liboh_skia_rtti_shim.so \
  /system/android/lib64/libandroidfw.so \
  /system/android/lib64/libminikin.so \
  /system/lib64/libappms.z.so \
  /system/lib64/libappspawn_client.z.so \
  /system/lib64/libbms.z.so \
  /system/lib64/libinstalls.z.so \
  /system/lib64/libapk_installer.so \
  /system/lib/ld-musl-aarch64.so.1 \
  /system/lib/libc_musl.so \
  /system/etc/fonts.xml
grep -n cgroup /system/etc/init/appspawn_x.cfg
readlink -f /system/lib/libc_musl.so
ls -lZ /system/bin/appspawn-x /system/etc/init/appspawn_x.cfg /system/lib/libc_musl.so /dev/unix/socket/AppSpawnX 2>/dev/null || true
grep AppSpawnX /proc/net/unix 2>/dev/null || true
cat /proc/cgroups
mount | grep cgroup
" >"$EVIDENCE/post-deploy-receipt.txt"

[[ "$(device_hash /system/android/lib64/libart.so)" == "$EXPECTED_ART" ]]
[[ "$(device_hash /system/android/lib64/liboh_adapter_bridge.so)" == "$EXPECTED_BRIDGE" ]]
[[ "$(device_hash /system/android/lib64/libhwui.so)" == "$EXPECTED_HWUI" ]]
[[ "$(device_hash /system/android/lib64/liboh_hwui_shim.so)" == "$EXPECTED_HWUI_SHIM" ]]
[[ "$(device_hash /system/android/lib64/liboh_skia_rtti_shim.so)" == "$EXPECTED_RTTI" ]]
[[ "$(device_hash /system/android/lib64/libandroidfw.so)" == "$EXPECTED_ANDROIDFW" ]]
[[ "$(device_hash /system/android/lib64/libminikin.so)" == "$EXPECTED_MINIKIN" ]]
[[ "$(device_hash /system/etc/fonts.xml)" == "$EXPECTED_FONTS" ]]
[[ "$(device_hash /system/etc/init/appspawn_x.cfg)" == "$EXPECTED_CFG" ]]
[[ "$(device_hash /system/lib64/libappms.z.so)" == "$EXPECTED_APPMS" ]]
[[ "$(device_hash /system/lib64/libappspawn_client.z.so)" == "$EXPECTED_CLIENT" ]]
[[ "$(device_hash /system/lib64/libbms.z.so)" == "$EXPECTED_BMS" ]]
[[ "$(device_hash /system/lib64/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]]
[[ "$(device_hash /system/lib64/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]]

{
    print "experiment: fn01-fn03-r18-runtime-deploy"
    print "target: $TARGET"
    print "device_write: true"
    print "rebooted: true"
    print "cfg_cgroup_false: true"
    print "runtime_generation: d600-deploy-merged-20260726"
    print "verdict: PASS"
    print "claim_boundary: RUNTIME_AND_SYSTEM_SERVICE_DEPLOY_ONLY"
} >"$EVIDENCE/DEPLOY-VERDICT.yaml"

print "PASS: fn01-fn03 r18/merged runtime deployed"
print "Evidence=$EVIDENCE"
