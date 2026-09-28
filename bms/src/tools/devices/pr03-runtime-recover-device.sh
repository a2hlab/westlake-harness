#!/system/bin/sh
# PR03 developer recovery hook. Executed once by OpenHarmony init on every boot.

set -u
PATH=/system/bin:/vendor/bin:/chipset/bin:/bin:/usr/bin
export PATH

PAYLOAD=/data/pr03-74e6-portable
GENERATION=74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d
ROUTE_TARGET=/system/lib64/westlake/route-a/$GENERATION
STATE_DIR=/data/service/el1/public/appspawnx
RECEIPT=$STATE_DIR/pr03-boot-recovery.txt
TMP=$RECEIPT.tmp
APPSPAWN_SHA=43d5a319fa43e30fb712c2e39d29ba55e4bf82d171e97af1e6da9fcacc28920c
CHILD_SHA=66afb06c10db5e986d294a465cf787f4be3302ce6be3a17d49309b368b1ec090
PROVIDER_SHA=6787ea7d3c4ec0a382621360e3434885b0167446e22217a439b8d17745e54630
ADAPTER_SHA=7db99e1b760cf843b1a99db1382a3299f189c8cbca786ec411b7c35a2af6ffb9
RUNTIME_SHA=9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db
RUNTIME_JAR_SHA=06141543bec26c5036931d8d2d71b0efaa45d5ffd73434557d165cd42672be0d
PTHREAD_BRIDGE_SHA=cce31e656e233b665c9ad16051ade7292319b326787ee55d3aa9327960b3316a
NATIVE_LOADER_SHA=f8a5c1921cb95f62396568cd30a703883ec496f4494478201b4d64b16ad9daca
ROUTE_NATIVE_LOADER_SHA=eddeb87ef17754b28f83cd732fe5b606504005af0c77b21923ac62c20e3c34ea
LIBANDROID_SHA=6e9c0c2ced8448fb03ff9cdd36bcf426d86db2ce014e7dd8c3884821d11c590b

mkdir -p "$STATE_DIR"
: > "$TMP"
echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)" >> "$TMP"
echo "generation=$GENERATION" >> "$TMP"
echo "state=RESTORING" >> "$TMP"

fail()
{
    echo "failed_step=$1" >> "$TMP"
    echo "state=FAILED" >> "$TMP"
    mv "$TMP" "$RECEIPT"
    exit 1
}

appspawn_listener_flags()
{
    while read addr refs protocol flags type state inode path; do
        if [ "$path" = /dev/unix/socket/AppSpawnX ]; then
            echo "$flags"
            return 0
        fi
    done < /proc/net/unix
    return 1
}

# This service is condition-started by bootevent.boot.completed, after /data is
# mounted.  Enter the same permissive developer mode as the accepted PR03 run
# before invoking parameter/service utilities; the su service domain cannot
# reliably execute those helpers while global enforcing is still active.
setenforce 0 >/dev/null 2>&1 || fail SET_PERMISSIVE
selinux_mode=$(getenforce 2>/dev/null)
case "$selinux_mode" in Permissive*) selinux_mode=Permissive ;; *) fail SET_PERMISSIVE ;; esac
echo "selinux_mode=$selinux_mode" >> "$TMP"
param set sys.pr03.runtime.ready false >/dev/null 2>&1 || true

