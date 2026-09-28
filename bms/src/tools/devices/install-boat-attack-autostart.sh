#!/usr/bin/env bash

set -Eeuo pipefail

SELF="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
HDC_BIN="${HDC_BIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"

BOARD_ONLY=61ae0be500000000000000000324012c
BOARD_8605=5ce2dcee00000000000000000923012c
BOARD_5EA1="5ea1719200000000000000001123012c"
ROM_ONLY=OpenHarmony-6.1.0.31
BOARD="${2:-$BOARD_ONLY}"
MODE="${1:-status}"
case "$BOARD" in
    "$BOARD_ONLY") BOARD_LABEL=61ae ;;
    "$BOARD_8605") BOARD_LABEL=8605 ;;
    "$BOARD_5EA1") BOARD_LABEL=5ea1 ;;
    "5ea34a4500000000000000001123012c") BOARD_LABEL=5ea ;;
    "61b0657200000000000000000324012c") BOARD_LABEL=61b ;;
    "5cd1e3dd00000000000000000923012c") BOARD_LABEL=5cd ;;
    *) BOARD_LABEL=unsupported ;;
esac

GENERATION=strict-boat-assembled-20260924T074522Z-25403
CANDIDATE="$REPO_ROOT/.bridge-payload/zigzag-candidates/$GENERATION"
DEVICE_SCRIPT="$SCRIPT_DIR/boat-attack-autostart-device.sh"
DEVICE_CFG="$SCRIPT_DIR/boat-attack-autostart.cfg"
UNITY="$REPO_ROOT/.state/boat-attack/c-candidates/c7-unity-disable-swappy/libunity.so"
IL2CPP="$REPO_ROOT/.state/boat-attack/c-candidates/c4-il2cpp-pthread-edge/libil2cpp.so"
SIGNAL_BOX="$REPO_ROOT/.state/boat-attack/c-candidates/c1-unity-signal-box/libwestlake_bionic_signal_box.so"

DEVICE_ROOT=/data/boatattack-autostart
DEVICE_PAYLOAD="$DEVICE_ROOT/generations/$GENERATION"
DEVICE_SCRIPT_TARGET=/system/etc/boat-attack-autostart.sh
DEVICE_CFG_TARGET=/system/etc/init/00_pr03_runtime_recovery.cfg
DEVICE_APK=/data/app/el1/bundle/public/com.Unity3d.BoatAttackDay/android/base.apk

APK_SHA=8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444
UNITY_SHA=1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac
IL2CPP_SHA=f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746
SIGNAL_SHA=7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da
ADAPTER_SHA=8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e
PROVIDER_SHA=f821d20eaefc798b638192124e3a98683103f3d509c0b66ca1c6946037cccdb0
CHILD_SHA=47f238aede6336ce3770861a6a742e71abc28f35516481299797c05c63149b57
APPSPAWN_SHA=76e6df931905177c8abde4054ee5516cb6d8394c67dce8f79dfadf0847b96747
RUNTIME_JAR_SHA=56e4d4733bb6dc4f260981f51184234522df7a67c0eca01bd1b9ef87369221af
PTHREAD_SHA=db31d6d81c543860449e4e13f94dda6d39acde94ce00e34e7087a4d796e88fc6
NATIVE_LOADER_SHA=fde6f31c6f8911bd5be165d69bc248f47699be435240dc855fa7528c0ba73ccd
RUNTIME_SHA=adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130
EXPECTED_LAUNCH_MODE=MANUAL

CHANNEL_ROOT="$REPO_ROOT/var/state/agent-channel"
LOCK_ROOT="$CHANNEL_ROOT/.locks"
LOCK_DIR="$LOCK_ROOT/$BOARD.lock"
CHANNEL_FILE="$CHANNEL_ROOT/boat-attack-autostart-$BOARD_LABEL.md"
CLAIMED=0
ROOT_REMOUNTED=0

die()
{
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

usage()
{
    printf '%s\n' \
        "usage: $SELF install [supported-board-serial]" \
        "       $SELF activate [supported-board-serial]" \
        "       $SELF finalize [supported-board-serial]" \
        "       $SELF status [supported-board-serial]" \
        "       $SELF reboot-test [supported-board-serial]" \
        "       $SELF uninstall [supported-board-serial]"
}

H()
{
    "$HDC_BIN" -t "$BOARD" "$@"
}

D()
{
    H shell "$1" 2>&1 | tr -d '\r'
}

sha256_file()
{
    shasum -a 256 "$1" | awk '{print $1}'
}

device_hash()
{
    D "sha256sum '$1' 2>/dev/null" | awk 'NR == 1 {print $1}'
}

manifest_value()
{
    sed -n "s/^${2}=//p" "$1" | head -n 1
}

require_hash()
{
    local expected=$1 file=$2 actual
    [ -f "$file" ] || die "missing input: $file"
    actual="$(sha256_file "$file")"
    [ "$actual" = "$expected" ] || die "hash drift: $file expected=$expected actual=$actual"
}

write_channel()
{
    local status=$1 detail=${2:-}
    mkdir -p "$CHANNEL_ROOT"
    {
        printf 'STATUS=%s\n' "$status"
        printf 'BOARD=%s\n' "$BOARD"
        printf 'OWNER_PID=%s\n' "$$"
        printf 'TASK=BoatAttack device-native boot preparation with manual launch\n'
        printf 'DETAIL=%s\n' "$detail"
    } > "$CHANNEL_FILE"
}

claim_board()
{
    local file state
    mkdir -p "$LOCK_ROOT"
    while IFS= read -r file; do
        [ "$file" = "$CHANNEL_FILE" ] && continue
        state="$(sed -n 's/^STATUS=//p;s/^status:[[:space:]]*//p;s/^- status:[[:space:]]*//p' "$file" | tail -n 1)"
        case "$state" in
            ACTIVE|CLAIMED) die "device channel already active: $file" ;;
        esac
    done < <(find "$CHANNEL_ROOT" -maxdepth 1 -type f -name '*.md' -print 2>/dev/null | sort)
    mkdir "$LOCK_DIR" 2>/dev/null || die "device lock already exists: $LOCK_DIR"
    CLAIMED=1
    write_channel ACTIVE "$MODE"
}

