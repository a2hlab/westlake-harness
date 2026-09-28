#!/usr/bin/env bash

set -Eeuo pipefail

SELF="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
ZIGZAG_DRIVER="$REPO_ROOT/src/tools/devices/zigzag-apk-lightup.sh"

HDC_BIN="${HDC_BIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
PATCHELF_BIN="${PATCHELF_BIN:-/opt/homebrew/bin/patchelf}"
FFMPEG_BIN="${FFMPEG_BIN:-$(command -v ffmpeg || true)}"
OH_SDK="${OH_SDK:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native}"
OH_CC="$OH_SDK/llvm/bin/clang"

BOARD_ONLY="61ae0be500000000000000000324012c"
BOARD_8605="5ce2dcee00000000000000000923012c"
BOARD_5EA1="5ea1719200000000000000001123012c"
ROM_ONLY="OpenHarmony-6.1.0.31"
BUNDLE="com.Revenko.org.CapybaraAdventure"
ABILITY="com.unity3d.player.UnityPlayerActivity"

APK="$REPO_ROOT/APKS/CapybaraAdventure/dist/capybara-adventure-v1.2.0-unity.apk"
APK_SHA="552b731aa6b6c50871ac218c65665669c089ddb09ec780f414c18e3d685b5730"
RAW_UNITY_SHA="5ba5e9e337a158dcb3143a0fc4c608112674d8490e087c870dd2e86364fe5d39"
RAW_IL2CPP_SHA="f50a5aa1bfe6161aa0771dd6de0b2ef84fe0522a9bb17b4f4522e6f2352c9a85"
UNITY_SHA="d9a8fdb42c73f6d9caf7e63a97e8f0e012e3208f6fa147d994d84ae2834fd378"
IL2CPP_SHA="d36f292dcda8ae7f6c7ece9b6176755f68cda8a714f6366a58dc7e0918e5cf46"
GEOMETRY_SHA="ec080758323afb873f26965efbdd3bab98313e5d7791f59edf7f7e30c5e852be"
SIGNAL_BOX_SHA="7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da"
EMPTY_SHA="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

STATE_ROOT="$REPO_ROOT/.state/capybara-adventure"
UNITY_CANDIDATE="$STATE_ROOT/c-candidates/c24-private-geometry-import/libunity.so"
IL2CPP_CANDIDATE="$STATE_ROOT/c-candidates/c27-libil2cpp-persistent-no-collection/libil2cpp.so"
GEOMETRY_CANDIDATE="$STATE_ROOT/c-candidates/c24-private-geometry-import/libcapybara_geometry.so"
SIGNAL_BOX_SOURCE="$REPO_ROOT/.bridge-payload/zigzag-persisted/strict-20260809T160651Z-21101/files/libwestlake_bionic_signal_box.so"
SIGNAL_RENAME_MAP="$REPO_ROOT/src/adapter/framework/native-compat/bionic-signal-box/tuanjie_signal_symbols.map"
GEOMETRY_SOURCE="$REPO_ROOT/src/adapter/framework/native-compat/capybara-geometry-shim/src/capybara_geometry_shim.c"
GEOMETRY_RENAME_MAP="$REPO_ROOT/src/adapter/framework/native-compat/capybara-geometry-shim/capybara_rename.map"

DEVICE_APP_ROOT="/data/app/el1/bundle/public/$BUNDLE/android"
DEVICE_APK="$DEVICE_APP_ROOT/base.apk"
DEVICE_LIB_ROOT="$DEVICE_APP_ROOT/lib/arm64-v8a"
UNITY_TARGET="$DEVICE_LIB_ROOT/libunity.so"
IL2CPP_TARGET="$DEVICE_LIB_ROOT/libil2cpp.so"
GEOMETRY_TARGET="$DEVICE_LIB_ROOT/libcapybara_geometry.so"
SIGNAL_BOX_TARGET="$DEVICE_LIB_ROOT/libwestlake_bionic_signal_box.so"
REMOTE_ROOT="/data/capybara-apk-lightup/accepted-c27"
REMOTE_APK="$REMOTE_ROOT/capybara-adventure-v1.2.0-unity.apk"
REMOTE_UNITY="$REMOTE_ROOT/libunity.so"
REMOTE_IL2CPP="$REMOTE_ROOT/libil2cpp.so"
REMOTE_GEOMETRY="$REMOTE_ROOT/libcapybara_geometry.so"
REMOTE_SIGNAL_BOX="$REMOTE_ROOT/libwestlake_bionic_signal_box.so"

