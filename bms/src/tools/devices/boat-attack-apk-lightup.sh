#!/usr/bin/env bash

set -Eeuo pipefail

SELF="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
ZIGZAG_DRIVER="$REPO_ROOT/src/tools/devices/zigzag-apk-lightup.sh"

HDC_BIN="${HDC_BIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
PATCHELF_BIN="${PATCHELF_BIN:-/opt/homebrew/bin/patchelf}"
FFMPEG_BIN="${FFMPEG_BIN:-$(command -v ffmpeg || true)}"
FFPROBE_BIN="${FFPROBE_BIN:-$(command -v ffprobe || true)}"

BOARD_ONLY="61ae0be500000000000000000324012c"
BOARD_8605="5ce2dcee00000000000000000923012c"
BOARD_5EA1="5ea1719200000000000000001123012c"
ROM_ONLY="OpenHarmony-6.1.0.31"
BUNDLE="com.Unity3d.BoatAttackDay"
ABILITY="com.unity3d.player.UnityPlayerActivity"

APK="$REPO_ROOT/APKS/BoatAttack/dist/boat-attack-a.apk"
APK_SHA="8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444"
RAW_UNITY_SHA="1e44603c528af84aed2e4a538d411c119166b9ccadd7aa2abf51ffa97ef47ca2"
RAW_IL2CPP_SHA="58555c421de763165225e8bd9e2940f2e5c84515a2c87cdefc0892cae216f4fe"
UNITY_SHA="1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac"
IL2CPP_SHA="f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746"
SIGNAL_BOX_SHA="7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da"
EMPTY_SHA="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

STATE_ROOT="$REPO_ROOT/.state/boat-attack"
UNITY_CANDIDATE="$STATE_ROOT/c-candidates/c7-unity-disable-swappy/libunity.so"
IL2CPP_CANDIDATE="$STATE_ROOT/c-candidates/c4-il2cpp-pthread-edge/libil2cpp.so"
SIGNAL_BOX_CANDIDATE="$STATE_ROOT/c-candidates/c1-unity-signal-box/libwestlake_bionic_signal_box.so"
SIGNAL_RENAME_MAP="$REPO_ROOT/src/adapter/framework/native-compat/bionic-signal-box/tuanjie_signal_symbols.map"

SHARED_CANDIDATE="$REPO_ROOT/.bridge-payload/zigzag-candidates/strict-boat-assembled-20260924T074522Z-25403"
SHARED_ADAPTER_SHA="8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e"
SHARED_PROVIDER_SHA="f821d20eaefc798b638192124e3a98683103f3d509c0b66ca1c6946037cccdb0"
SHARED_CHILD_SHA="47f238aede6336ce3770861a6a742e71abc28f35516481299797c05c63149b57"
SHARED_APPSPAWN_SHA="76e6df931905177c8abde4054ee5516cb6d8394c67dce8f79dfadf0847b96747"
SHARED_RUNTIME_SHA="adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130"
SHARED_RUNTIME_JAR_SHA="56e4d4733bb6dc4f260981f51184234522df7a67c0eca01bd1b9ef87369221af"
SHARED_PTHREAD_SHA="db31d6d81c543860449e4e13f94dda6d39acde94ce00e34e7087a4d796e88fc6"
SHARED_NATIVE_LOADER_SHA="fde6f31c6f8911bd5be165d69bc248f47699be435240dc855fa7528c0ba73ccd"
SHARED_ADAPTER_TARGET="/system/android/lib64/liboh_adapter_bridge.so"
SHARED_PROVIDER_TARGET="/system/lib64/westlake/route-a/74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d/libwestlake_android_runtime_provider.so"
SHARED_CHILD_TARGET="/system/lib64/appspawn/libwestlake_android_child.z.so"
SHARED_APPSPAWN_TARGET="/system/bin/appspawn-x"
SHARED_RUNTIME_TARGET="/system/android/lib64/liboh_android_runtime.so"
SHARED_LIBANDROID_TARGET="/system/android/lib64/libandroid.so"
SHARED_RUNTIME_JAR_TARGET="/system/android/framework/oh-adapter-runtime.jar"
SHARED_PTHREAD_TARGET="/system/android/lib64/libwestlake_bionic_pthread_bridge.so"
SHARED_NATIVE_LOADER_TARGET="/system/android/lib64/libnativeloader.so"
SHARED_ROUTE_NATIVE_LOADER_TARGET="$SHARED_PROVIDER_TARGET"
SHARED_ROUTE_NATIVE_LOADER_TARGET="${SHARED_ROUTE_NATIVE_LOADER_TARGET%/libwestlake_android_runtime_provider.so}/libnativeloader.so"

DEVICE_APP_ROOT="/data/app/el1/bundle/public/$BUNDLE/android"
DEVICE_APK="$DEVICE_APP_ROOT/base.apk"
DEVICE_LIB_ROOT="$DEVICE_APP_ROOT/lib/arm64-v8a"
UNITY_TARGET="$DEVICE_LIB_ROOT/libunity.so"
IL2CPP_TARGET="$DEVICE_LIB_ROOT/libil2cpp.so"
SIGNAL_BOX_TARGET="$DEVICE_LIB_ROOT/libwestlake_bionic_signal_box.so"
REMOTE_ROOT="/data/boat-attack-apk-lightup/accepted-c10"
REMOTE_APK="$REMOTE_ROOT/boat-attack-a.apk"
REMOTE_UNITY="$REMOTE_ROOT/libunity.so"
REMOTE_IL2CPP="$REMOTE_ROOT/libil2cpp.so"
REMOTE_SIGNAL_BOX="$REMOTE_ROOT/libwestlake_bionic_signal_box.so"
AUTOSTART_PRIVATE_SOURCE="/boatattack-autostart/generations/${SHARED_CANDIDATE##*/}/private/"

RUN_ROOT="$REPO_ROOT/var/state/reproduce-boat-attack-apk"
CHANNEL_ROOT="$REPO_ROOT/var/state/agent-channel"
LOCK_ROOT="$CHANNEL_ROOT/.locks"

