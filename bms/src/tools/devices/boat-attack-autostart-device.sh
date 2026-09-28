#!/system/bin/sh
# D600 boot hook for the accepted BoatAttack Android APK generation.
# Prepares the fixed runtime after PR03 reports READY, then leaves BoatAttack stopped
# so a presenter can launch it from the desktop. Failures never block boot.

set -u

PATH=/system/bin:/vendor/bin:/chipset/bin:/bin:/usr/bin
export PATH

ROOT=/data/boatattack-autostart
GENERATION=strict-boat-assembled-20260924T074522Z-25403
LAUNCH_MODE=MANUAL
PAYLOAD=$ROOT/generations/$GENERATION
SHARED=$PAYLOAD/shared
PRIVATE=$PAYLOAD/private
DISABLED=$ROOT/DISABLED
RECEIPT=$ROOT/receipt.env
TMP=$ROOT/receipt.env.tmp.$$
LAUNCH_LOG=$ROOT/launch.txt

BUNDLE=com.Unity3d.BoatAttackDay
APP_ROOT=/data/app/el1/bundle/public/$BUNDLE/android
APP_DATA=/data/app/el1/100/base/$BUNDLE
APK=$APP_ROOT/base.apk
LIB_ROOT=$APP_ROOT/lib/arm64-v8a
UNITY_TARGET=$LIB_ROOT/libunity.so
IL2CPP_TARGET=$LIB_ROOT/libil2cpp.so
SIGNAL_TARGET=$LIB_ROOT/libwestlake_bionic_signal_box.so
APPSPAWN_SOCKET=/dev/unix/socket/AppSpawnX
RESOURCE_DB_ROOT=/data/service/el1/public/bms/bundle_resources
# Exact application label from the frozen APK's resources. Keep the handoff
# workaround aligned with the installer's resource-backed label projection.
LAUNCHER_LABEL='BoatAttack'
APP_RESOURCE_KEY=$BUNDLE
ABILITY_RESOURCE_KEY=$BUNDLE/entry/com.unity3d.player.UnityPlayerActivity

ROUTE_GENERATION=74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d
ROUTE_ROOT=/system/lib64/westlake/route-a/$ROUTE_GENERATION
ADAPTER_TARGET=/system/android/lib64/liboh_adapter_bridge.so
PROVIDER_TARGET=$ROUTE_ROOT/libwestlake_android_runtime_provider.so
CHILD_TARGET=/system/lib64/appspawn/libwestlake_android_child.z.so
APPSPAWN_TARGET=/system/bin/appspawn-x
RUNTIME_JAR_TARGET=/system/android/framework/oh-adapter-runtime.jar
PTHREAD_TARGET=/system/android/lib64/libwestlake_bionic_pthread_bridge.so
NATIVE_LOADER_TARGET=/system/android/lib64/libnativeloader.so
ROUTE_NATIVE_LOADER_TARGET=$ROUTE_ROOT/libnativeloader.so
LIBANDROID_TARGET=/system/android/lib64/libandroid.so
RUNTIME_TARGET=/system/android/lib64/liboh_android_runtime.so

APK_SHA=8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444
RAW_UNITY_SHA=1e44603c528af84aed2e4a538d411c119166b9ccadd7aa2abf51ffa97ef47ca2
RAW_IL2CPP_SHA=58555c421de763165225e8bd9e2940f2e5c84515a2c87cdefc0892cae216f4fe
UNITY_SHA=1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac
IL2CPP_SHA=f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746
SIGNAL_SHA=7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da
EMPTY_SHA=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

ADAPTER_SHA=8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e
PROVIDER_SHA=f821d20eaefc798b638192124e3a98683103f3d509c0b66ca1c6946037cccdb0
CHILD_SHA=47f238aede6336ce3770861a6a742e71abc28f35516481299797c05c63149b57
APPSPAWN_SHA=76e6df931905177c8abde4054ee5516cb6d8394c67dce8f79dfadf0847b96747
RUNTIME_JAR_SHA=56e4d4733bb6dc4f260981f51184234522df7a67c0eca01bd1b9ef87369221af
PTHREAD_SHA=db31d6d81c543860449e4e13f94dda6d39acde94ce00e34e7087a4d796e88fc6
NATIVE_LOADER_SHA=fde6f31c6f8911bd5be165d69bc248f47699be435240dc855fa7528c0ba73ccd
RUNTIME_SHA=adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130