on_exit()
{
    local rc=$?
    if [ "$ROOT_REMOUNTED" = 1 ]; then
        D 'sync; mount -o ro,remount /' >/dev/null 2>&1 || true
        ROOT_REMOUNTED=0
    fi
    if [ "$CLAIMED" = 1 ]; then
        if [ "$rc" = 0 ]; then
            write_channel RELEASED "$MODE complete"
        else
            write_channel FAILED "$MODE rc=$rc"
        fi
        rmdir "$LOCK_DIR" 2>/dev/null || true
    fi
    exit "$rc"
}
trap on_exit EXIT

root_mount_options()
{
    D "grep ' / ' /proc/mounts" | head -n 1 | awk '{print $4}'
}

make_root_writable()
{
    local options
    options="$(root_mount_options)"
    case ",$options," in
        *,rw,*) return 0 ;;
        *,ro,*) ;;
        *) die "cannot determine root mount mode: $options" ;;
    esac
    D 'mount -o rw,remount /' >/dev/null
    options="$(root_mount_options)"
    case ",$options," in
        *,rw,*) ROOT_REMOUNTED=1 ;;
        *) die "root remount rw failed: $options" ;;
    esac
}

restore_root_readonly()
{
    local options
    options="$(root_mount_options)"
    case ",$options," in
        *,ro,*) ROOT_REMOUNTED=0; return 0 ;;
        *,rw,*) ;;
        *) die "cannot determine root mount mode: $options" ;;
    esac
    D 'sync; mount -o ro,remount /' >/dev/null
    options="$(root_mount_options)"
    case ",$options," in
        *,ro,*) ROOT_REMOUNTED=0 ;;
        *) die "root remount ro failed: $options" ;;
    esac
}

local_preflight()
{
    [ "$(uname -s)" = Darwin ] || die "installer is local-Mac only"
    [ -x "$HDC_BIN" ] || die "missing hdc: $HDC_BIN"
    case "$BOARD" in
        "$BOARD_ONLY"|"$BOARD_8605"|"$BOARD_5EA1"|"5ea34a4500000000000000001123012c"|"61b0657200000000000000000324012c"|"5cd1e3dd00000000000000000923012c") ;;
        *) die "unsupported direct board: $BOARD" ;;
    esac
    /bin/sh -n "$DEVICE_SCRIPT"
    grep -qx "LAUNCH_MODE=$EXPECTED_LAUNCH_MODE" "$DEVICE_SCRIPT" \
        || die "device script is not configured for manual launch"
    command -v jq >/dev/null 2>&1 || die "jq is required to validate init cfg"
    jq -e . "$DEVICE_CFG" >/dev/null
    require_hash "$ADAPTER_SHA" "$CANDIDATE/files/liboh_adapter_bridge.so"
    require_hash "$PROVIDER_SHA" "$CANDIDATE/files/libwestlake_android_runtime_provider.so"
    require_hash "$CHILD_SHA" "$CANDIDATE/files/libwestlake_android_child.z.so"
    require_hash "$APPSPAWN_SHA" "$CANDIDATE/files/appspawn-x"
    require_hash "$RUNTIME_JAR_SHA" "$CANDIDATE/files/oh-adapter-runtime.jar"
    require_hash "$PTHREAD_SHA" "$CANDIDATE/files/libwestlake_bionic_pthread_bridge.so"
    require_hash "$NATIVE_LOADER_SHA" "$CANDIDATE/files/libnativeloader.so"
    require_hash "$RUNTIME_SHA" "$CANDIDATE/files/libandroid.so"
    require_hash "$UNITY_SHA" "$UNITY"
    require_hash "$IL2CPP_SHA" "$IL2CPP"
    require_hash "$SIGNAL_SHA" "$SIGNAL_BOX"
}

device_preflight()
{
    "$HDC_BIN" list targets 2>/dev/null | tr -d '\r' | grep -qx "$BOARD" \
        || die "$BOARD_LABEL is not connected"
    [ "$(D 'param get const.ohos.fullname' | tr -d ' \n')" = "$ROM_ONLY" ] \
        || die "unexpected ROM"
    [ "$(D 'param get bootevent.boot.completed' | tr -d ' \n')" = true ] \
        || die "boot is not complete"
    [ "$(device_hash "$DEVICE_APK")" = "$APK_SHA" ] \
        || die "exact BoatAttack APK is not installed"
    grep -q '^state=READY$' < <(D 'cat /data/service/el1/public/appspawnx/pr03-boot-recovery.txt 2>/dev/null') \
        || die "PR03 boot recovery is not READY"
}