MODE="${1:-check}"
BOARD="${2:-$BOARD_ONLY}"
case "$BOARD" in
    "$BOARD_ONLY") BOARD_LABEL=61ae ;;
    "$BOARD_8605") BOARD_LABEL=8605 ;;
    "$BOARD_5EA1") BOARD_LABEL=5ea1 ;;
    "5ea34a4500000000000000001123012c") BOARD_LABEL=5ea ;;
    "61b0657200000000000000000324012c") BOARD_LABEL=61b ;;
    "5cd1e3dd00000000000000000923012c") BOARD_LABEL=5cd ;;
    *) BOARD_LABEL=unsupported ;;
esac
CHANNEL_FILE="$CHANNEL_ROOT/boat-attack-apk-c-$BOARD_LABEL.md"
LOCK_DIR="$LOCK_ROOT/$BOARD.lock"
CLAIMED=0
RUN_EVIDENCE=""
ZIGZAG_RECEIPT=""

die()
{
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

usage()
{
    printf '%s\n' \
        "usage: $SELF check [supported-board-serial]" \
        "       $SELF quick [supported-board-serial]" \
        "       $SELF status [supported-board-serial]" \
        "       $SELF restore [supported-board-serial]" \
        "       $SELF rollback [supported-board-serial]"
}

trim()
{
    tr -d ' \r\n'
}

sha256_file()
{
    shasum -a 256 "$1" | awk '{print $1}'
}

manifest_value()
{
    local manifest=$1 key=$2
    sed -n "s/^${key}=//p" "$manifest" | head -n 1
}

require_hash()
{
    local expected=$1 path=$2 actual
    [ -f "$path" ] || die "missing fixed input: $path"
    actual="$(sha256_file "$path")"
    [ "$actual" = "$expected" ] \
        || die "hash drift: $path expected=$expected actual=$actual"
}

H()
{
    "$HDC_BIN" -t "$BOARD" "$@"
}

D()
{
    H shell "$1" 2>&1 | tr -d '\r'
}

device_hash()
{
    D "sha256sum '$1' 2>/dev/null" | awk 'NR == 1 {print $1}'
}

mount_line()
{
    local target=$1
    D 'cat /proc/self/mountinfo' \
        | awk -v wanted="$target" '$5 == wanted {print; exit}'
}

patch_binary_hex_exact()
{
    local file=$1 offset=$2 expected=$3 replacement=$4 label=$5
    perl -e '
        use strict;
        use warnings;
        my ($path, $offset_text, $expected, $replacement, $label) = @ARGV;
        length($expected) == length($replacement)
            or die "$label: replacement length mismatch\n";
        my $offset = oct($offset_text);
        my $expected_bytes = pack("H*", $expected);
        my $replacement_bytes = pack("H*", $replacement);
        open my $fh, "+<:raw", $path or die "open $path: $!\n";
        seek($fh, $offset, 0) or die "seek $path: $!\n";
        my $actual = "";
        my $count = read($fh, $actual, length($expected_bytes));
        defined($count) && $count == length($expected_bytes)
            or die "$label: short read at $offset_text\n";
        unpack("H*", $actual) eq $expected
            or die "$label: generation mismatch at $offset_text, got="
                . unpack("H*", $actual) . " expected=$expected\n";
        seek($fh, $offset, 0) or die "seek-write $path: $!\n";
        my $written = syswrite($fh, $replacement_bytes);
        defined($written) && $written == length($replacement_bytes)
            or die "$label: short write at $offset_text\n";
        close $fh or die "close $path: $!\n";
    ' "$file" "$offset" "$expected" "$replacement" "$label"
}

candidate_state()
{
    if [ -f "$UNITY_CANDIDATE" ] && [ -f "$IL2CPP_CANDIDATE" ] \
        && [ -f "$SIGNAL_BOX_CANDIDATE" ] \
        && [ "$(sha256_file "$UNITY_CANDIDATE")" = "$UNITY_SHA" ] \
        && [ "$(sha256_file "$IL2CPP_CANDIDATE")" = "$IL2CPP_SHA" ] \
        && [ "$(sha256_file "$SIGNAL_BOX_CANDIDATE")" = "$SIGNAL_BOX_SHA" ]; then
        printf 'READY\n'
    else
        printf 'BUILD_ON_RESTORE\n'
    fi
}

local_preflight()
{
    [ "$(uname -s)" = Darwin ] || die "this reproduction is local-Mac only"
    [ -z "${SSH_CONNECTION:-}" ] || die "SSH execution is outside this fixed workflow"
    [ -x "$HDC_BIN" ] || die "missing DevEco hdc: $HDC_BIN"
    [ -x "$PATCHELF_BIN" ] || die "missing patchelf: $PATCHELF_BIN"
    [ -x "$ZIGZAG_DRIVER" ] || die "missing ZigZag shared-candidate driver"
    [ -n "$FFMPEG_BIN" ] && [ -x "$FFMPEG_BIN" ] || die "ffmpeg is required"
    [ -n "$FFPROBE_BIN" ] && [ -x "$FFPROBE_BIN" ] || die "ffprobe is required"
    command -v unzip >/dev/null 2>&1 || die "unzip is required"
    command -v rg >/dev/null 2>&1 || die "rg is required"
    bash -n "$SELF"
    bash -n "$ZIGZAG_DRIVER"
    require_hash "$APK_SHA" "$APK"
    [ -s "$SIGNAL_RENAME_MAP" ] || die "missing signal rename map"
    [ -f "$SHARED_CANDIDATE/manifest.env" ] || die "missing accepted shared candidate"
    [ ! -f "$UNITY_CANDIDATE" ] || require_hash "$UNITY_SHA" "$UNITY_CANDIDATE"
    [ ! -f "$IL2CPP_CANDIDATE" ] || require_hash "$IL2CPP_SHA" "$IL2CPP_CANDIDATE"
    [ ! -f "$SIGNAL_BOX_CANDIDATE" ] \
        || require_hash "$SIGNAL_BOX_SHA" "$SIGNAL_BOX_CANDIDATE"
}

build_candidates()
{
    local build raw_unity raw_il2cpp signal_source
    [ "$(candidate_state)" != READY ] || return 0
    build="$(mktemp -d "$STATE_ROOT/c-reproduce-build.XXXXXX")"
    raw_unity="$build/libunity.so"
    raw_il2cpp="$build/libil2cpp.so"
    unzip -p "$APK" lib/arm64-v8a/libunity.so > "$raw_unity"
    unzip -p "$APK" lib/arm64-v8a/libil2cpp.so > "$raw_il2cpp"
    require_hash "$RAW_UNITY_SHA" "$raw_unity"
    require_hash "$RAW_IL2CPP_SHA" "$raw_il2cpp"

    "$PATCHELF_BIN" --rename-dynamic-symbols "$SIGNAL_RENAME_MAP" "$raw_unity"
    "$PATCHELF_BIN" --add-needed libwestlake_bionic_signal_box.so "$raw_unity"
    "$PATCHELF_BIN" --add-needed libwestlake_bionic_pthread_bridge.so "$raw_unity"
    patch_binary_hex_exact "$raw_unity" 0x761ed8 f40f1ef8 11000014 \
        "Unity core resolver -> eglGetProcAddress"
    patch_binary_hex_exact "$raw_unity" 0x690ac0 808900d0 c0035fd6 \
        "disable optional phone listener"
    patch_binary_hex_exact "$raw_unity" 0x67a554 f37bbfa9338a00d0 \
        e0031f2ac0035fd6 "disable unsupported Swappy predicate"

    "$PATCHELF_BIN" --rename-dynamic-symbols "$SIGNAL_RENAME_MAP" "$raw_il2cpp"
    "$PATCHELF_BIN" --add-needed libwestlake_bionic_signal_box.so "$raw_il2cpp"
    "$PATCHELF_BIN" --add-needed libwestlake_bionic_pthread_bridge.so "$raw_il2cpp"

    signal_source="$SHARED_CANDIDATE/files/libwestlake_bionic_signal_box.so"
    require_hash "$SIGNAL_BOX_SHA" "$signal_source"
    mkdir -p "$(dirname "$UNITY_CANDIDATE")" "$(dirname "$IL2CPP_CANDIDATE")" \
        "$(dirname "$SIGNAL_BOX_CANDIDATE")"
    require_hash "$UNITY_SHA" "$raw_unity"
    require_hash "$IL2CPP_SHA" "$raw_il2cpp"
    [ -e "$UNITY_CANDIDATE" ] || mv "$raw_unity" "$UNITY_CANDIDATE"
    [ -e "$IL2CPP_CANDIDATE" ] || mv "$raw_il2cpp" "$IL2CPP_CANDIDATE"
    [ -e "$SIGNAL_BOX_CANDIDATE" ] || cp "$signal_source" "$SIGNAL_BOX_CANDIDATE"
    require_hash "$UNITY_SHA" "$UNITY_CANDIDATE"
    require_hash "$IL2CPP_SHA" "$IL2CPP_CANDIDATE"
    require_hash "$SIGNAL_BOX_SHA" "$SIGNAL_BOX_CANDIDATE"
}

device_preflight()
{
    case "$BOARD" in
        "$BOARD_ONLY"|"$BOARD_8605"|"$BOARD_5EA1"|"5ea34a4500000000000000001123012c"|"61b0657200000000000000000324012c"|"5cd1e3dd00000000000000000923012c") ;;
        *) die "unsupported direct board: $BOARD" ;;
    esac
    "$HDC_BIN" list targets 2>/dev/null | tr -d '\r' | grep -qx "$BOARD" \
        || die "$BOARD_LABEL is not connected: $BOARD"
    [ "$(D 'param get const.ohos.fullname' | trim)" = "$ROM_ONLY" ] \
        || die "$BOARD_LABEL ROM is not $ROM_ONLY"
    [ "$(D 'uname -m' | trim)" = aarch64 ] || die "$BOARD_LABEL is not aarch64"
    [ "$(D 'param get bootevent.boot.completed' | trim)" = true ] \
        || die "$BOARD_LABEL boot is not complete"
}

