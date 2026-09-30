#!/usr/bin/env bash

set -Eeuo pipefail

SELF="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
DRIVER="$REPO_ROOT/src/tools/devices/zigzag-apk-lightup.sh"
RESTORE_DRIVER="$REPO_ROOT/src/tools/devices/restore-pr03-helloworld-5min.sh"
HDC_BIN="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc"

BOARD_ONLY="61ae0be500000000000000000324012c"
BOARD_8605="5ce2dcee00000000000000000923012c"
BOARD_5EA1="5ea1719200000000000000001123012c"
ROM_ONLY="OpenHarmony-6.1.0.31"
APK="$REPO_ROOT/src/vendor/samples/apks/ZigZag/project/dist/zigzag.apk"
[ -f "$APK" ] || APK="$REPO_ROOT/APKS/ZigZag/project/dist/zigzag.apk"
APK_SHA="aaa7c9cce4886eef1280e917fd25bf434c53065cf0bf8b5704b83738137275bc"
ZIGZAG_BUNDLE="com.a2hlab.bridge.zigzag"
ZIGZAG_ABILITY="com.unity3d.player.UnityPlayerActivity"

CANDIDATE_ID="strict-20260809T160651Z-21101"
PERSISTED_ROOT="$REPO_ROOT/.bridge-payload/zigzag-persisted"
PERSISTED_POINTER="$PERSISTED_ROOT/current"
FILES_MANIFEST_SHA="e9b27d092d33af3742d73ca3de51ce632753d81ffd939bf0b699271dfcb94a4c"
CANDIDATE_MANIFEST_SHA="c76bba256156be2fc8b8a6503a071d34456d5620f669b0032553d45e529c4f8d"
RECOVERY_SHA="7eaf26fbbaf69227fcde865bd259fb3a4f8ffae9cd5aab00b4a6c2302ac5b4ab"
DRIVER_SHA="e2fdbafbe9aaf3adbdb0f4eac9f50fa0336d66d62527d5bd1a67b58c461b2d59"
RESTORE_DRIVER_SHA="76ffae6d306c84ef54a9cb014820b4be79b23e81ceb07acd1054d2eb51eae293"

CHANNEL_ROOT="$REPO_ROOT/var/state/agent-channel"
LOCK_ROOT="$CHANNEL_ROOT/.locks"
RUN_ROOT="$REPO_ROOT/var/state/reproduce-zigzag-apk"

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
CHANNEL_FILE="$CHANNEL_ROOT/reproduce-zigzag-apk-$BOARD_LABEL.md"
LOCK_DIR="$LOCK_ROOT/$BOARD.lock"
CANDIDATE=""
CLAIMED=0
RUN_LOG=""
RUN_EVIDENCE=""

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

sha256_file()
{
    shasum -a 256 "$1" | awk '{print $1}'
}

trim()
{
    tr -d ' \r\n'
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

require_manifest_value()
{
    local manifest=$1 key=$2 expected=$3 actual
    actual="$(manifest_value "$manifest" "$key")"
    [ "$actual" = "$expected" ] \
        || die "candidate manifest drift: $key expected=$expected actual=${actual:-MISSING}"
}

resolve_fixed_candidate()
{
    local requested
    [ -f "$PERSISTED_POINTER" ] || die "missing persisted pointer: $PERSISTED_POINTER"
    IFS= read -r requested < "$PERSISTED_POINTER"
    [ -d "$requested" ] || die "persisted candidate directory missing: $requested"
    CANDIDATE="$(cd "$requested" && pwd -P)"
    case "$CANDIDATE" in
        "$PERSISTED_ROOT/$CANDIDATE_ID") ;;
        *) die "persisted pointer is not the accepted fixed candidate: $CANDIDATE" ;;
    esac
}