SHARED_CANDIDATE="$REPO_ROOT/.bridge-payload/zigzag-candidates/strict-20260811T044910Z-68706"
SHARED_ADAPTER_SHA="54c927cb2fcc89e9afb547a1447318c9139c4afb3aa69d935f79627a9724d052"
SHARED_PROVIDER_SHA="69ffe2cba0136ad1aa422747c895780b1c5408511526a243da286a357f52e983"
SHARED_CHILD_SHA="b518456345a517f9b86f9a8879cc1106def1418081c20c66c744bb363e146efe"
SHARED_APPSPAWN_SHA="c7bf5fb0d9d07a6a5ffdb33cb07f7d7d07a3a8040afee1be573ba6dfc5f5203b"
SHARED_RUNTIME_JAR_SHA="01d817200a85f979ab1b728cb227981f9661bc0b514e1b3ae13496e04f854123"
SHARED_ADAPTER_TARGET="/system/android/lib64/liboh_adapter_bridge.so"
SHARED_PROVIDER_TARGET="/system/lib64/westlake/route-a/74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d/libwestlake_android_runtime_provider.so"
SHARED_CHILD_TARGET="/system/lib64/appspawn/libwestlake_android_child.z.so"
SHARED_APPSPAWN_TARGET="/system/bin/appspawn-x"
SHARED_RUNTIME_JAR_TARGET="/system/android/framework/oh-adapter-runtime.jar"

RUN_ROOT="$REPO_ROOT/var/state/reproduce-capybara-apk"
ZIGZAG_RUN_ROOT="$REPO_ROOT/var/state/reproduce-zigzag-apk"
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
CHANNEL_FILE="$CHANNEL_ROOT/capybara-apk-c-$BOARD_LABEL.md"
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
        && [ -f "$GEOMETRY_CANDIDATE" ] \
        && [ "$(sha256_file "$UNITY_CANDIDATE")" = "$UNITY_SHA" ] \
        && [ "$(sha256_file "$IL2CPP_CANDIDATE")" = "$IL2CPP_SHA" ] \
        && [ "$(sha256_file "$GEOMETRY_CANDIDATE")" = "$GEOMETRY_SHA" ]; then
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
    [ -x "$OH_CC" ] || die "missing OpenHarmony clang: $OH_CC"
    [ -x "$ZIGZAG_DRIVER" ] || die "missing ZigZag shared-candidate driver: $ZIGZAG_DRIVER"
    [ -n "$FFMPEG_BIN" ] && [ -x "$FFMPEG_BIN" ] || die "ffmpeg is required"
    command -v unzip >/dev/null 2>&1 || die "unzip is required"
    command -v rg >/dev/null 2>&1 || die "rg is required"
    bash -n "$SELF"
    bash -n "$ZIGZAG_DRIVER"
    require_hash "$APK_SHA" "$APK"
    require_hash "$SIGNAL_BOX_SHA" "$SIGNAL_BOX_SOURCE"
    [ -s "$SIGNAL_RENAME_MAP" ] || die "missing signal rename map: $SIGNAL_RENAME_MAP"
    [ -s "$GEOMETRY_SOURCE" ] || die "missing geometry shim source: $GEOMETRY_SOURCE"
    [ -s "$GEOMETRY_RENAME_MAP" ] || die "missing geometry rename map: $GEOMETRY_RENAME_MAP"
    [ -f "$SHARED_CANDIDATE/manifest.env" ] \
        || die "missing accepted shared candidate: $SHARED_CANDIDATE"
    [ ! -f "$UNITY_CANDIDATE" ] || require_hash "$UNITY_SHA" "$UNITY_CANDIDATE"
    [ ! -f "$IL2CPP_CANDIDATE" ] || require_hash "$IL2CPP_SHA" "$IL2CPP_CANDIDATE"
    [ ! -f "$GEOMETRY_CANDIDATE" ] || require_hash "$GEOMETRY_SHA" "$GEOMETRY_CANDIDATE"
}