mkdir -p "$ROOT"

hash_file()
{
    sha256sum "$1" 2>/dev/null | cut -d ' ' -f 1
}

top_mount_line()
{
    _wanted=$1
    _line=
    while IFS= read -r _record; do
        set -- $_record
        if [ "${5:-}" = "$_wanted" ]; then
            _line=$_record
        fi
    done < /proc/self/mountinfo
    printf '%s\n' "$_line"
}

mount_is_ours()
{
    line=$(top_mount_line "$1")
    [ -n "$line" ] && printf '%s\n' "$line" | grep -Fq /boatattack-autostart/
}

write_header()
{
    : > "$TMP"
    echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)" >> "$TMP"
    echo "generation=$GENERATION" >> "$TMP"
    echo "state=STARTING" >> "$TMP"
}

finish()
{
    echo "state=$1" >> "$TMP"
    mv "$TMP" "$RECEIPT"
    sync
    exit 0
}

fail()
{
    echo "failed_step=$1" >> "$TMP"
    finish FAILED
}

verify_payloads()
{
    [ "$(hash_file "$SHARED/liboh_adapter_bridge.so")" = "$ADAPTER_SHA" ] &&
    [ "$(hash_file "$SHARED/libwestlake_android_runtime_provider.so")" = "$PROVIDER_SHA" ] &&
    [ "$(hash_file "$SHARED/libwestlake_android_child.z.so")" = "$CHILD_SHA" ] &&
    [ "$(hash_file "$SHARED/appspawn-x")" = "$APPSPAWN_SHA" ] &&
    [ "$(hash_file "$SHARED/oh-adapter-runtime.jar")" = "$RUNTIME_JAR_SHA" ] &&
    [ "$(hash_file "$SHARED/libwestlake_bionic_pthread_bridge.so")" = "$PTHREAD_SHA" ] &&
    [ "$(hash_file "$SHARED/libnativeloader.so")" = "$NATIVE_LOADER_SHA" ] &&
    [ "$(hash_file "$SHARED/libandroid.so")" = "$RUNTIME_SHA" ] &&
    [ "$(hash_file "$SHARED/liboh_android_runtime.so")" = "$RUNTIME_SHA" ] &&
    [ "$(hash_file "$PRIVATE/libunity.so")" = "$UNITY_SHA" ] &&
    [ "$(hash_file "$PRIVATE/libil2cpp.so")" = "$IL2CPP_SHA" ] &&
    [ "$(hash_file "$PRIVATE/libwestlake_bionic_signal_box.so")" = "$SIGNAL_SHA" ]
}

shared_ready()
{
    [ "$(hash_file "$ADAPTER_TARGET")" = "$ADAPTER_SHA" ] &&
    [ "$(hash_file "$PROVIDER_TARGET")" = "$PROVIDER_SHA" ] &&
    [ "$(hash_file "$CHILD_TARGET")" = "$CHILD_SHA" ] &&
    [ "$(hash_file "$APPSPAWN_TARGET")" = "$APPSPAWN_SHA" ] &&
    [ "$(hash_file "$RUNTIME_JAR_TARGET")" = "$RUNTIME_JAR_SHA" ] &&
    [ "$(hash_file "$PTHREAD_TARGET")" = "$PTHREAD_SHA" ] &&
    [ "$(hash_file "$NATIVE_LOADER_TARGET")" = "$NATIVE_LOADER_SHA" ] &&
    [ "$(hash_file "$ROUTE_NATIVE_LOADER_TARGET")" = "$NATIVE_LOADER_SHA" ] &&
    [ "$(hash_file "$LIBANDROID_TARGET")" = "$RUNTIME_SHA" ] &&
    [ "$(hash_file "$RUNTIME_TARGET")" = "$RUNTIME_SHA" ]
}

private_ready()
{
    [ "$(hash_file "$UNITY_TARGET")" = "$UNITY_SHA" ] &&
    [ "$(hash_file "$IL2CPP_TARGET")" = "$IL2CPP_SHA" ] &&
    [ "$(hash_file "$SIGNAL_TARGET")" = "$SIGNAL_SHA" ]
}

unmount_ours()
{
    target=$1
    if mount_is_ours "$target"; then
        umount "$target" >/dev/null 2>&1 || return 1
    fi
    return 0
}