verify_fixed_candidate()
{
    local manifest="$CANDIDATE/manifest.env"
    local files="$CANDIDATE/files"

    require_hash "$CANDIDATE_MANIFEST_SHA" "$manifest"
    require_hash "$FILES_MANIFEST_SHA" "$CANDIDATE/files.sha256"
    require_hash "$RECOVERY_SHA" "$CANDIDATE/pr03-runtime-recover.sh"

    require_manifest_value "$manifest" CANDIDATE_ID "$CANDIDATE_ID"
    require_manifest_value "$manifest" ZIGZAG_APK_SHA "$APK_SHA"
    require_manifest_value "$manifest" ADAPTER_SHA "84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a"
    require_manifest_value "$manifest" PROVIDER_SHA "80c9aee0f39b860b1ce8d72af106e4fde49c0dbf41ef1b426c1e3103086d9b2f"
    require_manifest_value "$manifest" CHILD_SHA "0976dee89c0464cd6aeaf7d4c3c4afd1466926b7d69dc8e01d4910f92bf12e40"
    require_manifest_value "$manifest" APPSPAWN_SHA "1f6cf53be7b3225a6d0a2b5f66278c32f5d9f5f99a0f56ece3f57a630db4d908"
    require_manifest_value "$manifest" RUNTIME_JAR_SHA "9161b50756d3ffdfb2a8908ea7ec13f908214688321b2785365977ac40b28dea"
    require_manifest_value "$manifest" PTHREAD_BRIDGE_SHA "db31d6d81c543860449e4e13f94dda6d39acde94ce00e34e7087a4d796e88fc6"
    require_manifest_value "$manifest" NATIVE_LOADER_SHA "fde6f31c6f8911bd5be165d69bc248f47699be435240dc855fa7528c0ba73ccd"
    require_manifest_value "$manifest" LIBANDROID_SHA "9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db"
    require_manifest_value "$manifest" MEDIANDK_SHA "110d02fc4bbb32ed241358c6329f6aa5e4849f021e5b224f9ae2b826f8fa75fb"
    require_manifest_value "$manifest" SIGNAL_BOX_SHA "7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da"
    require_manifest_value "$manifest" PATCHED_LIBMAIN_SHA "2abf2614750cffeaaeaa93880c299c7c27913255ca7c1a4177394b72725b23e8"
    require_manifest_value "$manifest" PATCHED_LIBIL2CPP_SHA "3bea2f16c8887630922b092368ab10c38292faed5f5b864e9a4c1fbba21056e6"
    require_manifest_value "$manifest" PATCHED_LIBTUANJIE_SHA "eb9d8c6de0f415e66896dfea5f5ddf16891d856766e5be1e6fb923166e844c9b"
    require_manifest_value "$manifest" TUANJIE_CORE_RESOLVER "eglGetProcAddress"
    require_manifest_value "$manifest" TUANJIE_CORE_GETPROC_FILE_OFFSET "0xaaaad4"
    require_manifest_value "$manifest" TUANJIE_CORE_GETPROC_PATCH_HEX "11000014"

    [ -d "$files" ] || die "candidate files directory missing: $files"
    (cd "$files" && shasum -a 256 -c ../files.sha256 >/dev/null) \
        || die "one or more persisted candidate files drifted"
}

local_preflight()
{
    [ "$(uname -s)" = Darwin ] || die "this fixed reproduction is local-Mac only"
    [ -z "${SSH_CONNECTION:-}" ] || die "SSH/mac-server execution is forbidden for this skill"
    [ -x "$HDC_BIN" ] || die "missing fixed DevEco hdc: $HDC_BIN"
    [ -x "$DRIVER" ] || die "missing executable driver: $DRIVER"
    command -v ffmpeg >/dev/null 2>&1 || die "ffmpeg is required for pixel validation"
    command -v rg >/dev/null 2>&1 || die "rg is required for evidence validation"
    bash -n "$SELF"
    bash -n "$DRIVER"
    resolve_fixed_candidate
}