[ -d "$PAYLOAD/android" ] || fail MISSING_ANDROID
[ -d "$PAYLOAD/route" ] || fail MISSING_ROUTE
[ -x "$PAYLOAD/runtime/appspawn-x" ] || fail MISSING_APPSPAWN
[ -f "$PAYLOAD/runtime/libwestlake_android_child.z.so" ] || fail MISSING_CHILD
[ "$(sha256sum "$PAYLOAD/runtime/appspawn-x" | cut -d ' ' -f 1)" = "$APPSPAWN_SHA" ] || fail APPSPAWN_IDENTITY
[ "$(sha256sum "$PAYLOAD/runtime/libwestlake_android_child.z.so" | cut -d ' ' -f 1)" = "$CHILD_SHA" ] || fail CHILD_IDENTITY
[ "$(sha256sum "$PAYLOAD/route/libwestlake_android_runtime_provider.so" | cut -d ' ' -f 1)" = "$PROVIDER_SHA" ] || fail PROVIDER_IDENTITY
[ "$(sha256sum "$PAYLOAD/android/lib64/liboh_adapter_bridge.so" | cut -d ' ' -f 1)" = "$ADAPTER_SHA" ] || fail ADAPTER_IDENTITY
[ "$(sha256sum "$PAYLOAD/android/lib64/liboh_android_runtime.so" | cut -d ' ' -f 1)" = "$RUNTIME_SHA" ] || fail RUNTIME_IDENTITY
[ "$(sha256sum "$PAYLOAD/android/framework/oh-adapter-runtime.jar" | cut -d ' ' -f 1)" = "$RUNTIME_JAR_SHA" ] || fail RUNTIME_JAR_IDENTITY
[ "$(sha256sum "$PAYLOAD/android/lib64/libwestlake_bionic_pthread_bridge.so" | cut -d ' ' -f 1)" = "$PTHREAD_BRIDGE_SHA" ] || fail PTHREAD_BRIDGE_IDENTITY
[ "$(sha256sum "$PAYLOAD/android/lib64/libnativeloader.so" | cut -d ' ' -f 1)" = "$NATIVE_LOADER_SHA" ] || fail NATIVE_LOADER_IDENTITY
[ "$(sha256sum "$PAYLOAD/route/libnativeloader.so" | cut -d ' ' -f 1)" = "$ROUTE_NATIVE_LOADER_SHA" ] || fail ROUTE_NATIVE_LOADER_IDENTITY
[ "$(sha256sum "$PAYLOAD/android/lib64/libandroid.so" | cut -d ' ' -f 1)" = "$LIBANDROID_SHA" ] || fail LIBANDROID_IDENTITY

# The condition job is the primary sequencing guard. Assert it again so a
# manual early start fails closed instead of mounting over native boot.
boot_completed=$(param get bootevent.boot.completed 2>/dev/null)
case "$boot_completed" in true*) ;; *) fail HOST_BOOT_TIMEOUT ;; esac
echo "host_boot_completed=true" >> "$TMP"

# appspawn_x.cfg is deliberately ondemand.  Init owns and listen()s this socket
# before the Android daemon exists, then passes the control fd to the daemon on
# the first AMS connection.  Calling stop_service here when no daemon exists
# tears down that listener and makes the first post-boot Android request use a
# stale client generation.  A clean boot must therefore have the init listener
# but no appspawn-x process; any process here means recovery lost the race and
# must fail closed instead of remounting beneath a live parent or child.
[ -z "$(pidof appspawn-x 2>/dev/null)" ] || fail APPSPAWN_STARTED_BEFORE_RECOVERY
[ -S /dev/unix/socket/AppSpawnX ] || fail MISSING_INIT_APPSPAWN_LISTENER
[ "$(appspawn_listener_flags 2>/dev/null)" = 00010000 ] || fail INIT_APPSPAWN_NOT_LISTENING
[ "$(stat -c '%a:%u:%g:%C' /dev/unix/socket/AppSpawnX 2>/dev/null)" = \
    "660:0:6005:u:object_r:appspawn_socket:s0" ] || fail INIT_APPSPAWN_LISTENER_IDENTITY
echo "appspawn_transport=INIT_ONDEMAND_LISTENER" >> "$TMP"

mount_count_for_targets()
{
    count=0
    for target in \
        /system/lib64/libwestlake_thread_guard_registry.so \
        /system/etc/sandbox/appdata-sandbox.json \
        /system/bin/appspawn-x \
        /system/lib64/appspawn/libwestlake_android_child.z.so \
        /system/android/framework/oh-adapter-runtime.jar \
        /system/android/lib64/liblzma.so \
        "$ROUTE_TARGET" \
        /system/android; do
        found=$(grep -F -c " $target " /proc/self/mountinfo 2>/dev/null || true)
        count=$((count + found))
    done
    echo "$count"
}