rollback_private_mounts()
{
    unmount_ours "$IL2CPP_TARGET" || return 1
    unmount_ours "$UNITY_TARGET" || return 1
    unmount_ours "$SIGNAL_TARGET" || return 1
    if [ "$(hash_file "$SIGNAL_TARGET")" = "$EMPTY_SHA" ]; then
        rm -f "$SIGNAL_TARGET"
    fi
    return 0
}

rollback_shared_mounts()
{
    unmount_ours "$RUNTIME_TARGET" || return 1
    unmount_ours "$LIBANDROID_TARGET" || return 1
    unmount_ours "$ROUTE_NATIVE_LOADER_TARGET" || return 1
    unmount_ours "$NATIVE_LOADER_TARGET" || return 1
    unmount_ours "$PTHREAD_TARGET" || return 1
    unmount_ours "$RUNTIME_JAR_TARGET" || return 1
    unmount_ours "$APPSPAWN_TARGET" || return 1
    unmount_ours "$CHILD_TARGET" || return 1
    unmount_ours "$PROVIDER_TARGET" || return 1
    unmount_ours "$ADAPTER_TARGET" || return 1
    return 0
}

assert_private_targets_clear()
{
    for target in "$SIGNAL_TARGET" "$UNITY_TARGET" "$IL2CPP_TARGET"; do
        line=$(top_mount_line "$target")
        [ -z "$line" ] || mount_is_ours "$target" || return 1
    done
    return 0
}

assert_shared_targets_clear()
{
    for target in "$ADAPTER_TARGET" "$PROVIDER_TARGET" "$CHILD_TARGET" \
        "$APPSPAWN_TARGET" "$RUNTIME_JAR_TARGET" "$PTHREAD_TARGET" \
        "$NATIVE_LOADER_TARGET" "$ROUTE_NATIVE_LOADER_TARGET" \
        "$LIBANDROID_TARGET" "$RUNTIME_TARGET"; do
        line=$(top_mount_line "$target")
        [ -z "$line" ] && continue
        mount_is_ours "$target" && continue
        printf '%s\n' "$line" | grep -Fq /pr03-74e6-portable/ && continue
        return 1
    done
    return 0
}

mount_shared()
{
    rollback_shared_mounts || return 1
    assert_shared_targets_clear || return 1
    [ -z "$(pidof appspawn-x 2>/dev/null)" ] || return 1

    mount --bind "$SHARED/liboh_adapter_bridge.so" "$ADAPTER_TARGET" || return 1
    mount --bind "$SHARED/libwestlake_android_runtime_provider.so" "$PROVIDER_TARGET" || return 1
    mount --bind "$SHARED/libwestlake_android_child.z.so" "$CHILD_TARGET" || return 1
    mount --bind "$SHARED/appspawn-x" "$APPSPAWN_TARGET" || return 1
    mount --bind "$SHARED/oh-adapter-runtime.jar" "$RUNTIME_JAR_TARGET" || return 1
    mount --bind "$SHARED/libwestlake_bionic_pthread_bridge.so" "$PTHREAD_TARGET" || return 1
    mount --bind "$SHARED/libnativeloader.so" "$NATIVE_LOADER_TARGET" || return 1
    mount --bind "$SHARED/libnativeloader.so" "$ROUTE_NATIVE_LOADER_TARGET" || return 1
    mount --bind "$SHARED/libandroid.so" "$LIBANDROID_TARGET" || return 1
    mount --bind "$SHARED/liboh_android_runtime.so" "$RUNTIME_TARGET" || return 1

    chmod 0755 "$CHILD_TARGET" "$APPSPAWN_TARGET"
    chmod 0644 "$ADAPTER_TARGET" "$PROVIDER_TARGET" "$RUNTIME_JAR_TARGET" \
        "$PTHREAD_TARGET" "$NATIVE_LOADER_TARGET" "$ROUTE_NATIVE_LOADER_TARGET" \
        "$LIBANDROID_TARGET" "$RUNTIME_TARGET"
    chcon u:object_r:appspawn_exec:s0 "$APPSPAWN_TARGET"
    chcon u:object_r:system_file:s0 "$RUNTIME_JAR_TARGET"
    chcon u:object_r:system_lib_file:s0 "$ADAPTER_TARGET" "$PROVIDER_TARGET" \
        "$CHILD_TARGET" "$PTHREAD_TARGET" "$NATIVE_LOADER_TARGET" \
        "$ROUTE_NATIVE_LOADER_TARGET" "$LIBANDROID_TARGET" "$RUNTIME_TARGET"
    shared_ready
}

