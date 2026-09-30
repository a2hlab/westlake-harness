#!/usr/bin/env bash

set -Eeuo pipefail

SELF="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
RESTORE_DRIVER="$REPO_ROOT/src/tools/devices/restore-pr03-helloworld-5min.sh"
RECOVERY_SCRIPT="$REPO_ROOT/src/tools/devices/pr03-runtime-recover-device.sh"
RECOVERY_CFG="$REPO_ROOT/src/tools/devices/pr03-runtime-recovery.cfg"
HDC_BIN="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc"
FFMPEG_BIN="$(command -v ffmpeg || true)"

BOARD_ONLY="61ae0be500000000000000000324012c"
BOARD_8605="5ce2dcee00000000000000000923012c"
BOARD_5EA1="5ea1719200000000000000001123012c"
ROM_ONLY="OpenHarmony-6.1.0.31"
PACKAGE="com.example.helloworld"
ABILITY="com.example.helloworld.MainActivity"
APK_PATH="$HOME/orca/.bridge-payload/pr03-74e6-portable/apk/HelloWorld.apk"
APK_TARGET="/data/app/el1/bundle/public/$PACKAGE/android/base.apk"
APK_SHA="2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd"
GENERATION="74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d"
PROVIDER_TARGET="/system/lib64/westlake/route-a/$GENERATION/libwestlake_android_runtime_provider.so"

RESTORE_DRIVER_SHA="76ffae6d306c84ef54a9cb014820b4be79b23e81ceb07acd1054d2eb51eae293"
RECOVERY_SCRIPT_SHA="8dde8c4a19926d87a0fb6ef1833a66a0fbdd42d01680188df883838c2c91965b"
RECOVERY_CFG_SHA="e2d68c9f921fad83db1a2593cf32eebf3306ed4538b2abaa4117cdb417b8581a"

PR03_APPSPAWN_SHA="43d5a319fa43e30fb712c2e39d29ba55e4bf82d171e97af1e6da9fcacc28920c"
PR03_CHILD_SHA="66afb06c10db5e986d294a465cf787f4be3302ce6be3a17d49309b368b1ec090"
PR03_PROVIDER_SHA="6787ea7d3c4ec0a382621360e3434885b0167446e22217a439b8d17745e54630"
PR03_RUNTIME_SHA="9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db"
PR03_ADAPTER_SHA="7db99e1b760cf843b1a99db1382a3299f189c8cbca786ec411b7c35a2af6ffb9"
PR03_JAR_SHA="06141543bec26c5036931d8d2d71b0efaa45d5ffd73434557d165cd42672be0d"

ZIGZAG_APPSPAWN_SHA="1f6cf53be7b3225a6d0a2b5f66278c32f5d9f5f99a0f56ece3f57a630db4d908"
ZIGZAG_CHILD_SHA="0976dee89c0464cd6aeaf7d4c3c4afd1466926b7d69dc8e01d4910f92bf12e40"
ZIGZAG_PROVIDER_SHA="80c9aee0f39b860b1ce8d72af106e4fde49c0dbf41ef1b426c1e3103086d9b2f"
ZIGZAG_RUNTIME_SHA="$PR03_RUNTIME_SHA"
ZIGZAG_ADAPTER_SHA="84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a"
ZIGZAG_JAR_SHA="9161b50756d3ffdfb2a8908ea7ec13f908214688321b2785365977ac40b28dea"

# Newer accepted Unity superset used by the fixed BoatAttack handoff image.
# HelloWorld passed its first-frame and RED-touch gate on this exact shared set.
BOAT_APPSPAWN_SHA="76e6df931905177c8abde4054ee5516cb6d8394c67dce8f79dfadf0847b96747"
BOAT_CHILD_SHA="47f238aede6336ce3770861a6a742e71abc28f35516481299797c05c63149b57"
BOAT_PROVIDER_SHA="f821d20eaefc798b638192124e3a98683103f3d509c0b66ca1c6946037cccdb0"
BOAT_RUNTIME_SHA="adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130"
BOAT_ADAPTER_SHA="8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e"
BOAT_JAR_SHA="635a65e1ee7ef699ca138204fd359018e7f459512f0d1d0a4cd30cd2474d1396"