bundle_uid()
{
    D "bm dump -n '$BUNDLE' 2>/dev/null" \
        | grep -oE '"uid": *[0-9]+' | head -n 1 | grep -oE '[0-9]+$' || true
}

pids_for_uid()
{
    local uid=$1
    D 'ps -ef' | awk -v wanted="$uid" \
        '$1 == wanted && $2 ~ /^[0-9]+$/ {print $2}' | sed '/^$/d'
}

surface_ids()
{
    perl -ne 'while (/SURFACE_NODE\[([0-9]+)\].*Name \[AdapterSurfaceView\]/g) {print "$1\n"}'
}

foreground_surface_ids()
{
    perl -ne 'while (/SURFACE_NODE\[([0-9]+)\].*abilityState: foreground.*Name \[AdapterSurfaceView\]/g) {print "$1\n"}'
}

single_target_pid()
{
    local uid=$1 pids count
    pids="$(pids_for_uid "$uid")"
    count="$(printf '%s\n' "$pids" | sed '/^$/d' | wc -l | trim)"
    [ "$count" = 1 ] || return 1
    printf '%s\n' "$pids" | head -n 1
}

stop_target()
{
    local uid pid attempt
    uid="$(bundle_uid)"
    D "aa force-stop '$BUNDLE' >/dev/null 2>&1 || true" >/dev/null || true
    [ -n "$uid" ] || return 0
    while IFS= read -r pid; do
        case "$pid" in ''|*[!0-9]*) continue ;; esac
        D "kill -9 '$pid' >/dev/null 2>&1 || true" >/dev/null || true
    done < <(pids_for_uid "$uid")
    for attempt in $(seq 1 30); do
        [ -z "$(pids_for_uid "$uid")" ] && return 0
        sleep 0.1
    done
    return 1
}