bundle_uid()
{
    bm dump -n "$BUNDLE" 2>/dev/null |
        sed -n 's/.*"uid":[[:space:]]*\([0-9][0-9]*\).*/\1/p' | head -n 1
}

ensure_launcher_label()
{
    backup_root=$ROOT/label-backup
    mkdir -p "$backup_root" || return 1
    for db_name in bundleResource.db bundleResource_slave.db; do
        db=$RESOURCE_DB_ROOT/$db_name
        backup=$backup_root/$db_name.before-boat-label
        [ -f "$db" ] || return 1
        if [ ! -f "$backup" ]; then
            tmp_backup=$backup.tmp.$$
            rm -f "$tmp_backup"
            sqlite3 "$db" ".timeout 5000" ".backup '$tmp_backup'" || return 1
            [ -s "$tmp_backup" ] || return 1
            mv "$tmp_backup" "$backup" || return 1
        fi
        ready_count=$(sqlite3 "$db" ".timeout 5000" \
            "BEGIN IMMEDIATE; UPDATE bundleResource SET LABEL='$LAUNCHER_LABEL' WHERE NAME='$APP_RESOURCE_KEY' OR NAME='$ABILITY_RESOURCE_KEY'; COMMIT; SELECT COUNT(*) FROM bundleResource WHERE (NAME='$APP_RESOURCE_KEY' OR NAME='$ABILITY_RESOURCE_KEY') AND LABEL='$LAUNCHER_LABEL';" 2>/dev/null) || return 1
        [ "$ready_count" = 2 ] || return 1
    done
    return 0
}

target_pids()
{
    _wanted_uid=$1
    ps -ef 2>/dev/null | while read _user _pid _rest; do
        [ "$_user" = "$_wanted_uid" ] || continue
        case "$_pid" in ''|*[!0-9]*) continue ;; esac
        printf '%s\n' "$_pid"
    done
}

parent_pids()
{
    for candidate_pid in $(pidof appspawn-x 2>/dev/null); do
        candidate_name=$(sed -n 's/^Name:[[:space:]]*//p' "/proc/$candidate_pid/status" 2>/dev/null)
        candidate_ppid=$(sed -n 's/^PPid:[[:space:]]*//p' "/proc/$candidate_pid/status" 2>/dev/null)
        [ "$candidate_name" = appspawn-x ] || continue
        [ "$candidate_ppid" = 1 ] || continue
        printf '%s\n' "$candidate_pid"
    done
}

socket_identity()
{
    stat -c '%i:%a:%u:%g:%C' "$APPSPAWN_SOCKET" 2>/dev/null
}

listener_inode()
{
    while IFS= read -r line; do
        set -- $line
        if [ "${4:-}" = 00010000 ] && [ "${8:-}" = "$APPSPAWN_SOCKET" ]; then
            printf '%s\n' "${7:-}"
            return 0
        fi
    done < /proc/net/unix
    return 1
}

ensure_parent()
{
    socket_before=$(socket_identity)
    case "$socket_before" in
        *:660:0:6005:u:object_r:appspawn_socket:s0|\
        *:666:0:6005:u:object_r:appspawn_socket:s0) ;;
        *) return 1 ;;
    esac
    [ -n "$(listener_inode)" ] || return 1

    count=0
    for one_pid in $(parent_pids); do
        count=$((count + 1))
    done
    if [ "$count" = 0 ]; then
        begetctl start_service appspawn-x >/dev/null 2>&1 || true
    fi

    attempt=0
    last=
    stable=0
    parent_hash=
    while [ "$attempt" -lt 40 ]; do
        sleep 1
        count=0
        parent=
        for one_pid in $(parent_pids); do
            count=$((count + 1))
            parent=$one_pid
        done
        parent_hash=
        if [ "$count" = 1 ] && [ -n "$parent" ]; then
            parent_hash=$(hash_file "/proc/$parent/exe")
        fi
        if [ "$count" = 1 ] && [ -n "$parent" ] && [ "$parent" = "$last" ] &&
            [ "$parent_hash" = "$APPSPAWN_SHA" ]; then
            stable=$((stable + 1))
        else
            stable=0
        fi
        last=$parent
        [ "$stable" -ge 2 ] && break
        attempt=$((attempt + 1))
    done
    if [ "$stable" -lt 2 ]; then
        echo "appspawn_observed_count=$count" >> "$TMP"
        echo "appspawn_observed_pid=$parent" >> "$TMP"
        echo "appspawn_observed_hash=$parent_hash" >> "$TMP"
        echo "appspawn_observed_last=$last" >> "$TMP"
        echo "appspawn_observed_stable=$stable" >> "$TMP"
        return 1
    fi

    socket_after=$(socket_identity)
    if [ "$socket_after" = "$socket_before" ]; then
        APPSPAWN_SOCKET_REPAIRED=false
    else
        APPSPAWN_SOCKET_REPAIRED=true
    fi
    chown 0:6005 "$APPSPAWN_SOCKET" >/dev/null 2>&1 || return 1
    chmod 0660 "$APPSPAWN_SOCKET" >/dev/null 2>&1 || return 1
    chcon u:object_r:appspawn_socket:s0 "$APPSPAWN_SOCKET" >/dev/null 2>&1 || return 1
    [ "$(stat -c '%a:%u:%g:%C' "$APPSPAWN_SOCKET" 2>/dev/null)" = \
        660:0:6005:u:object_r:appspawn_socket:s0 ] || return 1
    [ -n "$(listener_inode)" ] || return 1
    APPSPAWN_PARENT_PID=$parent
    return 0
}