send_payload()
{
    local staging=$1
    H file send "$CANDIDATE/files/liboh_adapter_bridge.so" "$staging/liboh_adapter_bridge.so" >/dev/null
    H file send "$CANDIDATE/files/libwestlake_android_runtime_provider.so" "$staging/libwestlake_android_runtime_provider.so" >/dev/null
    H file send "$CANDIDATE/files/libwestlake_android_child.z.so" "$staging/libwestlake_android_child.z.so" >/dev/null
    H file send "$CANDIDATE/files/appspawn-x" "$staging/appspawn-x" >/dev/null
    H file send "$CANDIDATE/files/oh-adapter-runtime.jar" "$staging/oh-adapter-runtime.jar" >/dev/null
    H file send "$CANDIDATE/files/libwestlake_bionic_pthread_bridge.so" "$staging/libwestlake_bionic_pthread_bridge.so" >/dev/null
    H file send "$CANDIDATE/files/libnativeloader.so" "$staging/libnativeloader.so" >/dev/null
    H file send "$CANDIDATE/files/libandroid.so" "$staging/libandroid.so" >/dev/null
    H file send "$CANDIDATE/files/libandroid.so" "$staging/liboh_android_runtime.so" >/dev/null
    H file send "$UNITY" "$staging/libunity.so" >/dev/null
    H file send "$IL2CPP" "$staging/libil2cpp.so" >/dev/null
    H file send "$SIGNAL_BOX" "$staging/libwestlake_bionic_signal_box.so" >/dev/null
    H file send "$DEVICE_SCRIPT" "$staging/boat-attack-autostart.sh" >/dev/null
    H file send "$DEVICE_CFG" "$staging/startup.cfg" >/dev/null
}

verify_remote_staging()
{
    local staging=$1 script_sha cfg_sha
    script_sha="$(sha256_file "$DEVICE_SCRIPT")"
    cfg_sha="$(sha256_file "$DEVICE_CFG")"
    [ "$(device_hash "$staging/liboh_adapter_bridge.so")" = "$ADAPTER_SHA" ] &&
    [ "$(device_hash "$staging/libwestlake_android_runtime_provider.so")" = "$PROVIDER_SHA" ] &&
    [ "$(device_hash "$staging/libwestlake_android_child.z.so")" = "$CHILD_SHA" ] &&
    [ "$(device_hash "$staging/appspawn-x")" = "$APPSPAWN_SHA" ] &&
    [ "$(device_hash "$staging/oh-adapter-runtime.jar")" = "$RUNTIME_JAR_SHA" ] &&
    [ "$(device_hash "$staging/libwestlake_bionic_pthread_bridge.so")" = "$PTHREAD_SHA" ] &&
    [ "$(device_hash "$staging/libnativeloader.so")" = "$NATIVE_LOADER_SHA" ] &&
    [ "$(device_hash "$staging/libandroid.so")" = "$RUNTIME_SHA" ] &&
    [ "$(device_hash "$staging/liboh_android_runtime.so")" = "$RUNTIME_SHA" ] &&
    [ "$(device_hash "$staging/libunity.so")" = "$UNITY_SHA" ] &&
    [ "$(device_hash "$staging/libil2cpp.so")" = "$IL2CPP_SHA" ] &&
    [ "$(device_hash "$staging/libwestlake_bionic_signal_box.so")" = "$SIGNAL_SHA" ] &&
    [ "$(device_hash "$staging/boat-attack-autostart.sh")" = "$script_sha" ] &&
    [ "$(device_hash "$staging/startup.cfg")" = "$cfg_sha" ]
}

verify_remote_payload()
{
    [ "$(device_hash "$DEVICE_PAYLOAD/shared/liboh_adapter_bridge.so")" = "$ADAPTER_SHA" ] &&
    [ "$(device_hash "$DEVICE_PAYLOAD/shared/libwestlake_android_runtime_provider.so")" = "$PROVIDER_SHA" ] &&
    [ "$(device_hash "$DEVICE_PAYLOAD/shared/libwestlake_android_child.z.so")" = "$CHILD_SHA" ] &&
    [ "$(device_hash "$DEVICE_PAYLOAD/shared/appspawn-x")" = "$APPSPAWN_SHA" ] &&
    [ "$(device_hash "$DEVICE_PAYLOAD/shared/oh-adapter-runtime.jar")" = "$RUNTIME_JAR_SHA" ] &&
    [ "$(device_hash "$DEVICE_PAYLOAD/shared/libwestlake_bionic_pthread_bridge.so")" = "$PTHREAD_SHA" ] &&
    [ "$(device_hash "$DEVICE_PAYLOAD/shared/libnativeloader.so")" = "$NATIVE_LOADER_SHA" ] &&
    [ "$(device_hash "$DEVICE_PAYLOAD/shared/libandroid.so")" = "$RUNTIME_SHA" ] &&
    [ "$(device_hash "$DEVICE_PAYLOAD/shared/liboh_android_runtime.so")" = "$RUNTIME_SHA" ] &&
    [ "$(device_hash "$DEVICE_PAYLOAD/private/libunity.so")" = "$UNITY_SHA" ] &&
    [ "$(device_hash "$DEVICE_PAYLOAD/private/libil2cpp.so")" = "$IL2CPP_SHA" ] &&
    [ "$(device_hash "$DEVICE_PAYLOAD/private/libwestlake_bionic_signal_box.so")" = "$SIGNAL_SHA" ]
}