# A previous interrupted/manual recovery may have stacked a parent bind over
# a child bind.  In that state the hidden child cannot be addressed by path;
# peel one visible layer per pass until the entire old closure is gone.
for pass in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16; do
    before=$(mount_count_for_targets)
    [ "$before" = 0 ] && break
    for target in \
        /system/lib64/libwestlake_thread_guard_registry.so \
        /system/etc/sandbox/appdata-sandbox.json \
        /system/bin/appspawn-x \
        /system/lib64/appspawn/libwestlake_android_child.z.so \
        /system/android/framework/oh-adapter-runtime.jar \
        /system/android/lib64/liblzma.so \
        "$ROUTE_TARGET" \
        /system/android; do
        grep -F " $target " /proc/self/mountinfo >/dev/null 2>&1 && \
            umount "$target" 2>/dev/null || true
    done
    after=$(mount_count_for_targets)
    [ "$after" -lt "$before" ] || fail UNMOUNT_STALLED
done
[ "$(mount_count_for_targets)" = 0 ] || fail UNMOUNT_DRAIN

[ -d /system/android ] || fail MISSING_ANDROID_MOUNTPOINT
[ -d /system/lib64/appspawn ] || fail MISSING_CHILD_MOUNTPOINT
[ -d "$ROUTE_TARGET" ] || fail MISSING_ROUTE_MOUNTPOINT
[ -d /system/etc/sandbox ] || fail MISSING_SANDBOX_MOUNTPOINT
[ -e /system/bin/appspawn-x ] || fail MISSING_APPSPAWN_MOUNTPOINT
[ -e /system/lib64/appspawn/libwestlake_android_child.z.so ] || fail MISSING_CHILD_FILE_MOUNTPOINT
[ -e /system/etc/sandbox/appdata-sandbox.json ] || fail MISSING_SANDBOX_FILE_MOUNTPOINT
[ -e /system/lib64/libwestlake_thread_guard_registry.so ] || fail MISSING_TGR_MOUNTPOINT

mount --bind "$PAYLOAD/android" /system/android || fail MOUNT_ANDROID
mount --bind "$PAYLOAD/route" "$ROUTE_TARGET" || fail MOUNT_ROUTE
mount --bind "$PAYLOAD/route/liblzma.so" /system/android/lib64/liblzma.so || fail MOUNT_LZMA
mount --bind "$PAYLOAD/runtime/libwestlake_android_child.z.so" /system/lib64/appspawn/libwestlake_android_child.z.so || fail MOUNT_CHILD
mount --bind "$PAYLOAD/runtime/appspawn-x" /system/bin/appspawn-x || fail MOUNT_APPSPAWN
mount --bind "$PAYLOAD/runtime/appdata-sandbox.json" /system/etc/sandbox/appdata-sandbox.json || fail MOUNT_SANDBOX
mount --bind "$PAYLOAD/route/libwestlake_thread_guard_registry.so" /system/lib64/libwestlake_thread_guard_registry.so || fail MOUNT_TGR

find /system/android -type d -exec chmod 0755 {} \;
find /system/android -exec chcon u:object_r:system_file:s0 {} \;
find /system/android/lib64 -exec chcon u:object_r:system_lib_file:s0 {} \;
find "$ROUTE_TARGET" -type d -exec chmod 0755 {} \;
find "$ROUTE_TARGET" -exec chcon u:object_r:system_lib_file:s0 {} \;
chmod 0755 /system/bin/appspawn-x /system/lib64/appspawn/libwestlake_android_child.z.so
chmod 0644 /system/etc/sandbox/appdata-sandbox.json /system/lib64/libwestlake_thread_guard_registry.so /system/android/lib64/liblzma.so
chcon u:object_r:appspawn_exec:s0 /system/bin/appspawn-x
chcon u:object_r:system_lib_file:s0 /system/lib64/appspawn/libwestlake_android_child.z.so /system/lib64/libwestlake_thread_guard_registry.so /system/android/lib64/liblzma.so
chcon u:object_r:system_etc_file:s0 /system/etc/sandbox/appdata-sandbox.json

if [ -f /system/android/framework/arm64/boot.art ] && [ ! -e /system/android/framework/boot.art ]; then
    ln -sf arm64/boot.art /system/android/framework/boot.art