find_current_zigzag_receipt()
{
    local current_boot receipt evidence candidate evidence_boot
    current_boot="$(D 'cat /proc/sys/kernel/random/boot_id' | trim)"
    while IFS= read -r receipt; do
        [ -f "$receipt" ] || continue
        [ "$(manifest_value "$receipt" DEVELOPER_REPRODUCIBLE_LIGHT)" = 1 ] || continue
        candidate="$(manifest_value "$receipt" candidate)"
        [ "$candidate" = "$SHARED_CANDIDATE" ] || continue
        evidence="$(dirname "$receipt")"
        [ -f "$evidence/envstamp.txt" ] || continue
        [ "$(manifest_value "$evidence/envstamp.txt" artifact_sha256)" = \
            aaa7c9cce4886eef1280e917fd25bf434c53065cf0bf8b5704b83738137275bc ] \
            || continue
        evidence_boot="$(manifest_value "$evidence/envstamp.txt" boot_id)"
        if [ "$evidence_boot" = "$current_boot" ]; then
            ZIGZAG_RECEIPT="$receipt"
            return 0
        fi
    done < <(find "$REPO_ROOT/var/evidence/ab-compare" \
        -name DEVELOPER-REPRODUCIBLE-LIGHT.env -type f -print 2>/dev/null | sort -r)
    return 1
}

shared_hashes_ready()
{
    [ "$(device_hash "$SHARED_ADAPTER_TARGET")" = "$SHARED_ADAPTER_SHA" ] \
        && [ "$(device_hash "$SHARED_PROVIDER_TARGET")" = "$SHARED_PROVIDER_SHA" ] \
        && [ "$(device_hash "$SHARED_CHILD_TARGET")" = "$SHARED_CHILD_SHA" ] \
        && [ "$(device_hash "$SHARED_APPSPAWN_TARGET")" = "$SHARED_APPSPAWN_SHA" ] \
        && [ "$(device_hash "$SHARED_RUNTIME_TARGET")" = "$SHARED_RUNTIME_SHA" ] \
        && [ "$(device_hash "$SHARED_LIBANDROID_TARGET")" = "$SHARED_RUNTIME_SHA" ] \
        && [ "$(device_hash "$SHARED_RUNTIME_JAR_TARGET")" = "$SHARED_RUNTIME_JAR_SHA" ] \
        && [ "$(device_hash "$SHARED_PTHREAD_TARGET")" = "$SHARED_PTHREAD_SHA" ] \
        && [ "$(device_hash "$SHARED_NATIVE_LOADER_TARGET")" = "$SHARED_NATIVE_LOADER_SHA" ] \
        && [ "$(device_hash "$SHARED_ROUTE_NATIVE_LOADER_TARGET")" = "$SHARED_NATIVE_LOADER_SHA" ]
}

require_shared_baseline()
{
    shared_hashes_ready || die "accepted BoatAttack shared generation is not active; run restore"
    find_current_zigzag_receipt \
        || die "no accepted ZigZag receipt for this shared generation and boot; run restore"
}

restore_shared_baseline()
{
    if shared_hashes_ready && find_current_zigzag_receipt; then
        return 0
    fi
    "$ZIGZAG_DRIVER" run-light-risk "$BOARD" "$SHARED_CANDIDATE"
    require_shared_baseline
}

unmount_private_target()
{
    local target=$1 line
    line="$(mount_line "$target")"
    [ -n "$line" ] || return 0
    printf '%s\n' "$line" | grep -Fq '/boat-attack-apk-lightup/' \
        || die "refusing to unmount a non-BoatAttack layer: $line"
    D "umount '$target'" >/dev/null
    [ -z "$(mount_line "$target")" ]
}

rollback_private()
{
    local signal_under
    stop_target || return 1
    unmount_private_target "$IL2CPP_TARGET" || return 1
    unmount_private_target "$UNITY_TARGET" || return 1
    unmount_private_target "$SIGNAL_BOX_TARGET" || return 1
    signal_under="$(device_hash "$SIGNAL_BOX_TARGET")"
    if [ "$signal_under" = "$EMPTY_SHA" ]; then
        D "rm -f '$SIGNAL_BOX_TARGET'" >/dev/null || return 1
    fi
    if [ "$(device_hash "$DEVICE_APK")" = "$APK_SHA" ]; then
        [ "$(device_hash "$UNITY_TARGET")" = "$RAW_UNITY_SHA" ] || return 1
        [ "$(device_hash "$IL2CPP_TARGET")" = "$RAW_IL2CPP_SHA" ] || return 1
    fi
}

prepare_sandbox()
{
    local uid=$1
    D "set -e; for d in /data/app/el1/100/base /data/app/el1/100/database /data/app/el2/100/base /data/app/el2/100/database /data/app/el2/100/sharefiles /data/app/el3/100/base /data/app/el3/100/database /data/app/el4/100/base /data/app/el4/100/database; do mkdir -p \${d}/'$BUNDLE'; done; mkdir -p /data/app/el2/100/log/'$BUNDLE'; for s in cache code_cache databases files haps no_backup preferences shared_prefs temp; do mkdir -p /data/app/el2/100/base/'$BUNDLE'/\${s}; done; chown -R '$uid':'$uid' /data/app/el1/100/base/'$BUNDLE' /data/app/el1/100/database/'$BUNDLE' /data/app/el2/100/base/'$BUNDLE' /data/app/el2/100/database/'$BUNDLE' /data/app/el2/100/sharefiles/'$BUNDLE' /data/app/el3/100/base/'$BUNDLE' /data/app/el3/100/database/'$BUNDLE' /data/app/el4/100/base/'$BUNDLE' /data/app/el4/100/database/'$BUNDLE'; chown '$uid':log /data/app/el2/100/log/'$BUNDLE'; chmod -R 0700 /data/app/el1/100/base/'$BUNDLE' /data/app/el2/100/base/'$BUNDLE' /data/app/el2/100/sharefiles/'$BUNDLE' /data/app/el3/100/base/'$BUNDLE' /data/app/el4/100/base/'$BUNDLE'; chmod 0770 /data/app/el1/100/database/'$BUNDLE' /data/app/el2/100/database/'$BUNDLE' /data/app/el2/100/log/'$BUNDLE' /data/app/el3/100/database/'$BUNDLE' /data/app/el4/100/database/'$BUNDLE'; chcon -R u:object_r:appdat:s0 /data/app/el1/100/base/'$BUNDLE' /data/app/el1/100/database/'$BUNDLE' /data/app/el2/100/base/'$BUNDLE' /data/app/el2/100/database/'$BUNDLE' /data/app/el2/100/sharefiles/'$BUNDLE' /data/app/el3/100/base/'$BUNDLE' /data/app/el3/100/database/'$BUNDLE' /data/app/el4/100/base/'$BUNDLE' /data/app/el4/100/database/'$BUNDLE'; chcon u:object_r:data_app_el2_file:s0 /data/app/el2/100/log/'$BUNDLE'" >/dev/null
}