install_autostart()
{
    local transaction staging backup previous_backup script_sha cfg_sha current_state
    script_sha="$(sha256_file "$DEVICE_SCRIPT")"
    cfg_sha="$(sha256_file "$DEVICE_CFG")"
    previous_backup=
    current_state="$(D "sed -n 's/^state=//p' '$DEVICE_ROOT/install.env' 2>/dev/null" | tail -n 1)"
    if [ "$current_state" = READY ] \
        && [ "$(device_hash "$DEVICE_SCRIPT_TARGET")" = "$script_sha" ] \
        && [ "$(device_hash "$DEVICE_CFG_TARGET")" = "$cfg_sha" ]; then
        D "rm -f '$DEVICE_ROOT/DISABLED'; '$DEVICE_SCRIPT_TARGET' start" >/dev/null
        restore_root_readonly
        status_autostart
        printf 'BOAT_ATTACK_AUTOSTART_INSTALL=PASS\npayload=reused_without_update\n'
        return 0
    fi
    case "$current_state" in
        ''|UNINSTALLED) ;;
        READY)
            verify_remote_payload \
                || die "existing autostart payload identity does not match this generation"
            previous_backup="$(D "sed -n 's/^backup=//p' '$DEVICE_ROOT/install.env' 2>/dev/null" | tail -n 1)"
            [ -n "$previous_backup" ] || die "existing install rollback backup is missing"
            ;;
        *) die "existing autostart generation must be uninstalled before replacement" ;;
    esac

    transaction="$(date -u +%Y%m%dT%H%M%SZ)-$$"
    staging="$DEVICE_ROOT/install-staging/$transaction"
    backup="$DEVICE_ROOT/install-backup/$transaction"
    D "set -e; test ! -e '$staging'; test ! -e '$backup'; mkdir -p '$staging' '$backup'" >/dev/null
    send_payload "$staging"
    verify_remote_staging "$staging" || die "remote staging identity mismatch"

    if verify_remote_payload; then
        [ -n "$previous_backup" ] || previous_backup="$backup"
        make_root_writable
        D "set -e; if test -e '$DEVICE_SCRIPT_TARGET'; then cp '$DEVICE_SCRIPT_TARGET' '$backup/boat-attack-autostart.sh'; else touch '$backup/script.missing'; fi; if test -e '$DEVICE_CFG_TARGET'; then cp '$DEVICE_CFG_TARGET' '$backup/startup.cfg'; else touch '$backup/cfg.missing'; fi; cp '$staging/boat-attack-autostart.sh' '$DEVICE_SCRIPT_TARGET'; cp '$staging/startup.cfg' '$DEVICE_CFG_TARGET'; chown 0:0 '$DEVICE_SCRIPT_TARGET' '$DEVICE_CFG_TARGET'; chmod 0550 '$DEVICE_SCRIPT_TARGET' '$DEVICE_CFG_TARGET'; chcon u:object_r:system_etc_file:s0 '$DEVICE_SCRIPT_TARGET' '$DEVICE_CFG_TARGET'; rm -f '$DEVICE_ROOT/DISABLED'; printf 'state=READY\ngeneration=%s\nbackup=%s\nupdate_backup=%s\nscript_sha256=%s\ncfg_sha256=%s\npayload=reused\nlaunch_mode=%s\n' '$GENERATION' '$previous_backup' '$backup' '$script_sha' '$cfg_sha' '$EXPECTED_LAUNCH_MODE' > '$DEVICE_ROOT/install.env'; sync" >/dev/null
        [ "$(device_hash "$DEVICE_SCRIPT_TARGET")" = "$script_sha" ] \
            && [ "$(device_hash "$DEVICE_CFG_TARGET")" = "$cfg_sha" ] \
            || die "system startup files failed readback"
        restore_root_readonly
        D "'$DEVICE_SCRIPT_TARGET' start" >/dev/null
        status_autostart
        printf 'BOAT_ATTACK_AUTOSTART_INSTALL=PASS\nbackup=%s\nupdate_backup=%s\npayload=reused\n' \
            "$previous_backup" "$backup"
        return 0
    fi
    [ "$(D "test -e '$DEVICE_PAYLOAD' && echo true || echo false" | tail -n 1)" = false ] \
        || die "immutable device payload exists with an unexpected identity"
    make_root_writable

    D "set -e; if test -e '$DEVICE_SCRIPT_TARGET'; then cp '$DEVICE_SCRIPT_TARGET' '$backup/boat-attack-autostart.sh'; else touch '$backup/script.missing'; fi; if test -e '$DEVICE_CFG_TARGET'; then cp '$DEVICE_CFG_TARGET' '$backup/startup.cfg'; else touch '$backup/cfg.missing'; fi; mkdir -p '$DEVICE_PAYLOAD/shared' '$DEVICE_PAYLOAD/private'; cp '$staging/liboh_adapter_bridge.so' '$DEVICE_PAYLOAD/shared/liboh_adapter_bridge.so'; cp '$staging/libwestlake_android_runtime_provider.so' '$DEVICE_PAYLOAD/shared/libwestlake_android_runtime_provider.so'; cp '$staging/libwestlake_android_child.z.so' '$DEVICE_PAYLOAD/shared/libwestlake_android_child.z.so'; cp '$staging/appspawn-x' '$DEVICE_PAYLOAD/shared/appspawn-x'; cp '$staging/oh-adapter-runtime.jar' '$DEVICE_PAYLOAD/shared/oh-adapter-runtime.jar'; cp '$staging/libwestlake_bionic_pthread_bridge.so' '$DEVICE_PAYLOAD/shared/libwestlake_bionic_pthread_bridge.so'; cp '$staging/libnativeloader.so' '$DEVICE_PAYLOAD/shared/libnativeloader.so'; cp '$staging/libandroid.so' '$DEVICE_PAYLOAD/shared/libandroid.so'; cp '$staging/liboh_android_runtime.so' '$DEVICE_PAYLOAD/shared/liboh_android_runtime.so'; cp '$staging/libunity.so' '$DEVICE_PAYLOAD/private/libunity.so'; cp '$staging/libil2cpp.so' '$DEVICE_PAYLOAD/private/libil2cpp.so'; cp '$staging/libwestlake_bionic_signal_box.so' '$DEVICE_PAYLOAD/private/libwestlake_bionic_signal_box.so'; cp '$staging/boat-attack-autostart.sh' '$DEVICE_SCRIPT_TARGET'; cp '$staging/startup.cfg' '$DEVICE_CFG_TARGET'; chown -R 0:0 '$DEVICE_PAYLOAD'; chmod 0755 '$DEVICE_PAYLOAD/shared/appspawn-x' '$DEVICE_PAYLOAD/shared/libwestlake_android_child.z.so' '$DEVICE_PAYLOAD/private/libunity.so' '$DEVICE_PAYLOAD/private/libil2cpp.so' '$DEVICE_PAYLOAD/private/libwestlake_bionic_signal_box.so'; chmod 0644 '$DEVICE_PAYLOAD/shared/liboh_adapter_bridge.so' '$DEVICE_PAYLOAD/shared/libwestlake_android_runtime_provider.so' '$DEVICE_PAYLOAD/shared/oh-adapter-runtime.jar' '$DEVICE_PAYLOAD/shared/libwestlake_bionic_pthread_bridge.so' '$DEVICE_PAYLOAD/shared/libnativeloader.so' '$DEVICE_PAYLOAD/shared/libandroid.so' '$DEVICE_PAYLOAD/shared/liboh_android_runtime.so'; chcon u:object_r:appspawn_exec:s0 '$DEVICE_PAYLOAD/shared/appspawn-x'; chcon u:object_r:system_file:s0 '$DEVICE_PAYLOAD/shared/oh-adapter-runtime.jar'; chcon u:object_r:system_lib_file:s0 '$DEVICE_PAYLOAD/shared/liboh_adapter_bridge.so' '$DEVICE_PAYLOAD/shared/libwestlake_android_runtime_provider.so' '$DEVICE_PAYLOAD/shared/libwestlake_android_child.z.so' '$DEVICE_PAYLOAD/shared/libwestlake_bionic_pthread_bridge.so' '$DEVICE_PAYLOAD/shared/libnativeloader.so' '$DEVICE_PAYLOAD/shared/libandroid.so' '$DEVICE_PAYLOAD/shared/liboh_android_runtime.so'; chcon u:object_r:data_app_el1_file:s0 '$DEVICE_PAYLOAD/private/libunity.so' '$DEVICE_PAYLOAD/private/libil2cpp.so' '$DEVICE_PAYLOAD/private/libwestlake_bionic_signal_box.so'; chown 0:0 '$DEVICE_SCRIPT_TARGET' '$DEVICE_CFG_TARGET'; chmod 0550 '$DEVICE_SCRIPT_TARGET' '$DEVICE_CFG_TARGET'; chcon u:object_r:system_etc_file:s0 '$DEVICE_SCRIPT_TARGET' '$DEVICE_CFG_TARGET'; rm -f '$DEVICE_ROOT/DISABLED'; printf 'state=READY\ngeneration=%s\nbackup=%s\nscript_sha256=%s\ncfg_sha256=%s\nlaunch_mode=%s\n' '$GENERATION' '$backup' '$script_sha' '$cfg_sha' '$EXPECTED_LAUNCH_MODE' > '$DEVICE_ROOT/install.env'; sync" >/dev/null \
        || die "device publish failed; backup retained at $backup"

    [ "$(device_hash "$DEVICE_SCRIPT_TARGET")" = "$script_sha" ] \
        && [ "$(device_hash "$DEVICE_CFG_TARGET")" = "$cfg_sha" ] \
        || die "system startup files failed readback"
    restore_root_readonly
    D "'$DEVICE_SCRIPT_TARGET' start" >/dev/null
    status_autostart
    printf 'BOAT_ATTACK_AUTOSTART_INSTALL=PASS\nbackup=%s\n' "$backup"
}