wait_package()
{
    PACKAGE_UID=
    attempt=0
    while [ "$attempt" -lt 600 ]; do
        meta=$(stat -c '%u:%g:%C' "$APP_DATA" 2>/dev/null || true)
        uid=${meta%%:*}
        remainder=${meta#*:}
        gid=${remainder%%:*}
        label=${remainder#*:}
        case "$uid" in
            ''|*[!0-9]*) ;;
            *)
                if [ "$uid" -gt 10000 ] && [ "$gid" = "$uid" ] &&
                    [ "$label" = u:object_r:appdat:s0 ] &&
                    [ "$(hash_file "$APK")" = "$APK_SHA" ]; then
                    PACKAGE_UID=$uid
                    return 0
                fi
                ;;
        esac
        attempt=$((attempt + 1))
        sleep 1
    done
    return 1
}

wait_bms_ready()
{
    attempt=0
    while [ "$attempt" -lt 240 ]; do
        case "$(param get bootevent.bms.main.bundles.ready 2>/dev/null)" in
            true*) return 0 ;;
        esac
        attempt=$((attempt + 1))
        sleep 1
    done
    return 1
}

stop_target()
{
    uid=$1
    aa force-stop "$BUNDLE" >/dev/null 2>&1 || true
    for one_pid in $(target_pids "$uid"); do
        kill -9 "$one_pid" >/dev/null 2>&1 || true
    done
    attempt=0
    while [ "$attempt" -lt 30 ]; do
        [ -z "$(target_pids "$uid")" ] && return 0
        attempt=$((attempt + 1))
        sleep 1
    done
    return 1
}

mount_private()
{
    rollback_private_mounts || return 1
    assert_private_targets_clear || return 1
    [ "$(hash_file "$UNITY_TARGET")" = "$RAW_UNITY_SHA" ] || return 1
    [ "$(hash_file "$IL2CPP_TARGET")" = "$RAW_IL2CPP_SHA" ] || return 1
    [ -z "$(hash_file "$SIGNAL_TARGET")" ] || return 1

    touch "$SIGNAL_TARGET" || return 1
    chown 0:0 "$SIGNAL_TARGET"
    chmod 0644 "$SIGNAL_TARGET"
    chcon u:object_r:data_app_el1_file:s0 "$SIGNAL_TARGET"

    mount --bind "$PRIVATE/libwestlake_bionic_signal_box.so" "$SIGNAL_TARGET" || return 1
    mount --bind "$PRIVATE/libunity.so" "$UNITY_TARGET" || return 1
    mount --bind "$PRIVATE/libil2cpp.so" "$IL2CPP_TARGET" || return 1
    chmod 0755 "$SIGNAL_TARGET" "$UNITY_TARGET" "$IL2CPP_TARGET"
    chcon u:object_r:data_app_el1_file:s0 "$SIGNAL_TARGET" "$UNITY_TARGET" "$IL2CPP_TARGET"
    private_ready
}