CHANNEL_ROOT="$REPO_ROOT/var/state/agent-channel"
LOCK_ROOT="$CHANNEL_ROOT/.locks"
RUN_ROOT="$REPO_ROOT/var/state/reproduce-helloworld"

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
CHANNEL_FILE="$CHANNEL_ROOT/reproduce-helloworld-$BOARD_LABEL.md"
LOCK_DIR="$LOCK_ROOT/$BOARD.lock"
CLAIMED=0
RUN_DIR=""
RUN_LOG=""
RUN_EVIDENCE=""
RUNTIME_PROFILE="UNKNOWN"
RUNTIME_APPSPAWN_SHA=""
RUNTIME_CHILD_SHA=""
RUNTIME_PROVIDER_SHA=""
RUNTIME_RUNTIME_SHA=""
RUNTIME_ADAPTER_SHA=""
RUNTIME_JAR_SHA=""

die()
{
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

usage()
{
    printf '%s\n' \
        "usage: $SELF check [supported-board-serial]" \
        "       $SELF status [supported-board-serial]" \
        "       $SELF quick [supported-board-serial]" \
        "       $SELF restore [supported-board-serial]" \
        "       $SELF dry-run-quick [supported-board-serial]" \
        "       $SELF dry-run-restore [supported-board-serial]"
}

trim()
{
    tr -d ' \r\n'
}

sha256_file()
{
    shasum -a 256 "$1" | awk '{print $1}'
}

require_hash()
{
    local expected=$1 path=$2 actual
    [ -f "$path" ] || die "missing fixed input: $path"
    actual="$(sha256_file "$path")"
    [ "$actual" = "$expected" ] \
        || die "hash drift: $path expected=$expected actual=$actual"
}

local_preflight()
{
    [ "$(uname -s)" = Darwin ] || die "this fixed reproduction is local-Mac only"
    [ -z "${SSH_CONNECTION:-}" ] || die "SSH/mac-server execution is forbidden for this skill"
    [ -x "$HDC_BIN" ] || die "missing fixed DevEco hdc: $HDC_BIN"
    [ -x "$FFMPEG_BIN" ] || die "ffmpeg is required for pixel validation"
    command -v rg >/dev/null 2>&1 || die "rg is required for evidence validation"
    bash -n "$SELF"
}

local_static_audit()
{
    [ -x "$RESTORE_DRIVER" ] || die "missing executable restore driver: $RESTORE_DRIVER"
    bash -n "$RESTORE_DRIVER"
    require_hash "$RESTORE_DRIVER_SHA" "$RESTORE_DRIVER"
    require_hash "$RECOVERY_SCRIPT_SHA" "$RECOVERY_SCRIPT"
    require_hash "$RECOVERY_CFG_SHA" "$RECOVERY_CFG"
    require_hash "$APK_SHA" "$APK_PATH"
    env -u BRIDGE_PAYLOAD -u HDC_BIN -u FFMPEG_BIN \
        "$RESTORE_DRIVER" --check-only >/dev/null
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
    D "sha256sum '$1' 2>/dev/null || true" | awk 'NR == 1 {print $1}'
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

detect_runtime_profile()
{
    RUNTIME_APPSPAWN_SHA="$(device_hash /system/bin/appspawn-x)"
    RUNTIME_CHILD_SHA="$(device_hash /system/lib64/appspawn/libwestlake_android_child.z.so)"
    RUNTIME_PROVIDER_SHA="$(device_hash "$PROVIDER_TARGET")"
    RUNTIME_RUNTIME_SHA="$(device_hash /system/android/lib64/liboh_android_runtime.so)"
    RUNTIME_ADAPTER_SHA="$(device_hash /system/android/lib64/liboh_adapter_bridge.so)"
    RUNTIME_JAR_SHA="$(device_hash /system/android/framework/oh-adapter-runtime.jar)"
    RUNTIME_PROFILE=UNKNOWN

    if [ "$RUNTIME_APPSPAWN_SHA" = "$PR03_APPSPAWN_SHA" ] \
        && [ "$RUNTIME_CHILD_SHA" = "$PR03_CHILD_SHA" ] \
        && [ "$RUNTIME_PROVIDER_SHA" = "$PR03_PROVIDER_SHA" ] \
        && [ "$RUNTIME_RUNTIME_SHA" = "$PR03_RUNTIME_SHA" ] \
        && [ "$RUNTIME_ADAPTER_SHA" = "$PR03_ADAPTER_SHA" ] \
        && [ "$RUNTIME_JAR_SHA" = "$PR03_JAR_SHA" ]; then
        RUNTIME_PROFILE=pr03-touch
    elif [ "$RUNTIME_APPSPAWN_SHA" = "$ZIGZAG_APPSPAWN_SHA" ] \
        && [ "$RUNTIME_CHILD_SHA" = "$ZIGZAG_CHILD_SHA" ] \
        && [ "$RUNTIME_PROVIDER_SHA" = "$ZIGZAG_PROVIDER_SHA" ] \
        && [ "$RUNTIME_RUNTIME_SHA" = "$ZIGZAG_RUNTIME_SHA" ] \
        && [ "$RUNTIME_ADAPTER_SHA" = "$ZIGZAG_ADAPTER_SHA" ] \
        && [ "$RUNTIME_JAR_SHA" = "$ZIGZAG_JAR_SHA" ]; then
        RUNTIME_PROFILE=zigzag-accepted-superset
    elif [ "$RUNTIME_APPSPAWN_SHA" = "$BOAT_APPSPAWN_SHA" ] \
        && [ "$RUNTIME_CHILD_SHA" = "$BOAT_CHILD_SHA" ] \
        && [ "$RUNTIME_PROVIDER_SHA" = "$BOAT_PROVIDER_SHA" ] \
        && [ "$RUNTIME_RUNTIME_SHA" = "$BOAT_RUNTIME_SHA" ] \
        && [ "$RUNTIME_ADAPTER_SHA" = "$BOAT_ADAPTER_SHA" ] \
        && [ "$RUNTIME_JAR_SHA" = "$BOAT_JAR_SHA" ]; then
        RUNTIME_PROFILE=boat-accepted-superset
    fi
}

runtime_hash_report()
{
    printf 'runtime_profile=%s\n' "$RUNTIME_PROFILE"
    printf 'appspawn_sha256=%s\nchild_sha256=%s\nprovider_sha256=%s\n' \
        "${RUNTIME_APPSPAWN_SHA:-MISSING}" "${RUNTIME_CHILD_SHA:-MISSING}" \
        "${RUNTIME_PROVIDER_SHA:-MISSING}"
    printf 'runtime_sha256=%s\nadapter_sha256=%s\nruntime_jar_sha256=%s\n' \
        "${RUNTIME_RUNTIME_SHA:-MISSING}" "${RUNTIME_ADAPTER_SHA:-MISSING}" \
        "${RUNTIME_JAR_SHA:-MISSING}"
}

require_runtime_profile()
{
    detect_runtime_profile
    case "$RUNTIME_PROFILE" in
        pr03-touch|zigzag-accepted-superset|boat-accepted-superset) ;;
        *) runtime_hash_report >&2; die "runtime generation is not an accepted HelloWorld profile; use restore" ;;
    esac
}