activate_autostart()
{
    [ -n "$(device_hash "$DEVICE_SCRIPT_TARGET")" ] || die "autostart is not installed"
    D "rm -f '$DEVICE_ROOT/DISABLED'; '$DEVICE_SCRIPT_TARGET' start" >/dev/null
    restore_root_readonly
    status_autostart
    printf 'BOAT_ATTACK_AUTOSTART_ACTIVATE=PASS\n'
}

finalize_autostart()
{
    restore_root_readonly
    status_autostart
    printf 'BOAT_ATTACK_AUTOSTART_FINALIZE=PASS\n'
}

status_autostart()
{
    local script_sha cfg_sha remote_script_sha remote_cfg_sha status_output
    local current_boot receipt_boot receipt_state receipt_generation install_state
    local install_generation install_launch_mode enabled shared_ready_state private_ready_state root_options
    local receipt_launch_mode receipt_pid apk_sha unity_sha il2cpp_sha signal_sha
    local boat_pids pid_count boat_state current_pid

    script_sha="$(sha256_file "$DEVICE_SCRIPT")"
    cfg_sha="$(sha256_file "$DEVICE_CFG")"
    remote_script_sha="$(device_hash "$DEVICE_SCRIPT_TARGET")"
    remote_cfg_sha="$(device_hash "$DEVICE_CFG_TARGET")"
    status_output="$(D "if test -x '$DEVICE_SCRIPT_TARGET'; then '$DEVICE_SCRIPT_TARGET' status; else echo installed=false; fi")"

    printf 'device_script_sha256=%s\n' "$remote_script_sha"
    printf 'device_cfg_sha256=%s\n' "$remote_cfg_sha"
    printf '%s\n' "$status_output"

    [ "$remote_script_sha" = "$script_sha" ] || die "installed autostart script drift"
    [ "$remote_cfg_sha" = "$cfg_sha" ] || die "installed autostart init cfg drift"
    verify_remote_payload || die "installed autostart payload identity drift"

    install_state="$(D "sed -n 's/^state=//p' '$DEVICE_ROOT/install.env' 2>/dev/null" | tail -n 1)"
    install_generation="$(D "sed -n 's/^generation=//p' '$DEVICE_ROOT/install.env' 2>/dev/null" | tail -n 1)"
    install_launch_mode="$(D "sed -n 's/^launch_mode=//p' '$DEVICE_ROOT/install.env' 2>/dev/null" | tail -n 1)"
    current_boot="$(D 'cat /proc/sys/kernel/random/boot_id' | tr -d ' \n')"
    receipt_boot="$(printf '%s\n' "$status_output" | sed -n 's/^boot_id=//p' | head -n 1)"
    receipt_state="$(printf '%s\n' "$status_output" | sed -n 's/^state=//p' | tail -n 1)"
    receipt_generation="$(printf '%s\n' "$status_output" | sed -n 's/^generation=//p' | head -n 1)"
    receipt_launch_mode="$(printf '%s\n' "$status_output" | sed -n 's/^launch_mode=//p' | tail -n 1)"
    receipt_pid="$(printf '%s\n' "$status_output" | sed -n 's/^pid=//p' | tail -n 1)"
    enabled="$(printf '%s\n' "$status_output" | sed -n 's/^enabled=//p' | tail -n 1)"
    shared_ready_state="$(printf '%s\n' "$status_output" | sed -n 's/^shared_ready=//p' | tail -n 1)"
    private_ready_state="$(printf '%s\n' "$status_output" | sed -n 's/^private_ready=//p' | tail -n 1)"
    apk_sha="$(printf '%s\n' "$status_output" | sed -n 's/^apk_sha256=//p' | tail -n 1)"
    unity_sha="$(printf '%s\n' "$status_output" | sed -n 's/^unity_sha256=//p' | tail -n 1)"
    il2cpp_sha="$(printf '%s\n' "$status_output" | sed -n 's/^il2cpp_sha256=//p' | tail -n 1)"
    signal_sha="$(printf '%s\n' "$status_output" | sed -n 's/^signal_box_sha256=//p' | tail -n 1)"
    boat_pids="$(printf '%s\n' "$status_output" | sed -n 's/^boat_pids=//p' | tail -n 1 | tr ',' '\n' | sed '/^$/d')"
    pid_count="$(printf '%s\n' "$boat_pids" | sed '/^$/d' | wc -l | tr -d ' ')"
    root_options="$(root_mount_options)"

    [ "$install_state" = READY ] || die "autostart install metadata is not READY"
    [ "$install_generation" = "$GENERATION" ] || die "autostart install generation drift"
    [ "$install_launch_mode" = "$EXPECTED_LAUNCH_MODE" ] || die "autostart install launch mode drift"
    [ "$receipt_boot" = "$current_boot" ] || die "autostart receipt belongs to another boot"
    [ "$receipt_state" = READY ] || die "autostart receipt is not READY"
    [ "$receipt_generation" = "$GENERATION" ] || die "autostart receipt generation drift"
    [ "$receipt_launch_mode" = "$EXPECTED_LAUNCH_MODE" ] || die "autostart receipt is not manual-launch mode"
    [ "$receipt_pid" = NONE ] || die "boot preparation receipt unexpectedly records an app PID"
    [ "$enabled" = true ] || die "autostart is disabled"
    [ "$shared_ready_state" = true ] || die "accepted shared runtime is not ready"
    [ "$private_ready_state" = true ] || die "BoatAttack private payload is not ready"
    [ "$apk_sha" = "$APK_SHA" ] || die "BoatAttack APK identity drift"
    [ "$unity_sha" = "$UNITY_SHA" ] || die "BoatAttack libunity identity drift"
    [ "$il2cpp_sha" = "$IL2CPP_SHA" ] || die "BoatAttack libil2cpp identity drift"
    [ "$signal_sha" = "$SIGNAL_SHA" ] || die "BoatAttack signal-box identity drift"
    case "$pid_count" in
        0) boat_state=STOPPED_READY; current_pid=NONE ;;
        1) boat_state=RUNNING_MANUAL; current_pid="$boat_pids" ;;
        *) die "expected at most one live BoatAttack PID, got $pid_count" ;;
    esac
    case ",$root_options," in *,ro,*) ;; *) die "root filesystem is not read-only: $root_options" ;; esac

    printf 'BOAT_ATTACK_AUTOSTART_STATUS=PASS\nlaunch_mode=%s\nboat_state=%s\ncurrent_pid=%s\nroot_mount=ro\n' \
        "$EXPECTED_LAUNCH_MODE" "$boat_state" "$current_pid"
}