status_mode()
{
    [ -f "$RECEIPT" ] && cat "$RECEIPT"
    if [ -f "$DISABLED" ]; then echo enabled=false; else echo enabled=true; fi
    echo "shared_ready=$(shared_ready && echo true || echo false)"
    echo "private_ready=$(private_ready && echo true || echo false)"
    uid=$(bundle_uid 2>/dev/null || true)
    pids=
    if [ -n "$uid" ]; then
        for one_pid in $(target_pids "$uid"); do
            pids="${pids}${one_pid},"
        done
    fi
    echo "boat_pids=$pids"
    exit 0
}

rollback_mode()
{
    write_header
    touch "$DISABLED"
    uid=$(bundle_uid 2>/dev/null || true)
    if [ -n "$uid" ]; then
        stop_target "$uid" || fail STOP_TARGET_FOR_ROLLBACK
    fi
    rollback_private_mounts || fail PRIVATE_ROLLBACK
    if [ -z "$(pidof appspawn-x 2>/dev/null)" ]; then
        rollback_shared_mounts || fail SHARED_ROLLBACK
        echo shared_rollback=COMPLETE >> "$TMP"
    else
        echo shared_rollback=DEFERRED_UNTIL_REBOOT >> "$TMP"
    fi
    finish ROLLED_BACK
}

case "${1:-start}" in
    status) status_mode ;;
    rollback) rollback_mode ;;
    start) ;;
    *) exit 2 ;;
esac

write_header

if [ -f "$DISABLED" ]; then
    finish DISABLED
fi

case "$(param get bootevent.boot.completed 2>/dev/null)" in true*) ;; *) fail BOOT_NOT_COMPLETE ;; esac
case "$(param get sys.pr03.runtime.ready 2>/dev/null)" in true*) ;; *) fail PR03_NOT_READY ;; esac
grep -q '^state=READY$' /data/service/el1/public/appspawnx/pr03-boot-recovery.txt 2>/dev/null \
    || fail PR03_RECEIPT_NOT_READY
verify_payloads || fail PAYLOAD_IDENTITY

if shared_ready; then
    echo shared_state=PREEXISTING_ACCEPTED >> "$TMP"
else
    [ -z "$(pidof appspawn-x 2>/dev/null)" ] || fail APPSPAWN_ALREADY_STARTED
    if ! mount_shared; then
        rollback_shared_mounts || true
        fail SHARED_MOUNT
    fi
    echo shared_state=MOUNTED_BY_AUTOSTART >> "$TMP"
fi

if private_ready; then
    echo private_state=PREEXISTING_ACCEPTED >> "$TMP"
else
    [ -z "$(pidof appspawn-x 2>/dev/null)" ] || fail APPSPAWN_STARTED_BEFORE_PRIVATE
    if ! mount_private; then
        rollback_private_mounts || true
        fail PRIVATE_MOUNT
    fi
    echo private_state=MOUNTED_BY_AUTOSTART >> "$TMP"
fi

wait_bms_ready || fail BMS_NOT_READY
echo bms_ready=true >> "$TMP"
wait_package || fail PACKAGE_NOT_READY_OR_IDENTITY
uid=$PACKAGE_UID
echo "uid=$uid" >> "$TMP"
ensure_launcher_label || fail LAUNCHER_LABEL_NOT_READY
echo "launcher_label=$LAUNCHER_LABEL" >> "$TMP"
echo launcher_label_rows=2x2 >> "$TMP"
stop_target "$uid" || fail TARGET_DID_NOT_STOP
ensure_parent || fail APPSPAWN_PARENT_NOT_READY
echo "appspawn_parent_pid=$APPSPAWN_PARENT_PID" >> "$TMP"
echo "appspawn_socket_repaired=$APPSPAWN_SOCKET_REPAIRED" >> "$TMP"

: > "$LAUNCH_LOG"
echo "launch_mode=$LAUNCH_MODE" >> "$LAUNCH_LOG"
echo 'activity_start=DEFERRED_TO_USER' >> "$LAUNCH_LOG"
echo "launch_mode=$LAUNCH_MODE" >> "$TMP"
echo 'activity_start=DEFERRED_TO_USER' >> "$TMP"
echo 'ready_for_manual_launch=true' >> "$TMP"
echo 'pid=NONE' >> "$TMP"
echo "apk_sha256=$APK_SHA" >> "$TMP"
echo "unity_sha256=$UNITY_SHA" >> "$TMP"
echo "il2cpp_sha256=$IL2CPP_SHA" >> "$TMP"
echo "signal_box_sha256=$SIGNAL_SHA" >> "$TMP"
finish READY