bundle_dump()
{
    D "bm dump -n '$PACKAGE' 2>/dev/null"
}

bundle_uid()
{
    bundle_dump | grep -oE '"uid": *[0-9]+' | head -n 1 | grep -oE '[0-9]+$'
}

require_installed_identity()
{
    local actual dump
    actual="$(device_hash "$APK_TARGET")"
    [ "$actual" = "$APK_SHA" ] \
        || die "installed HelloWorld APK drift: expected=$APK_SHA actual=${actual:-MISSING}; use restore"
    dump="$(bundle_dump)"
    printf '%s\n' "$dump" | grep -q '"bundleType": 10' \
        || die "HelloWorld is not registered as Android bundleType=10"
    printf '%s\n' "$dump" | grep -Fq "\"name\": \"$ABILITY\"" \
        || die "HelloWorld activity identity drift: $ABILITY"
}

write_channel()
{
    local status=$1 rc=$2 tmp
    mkdir -p "$CHANNEL_ROOT"
    tmp="$(mktemp "$CHANNEL_ROOT/.reproduce-helloworld.XXXXXX")"
    {
        printf '# Device channel: fixed HelloWorld APK reproduction on %s\n\n' "$BOARD_LABEL"
        printf -- '- status: %s\n' "$status"
        printf -- '- owner: `reproduce-helloworld-%s`\n' "$$"
        printf -- '- target: `%s`\n' "$BOARD"
        printf -- '- mode: `%s`\n' "$MODE"
        printf -- '- host: `%s`\n' "$(hostname)"
        printf -- '- updated_utc: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        printf -- '- apk_sha256: `%s`\n' "$APK_SHA"
        printf -- '- runtime_profile: `%s`\n' "$RUNTIME_PROFILE"
        printf -- '- exit_code: `%s`\n' "$rc"
        printf -- '- evidence: `%s`\n' "${RUN_EVIDENCE:-PENDING}"
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

create_run()
{
    local run_id evidence_id
    run_id="$(date -u +%Y%m%dT%H%M%SZ)-${MODE}-$$"
    evidence_id="$(date +%Y%m%d-%H%M%S)-${BOARD_LABEL}-helloworld-${MODE}-reproduce-$$"
    RUN_DIR="$RUN_ROOT/$run_id"
    RUN_EVIDENCE="$REPO_ROOT/var/evidence/ab-compare/$evidence_id"
    mkdir -p "$RUN_DIR" "$RUN_EVIDENCE"
    RUN_LOG="$RUN_DIR/driver.log"
    write_channel ACTIVE PENDING
}

decoded_frame_md5()
{
    "$FFMPEG_BIN" -hide_banner -loglevel error -i "$1" \
        -map 0:v:0 -f md5 - 2>/dev/null | sed -n 's/^MD5=//p' | head -n 1
}

verify_nonblank_jpeg()
{
    local image=$1 stats bytes ymin ymax
    [ -s "$image" ] || return 1
    bytes="$(wc -c < "$image" | trim)"
    [ "$bytes" -ge 50000 ] || return 1
    stats="$image.signalstats.txt"
    "$FFMPEG_BIN" -hide_banner -loglevel error -i "$image" \
        -vf "signalstats,metadata=print:file=$stats" -f null - >/dev/null 2>&1 || return 1
    ymin="$(sed -n 's/^lavfi.signalstats.YMIN=//p' "$stats" | head -n 1)"
    ymax="$(sed -n 's/^lavfi.signalstats.YMAX=//p' "$stats" | head -n 1)"
    [ -n "$ymin" ] && [ -n "$ymax" ] || return 1
    [ "$ymin" -le 30 ] && [ "$ymax" -ge 220 ]
}

prepare_sandbox()
{
    local uid=$1
    D "set -e; for d in /data/app/el1/100/base /data/app/el1/100/database /data/app/el2/100/base /data/app/el2/100/database /data/app/el2/100/sharefiles /data/app/el3/100/base /data/app/el3/100/database /data/app/el4/100/base /data/app/el4/100/database; do mkdir -p \${d}/'$PACKAGE'; done; mkdir -p /data/app/el2/100/log/'$PACKAGE'; for s in cache code_cache databases files haps no_backup preferences shared_prefs temp; do mkdir -p /data/app/el2/100/base/'$PACKAGE'/\${s}; done; chown -R '$uid':'$uid' /data/app/el1/100/base/'$PACKAGE' /data/app/el1/100/database/'$PACKAGE' /data/app/el2/100/base/'$PACKAGE' /data/app/el2/100/database/'$PACKAGE' /data/app/el2/100/sharefiles/'$PACKAGE' /data/app/el3/100/base/'$PACKAGE' /data/app/el3/100/database/'$PACKAGE' /data/app/el4/100/base/'$PACKAGE' /data/app/el4/100/database/'$PACKAGE'; chown '$uid':log /data/app/el2/100/log/'$PACKAGE'; chmod -R 0700 /data/app/el1/100/base/'$PACKAGE' /data/app/el2/100/base/'$PACKAGE' /data/app/el2/100/sharefiles/'$PACKAGE' /data/app/el3/100/base/'$PACKAGE' /data/app/el4/100/base/'$PACKAGE'; chmod 0770 /data/app/el1/100/database/'$PACKAGE' /data/app/el2/100/database/'$PACKAGE' /data/app/el2/100/log/'$PACKAGE' /data/app/el3/100/database/'$PACKAGE' /data/app/el4/100/database/'$PACKAGE'; chcon -R u:object_r:appdat:s0 /data/app/el1/100/base/'$PACKAGE' /data/app/el1/100/database/'$PACKAGE' /data/app/el2/100/base/'$PACKAGE' /data/app/el2/100/database/'$PACKAGE' /data/app/el2/100/sharefiles/'$PACKAGE' /data/app/el3/100/base/'$PACKAGE' /data/app/el3/100/database/'$PACKAGE' /data/app/el4/100/base/'$PACKAGE' /data/app/el4/100/database/'$PACKAGE'; chcon u:object_r:data_app_el2_file:s0 /data/app/el2/100/log/'$PACKAGE'" >/dev/null
}

sole_parent_pid()
{
    D "ps -ef | grep '^root ' | grep 'appspawn-x --socket-name AppSpawnX' | grep -v grep" \
        | awk 'NR == 1 {print $2}'
}

ensure_parent()
{
    local uid=$1 parent count expected old_pids pid
    D "aa force-stop '$PACKAGE' >/dev/null 2>&1 || true; aa force-stop com.a2hlab.bridge.zigzag >/dev/null 2>&1 || true" >/dev/null
    old_pids="$(D "ps -ef | grep '^$uid ' | grep 'appspawn-x --socket-name AppSpawnX' | grep -v grep" \
        | awk '{print $2}' || true)"
    for pid in $old_pids; do
        D "kill -9 '$pid' 2>/dev/null || true" >/dev/null
    done
    for _ in $(seq 1 10); do
        [ -z "$(D "ps -ef | grep '^$uid ' | grep 'appspawn-x --socket-name AppSpawnX' | grep -v grep" || true)" ] \
            && break
        sleep 1
    done
    [ -z "$(D "ps -ef | grep '^$uid ' | grep 'appspawn-x --socket-name AppSpawnX' | grep -v grep" || true)" ] \
        || die "old HelloWorld child survived the cold-start fence"
    count="$(D "ps -ef | grep '^root ' | grep 'appspawn-x --socket-name AppSpawnX' | grep -v grep | wc -l" | trim)"
    if [ "$count" = 0 ]; then
        D "begetctl start_service appspawn-x" >/dev/null
        for _ in $(seq 1 20); do
            sleep 1
            count="$(D "ps -ef | grep '^root ' | grep 'appspawn-x --socket-name AppSpawnX' | grep -v grep | wc -l" | trim)"
            [ "$count" = 1 ] && break
        done
    fi
    [ "$count" = 1 ] || die "appspawn-x does not have exactly one root parent: $count"
    parent="$(sole_parent_pid | trim)"
    [ -n "$parent" ] || die "cannot resolve appspawn-x parent"
    expected="$RUNTIME_APPSPAWN_SHA"
    [ "$(device_hash "/proc/$parent/exe")" = "$expected" ] \
        || die "running appspawn-x does not match accepted runtime profile"
    printf '%s\n' "$parent"
}

write_envstamp()
{
    local boot_id=$1
    {
        printf 'claim=DEVELOPER_REPRODUCIBLE_LIGHT\n'
        printf 'host=%s\nboard=%s\nrom=%s\nboot_id=%s\n' \
            "$(hostname)" "$BOARD" "$ROM_ONLY" "$boot_id"
        printf 'package=%s\nability=%s\nbundle_type=10\napk_sha256=%s\n' \
            "$PACKAGE" "$ABILITY" "$APK_SHA"
        runtime_hash_report
        printf 'restore_driver_sha256=%s\nrecovery_script_sha256=%s\nrecovery_cfg_sha256=%s\n' \
            "$RESTORE_DRIVER_SHA" "$RECOVERY_SCRIPT_SHA" "$RECOVERY_CFG_SHA"
    } > "$RUN_EVIDENCE/envstamp.txt"
}

finalize_evidence()
{
    local uid=$1 parent=$2 child=$3 before=$4 after=$5 launch_token=$6
    local manifest receipt

    [ -n "$before" ] && [ -n "$after" ] && [ "$before" != "$after" ] \
        || die "decoded pixels did not change after CHANGE COLOR"
    grep -q 'mVisibleFromServer=true' "$RUN_EVIDENCE/visibility.log" \
        || die "HelloWorld window was not visible"
    grep -q 'Hello World' "$RUN_EVIDENCE/visibility.log" \
        || die "HelloWorld view-tree marker was not observed"
    grep -q 'Color changed to: RED' "$RUN_EVIDENCE/touch.log" \
        || die "CHANGE COLOR touch callback was not observed"
    ! grep -qE 'AndroidRuntimeException|Animators may only|FATAL EXCEPTION|Fatal signal|OnStartSpecifiedFailed|lifecycle.*timeout' \
        "$RUN_EVIDENCE/application.log" \
        || die "fatal/lifecycle marker observed in HelloWorld application log"

    {
        printf 'first_bad=NONE_OBSERVED_LIGHT\n'
        printf 'reason=exact APK, accepted runtime, visible pixels, RED touch callback, changed frame and stable child PID passed\n'
    } > "$RUN_EVIDENCE/first-bad.env"
    printf 'NONE_OBSERVED_LIGHT: first-frame pixels and CHANGE COLOR touch passed\n' \
        > "$RUN_EVIDENCE/first-bad.txt"
    {
        printf 'DEVELOPER_REPRODUCIBLE_LIGHT=1\n'
        printf 'package=%s\nability=%s\napk_sha256=%s\n' "$PACKAGE" "$ABILITY" "$APK_SHA"
        printf 'runtime_profile=%s\nuid=%s\nparent_pid=%s\nchild_pid=%s\n' \
            "$RUNTIME_PROFILE" "$uid" "$parent" "$child"
        printf 'launch_token=%s\nbefore_md5=%s\nafter_md5=%s\n' \
            "$launch_token" "$before" "$after"
    } > "$RUN_EVIDENCE/DEVELOPER-REPRODUCIBLE-LIGHT.env"

    manifest="$RUN_EVIDENCE/files.sha256"
    (
        cd "$RUN_EVIDENCE"
        shasum -a 256 before.jpeg after.jpeg visibility.log touch.log application.log \
            process-after-touch.txt envstamp.txt first-bad.env first-bad.txt \
            DEVELOPER-REPRODUCIBLE-LIGHT.env
    ) > "$manifest"

    receipt="$RUN_DIR/receipt.env"
    {
        printf 'REPRODUCE_HELLOWORLD=PASS\n'
        printf 'mode=%s\nboard=%s\npackage=%s\nability=%s\n' \
            "$MODE" "$BOARD" "$PACKAGE" "$ABILITY"
        printf 'apk_sha256=%s\nruntime_profile=%s\n' "$APK_SHA" "$RUNTIME_PROFILE"
        printf 'parent_pid=%s\nchild_pid=%s\nbefore_md5=%s\nafter_md5=%s\n' \
            "$parent" "$child" "$before" "$after"
        printf 'evidence=%s\nevidence_manifest_sha256=%s\n' \
            "$RUN_EVIDENCE" "$(sha256_file "$manifest")"
        printf 'developer_claim=DEVELOPER_REPRODUCIBLE_LIGHT\n'
    } > "$receipt"
    printf 'REPRODUCE_HELLOWORLD=PASS\nreceipt=%s\nevidence=%s\n' \
        "$receipt" "$RUN_EVIDENCE"
}

run_quick()
{
    local uid parent child_line child ppid logs before after boot_id launch_token remote_base
    require_installed_identity
    require_runtime_profile
    boot_id="$(D 'cat /proc/sys/kernel/random/boot_id' | trim)"
    write_envstamp "$boot_id"
    uid="$(bundle_uid | trim)"
    [ -n "$uid" ] || die "cannot resolve HelloWorld UID"
    prepare_sandbox "$uid"
    parent="$(ensure_parent "$uid" | trim)"
    printf 'parent_pid=%s\nuid=%s\n' "$parent" "$uid" > "$RUN_EVIDENCE/process-before.txt"

    D "power-shell setmode 602 >/dev/null 2>&1; power-shell timeout -o 86400000 >/dev/null 2>&1; power-shell wakeup >/dev/null 2>&1; power-shell display -o 230 >/dev/null 2>&1; hilog -r >/dev/null 2>&1 || true" >/dev/null
    launch_token="HW-FAST-${BOARD:0:8}-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    {
        printf 'launch_token=%s\n' "$launch_token"
        D "aa start -a '$ABILITY' -b '$PACKAGE' -W"
    } > "$RUN_EVIDENCE/launch.log"
    grep -q 'start ability successfully' "$RUN_EVIDENCE/launch.log" \
        || die "aa start did not report success"

    child_line=""
    for _ in $(seq 1 20); do
        child_line="$(D "ps -ef | grep '^$uid ' | grep 'appspawn-x --socket-name AppSpawnX' | grep -v grep | head -n 1" || true)"
        [ -n "$child_line" ] && break
        sleep 1
    done
    [ -n "$child_line" ] || {
        D "hilog -x | tail -n 5000" > "$RUN_EVIDENCE/hilog-failure.log" || true
        D "dmesg | tail -n 2000" > "$RUN_EVIDENCE/dmesg-failure.log" || true
        die "HelloWorld child did not appear"
    }
    set -- $child_line
    child="${2:-}"
    ppid="${3:-}"
    [ -n "$child" ] && [ "$ppid" = "$parent" ] \
        || die "HelloWorld child parent mismatch: child=${child:-MISSING} ppid=${ppid:-MISSING} parent=$parent"

    logs=""
    for _ in $(seq 1 15); do
        logs="$(D "hilog -x | grep -E '$PACKAGE|Hello World|mVisibleFromServer' | tail -n 1000" || true)"
        if printf '%s\n' "$logs" | grep -q 'mVisibleFromServer=true' \
            && printf '%s\n' "$logs" | grep -q 'Hello World'; then
            break
        fi
        sleep 1
    done
    printf '%s\n' "$logs" > "$RUN_EVIDENCE/visibility.log"

    remote_base="/data/local/tmp/reproduce-helloworld-$$"
    D "snapshot_display -f '${remote_base}-before.jpeg'" >/dev/null
    H file recv "${remote_base}-before.jpeg" "$RUN_EVIDENCE/before.jpeg" >/dev/null
    verify_nonblank_jpeg "$RUN_EVIDENCE/before.jpeg" || die "before screenshot is blank or invalid"
    before="$(decoded_frame_md5 "$RUN_EVIDENCE/before.jpeg")"

    D "hilog -r >/dev/null 2>&1 || true; uitest uiInput click 600 500 >/dev/null 2>&1 || uinput -T -c 600 500 100" >/dev/null
    sleep 2
    logs="$(D "hilog -x | grep -E 'Color changed to: RED|AndroidRuntimeException|Animators may only|FATAL EXCEPTION|Fatal signal|OnStartSpecifiedFailed|lifecycle.*timeout' | grep -v '/HDC_LOG:' | tail -n 500" || true)"
    printf '%s\n' "$logs" > "$RUN_EVIDENCE/touch.log"
    D "snapshot_display -f '${remote_base}-after.jpeg'" >/dev/null
    H file recv "${remote_base}-after.jpeg" "$RUN_EVIDENCE/after.jpeg" >/dev/null
    verify_nonblank_jpeg "$RUN_EVIDENCE/after.jpeg" || die "after screenshot is blank or invalid"
    after="$(decoded_frame_md5 "$RUN_EVIDENCE/after.jpeg")"

    sleep 3
    D "ps -ef | grep '^$uid *$child ' | grep -v grep || true" > "$RUN_EVIDENCE/process-after-touch.txt"
    grep -q "$child" "$RUN_EVIDENCE/process-after-touch.txt" \
        || die "HelloWorld child did not survive the touch checkpoint"
    D "hilog -x | grep -E '$PACKAGE|^[^ ]+ +[^ ]+ +$child ' | grep -v '/HDC_LOG:' | tail -n 2500" \
        > "$RUN_EVIDENCE/application.log" || true
    D "aa dump -a 2>/dev/null | grep -m1 'mission name.*#$PACKAGE:entry:$ABILITY' || true" \
        > "$RUN_EVIDENCE/mission.txt"
    D "rm -f '${remote_base}-before.jpeg' '${remote_base}-after.jpeg'" >/dev/null || true
    finalize_evidence "$uid" "$parent" "$child" "$before" "$after" "$launch_token"
}

run_restore()
{
    local rc raw_log raw_dir uid pair parent child before after boot_id launch_token
    set +e
    env -u BRIDGE_PAYLOAD -u HDC_BIN -u FFMPEG_BIN \
        "$RESTORE_DRIVER" "$BOARD" 2>&1 | tee "$RUN_LOG"
    rc=${PIPESTATUS[0]}
    set -e
    [ "$rc" -eq 0 ] || die "PR03 restore driver failed: rc=$rc log=$RUN_LOG"
    grep -q '^成功：HelloWorld 已在 .*上屏，CHANGE COLOR 点击后变为 RED。$' "$RUN_LOG" \
        || die "restore driver did not emit its success marker"

    raw_log="$(sed -n 's/^完整日志：//p' "$RUN_LOG" | tail -n 1)"
    [ -f "$raw_log" ] || die "restore driver returned no raw log"
    raw_dir="$(dirname "$raw_log")"
    case "$raw_dir" in
        "$REPO_ROOT/var/state/pr03-helloworld-restore/"*) ;;
        *) die "restore evidence escaped repository state: $raw_dir" ;;
    esac
    cp "$raw_dir/HelloWorld.jpeg" "$RUN_EVIDENCE/before.jpeg"
    cp "$raw_dir/HelloWorld-touch-red.jpeg" "$RUN_EVIDENCE/after.jpeg"
    cp "$raw_dir/visibility.txt" "$RUN_EVIDENCE/visibility.log"
    cp "$raw_dir/touch.txt" "$RUN_EVIDENCE/touch.log"
    cp "$raw_dir/restore.log" "$RUN_EVIDENCE/application.log"
    verify_nonblank_jpeg "$RUN_EVIDENCE/before.jpeg" || die "restore before screenshot is blank or invalid"
    verify_nonblank_jpeg "$RUN_EVIDENCE/after.jpeg" || die "restore after screenshot is blank or invalid"
    before="$(decoded_frame_md5 "$RUN_EVIDENCE/before.jpeg")"
    after="$(decoded_frame_md5 "$RUN_EVIDENCE/after.jpeg")"

    require_installed_identity
    detect_runtime_profile
    [ "$RUNTIME_PROFILE" = pr03-touch ] \
        || { runtime_hash_report >&2; die "restore did not produce exact PR03 touch profile"; }
    boot_id="$(D 'cat /proc/sys/kernel/random/boot_id' | trim)"
    write_envstamp "$boot_id"
    uid="$(sed -n 's/^HelloWorld UID=\([0-9][0-9]*\),.*$/\1/p' "$RUN_LOG" | tail -n 1)"
    pair="$(sed -n 's/^parent\/child：//p' "$RUN_LOG" | tail -n 1)"
    parent="${pair%/*}"
    child="${pair#*/}"
    launch_token="$(sed -n 's/^launch token：//p' "$RUN_LOG" | tail -n 1)"
    [ -n "$uid" ] && [ -n "$parent" ] && [ -n "$child" ] && [ "$parent" != "$child" ] \
        || die "restore process identity receipt is incomplete"
    D "ps -ef | grep '^$uid *$child ' | grep -v grep || true" > "$RUN_EVIDENCE/process-after-touch.txt"
    grep -q "$child" "$RUN_EVIDENCE/process-after-touch.txt" \
        || die "restored HelloWorld child is not alive"
    D "aa dump -a 2>/dev/null | grep -m1 'mission name.*#$PACKAGE:entry:$ABILITY' || true" \
        > "$RUN_EVIDENCE/mission.txt"
    printf 'raw_restore_dir=%s\nraw_restore_log_sha256=%s\n' \
        "$raw_dir" "$(sha256_file "$raw_log")" > "$RUN_EVIDENCE/restore-source.env"
    finalize_evidence "$uid" "$parent" "$child" "$before" "$after" "$launch_token"
}