device_target_pids()
{
    local uid=$1
    D 'ps -ef' | awk -v wanted="$uid" '$1 == wanted {print $2}'
}

target_online()
{
    "$HDC_BIN" list targets 2>/dev/null | tr -d '\r' | grep -qx "$BOARD"
}

reboot_test()
{
    local old_boot new_boot boot_ready receipt_boot receipt_state attempt
    local receipt_launch_mode receipt_pid uid pids pid_count
    old_boot="$(D 'cat /proc/sys/kernel/random/boot_id' | tr -d ' \n')"
    D 'sync; reboot' >/dev/null 2>&1 || true

    attempt=0
    while [ "$attempt" -lt 60 ]; do
        target_online || break
        attempt=$((attempt + 1))
        sleep 1
    done
    [ "$attempt" -lt 60 ] || die "board did not leave the old boot"

    attempt=0
    while [ "$attempt" -lt 180 ]; do
        if target_online; then
            new_boot="$(D 'cat /proc/sys/kernel/random/boot_id 2>/dev/null' | tr -d ' \n' || true)"
            boot_ready="$(D 'param get bootevent.boot.completed 2>/dev/null' | tr -d ' \n' || true)"
            if [ -n "$new_boot" ] && [ "$new_boot" != "$old_boot" ] && [ "$boot_ready" = true ]; then
                break
            fi
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    [ "$attempt" -lt 180 ] || die "new boot did not become ready"

    attempt=0
    while [ "$attempt" -lt 720 ]; do
        receipt_boot="$(D "sed -n 's/^boot_id=//p' '$DEVICE_ROOT/receipt.env' 2>/dev/null" | head -n 1)"
        receipt_state="$(D "sed -n 's/^state=//p' '$DEVICE_ROOT/receipt.env' 2>/dev/null" | tail -n 1)"
        if [ "$receipt_boot" = "$new_boot" ] && [ "$receipt_state" = READY ]; then
            break
        fi
        if [ "$receipt_boot" = "$new_boot" ] && [ "$receipt_state" = FAILED ]; then
            die "autostart failed during boot: $(D "cat '$DEVICE_ROOT/receipt.env' 2>/dev/null")"
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    [ "$attempt" -lt 720 ] \
        || die "autostart receipt did not reach READY: $(D "cat '$DEVICE_ROOT/receipt.env' 2>/dev/null")"

    [ "$(D "sed -n 's/^shared_state=//p' '$DEVICE_ROOT/receipt.env'" | tail -n 1)" = MOUNTED_BY_AUTOSTART ] \
        || die "shared runtime was not restored by the boot hook"
    [ "$(D "sed -n 's/^private_state=//p' '$DEVICE_ROOT/receipt.env'" | tail -n 1)" = MOUNTED_BY_AUTOSTART ] \
        || die "BoatAttack private payload was not restored by the boot hook"

    for target in \
        /system/android/lib64/liboh_adapter_bridge.so \
        /system/lib64/westlake/route-a/74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d/libwestlake_android_runtime_provider.so \
        /system/lib64/appspawn/libwestlake_android_child.z.so \
        /system/bin/appspawn-x \
        /system/android/framework/oh-adapter-runtime.jar \
        /system/android/lib64/libwestlake_bionic_pthread_bridge.so \
        /system/android/lib64/libnativeloader.so \
        /system/lib64/westlake/route-a/74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d/libnativeloader.so \
        /system/android/lib64/libandroid.so \
        /system/android/lib64/liboh_android_runtime.so \
        /data/app/el1/bundle/public/com.Unity3d.BoatAttackDay/android/lib/arm64-v8a/libwestlake_bionic_signal_box.so \
        /data/app/el1/bundle/public/com.Unity3d.BoatAttackDay/android/lib/arm64-v8a/libunity.so \
        /data/app/el1/bundle/public/com.Unity3d.BoatAttackDay/android/lib/arm64-v8a/libil2cpp.so; do
        D "grep -F ' $target ' /proc/self/mountinfo" | tail -n 1 | grep -Fq /boatattack-autostart/ \
            || die "boot mount source mismatch: $target"
    done

    receipt_launch_mode="$(D "sed -n 's/^launch_mode=//p' '$DEVICE_ROOT/receipt.env'" | tail -n 1)"
    receipt_pid="$(D "sed -n 's/^pid=//p' '$DEVICE_ROOT/receipt.env'" | tail -n 1)"
    uid="$(D "sed -n 's/^uid=//p' '$DEVICE_ROOT/receipt.env'" | tail -n 1)"
    [ "$receipt_launch_mode" = "$EXPECTED_LAUNCH_MODE" ] \
        || die "boot receipt did not select manual launch"
    [ "$receipt_pid" = NONE ] || die "boot receipt unexpectedly contains an app PID"
    case "$uid" in ''|*[!0-9]*) die "invalid BoatAttack UID in receipt" ;; esac
    sleep 10
    pids="$(device_target_pids "$uid")"
    pid_count="$(printf '%s\n' "$pids" | sed '/^$/d' | wc -l | tr -d ' ')"
    [ "$pid_count" = 0 ] || die "BoatAttack started automatically after boot: $pids"

    printf 'BOAT_ATTACK_AUTOSTART_REBOOT=PASS\nBOAT_ATTACK_MANUAL_BOOT_REBOOT=PASS\nold_boot=%s\nnew_boot=%s\nlaunch_mode=%s\npid=NONE\n' \
        "$old_boot" "$new_boot" "$EXPECTED_LAUNCH_MODE"
    D "cat '$DEVICE_ROOT/receipt.env'"
}