ensure_original_apk()
{
    local installed result uid
    installed="$(device_hash "$DEVICE_APK")"
    if [ "$installed" != "$APK_SHA" ]; then
        rollback_private || true
        D "bm uninstall -n '$BUNDLE' >/dev/null 2>&1 || true; mkdir -p '$REMOTE_ROOT'" >/dev/null
        H file send "$APK" "$REMOTE_APK" >/dev/null
        [ "$(device_hash "$REMOTE_APK")" = "$APK_SHA" ] || return 1
        result="$(D "bm install -p '$REMOTE_APK'")"
        printf '%s\n' "$result"
        printf '%s\n' "$result" | grep -q 'install bundle successfully' || return 1
    fi
    [ "$(device_hash "$DEVICE_APK")" = "$APK_SHA" ] || return 1
    uid="$(bundle_uid)"
    [ -n "$uid" ] || return 1
    prepare_sandbox "$uid"
}

private_target_owned()
{
    local target=$1 line
    line="$(mount_line "$target")"
    [ -n "$line" ] || return 1
    printf '%s\n' "$line" | grep -Fq '/boat-attack-apk-lightup/' && return 0
    printf '%s\n' "$line" | grep -Fq "$AUTOSTART_PRIVATE_SOURCE"
}

private_already_restored()
{
    [ "$(device_hash "$DEVICE_APK")" = "$APK_SHA" ] \
        && [ "$(device_hash "$UNITY_TARGET")" = "$UNITY_SHA" ] \
        && [ "$(device_hash "$IL2CPP_TARGET")" = "$IL2CPP_SHA" ] \
        && [ "$(device_hash "$SIGNAL_BOX_TARGET")" = "$SIGNAL_BOX_SHA" ] \
        && private_target_owned "$UNITY_TARGET" \
        && private_target_owned "$IL2CPP_TARGET" \
        && private_target_owned "$SIGNAL_BOX_TARGET"
}

restore_private()
{
    local signal_under
    build_candidates
    private_already_restored && return 0
    rollback_private || return 1
    ensure_original_apk || return 1
    [ "$(device_hash "$UNITY_TARGET")" = "$RAW_UNITY_SHA" ] || return 1
    [ "$(device_hash "$IL2CPP_TARGET")" = "$RAW_IL2CPP_SHA" ] || return 1
    signal_under="$(device_hash "$SIGNAL_BOX_TARGET")"
    [ -z "$signal_under" ] || return 1

    D "mkdir -p '$REMOTE_ROOT'" >/dev/null
    H file send "$UNITY_CANDIDATE" "$REMOTE_UNITY" >/dev/null
    H file send "$IL2CPP_CANDIDATE" "$REMOTE_IL2CPP" >/dev/null
    H file send "$SIGNAL_BOX_CANDIDATE" "$REMOTE_SIGNAL_BOX" >/dev/null
    [ "$(device_hash "$REMOTE_UNITY")" = "$UNITY_SHA" ] || return 1
    [ "$(device_hash "$REMOTE_IL2CPP")" = "$IL2CPP_SHA" ] || return 1
    [ "$(device_hash "$REMOTE_SIGNAL_BOX")" = "$SIGNAL_BOX_SHA" ] || return 1

    D "touch '$SIGNAL_BOX_TARGET'; chown 0:0 '$SIGNAL_BOX_TARGET'; chmod 0644 '$SIGNAL_BOX_TARGET'; chcon u:object_r:data_app_el1_file:s0 '$SIGNAL_BOX_TARGET'; chown 0:0 '$REMOTE_UNITY' '$REMOTE_IL2CPP' '$REMOTE_SIGNAL_BOX'; chmod 0755 '$REMOTE_UNITY' '$REMOTE_IL2CPP' '$REMOTE_SIGNAL_BOX'; chcon u:object_r:data_app_el1_file:s0 '$REMOTE_UNITY' '$REMOTE_IL2CPP' '$REMOTE_SIGNAL_BOX'; mount --bind '$REMOTE_SIGNAL_BOX' '$SIGNAL_BOX_TARGET'; mount --bind '$REMOTE_UNITY' '$UNITY_TARGET'; mount --bind '$REMOTE_IL2CPP' '$IL2CPP_TARGET'; chmod 0755 '$SIGNAL_BOX_TARGET' '$UNITY_TARGET' '$IL2CPP_TARGET'; chcon u:object_r:data_app_el1_file:s0 '$SIGNAL_BOX_TARGET' '$UNITY_TARGET' '$IL2CPP_TARGET'" >/dev/null \
        || return 1
    [ "$(device_hash "$UNITY_TARGET")" = "$UNITY_SHA" ] || return 1
    [ "$(device_hash "$IL2CPP_TARGET")" = "$IL2CPP_SHA" ] || return 1
    [ "$(device_hash "$SIGNAL_BOX_TARGET")" = "$SIGNAL_BOX_SHA" ] || return 1
    printf '%s\n' "$(mount_line "$UNITY_TARGET")" | grep -Fq '/boat-attack-apk-lightup/' || return 1
    printf '%s\n' "$(mount_line "$IL2CPP_TARGET")" | grep -Fq '/boat-attack-apk-lightup/' || return 1
    printf '%s\n' "$(mount_line "$SIGNAL_BOX_TARGET")" | grep -Fq '/boat-attack-apk-lightup/' || return 1
}