fi
for f in /system/android/framework/arm64/boot*.art /system/android/framework/arm64/boot*.oat /system/android/framework/arm64/boot*.vdex; do
    chcon u:object_r:system_lib_file:s0 "$f"
done
chcon u:object_r:system_fonts_file:s0 /system/android/etc/fonts.xml 2>/dev/null || true

param set persist.sys.abilityms.support_anco_app true
param set persist.sys.abilityms.timeout_unit_time_ratio 20
param set persist.sys.prefork.enable false
param set ro.product.cpu.abilist arm64-v8a >/dev/null 2>&1 || true
param set ro.product.cpu.abilist64 arm64-v8a >/dev/null 2>&1 || true
chmod 0666 /dev/mali0
chcon u:object_r:dev_mali:s0 /dev/mali0

[ "$(grep -c ' /pr03-74e6-portable/' /proc/self/mountinfo)" = 7 ] || fail MOUNT_COUNT
[ -f /system/android/framework/framework.jar ] || fail MISSING_FRAMEWORK_AFTER_MOUNT
[ "$(sha256sum /system/bin/appspawn-x | cut -d ' ' -f 1)" = "$APPSPAWN_SHA" ] || fail MOUNTED_APPSPAWN_IDENTITY
[ "$(sha256sum /system/lib64/appspawn/libwestlake_android_child.z.so | cut -d ' ' -f 1)" = "$CHILD_SHA" ] || fail MOUNTED_CHILD_IDENTITY
[ "$(sha256sum "$ROUTE_TARGET/libwestlake_android_runtime_provider.so" | cut -d ' ' -f 1)" = "$PROVIDER_SHA" ] || fail MOUNTED_PROVIDER_IDENTITY
[ "$(sha256sum /system/android/lib64/liboh_adapter_bridge.so | cut -d ' ' -f 1)" = "$ADAPTER_SHA" ] || fail MOUNTED_ADAPTER_IDENTITY
[ "$(sha256sum /system/android/lib64/liboh_android_runtime.so | cut -d ' ' -f 1)" = "$RUNTIME_SHA" ] || fail MOUNTED_RUNTIME_IDENTITY
[ "$(sha256sum /system/android/framework/oh-adapter-runtime.jar | cut -d ' ' -f 1)" = "$RUNTIME_JAR_SHA" ] || fail MOUNTED_RUNTIME_JAR_IDENTITY
[ "$(sha256sum /system/android/lib64/libwestlake_bionic_pthread_bridge.so | cut -d ' ' -f 1)" = "$PTHREAD_BRIDGE_SHA" ] || fail MOUNTED_PTHREAD_BRIDGE_IDENTITY
[ "$(sha256sum /system/android/lib64/libnativeloader.so | cut -d ' ' -f 1)" = "$NATIVE_LOADER_SHA" ] || fail MOUNTED_NATIVE_LOADER_IDENTITY
[ "$(sha256sum "$ROUTE_TARGET/libnativeloader.so" | cut -d ' ' -f 1)" = "$ROUTE_NATIVE_LOADER_SHA" ] || fail MOUNTED_ROUTE_NATIVE_LOADER_IDENTITY
[ "$(sha256sum /system/android/lib64/libandroid.so | cut -d ' ' -f 1)" = "$LIBANDROID_SHA" ] || fail MOUNTED_LIBANDROID_IDENTITY
echo "touch_closure=READY" >> "$TMP"

# Mounting the candidate must not consume or replace the init-owned listener.
# The first real APK launch is the only authorized trigger for the daemon.
[ -z "$(pidof appspawn-x 2>/dev/null)" ] || fail APPSPAWN_RACED_RECOVERY
[ "$(appspawn_listener_flags 2>/dev/null)" = 00010000 ] || fail INIT_APPSPAWN_LISTENER_LOST
echo "appspawn_parent=ONDEMAND_NOT_STARTED" >> "$TMP"

param set sys.pr03.runtime.ready true >/dev/null 2>&1 || true
echo "mount_count=7" >> "$TMP"
echo "state=READY" >> "$TMP"
mv "$TMP" "$RECEIPT"
sync