uninstall_autostart()
{
    local backup script_missing cfg_missing
    [ -n "$(device_hash "$DEVICE_SCRIPT_TARGET")" ] || die "autostart is not installed"
    D "begetctl stop_service boatattack-autostart >/dev/null 2>&1 || true; sleep 1" >/dev/null
    D "'$DEVICE_SCRIPT_TARGET' rollback" >/dev/null
    backup="$(D "sed -n 's/^backup=//p' '$DEVICE_ROOT/install.env' 2>/dev/null" | tail -n 1)"
    [ -n "$backup" ] || die "install backup is missing"
    script_missing="$(D "test -f '$backup/script.missing' && echo true || echo false" | tail -n 1)"
    cfg_missing="$(D "test -f '$backup/cfg.missing' && echo true || echo false" | tail -n 1)"
    make_root_writable
    D "set -e; touch '$DEVICE_ROOT/DISABLED'; if test -f '$backup/script.missing'; then rm -f '$DEVICE_SCRIPT_TARGET'; else cp '$backup/boat-attack-autostart.sh' '$DEVICE_SCRIPT_TARGET'; fi; if test -f '$backup/cfg.missing'; then rm -f '$DEVICE_CFG_TARGET'; else cp '$backup/startup.cfg' '$DEVICE_CFG_TARGET'; fi; printf 'state=UNINSTALLED\ngeneration=%s\nbackup=%s\n' '$GENERATION' '$backup' > '$DEVICE_ROOT/install.env'; sync" >/dev/null
    if [ "$script_missing" = true ]; then
        [ -z "$(device_hash "$DEVICE_SCRIPT_TARGET")" ] || die "system script removal failed"
    else
        [ "$(device_hash "$DEVICE_SCRIPT_TARGET")" = "$(device_hash "$backup/boat-attack-autostart.sh")" ] \
            || die "system script restore failed"
    fi
    if [ "$cfg_missing" = true ]; then
        [ -z "$(device_hash "$DEVICE_CFG_TARGET")" ] || die "init cfg removal failed"
    else
        [ "$(device_hash "$DEVICE_CFG_TARGET")" = "$(device_hash "$backup/startup.cfg")" ] \
            || die "init cfg restore failed"
    fi
    [ "$(D "sed -n 's/^state=//p' '$DEVICE_ROOT/install.env'" | tail -n 1)" = UNINSTALLED ] \
        || die "install metadata did not reach UNINSTALLED"
    restore_root_readonly
    printf 'BOAT_ATTACK_AUTOSTART_UNINSTALL=PASS\nbackup=%s\n' "$backup"
}

[ "$#" -le 2 ] || { usage; die "too many arguments"; }
case "$MODE" in
    install|activate|finalize|status|reboot-test|uninstall) ;;
    -h|--help|help) usage; exit 0 ;;
    *) usage; die "unknown mode: $MODE" ;;
esac

local_preflight
device_preflight

case "$MODE" in
    status) status_autostart ;;
    install)
        claim_board
        install_autostart
        ;;
    activate)
        claim_board
        activate_autostart
        ;;
    finalize)
        claim_board
        finalize_autostart
        ;;
    reboot-test)
        claim_board
        reboot_test
        ;;
    uninstall)
        claim_board
        uninstall_autostart
        ;;
esac