require_restored()
{
    [ "$(device_hash "$DEVICE_APK")" = "$APK_SHA" ] \
        || die "the exact original BoatAttack APK is not installed; run restore"
    [ "$(device_hash "$UNITY_TARGET")" = "$UNITY_SHA" ] \
        || die "accepted C7 libunity is not active; run restore"
    [ "$(device_hash "$IL2CPP_TARGET")" = "$IL2CPP_SHA" ] \
        || die "accepted C4 libil2cpp is not active; run restore"
    [ "$(device_hash "$SIGNAL_BOX_TARGET")" = "$SIGNAL_BOX_SHA" ] \
        || die "accepted signal box is not active; run restore"
}

capture_screen()
{
    local run=$1 label=$2 remote
    remote="/data/local/tmp/boat-attack-${label}-$$.jpeg"
    D "snapshot_display -f '$remote'" >/dev/null || return 1
    H file recv "$remote" "$run/$label.jpeg" >/dev/null || return 1
    D "rm -f '$remote'" >/dev/null || true
    [ -s "$run/$label.jpeg" ] || return 1
    [ "$(file "$run/$label.jpeg")" != "" ] || return 1
}

decoded_frame_hash()
{
    "$FFMPEG_BIN" -hide_banner -loglevel error -i "$1" \
        -vf 'format=rgb24' -f hash -hash sha256 - 2>/dev/null | sed 's/^SHA256=//'
}

frame_geometry()
{
    "$FFPROBE_BIN" -v error -select_streams v:0 \
        -show_entries stream=width,height -of csv=p=0:s=x "$1" 2>/dev/null
}

gameplay_difference()
{
    local before=$1 after=$2 output=$3
    "$FFMPEG_BIN" -hide_banner -loglevel error -i "$before" -i "$after" \
        -lavfi "[0:v]format=gray[a];[1:v]format=gray[b];[a][b]blend=all_mode=difference,signalstats,metadata=print:file=$output" \
        -f null - >/dev/null 2>&1 || return 1
    sed -n 's/^lavfi.signalstats.YAVG=//p' "$output" | head -n 1
}

assert_same_pid()
{
    local uid=$1 expected=$2 label=$3 actual
    actual="$(single_target_pid "$uid")" \
        || die "target process is missing or duplicated at $label"
    [ "$actual" = "$expected" ] \
        || die "target PID changed at $label: $expected -> $actual"
}

proc_snapshot()
{
    local uid=$1 output=$2
    D 'ps -ef' | awk -v wanted="$uid" '$1 == wanted {print}' > "$output" || true
}