status_report()
{
    local apk_hash dump uid processes mission boot_id
    apk_hash="$(device_hash "$APK_TARGET")"
    dump="$(bundle_dump || true)"
    uid="$(printf '%s\n' "$dump" | grep -oE '"uid": *[0-9]+' | head -n 1 | grep -oE '[0-9]+$' || true)"
    processes=""
    [ -z "$uid" ] || processes="$(D "ps -ef | grep '^$uid ' | grep -v grep || true")"
    mission="$(D "aa dump -a 2>/dev/null | grep -m1 'mission name.*#$PACKAGE:entry:$ABILITY' || true")"
    boot_id="$(D 'cat /proc/sys/kernel/random/boot_id' | trim)"
    detect_runtime_profile

    printf 'REPRODUCE_HELLOWORLD_STATUS=OK\n'
    printf 'host=%s\nboard=%s\nrom=%s\nboot_id=%s\n' \
        "$(hostname)" "$BOARD" "$ROM_ONLY" "$boot_id"
    printf 'package=%s\nability=%s\napk_sha256=%s\nbundle_type_10=%s\nuid=%s\n' \
        "$PACKAGE" "$ABILITY" "${apk_hash:-MISSING}" \
        "$([ -n "$dump" ] && printf '%s\n' "$dump" | grep -q '"bundleType": 10' && printf true || printf false)" \
        "${uid:-MISSING}"
    runtime_hash_report
    printf 'mission_present=%s\nprocesses=%s\n' \
        "$([ -n "$mission" ] && printf true || printf false)" "${processes:-NONE}"
}