local_static_audit()
{
    [ -x "$RESTORE_DRIVER" ] || die "missing executable restore driver: $RESTORE_DRIVER"
    bash -n "$RESTORE_DRIVER"
    require_hash "$DRIVER_SHA" "$DRIVER"
    require_hash "$RESTORE_DRIVER_SHA" "$RESTORE_DRIVER"
    require_hash "$APK_SHA" "$APK"
    verify_fixed_candidate
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

write_channel()
{
    local status=$1 rc=$2 tmp
    mkdir -p "$CHANNEL_ROOT"
    tmp="$(mktemp "$CHANNEL_ROOT/.reproduce-zigzag-apk.XXXXXX")"
    {
        printf '# Device channel: fixed ZigZag APK reproduction on %s\n\n' "$BOARD_LABEL"
        printf -- '- status: %s\n' "$status"
        printf -- '- owner: `reproduce-zigzag-apk-%s`\n' "$$"
        printf -- '- target: `%s`\n' "$BOARD"
        printf -- '- mode: `%s`\n' "$MODE"
        printf -- '- host: `%s`\n' "$(hostname)"
        printf -- '- updated_utc: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        printf -- '- candidate: `%s`\n' "$CANDIDATE_ID"
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

status_report()
{
    local apk_hash tuanjie_hash uid processes mission transaction
    apk_hash="$(device_hash "/data/app/el1/bundle/public/$ZIGZAG_BUNDLE/android/base.apk")"
    tuanjie_hash="$(device_hash "/data/app/el1/bundle/public/$ZIGZAG_BUNDLE/android/lib/arm64-v8a/libtuanjie.so")"
    uid="$(D "bm dump -n '$ZIGZAG_BUNDLE' 2>/dev/null" \
        | grep -oE '"uid": *[0-9]+' | head -n 1 | grep -oE '[0-9]+$' || true)"
    processes=""
    [ -z "$uid" ] || processes="$(D "ps -ef | grep '^$uid ' | grep -v grep || true")"
    mission="$(D "aa dump -a 2>/dev/null | grep -m1 'mission name.*#$ZIGZAG_BUNDLE:entry:$ZIGZAG_ABILITY' || true")"
    transaction="$(D "cat /data/zigzag-apk-lightup/persist-current.env 2>/dev/null || true")"

    printf 'REPRODUCE_ZIGZAG_APK_STATUS=OK\n'
    printf 'host=%s\nboard=%s\nrom=%s\nboot_id=%s\n' \
        "$(hostname)" "$BOARD" "$ROM_ONLY" "$(D 'cat /proc/sys/kernel/random/boot_id' | trim)"
    printf 'candidate=%s\napk_sha256=%s\ntuanjie_sha256=%s\n' \
        "$CANDIDATE" "${apk_hash:-MISSING}" "${tuanjie_hash:-MISSING}"
    printf 'uid=%s\nforeground=%s\nprocesses=%s\n' \
        "${uid:-MISSING}" "$([ -n "$mission" ] && printf true || printf false)" \
        "${processes:-NONE}"
    printf '%s\n' "$transaction"
}

create_run_dir()
{
    local run_id
    run_id="$(date -u +%Y%m%dT%H%M%SZ)-${MODE}"
    mkdir -p "$RUN_ROOT/$run_id"
    RUN_LOG="$RUN_ROOT/$run_id/driver.log"
}

verify_run_receipt()
{
    local hello_evidence zigzag_evidence first_pid pid_at_t unique_frames receipt
    local hello_before hello_after input_changed score_before score_after
    hello_evidence="$(sed -n 's/^HelloWorld=//p' "$RUN_LOG" | tail -n 1)"
    zigzag_evidence="$(sed -n 's/^ZigZag=//p' "$RUN_LOG" | tail -n 1)"
    [ -d "$zigzag_evidence" ] || die "driver returned no ZigZag evidence directory"
    case "$zigzag_evidence" in "$REPO_ROOT/var/evidence/"*) ;; *) die "ZigZag evidence escaped repository" ;; esac

    grep -qx 'DEVELOPER_REPRODUCIBLE_LIGHT=1' \
        "$zigzag_evidence/DEVELOPER-REPRODUCIBLE-LIGHT.env" \
        || die "developer-reproducible receipt missing"
    grep -qx 'first_bad=NONE_OBSERVED_LIGHT' "$zigzag_evidence/first-bad.env" \
        || die "lightweight acceptance did not close first-bad"

    if [ "$hello_evidence" = SKIPPED_ACCEPTED_RUNTIME_UNCHANGED ]; then
        hello_before=SKIPPED
        hello_after=SKIPPED
    else
        [ -d "$hello_evidence" ] || die "driver returned no HelloWorld evidence directory"
        case "$hello_evidence" in "$REPO_ROOT/var/evidence/"*) ;; *) die "HelloWorld evidence escaped repository" ;; esac
        for hello_file in visibility.log touch.log result.env before.jpeg after.jpeg; do
            [ -s "$hello_evidence/$hello_file" ] \
                || die "HelloWorld evidence is incomplete: $hello_file"
        done
        grep -q 'mVisibleFromServer=true' "$hello_evidence/visibility.log" \
            || die "HelloWorld was not reported visible"
        grep -q 'Color changed to: RED' "$hello_evidence/touch.log" \
            || die "HelloWorld touch callback is missing"
        [ "$(manifest_value "$hello_evidence/result.env" candidate)" = "$CANDIDATE" ] \
            || die "HelloWorld evidence candidate drifted"
        hello_before="$(manifest_value "$hello_evidence/result.env" before_md5)"
        hello_after="$(manifest_value "$hello_evidence/result.env" after_md5)"
        [ -n "$hello_before" ] && [ -n "$hello_after" ] && [ "$hello_before" != "$hello_after" ] \
            || die "HelloWorld decoded pixels did not change after touch"
    fi

    grep -qx 'requested=5' "$zigzag_evidence/touches.env" \
        || die "five-touch request receipt missing"
    grep -qx 'delivered=5' "$zigzag_evidence/touches.env" \
        || die "five touches were not delivered"
    grep -qx 'status=NO_TERMINATING_NATIVE_FATAL' \
        "$zigzag_evidence/faultlog-assessment.env" \
        || die "terminating-native-fatal oracle failed"
    grep -qx "artifact_sha256=$APK_SHA" "$zigzag_evidence/envstamp.txt" \
        || die "evidence is not bound to the fixed APK"
    grep -qx "bundle=$ZIGZAG_BUNDLE" "$zigzag_evidence/envstamp.txt" \
        || die "evidence bundle identity drifted"
    grep -qx "ability=$ZIGZAG_ABILITY" "$zigzag_evidence/envstamp.txt" \
        || die "evidence activity identity drifted"

    [ -s "$zigzag_evidence/input-state.env" ] \
        || die "ZigZag game-state receipt is missing"
    input_changed="$(manifest_value "$zigzag_evidence/input-state.env" input_changed)"
    score_before="$(manifest_value "$zigzag_evidence/input-state.env" top_score_before)"
    score_after="$(manifest_value "$zigzag_evidence/input-state.env" top_score_after)"
    [ "$input_changed" = 1 ] || die "ZigZag game-state change receipt is missing"
    case "$score_before:$score_after" in
        *[!0-9:]*) die "ZigZag TopScore receipt is not numeric" ;;
        :*|*:) die "ZigZag TopScore receipt is incomplete" ;;
    esac
    [ "$score_after" -gt "$score_before" ] \
        || die "five touches did not increase ZigZag TopScore"

    unique_frames="$(cut -d= -f2 "$zigzag_evidence/pixel-frames.env" \
        | sed '/^$/d' | sort -u | wc -l | trim)"
    [ "$unique_frames" = 4 ] || die "t+3/9/15/taps are not four distinct decoded frames"
    first_pid="$(tr -d ' \r\n' < "$zigzag_evidence/first-pid.txt")"
    [ -n "$first_pid" ] || die "first ZigZag PID is missing"
    for checkpoint in 3 9 15; do
        pid_at_t="$(awk 'NR == 1 {print $2}' "$zigzag_evidence/proc-t${checkpoint}.txt")"
        [ "$pid_at_t" = "$first_pid" ] \
            || die "ZigZag PID changed at t+$checkpoint: $first_pid -> $pid_at_t"
    done

    RUN_EVIDENCE="$zigzag_evidence"
    receipt="$(dirname "$RUN_LOG")/receipt.env"
    {
        printf 'REPRODUCE_ZIGZAG_APK=PASS\n'
        printf 'mode=%s\nboard=%s\ncandidate=%s\n' "$MODE" "$BOARD" "$CANDIDATE"
        printf 'apk_sha256=%s\nfirst_pid=%s\n' "$APK_SHA" "$first_pid"
        printf 'top_score_before=%s\ntop_score_after=%s\n' "$score_before" "$score_after"
        printf 'hello_evidence=%s\nzigzag_evidence=%s\n' "$hello_evidence" "$zigzag_evidence"
        printf 'developer_claim=DEVELOPER_REPRODUCIBLE_LIGHT\n'
    } > "$receipt"
    printf 'REPRODUCE_ZIGZAG_APK=PASS\nreceipt=%s\nHelloWorld=%s\nZigZag=%s\n' \
        "$receipt" "$hello_evidence" "$zigzag_evidence"
}

run_quick()
{
    create_run_dir
    "$DRIVER" run-light-risk "$BOARD" "$CANDIDATE" 2>&1 | tee "$RUN_LOG"
    verify_run_receipt
}

run_restore()
{
    create_run_dir
    "$DRIVER" restore "$BOARD" 2>&1 | tee "$RUN_LOG"
    verify_run_receipt
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
case "$MODE" in
    check|status|dry-run-quick|dry-run-restore) device_preflight ;;
esac

case "$MODE" in
    check)
        printf 'REPRODUCE_ZIGZAG_APK_CHECK=PASS\nboard=%s\nrom=%s\napk_sha256=%s\ncandidate=%s\n' \
            "$BOARD" "$ROM_ONLY" "$APK_SHA" "$CANDIDATE"
        ;;
    status)
        status_report
        ;;
    dry-run-quick)
        printf 'DRY_RUN=PASS\n%s run-light-risk %s %s\n' \
            "$DRIVER" "$BOARD" "$CANDIDATE"
        ;;
    dry-run-restore)
        printf 'DRY_RUN=PASS\n%s restore %s\n' "$DRIVER" "$BOARD"
        ;;
    quick)
        claim_board
        run_quick
        ;;
    restore)
        claim_board
        run_restore
        ;;
esac