run_quick()
{
    local run uid pid attempt launch_epoch now i hash geometry unique_frames diff_yavg
    local target_fault=0 faultlog fault_name node="" candidate_node first_buffer current
    run="$RUN_ROOT/$(date -u +%Y%m%dT%H%M%SZ)-quick"
    mkdir -p "$run"
    RUN_EVIDENCE="$run"
    uid="$(bundle_uid)"
    [ -n "$uid" ] || die "BoatAttack package UID is missing"

    D "power-shell wakeup; power-shell timeout -o 86400000; power-shell setmode 602" >/dev/null
    stop_target || die "could not stop the previous BoatAttack child"
    D "hidumper -s RenderService -a 'RSTree'" > "$run/tree-before.txt"
    surface_ids < "$run/tree-before.txt" | sort -u > "$run/node-ids-before.txt"
    D 'find /data/log/faultlog -type f 2>/dev/null | sort' > "$run/faultlogs-before.txt" || true
    D 'hilog -r >/dev/null 2>&1 || true' >/dev/null
    launch_epoch="$(date +%s)"
    D "aa start -a '$ABILITY' -b '$BUNDLE' -W" > "$run/launch.txt"
    rg -q 'start ability successfully' "$run/launch.txt" \
        || die "BoatAttack Activity did not start"

    pid=""
    for attempt in $(seq 1 80); do
        pid="$(single_target_pid "$uid" || true)"
        [ -n "$pid" ] && break
        sleep 0.1
    done
    [ -n "$pid" ] || die "BoatAttack Android child did not appear"
    printf '%s\n' "$pid" > "$run/first-pid.txt"
    proc_snapshot "$uid" "$run/proc-launch.txt"

    for attempt in $(seq 1 160); do
        D "hidumper -s RenderService -a 'RSTree'" > "$run/tree-current.txt"
        while IFS= read -r candidate_node; do
            [ -n "$candidate_node" ] || continue
            if ! grep -qx "$candidate_node" "$run/node-ids-before.txt"; then
                node="$candidate_node"
                cp "$run/tree-current.txt" "$run/tree-first-node.txt"
                break
            fi
        done < <(foreground_surface_ids < "$run/tree-current.txt")
        [ -n "$node" ] && break
        sleep 0.1
    done
    [ -n "$node" ] || die "new foreground AdapterSurfaceView did not appear"

    for attempt in $(seq 1 120); do
        D "hidumper -s RenderService -a 'surfacenode $node'" > "$run/surface-node.txt"
        rg -q 'sequence = [0-9]+.*config = \[[0-9]+x[0-9]+,' \
            "$run/surface-node.txt" && break
        sleep 0.1
    done
    sed -nE 's/.*sequence = ([0-9]+).*config = \[([0-9]+x[0-9]+),.*/\1 \2/p' \
        "$run/surface-node.txt" | sort -n > "$run/buffer-configs.txt"
    [ -s "$run/buffer-configs.txt" ] || die "BoatAttack surface queue remained empty"
    first_buffer="$(head -n 1 "$run/buffer-configs.txt")"
    [ "${first_buffer#* }" = 1920x1200 ] \
        || die "first retained Unity buffer is $first_buffer, expected 1920x1200"
    awk '$2 != "1920x1200" {exit 1}' "$run/buffer-configs.txt" \
        || die "a retained Unity buffer is not 1920x1200"
    rg -q 'Bounds.*1920.*1200' "$run/surface-node.txt" \
        || die "AdapterSurfaceView Bounds are not 1920x1200"
    rg -q 'default-size.*1920x1200' "$run/surface-node.txt" \
        || die "AdapterSurfaceView default size is not 1920x1200"

    sleep 3
    capture_screen "$run" t3 || die "failed to capture t+3"
    proc_snapshot "$uid" "$run/proc-t3.txt"
    assert_same_pid "$uid" "$pid" t3
    sleep 6
    capture_screen "$run" t9 || die "failed to capture t+9"
    proc_snapshot "$uid" "$run/proc-t9.txt"
    assert_same_pid "$uid" "$pid" t9
    sleep 6
    capture_screen "$run" t15 || die "failed to capture t+15"
    proc_snapshot "$uid" "$run/proc-t15.txt"
    assert_same_pid "$uid" "$pid" t15
    sleep 15
    capture_screen "$run" ready || die "failed to capture race-ready frame"
    assert_same_pid "$uid" "$pid" ready

    : > "$run/five-touches.txt"
    D 'uinput -T -d 1740 1100 -i 9000 -u 1740 1100' >> "$run/five-touches.txt"
    printf 'touch_1=accelerate\n' >> "$run/five-touches.txt"
    capture_screen "$run" touch-1-accelerate || die "failed to capture touch 1"
    assert_same_pid "$uid" "$pid" touch1
    D 'uinput -T -m 220 1000 70 1000 -k 5000 700' >> "$run/five-touches.txt"
    printf 'touch_2=left\n' >> "$run/five-touches.txt"
    capture_screen "$run" touch-2-left || die "failed to capture touch 2"
    assert_same_pid "$uid" "$pid" touch2
    D 'uinput -T -d 1740 1100 -i 9000 -u 1740 1100' >> "$run/five-touches.txt"
    printf 'touch_3=accelerate\n' >> "$run/five-touches.txt"
    capture_screen "$run" touch-3-accelerate || die "failed to capture touch 3"
    assert_same_pid "$uid" "$pid" touch3
    D 'uinput -T -m 220 1000 370 1000 -k 5000 700' >> "$run/five-touches.txt"
    printf 'touch_4=right\n' >> "$run/five-touches.txt"
    capture_screen "$run" touch-4-right || die "failed to capture touch 4"
    assert_same_pid "$uid" "$pid" touch4
    D 'uinput -T -c 1440 1100 200' >> "$run/five-touches.txt"
    printf 'touch_5=reset\n' >> "$run/five-touches.txt"
    sleep 2
    capture_screen "$run" touch-5-reset || die "failed to capture touch 5"
    proc_snapshot "$uid" "$run/proc-after-five.txt"
    assert_same_pid "$uid" "$pid" touch5

    : > "$run/frame-hashes.env"
    for i in t3 t9 t15 ready touch-1-accelerate touch-2-left touch-3-accelerate touch-4-right touch-5-reset; do
        geometry="$(frame_geometry "$run/$i.jpeg")"
        [ "$geometry" = 1920x1200 ] \
            || die "$i frame geometry drifted: ${geometry:-UNREADABLE}"
        hash="$(decoded_frame_hash "$run/$i.jpeg")"
        [ -n "$hash" ] || die "could not decode $i frame"
        printf '%s=%s\n' "$i" "$hash" >> "$run/frame-hashes.env"
    done
    unique_frames="$(cut -d= -f2 "$run/frame-hashes.env" | sort -u | wc -l | trim)"
    [ "$unique_frames" -ge 8 ] || die "game checkpoints did not show enough state change"
    diff_yavg="$(gameplay_difference "$run/ready.jpeg" "$run/touch-5-reset.jpeg" \
        "$run/gameplay-difference.env")"
    [ -n "$diff_yavg" ] || die "could not measure touch-driven state change"
    awk -v value="$diff_yavg" 'BEGIN {exit !(value >= 10.0)}' \
        || die "touch sequence did not materially change the game: YAVG=$diff_yavg"

    D 'find /data/log/faultlog -type f 2>/dev/null | sort' > "$run/faultlogs-after.txt" || true
    comm -13 "$run/faultlogs-before.txt" "$run/faultlogs-after.txt" \
        > "$run/faultlogs-new.txt" || true
    while IFS= read -r faultlog; do
        [ -n "$faultlog" ] || continue
        fault_name="$(basename "$faultlog")"
        H file recv "$faultlog" "$run/faultlog-$fault_name" >/dev/null 2>&1 || true
        case "$fault_name" in *"-$pid-"*) target_fault=1 ;; esac
        if [ -f "$run/faultlog-$fault_name" ] \
            && rg -q "$BUNDLE|Pid:[[:space:]]*$pid|pid[=:][[:space:]]*$pid" \
                "$run/faultlog-$fault_name"; then
            target_fault=1
        fi
    done < "$run/faultlogs-new.txt"
    [ "$target_fault" = 0 ] || die "a new target faultlog was created"
    D 'hilog -x' > "$run/hilog.txt" || true
    if rg -i -q 'Fatal signal|native fatal|SIGABRT|SIGSEGV|FDSAN|Start Process Specified Ability TimeOut|lifecycle.{0,40}time.?out' \
        "$run/hilog.txt"; then
        die "terminating marker found in hilog"
    fi
    assert_same_pid "$uid" "$pid" final
    now="$(date +%s)"
    [ $((now - launch_epoch)) -ge 15 ] || die "target did not meet the 15-second lifetime"

    {
        printf 'BOAT_ATTACK_APK_QUICK=PASS\n'
        printf 'board=%s\nboot_id=%s\n' "$BOARD" "$(D 'cat /proc/sys/kernel/random/boot_id' | trim)"
        printf 'package=%s\nactivity=%s\napk_sha256=%s\n' "$BUNDLE" "$ABILITY" "$APK_SHA"
        printf 'pid=%s\nuid=%s\nlifetime_seconds=%s\n' "$pid" "$uid" "$((now - launch_epoch))"
        printf 'surface_node=%s\nfirst_retained_buffer=%s\n' "$node" "$first_buffer"
        printf 'all_retained_buffers=1920x1200\ngeometry=1920x1200\n'
        printf 'touches_delivered=5\nunique_frames=%s\n' "$unique_frames"
        printf 'gameplay_difference_yavg=%s\n' "$diff_yavg"
        printf 'unity_sha256=%s\nil2cpp_sha256=%s\nsignal_box_sha256=%s\n' \
            "$UNITY_SHA" "$IL2CPP_SHA" "$SIGNAL_BOX_SHA"
        printf 'shared_candidate=%s\nzigzag_receipt=%s\nevidence=%s\n' \
            "$SHARED_CANDIDATE" "$ZIGZAG_RECEIPT" "$run"
    } > "$run/receipt.env"
    printf 'BOAT_ATTACK_APK_QUICK=PASS\nreceipt=%s\nevidence=%s\npid=%s\n' \
        "$run/receipt.env" "$run" "$pid"
}