[ "$#" -le 2 ] || { usage; die "too many arguments"; }
case "$MODE" in
    check|status|quick|restore|dry-run-quick|dry-run-restore) ;;
    -h|--help|help) usage; exit 0 ;;
    *) usage; die "unknown mode: $MODE" ;;
esac

local_preflight
case "$MODE" in
    check|restore|dry-run-restore) local_static_audit ;;
esac
device_preflight

case "$MODE" in
    check)
        require_installed_identity
        require_runtime_profile
        printf 'REPRODUCE_HELLOWORLD_CHECK=PASS\nboard=%s\nrom=%s\n' "$BOARD" "$ROM_ONLY"
        printf 'package=%s\nability=%s\napk_sha256=%s\n' "$PACKAGE" "$ABILITY" "$APK_SHA"
        runtime_hash_report
        ;;
    status)
        status_report
        ;;
    dry-run-quick)
        require_installed_identity
        require_runtime_profile
        printf 'DRY_RUN=PASS\n%s quick %s\n' "$SELF" "$BOARD"
        ;;
    dry-run-restore)
        printf 'DRY_RUN=PASS\n%s %s\n' "$RESTORE_DRIVER" "$BOARD"
        ;;
    quick)
        claim_board
        create_run
        run_quick 2>&1 | tee "$RUN_LOG"
        ;;
    restore)
        detect_runtime_profile
        claim_board
        create_run
        run_restore
        ;;
esac