build_candidates()
{
    local build
    if [ "$(candidate_state)" = READY ]; then
        return 0
    fi
    [ ! -e "$UNITY_CANDIDATE" ] || require_hash "$UNITY_SHA" "$UNITY_CANDIDATE"
    [ ! -e "$IL2CPP_CANDIDATE" ] || require_hash "$IL2CPP_SHA" "$IL2CPP_CANDIDATE"
    [ ! -e "$GEOMETRY_CANDIDATE" ] || require_hash "$GEOMETRY_SHA" "$GEOMETRY_CANDIDATE"

    mkdir -p "$(dirname "$UNITY_CANDIDATE")" "$(dirname "$IL2CPP_CANDIDATE")"
    build="$(mktemp -d "$STATE_ROOT/c-reproduce-build.XXXXXX")"
    unzip -j -q "$APK" lib/arm64-v8a/libunity.so lib/arm64-v8a/libil2cpp.so -d "$build"
    require_hash "$RAW_UNITY_SHA" "$build/libunity.so"
    require_hash "$RAW_IL2CPP_SHA" "$build/libil2cpp.so"

    "$PATCHELF_BIN" --add-needed libwestlake_bionic_pthread_bridge.so "$build/libunity.so"
    "$PATCHELF_BIN" --rename-dynamic-symbols "$SIGNAL_RENAME_MAP" "$build/libunity.so"
    "$PATCHELF_BIN" --add-needed libwestlake_bionic_signal_box.so "$build/libunity.so"
    patch_binary_hex_exact "$build/libunity.so" 0x6dd710 f40f1ef8 11000014 \
        "Unity core resolver -> eglGetProcAddress"
    patch_binary_hex_exact "$build/libunity.so" 0x3885d0 f37bbfa9b37200b0 \
        e0031f2ac0035fd6 "disable unsupported Swappy predicate"
    patch_binary_hex_exact "$build/libunity.so" 0xa2f044 f50f1df8283f00d0 \
        e0031f2ac0035fd6 "report optional vibrator unavailable"

    "$OH_CC" --target=aarch64-linux-ohos --sysroot="$OH_SDK/sysroot" \
        -fPIC -O2 -D__OHOS__ -D_GNU_SOURCE -std=c11 \
        -Wall -Wextra -Werror -pedantic -fno-stack-protector \
        -fno-unwind-tables -fno-asynchronous-unwind-tables \
        -mno-outline-atomics -c "$GEOMETRY_SOURCE" \
        -o "$build/capybara_geometry_shim.o"
    "$OH_CC" --target=aarch64-linux-ohos --sysroot="$OH_SDK/sysroot" \
        -B"$OH_SDK/llvm/bin" -fuse-ld=lld -shared \
        -Wl,-z,defs -Wl,-z,now -Wl,-z,relro -Wl,--no-undefined \
        -Wl,--fatal-warnings -Wl,--hash-style=both \
        -Wl,-soname,libcapybara_geometry.so \
        "$build/capybara_geometry_shim.o" -lc \
        -o "$build/libcapybara_geometry.so"
    "$PATCHELF_BIN" --rename-dynamic-symbols "$GEOMETRY_RENAME_MAP" \
        "$build/libunity.so"
    "$PATCHELF_BIN" --add-needed libcapybara_geometry.so "$build/libunity.so"

    "$PATCHELF_BIN" --add-needed libwestlake_bionic_pthread_bridge.so "$build/libil2cpp.so"
    "$PATCHELF_BIN" --rename-dynamic-symbols "$SIGNAL_RENAME_MAP" "$build/libil2cpp.so"
    "$PATCHELF_BIN" --add-needed libwestlake_bionic_signal_box.so "$build/libil2cpp.so"
    patch_binary_hex_exact "$build/libil2cpp.so" 0x25be3a8 f60f1df8 c0035fd6 \
        "disable optional Unity Ads startup"
    patch_binary_hex_exact "$build/libil2cpp.so" 0xd2f460 87d7ff1787d7ff17 \
        e0031f2ac0035fd6 "disable broken incremental GC veneers"
    patch_binary_hex_exact "$build/libil2cpp.so" 0x3259196 \
        47435f444f4e545f474300 5041544800000000000000 \
        "activate the built-in no-collection mode from inherited PATH"
    patch_binary_hex_exact "$build/libil2cpp.so" 0xdb1890 f40f1ef8 c0035fd6 \
        "keep no-collection mode active after runtime GC enable"

    require_hash "$UNITY_SHA" "$build/libunity.so"
    require_hash "$IL2CPP_SHA" "$build/libil2cpp.so"
    require_hash "$GEOMETRY_SHA" "$build/libcapybara_geometry.so"
    [ -e "$UNITY_CANDIDATE" ] || mv "$build/libunity.so" "$UNITY_CANDIDATE"
    [ -e "$IL2CPP_CANDIDATE" ] || mv "$build/libil2cpp.so" "$IL2CPP_CANDIDATE"
    [ -e "$GEOMETRY_CANDIDATE" ] \
        || mv "$build/libcapybara_geometry.so" "$GEOMETRY_CANDIDATE"
    require_hash "$UNITY_SHA" "$UNITY_CANDIDATE"
    require_hash "$IL2CPP_SHA" "$IL2CPP_CANDIDATE"
    require_hash "$GEOMETRY_SHA" "$GEOMETRY_CANDIDATE"
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

find_current_zigzag_receipt()
{
    local current_boot receipt evidence evidence_boot candidate
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

shared_baseline_ready()
{
    ZIGZAG_RECEIPT=""
    [ "$(device_hash "$SHARED_ADAPTER_TARGET")" = "$SHARED_ADAPTER_SHA" ] \
        && [ "$(device_hash "$SHARED_PROVIDER_TARGET")" = "$SHARED_PROVIDER_SHA" ] \
        && [ "$(device_hash "$SHARED_CHILD_TARGET")" = "$SHARED_CHILD_SHA" ] \
        && [ "$(device_hash "$SHARED_APPSPAWN_TARGET")" = "$SHARED_APPSPAWN_SHA" ] \
        && [ "$(device_hash "$SHARED_RUNTIME_JAR_TARGET")" = "$SHARED_RUNTIME_JAR_SHA" ] \
        && find_current_zigzag_receipt
}

restore_shared_baseline()
{
    if shared_baseline_ready; then
        return 0
    fi
    "$ZIGZAG_DRIVER" run-light-risk "$BOARD" "$SHARED_CANDIDATE"
    require_shared_baseline
}

require_shared_baseline()
{
    [ "$(device_hash "$SHARED_ADAPTER_TARGET")" = "$SHARED_ADAPTER_SHA" ] \
        || die "accepted Capybara shared adapter is not active; run restore"
    [ "$(device_hash "$SHARED_PROVIDER_TARGET")" = "$SHARED_PROVIDER_SHA" ] \
        || die "accepted Capybara shared provider is not active; run restore"
    [ "$(device_hash "$SHARED_CHILD_TARGET")" = "$SHARED_CHILD_SHA" ] \
        || die "accepted Capybara shared child is not active; run restore"
    [ "$(device_hash "$SHARED_APPSPAWN_TARGET")" = "$SHARED_APPSPAWN_SHA" ] \
        || die "accepted Capybara shared appspawn-x is not active; run restore"
    [ "$(device_hash "$SHARED_RUNTIME_JAR_TARGET")" = "$SHARED_RUNTIME_JAR_SHA" ] \
        || die "accepted Capybara shared runtime jar is not active; run restore"
    find_current_zigzag_receipt \
        || die "no accepted ZigZag Android APK receipt for this shared candidate and boot; run restore"
}

bundle_uid()
{
    D "bm dump -n '$BUNDLE' 2>/dev/null" \
        | grep -oE '"uid": *[0-9]+' | head -n 1 | grep -oE '[0-9]+$' || true
}

pids_for_uid()
{
    local uid=$1
    D "ps -ef" \
        | awk -v wanted="$uid" '$1 == wanted && $2 ~ /^[0-9]+$/ {print $2}' \
        | sed '/^$/d'
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
    for attempt in $(seq 1 20); do
        [ -z "$(pids_for_uid "$uid")" ] && return 0
        sleep 0.1
    done
    return 1
}

mount_line()
{
    local target=$1
    D "cat /proc/self/mountinfo" \
        | awk -v wanted="$target" '$5 == wanted {print; exit}'
}

unmount_private_target()
{
    local target=$1 line
    line="$(mount_line "$target")"
    [ -n "$line" ] || return 0
    printf '%s\n' "$line" | grep -Fq '/capybara-apk-lightup/' \
        || die "refusing to unmount a non-Capybara layer: $line"
    D "umount '$target'" >/dev/null
    [ -z "$(mount_line "$target")" ]
}

rollback_private()
{
    local base_hash geometry_under signal_under
    stop_target || return 1
    unmount_private_target "$IL2CPP_TARGET" || return 1
    unmount_private_target "$UNITY_TARGET" || return 1
    unmount_private_target "$GEOMETRY_TARGET" || return 1
    unmount_private_target "$SIGNAL_BOX_TARGET" || return 1

    geometry_under="$(device_hash "$GEOMETRY_TARGET")"
    if [ "$geometry_under" = "$EMPTY_SHA" ]; then
        D "rm -f '$GEOMETRY_TARGET'" >/dev/null || return 1
    fi
    signal_under="$(device_hash "$SIGNAL_BOX_TARGET")"
    if [ "$signal_under" = "$EMPTY_SHA" ]; then
        D "rm -f '$SIGNAL_BOX_TARGET'" >/dev/null || return 1
    fi
    base_hash="$(device_hash "$DEVICE_APK")"
    if [ "$base_hash" = "$APK_SHA" ]; then
        [ "$(device_hash "$UNITY_TARGET")" = "$RAW_UNITY_SHA" ] || return 1
        [ "$(device_hash "$IL2CPP_TARGET")" = "$RAW_IL2CPP_SHA" ] || return 1
    fi
    return 0
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

restore_private()
{
    local geometry_under signal_under
    build_candidates
    rollback_private || return 1
    ensure_original_apk || return 1
    [ "$(device_hash "$UNITY_TARGET")" = "$RAW_UNITY_SHA" ] || return 1
    [ "$(device_hash "$IL2CPP_TARGET")" = "$RAW_IL2CPP_SHA" ] || return 1
    geometry_under="$(device_hash "$GEOMETRY_TARGET")"
    [ -z "$geometry_under" ] || return 1
    signal_under="$(device_hash "$SIGNAL_BOX_TARGET")"
    [ -z "$signal_under" ] || return 1

    D "mkdir -p '$REMOTE_ROOT'" >/dev/null
    H file send "$UNITY_CANDIDATE" "$REMOTE_UNITY" >/dev/null
    H file send "$IL2CPP_CANDIDATE" "$REMOTE_IL2CPP" >/dev/null
    H file send "$GEOMETRY_CANDIDATE" "$REMOTE_GEOMETRY" >/dev/null
    H file send "$SIGNAL_BOX_SOURCE" "$REMOTE_SIGNAL_BOX" >/dev/null
    [ "$(device_hash "$REMOTE_UNITY")" = "$UNITY_SHA" ] || return 1
    [ "$(device_hash "$REMOTE_IL2CPP")" = "$IL2CPP_SHA" ] || return 1
    [ "$(device_hash "$REMOTE_GEOMETRY")" = "$GEOMETRY_SHA" ] || return 1
    [ "$(device_hash "$REMOTE_SIGNAL_BOX")" = "$SIGNAL_BOX_SHA" ] || return 1

    D "chmod 0755 '$REMOTE_UNITY' '$REMOTE_IL2CPP' '$REMOTE_GEOMETRY' '$REMOTE_SIGNAL_BOX'; chown 0:0 '$REMOTE_UNITY' '$REMOTE_IL2CPP' '$REMOTE_GEOMETRY' '$REMOTE_SIGNAL_BOX'; chcon u:object_r:data_app_el1_file:s0 '$REMOTE_UNITY' '$REMOTE_IL2CPP' '$REMOTE_GEOMETRY' '$REMOTE_SIGNAL_BOX'; touch '$GEOMETRY_TARGET' '$SIGNAL_BOX_TARGET'; chown 0:0 '$GEOMETRY_TARGET' '$SIGNAL_BOX_TARGET'; chmod 0644 '$GEOMETRY_TARGET' '$SIGNAL_BOX_TARGET'; chcon u:object_r:data_app_el1_file:s0 '$GEOMETRY_TARGET' '$SIGNAL_BOX_TARGET'; mount --bind '$REMOTE_SIGNAL_BOX' '$SIGNAL_BOX_TARGET'; mount --bind '$REMOTE_GEOMETRY' '$GEOMETRY_TARGET'; mount --bind '$REMOTE_UNITY' '$UNITY_TARGET'; mount --bind '$REMOTE_IL2CPP' '$IL2CPP_TARGET'; chmod 0755 '$GEOMETRY_TARGET' '$SIGNAL_BOX_TARGET' '$UNITY_TARGET' '$IL2CPP_TARGET'; chcon u:object_r:data_app_el1_file:s0 '$GEOMETRY_TARGET' '$SIGNAL_BOX_TARGET' '$UNITY_TARGET' '$IL2CPP_TARGET'" >/dev/null \
        || return 1
    [ "$(device_hash "$UNITY_TARGET")" = "$UNITY_SHA" ] || return 1
    [ "$(device_hash "$IL2CPP_TARGET")" = "$IL2CPP_SHA" ] || return 1
    [ "$(device_hash "$GEOMETRY_TARGET")" = "$GEOMETRY_SHA" ] || return 1
    [ "$(device_hash "$SIGNAL_BOX_TARGET")" = "$SIGNAL_BOX_SHA" ] || return 1
    printf '%s\n' "$(mount_line "$UNITY_TARGET")" | grep -Fq '/capybara-apk-lightup/' || return 1
    printf '%s\n' "$(mount_line "$IL2CPP_TARGET")" | grep -Fq '/capybara-apk-lightup/' || return 1
    printf '%s\n' "$(mount_line "$GEOMETRY_TARGET")" | grep -Fq '/capybara-apk-lightup/' || return 1
    printf '%s\n' "$(mount_line "$SIGNAL_BOX_TARGET")" | grep -Fq '/capybara-apk-lightup/' || return 1
}

require_restored()
{
    [ "$(device_hash "$DEVICE_APK")" = "$APK_SHA" ] \
        || die "the exact original Capybara APK is not installed; run restore"
    [ "$(device_hash "$UNITY_TARGET")" = "$UNITY_SHA" ] \
        || die "accepted C24 libunity is not active; run restore"
    [ "$(device_hash "$IL2CPP_TARGET")" = "$IL2CPP_SHA" ] \
        || die "accepted C27 libil2cpp is not active; run restore"
    [ "$(device_hash "$GEOMETRY_TARGET")" = "$GEOMETRY_SHA" ] \
        || die "accepted C24 geometry shim is not active; run restore"
    [ "$(device_hash "$SIGNAL_BOX_TARGET")" = "$SIGNAL_BOX_SHA" ] \
        || die "accepted signal box is not active; run restore"
}

verify_nonblank_jpeg()
{
    local image=$1 stats ymin ymax
    [ -s "$image" ] || return 1
    stats="$image.signalstats.txt"
    "$FFMPEG_BIN" -hide_banner -loglevel error -i "$image" \
        -vf "signalstats,metadata=print:file=$stats" -f null - >/dev/null 2>&1 || return 1
    ymin="$(sed -n 's/^lavfi.signalstats.YMIN=//p' "$stats" | head -n 1)"
    ymax="$(sed -n 's/^lavfi.signalstats.YMAX=//p' "$stats" | head -n 1)"
    [ -n "$ymin" ] && [ -n "$ymax" ] || return 1
    [ "$ymin" -le 30 ] && [ "$ymax" -ge 220 ]
}

capture_screen()
{
    local run=$1 label=$2 remote
    remote="/data/local/tmp/capybara-${label}-$$.jpeg"
    D "snapshot_display -f '$remote'" >/dev/null || return 1
    H file recv "$remote" "$run/$label.jpeg" >/dev/null || return 1
    D "rm -f '$remote'" >/dev/null || true
    verify_nonblank_jpeg "$run/$label.jpeg"
}

game_frame_hash()
{
    "$FFMPEG_BIN" -hide_banner -loglevel error -i "$1" \
        -vf 'crop=1200:750:0:0,format=rgb24' -f hash -hash sha256 - 2>/dev/null \
        | sed 's/^SHA256=//'
}

gameplay_difference()
{
    local before=$1 after=$2 output=$3
    "$FFMPEG_BIN" -hide_banner -loglevel error -i "$before" -i "$after" \
        -lavfi "[0:v]crop=1200:750:0:0,format=gray[a];[1:v]crop=1200:750:0:0,format=gray[b];[a][b]blend=all_mode=difference,signalstats,metadata=print:file=$output" \
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
    D "ps -ef" | awk -v wanted="$uid" '$1 == wanted {print}' > "$output" || true
}

run_quick()
{
    local run uid pid attempt launch_epoch now delivered=0 i output
    local hash unique_frames diff_yavg target_fault=0 faultlog fault_name
    local menu_hash gameplay_hash touched_hash
    run="$RUN_ROOT/$(date -u +%Y%m%dT%H%M%SZ)-quick"
    mkdir -p "$run"
    RUN_EVIDENCE="$run"
    uid="$(bundle_uid)"
    [ -n "$uid" ] || die "Capybara package UID is missing"

    D "power-shell wakeup; power-shell timeout -o 86400000; power-shell setmode 602; uitest uiInput keyEvent Home >/dev/null 2>&1 || true; uitest dumpLayout -p /data/local/tmp/capybara-prelaunch.json >/dev/null 2>&1 || true; if grep -q ScreenLockRootComponent /data/local/tmp/capybara-prelaunch.json 2>/dev/null; then uitest uiInput swipe 600 1700 600 300 800 >/dev/null 2>&1 || true; fi" >/dev/null
    stop_target || die "could not stop the previous Capybara child"
    D "find /data/log/faultlog -type f 2>/dev/null | sort" > "$run/faultlogs-before.txt" || true
    D "hilog -r >/dev/null 2>&1 || true" >/dev/null
    launch_epoch="$(date +%s)"
    D "aa start -a '$ABILITY' -b '$BUNDLE' -W" > "$run/launch.txt"
    rg -q 'start ability successfully' "$run/launch.txt" || die "Capybara Activity did not start"

    pid=""
    for attempt in $(seq 1 50); do
        pid="$(single_target_pid "$uid" || true)"
        [ -n "$pid" ] && break
        sleep 0.1
    done
    [ -n "$pid" ] || die "Capybara Android child did not appear"
    printf '%s\n' "$pid" > "$run/first-pid.txt"
    proc_snapshot "$uid" "$run/proc-launch.txt"

    sleep 3
    capture_screen "$run" t3 || die "failed to capture t+3"
    proc_snapshot "$uid" "$run/proc-t3.txt"
    assert_same_pid "$uid" "$pid" t3

    sleep 6
    capture_screen "$run" t9 || die "failed to capture t+9"
    proc_snapshot "$uid" "$run/proc-t9.txt"
    assert_same_pid "$uid" "$pid" t9
    output="$(D 'uitest uiInput click 1060 620')" || die "SKIP touch was not delivered"
    printf '%s\n' "${output:-DELIVERED}" > "$run/skip-click.txt"

    sleep 3
    capture_screen "$run" menu || die "failed to capture the main menu"
    assert_same_pid "$uid" "$pid" menu
    output="$(D 'uitest uiInput click 850 615')" || die "PLAY touch was not delivered"
    printf '%s\n' "${output:-DELIVERED}" > "$run/play-click.txt"

    sleep 2
    capture_screen "$run" after-play || die "failed to capture gameplay"
    assert_same_pid "$uid" "$pid" after-play
    : > "$run/five-touches.txt"
    for i in 1 2 3 4 5; do
        output="$(D 'uitest uiInput click 600 375')" || die "touch $i was not delivered"
        printf 'touch_%s=%s\n' "$i" "${output:-DELIVERED}" >> "$run/five-touches.txt"
        delivered=$((delivered + 1))
        sleep 1
    done

    now="$(date +%s)"
    while [ $((now - launch_epoch)) -lt 15 ]; do
        sleep 1
        now="$(date +%s)"
    done
    capture_screen "$run" after-five || die "failed to capture the five-touch result"
    proc_snapshot "$uid" "$run/proc-after-five.txt"
    assert_same_pid "$uid" "$pid" after-five
    now="$(date +%s)"

    : > "$run/frame-hashes.env"
    for label in t3 t9 menu after-play after-five; do
        hash="$(game_frame_hash "$run/$label.jpeg")"
        [ -n "$hash" ] || die "could not decode $label frame"
        printf '%s=%s\n' "$label" "$hash" >> "$run/frame-hashes.env"
    done
    unique_frames="$(cut -d= -f2 "$run/frame-hashes.env" | sort -u | wc -l | trim)"
    menu_hash="$(sed -n 's/^menu=//p' "$run/frame-hashes.env")"
    gameplay_hash="$(sed -n 's/^after-play=//p' "$run/frame-hashes.env")"
    touched_hash="$(sed -n 's/^after-five=//p' "$run/frame-hashes.env")"
    [ "$unique_frames" -ge 3 ] || die "the game-area checkpoints did not show enough state change"
    [ "$menu_hash" != "$gameplay_hash" ] \
        || die "PLAY did not change the menu into gameplay"
    [ "$gameplay_hash" != "$touched_hash" ] \
        || die "the five touches did not change gameplay pixels"
    diff_yavg="$(gameplay_difference "$run/after-play.jpeg" "$run/after-five.jpeg" \
        "$run/gameplay-difference.env")"
    [ -n "$diff_yavg" ] || die "could not measure touch-driven state change"
    awk -v value="$diff_yavg" 'BEGIN {exit !(value >= 10.0)}' \
        || die "touch sequence did not produce a material game-state change: YAVG=$diff_yavg"

    D "find /data/log/faultlog -type f 2>/dev/null | sort" > "$run/faultlogs-after.txt" || true
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
    D "hilog -x | grep -E '(^|[[:space:]])$pid([[:space:]]|$)|$BUNDLE' | tail -n 12000" \
        > "$run/hilog-target.txt" || true
    if rg -i -q 'Fatal signal|native fatal|SIGABRT|SIGSEGV|FDSAN|Start Process Specified Ability TimeOut|lifecycle.{0,40}time.?out' \
        "$run/hilog-target.txt"; then
        die "terminating marker found in target hilog"
    fi
    assert_same_pid "$uid" "$pid" final

    {
        printf 'CAPYBARA_APK_QUICK=PASS\n'
        printf 'board=%s\nboot_id=%s\n' "$BOARD" "$(D 'cat /proc/sys/kernel/random/boot_id' | trim)"
        printf 'package=%s\nactivity=%s\napk_sha256=%s\n' "$BUNDLE" "$ABILITY" "$APK_SHA"
        printf 'pid=%s\nuid=%s\ngame_clock_seconds=%s\n' "$pid" "$uid" "$((now - launch_epoch))"
        printf 'game_content_geometry=1200x750+0+0\nhost_lower_backdrop=NON_BLOCKING\n'
        printf 'touches_delivered=%s\nunique_game_frames=%s\ngameplay_difference_yavg=%s\n' \
            "$delivered" "$unique_frames" "$diff_yavg"
        printf 'unity_sha256=%s\nil2cpp_sha256=%s\ngeometry_sha256=%s\nsignal_box_sha256=%s\n' \
            "$UNITY_SHA" "$IL2CPP_SHA" "$GEOMETRY_SHA" "$SIGNAL_BOX_SHA"
        printf 'shared_candidate=%s\n' "$SHARED_CANDIDATE"
        printf 'zigzag_receipt=%s\nevidence=%s\n' "$ZIGZAG_RECEIPT" "$run"
    } > "$run/receipt.env"
    printf 'CAPYBARA_APK_QUICK=PASS\nreceipt=%s\nevidence=%s\npid=%s\n' \
        "$run/receipt.env" "$run" "$pid"
}

status_report()
{
    local uid pid
    uid="$(bundle_uid)"
    pid=""
    [ -z "$uid" ] || pid="$(single_target_pid "$uid" || true)"
    find_current_zigzag_receipt || true
    printf 'CAPYBARA_APK_STATUS=OK\n'
    printf 'board=%s\nrom=%s\nboot_id=%s\n' \
        "$BOARD" "$ROM_ONLY" "$(D 'cat /proc/sys/kernel/random/boot_id' | trim)"
    printf 'package=%s\nactivity=%s\napk_sha256=%s\n' \
        "$BUNDLE" "$ABILITY" "$(device_hash "$DEVICE_APK")"
    printf 'uid=%s\npid=%s\n' "${uid:-MISSING}" "${pid:-NONE}"
    printf 'unity_sha256=%s\nil2cpp_sha256=%s\ngeometry_sha256=%s\nsignal_box_sha256=%s\n' \
        "$(device_hash "$UNITY_TARGET")" "$(device_hash "$IL2CPP_TARGET")" \
        "$(device_hash "$GEOMETRY_TARGET")" "$(device_hash "$SIGNAL_BOX_TARGET")"
    printf 'unity_mount=%s\nil2cpp_mount=%s\ngeometry_mount=%s\nsignal_box_mount=%s\n' \
        "$(mount_line "$UNITY_TARGET")" "$(mount_line "$IL2CPP_TARGET")" \
        "$(mount_line "$GEOMETRY_TARGET")" "$(mount_line "$SIGNAL_BOX_TARGET")"
    printf 'zigzag_receipt=%s\n' "${ZIGZAG_RECEIPT:-NONE_FOR_CURRENT_BOOT}"
}

write_channel()
{
    local status=$1 rc=$2 tmp result
    result="FAIL:$rc"
    [ "$rc" = 0 ] && result=PASS
    mkdir -p "$CHANNEL_ROOT"
    tmp="$(mktemp "$CHANNEL_ROOT/.capybara-apk-c.XXXXXX")"
    {
        printf '# Device channel: Capybara Adventure Android APK on %s\n\n' "$BOARD_LABEL"
        printf -- '- status: %s\n' "$status"
        printf -- '- owner: `reproduce-capybara-apk-%s`\n' "$$"
        printf -- '- target: `%s`\n' "$BOARD"
        printf -- '- mode: `%s`\n' "$MODE"
        printf -- '- updated_utc: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        printf -- '- package_activity: `%s/%s`\n' "$BUNDLE" "$ABILITY"
        printf -- '- apk_sha256: `%s`\n' "$APK_SHA"
        printf -- '- result: `%s`\n' "$result"
        printf -- '- evidence: `%s`\n' "${RUN_EVIDENCE:-NONE}"
        printf -- '- rollback: stop only the target UID, unmount the four app-private Capybara files, and leave the exact APK installed\n'
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
        printf 'CAPYBARA_APK_CHECK=PASS\nboard=%s\nrom=%s\napk_sha256=%s\ncandidate=%s\nzigzag_receipt=%s\n' \
            "$BOARD" "$ROM_ONLY" "$APK_SHA" "$(candidate_state)" "$ZIGZAG_RECEIPT"
        ;;
    status)
        status_report
        ;;
    rollback)
        claim_board
        rollback_private || die "Capybara app-private rollback failed"
        printf 'CAPYBARA_APK_ROLLBACK=PASS\napk_state=%s\n' "$(device_hash "$DEVICE_APK")"
        ;;
    restore)
        claim_board
        restore_shared_baseline
        if ! restore_private; then
            rollback_private || true
            die "Capybara app-private restore failed and was rolled back"
        fi
        printf 'CAPYBARA_APK_RESTORE=PASS\napk_sha256=%s\nunity_sha256=%s\nil2cpp_sha256=%s\ngeometry_sha256=%s\nshared_candidate=%s\nzigzag_receipt=%s\n' \
            "$APK_SHA" "$UNITY_SHA" "$IL2CPP_SHA" "$GEOMETRY_SHA" \
            "$SHARED_CANDIDATE" "$ZIGZAG_RECEIPT"
        ;;
    quick)
        require_shared_baseline
        require_restored
        claim_board
        run_quick
        ;;
esac