status_report()
{
    local uid pid
    uid="$(bundle_uid)"
    pid=""
    [ -z "$uid" ] || pid="$(single_target_pid "$uid" || true)"
    find_current_zigzag_receipt || true
    printf 'BOAT_ATTACK_APK_STATUS=OK\n'
    printf 'board=%s\nrom=%s\nboot_id=%s\n' \
        "$BOARD" "$ROM_ONLY" "$(D 'cat /proc/sys/kernel/random/boot_id' | trim)"
    printf 'package=%s\nactivity=%s\napk_sha256=%s\n' \
        "$BUNDLE" "$ABILITY" "$(device_hash "$DEVICE_APK")"
    printf 'uid=%s\npid=%s\n' "${uid:-MISSING}" "${pid:-NONE}"
    printf 'unity_sha256=%s\nil2cpp_sha256=%s\nsignal_box_sha256=%s\n' \
        "$(device_hash "$UNITY_TARGET")" "$(device_hash "$IL2CPP_TARGET")" \
        "$(device_hash "$SIGNAL_BOX_TARGET")"
    printf 'unity_mount=%s\nil2cpp_mount=%s\nsignal_box_mount=%s\n' \
        "$(mount_line "$UNITY_TARGET")" "$(mount_line "$IL2CPP_TARGET")" \
        "$(mount_line "$SIGNAL_BOX_TARGET")"
    printf 'shared_generation=%s\nzigzag_receipt=%s\n' \
        "$(shared_hashes_ready && printf ACCEPTED || printf DRIFTED)" \
        "${ZIGZAG_RECEIPT:-NONE_FOR_CURRENT_BOOT}"
}

write_channel()
{
    local status=$1 rc=$2 tmp result
    result="FAIL:$rc"
    [ "$rc" = 0 ] && result=PASS
    mkdir -p "$CHANNEL_ROOT"
    tmp="$(mktemp "$CHANNEL_ROOT/.boat-attack-apk-c.XXXXXX")"
    {
        printf '# Device channel: BoatAttack Android APK on %s\n\n' "$BOARD_LABEL"
        printf -- '- status: %s\n' "$status"
        printf -- '- owner: `reproduce-boat-attack-apk-%s`\n' "$$"
        printf -- '- target: `%s`\n' "$BOARD"
        printf -- '- mode: `%s`\n' "$MODE"
        printf -- '- updated_utc: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        printf -- '- package_activity: `%s/%s`\n' "$BUNDLE" "$ABILITY"
        printf -- '- apk_sha256: `%s`\n' "$APK_SHA"
        printf -- '- result: `%s`\n' "$result"
        printf -- '- evidence: `%s`\n' "${RUN_EVIDENCE:-NONE}"
        printf -- '- rollback: stop only the target UID and unmount the three BoatAttack-private files; leave the APK and shared generation unchanged\n'
    } > "$tmp"
    mv "$tmp" "$CHANNEL_FILE"
}

claim_board()
{
    local channel
    mkdir -p "$CHANNEL_ROOT" "$LOCK_ROOT"
    for channel in "$CHANNEL_ROOT"/*.md; do
        [ -f "$channel" ] || continue
        [ "$channel" = "$CHANNEL_FILE" ] && continue
        if grep -Fq "$BOARD" "$channel" \
            && grep -Eq '^- status: (ACTIVE|CLAIMED)$' "$channel"; then
            die "$BOARD_LABEL already has an active writer: $channel"
        fi
    done
    mkdir "$LOCK_DIR" 2>/dev/null \
        || die "$BOARD_LABEL atomic lock already exists: $LOCK_DIR"
    CLAIMED=1
    write_channel ACTIVE PENDING
}

on_exit()
{
    local rc=$? status
    trap - EXIT
    if [ "$CLAIMED" = 1 ]; then
        status=FAILED
        [ "$rc" -eq 0 ] && status=RELEASED
        set +e
        write_channel "$status" "$rc"
        rmdir "$LOCK_DIR" 2>/dev/null || true
        set -e
    fi
    exit "$rc"
}
trap on_exit EXIT

[ "$#" -le 2 ] || { usage; die "too many arguments"; }
case "$MODE" in
    check|quick|status|restore|rollback) ;;
    -h|--help|help) usage; exit 0 ;;
    *) usage; die "unknown mode: $MODE" ;;
esac

local_preflight
device_preflight

case "$MODE" in
    check)
        require_shared_baseline
        require_restored
        printf 'BOAT_ATTACK_APK_CHECK=PASS\nboard=%s\nrom=%s\napk_sha256=%s\ncandidate=%s\nzigzag_receipt=%s\n' \
            "$BOARD" "$ROM_ONLY" "$APK_SHA" "$(candidate_state)" "$ZIGZAG_RECEIPT"
        ;;
    status)
        status_report
        ;;
    rollback)
        claim_board
        rollback_private || die "BoatAttack app-private rollback failed"
        printf 'BOAT_ATTACK_APK_ROLLBACK=PASS\napk_sha256=%s\n' "$(device_hash "$DEVICE_APK")"
        ;;
    restore)
        claim_board
        restore_shared_baseline
        if ! restore_private; then
            rollback_private || true
            die "BoatAttack app-private restore failed and was rolled back"
        fi
        printf 'BOAT_ATTACK_APK_RESTORE=PASS\napk_sha256=%s\nunity_sha256=%s\nil2cpp_sha256=%s\nshared_candidate=%s\nzigzag_receipt=%s\n' \
            "$APK_SHA" "$UNITY_SHA" "$IL2CPP_SHA" "$SHARED_CANDIDATE" "$ZIGZAG_RECEIPT"
        ;;
    quick)
        require_shared_baseline
        require_restored
        claim_board
        run_quick
        ;;
esac
