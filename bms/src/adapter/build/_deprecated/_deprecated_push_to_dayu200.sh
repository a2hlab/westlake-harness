#!/bin/bash
# push_to_dayu200.sh — selective deploy of adapter/out/deploy_package/ to a
# DAYU200 device over hdc. Backup-aware, scope-aware, idempotent.
#
# Backup contract (per user spec 2026-04-12):
#   1. For each device-image file we are about to overwrite, FIRST check
#      whether a backup already exists at <path>.adapter_orig on the device.
#   2. If no backup exists, create it on the device BEFORE overwriting:
#         hdc shell cp /system/.../foo.so /system/.../foo.so.adapter_orig
#   3. Only after backup is confirmed (existing or just created), do the
#      hdc file send overwrite.
#   4. If the target file does NOT exist on the device (we are adding a new
#      file, not replacing one), no backup is needed — just push.
#
# Scope flags:
#   --file PATH        Push a single file (PATH = relative path under
#                      deploy_package/, e.g. system/lib/platformsdk/libbms.z.so).
#                      May be repeated. Positional args also accepted.
#   --dir  PATH        Push every file directly inside PATH (NON-recursive).
#                      Subdirectories are skipped. Use this for "just the
#                      .so files in system/android/lib/" without recursing.
#   --dir-r PATH       Push every file under PATH recursively. Use for
#                      "everything under system/android/framework/".
#   --all              Push every file in deploy_package/ (full flash).
#                      Excludes any *.adapter_orig and *.before_refresh_*
#                      backup files left behind by other scripts.
#
# Other flags:
#   --deploy=PATH      Override deploy package root (default: auto-detect
#                      from $ADAPTER_ROOT/out/deploy_package or relative to
#                      this script).
#   --device=SERIAL    Target a specific hdc device by serial.
#   --dry-run          Print every action that would be taken; do nothing.
#   --no-backup        Skip backup step entirely (DANGEROUS — only use when
#                      you've already verified backups exist).
#   --no-remount       Skip /system remount (assume the device already has
#                      /system mounted rw).
#   --verify           After each push, md5sum the device file and compare
#                      against the local file. Adds time but catches silent
#                      transfer failures.
#   -h, --help         Show this usage.
#
# Examples:
#   # Push the 6 critical Gap 1-6 files
#   push_to_dayu200.sh \
#       system/lib/platformsdk/libbms.z.so \
#       system/android/lib/libandroid_runtime.so \
#       system/android/lib/libhwui.so \
#       system/android/framework/framework.jar \
#       system/android/framework/arm/boot.oat \
#       system/android/framework/arm/boot.art \
#       system/bin/appspawn-x
#
#   # Push every Android-side native lib (non-recursive — only .so files
#   # directly under system/android/lib/, no subdirectories)
#   push_to_dayu200.sh --dir system/android/lib
#
#   # Push every framework jar/oat/dex under system/android/framework/ recursively
#   push_to_dayu200.sh --dir-r system/android/framework
#
#   # Full flash, dry-run first to see what would happen
#   push_to_dayu200.sh --all --dry-run
#   push_to_dayu200.sh --all
#
#   # Re-push libbms only, with md5 verification, but skip backup (already done)
#   push_to_dayu200.sh --verify --no-backup system/lib/platformsdk/libbms.z.so
set -e

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
ADAPTER_ROOT=${ADAPTER_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
DEPLOY=""
DEVICE=""
DRY_RUN=0
NO_BACKUP=0
NO_REMOUNT=0
VERIFY=0
ALL=0
DIR_ARGS=()        # paths from --dir
DIR_R_ARGS=()      # paths from --dir-r
FILE_ARGS=()       # paths from --file or positional

usage() {
    sed -n '/^# push_to_dayu200/,/^set -e/p' "$0" | sed 's/^# \{0,1\}//; /^set -e/d'
    exit 0
}

# ---------------------------------------------------------------------------
# Pass 1 — collect raw args. DEPLOY-relative expansion happens in Pass 2.
# ---------------------------------------------------------------------------
while [ $# -gt 0 ]; do
    case "$1" in
        --file)
            shift; FILE_ARGS+=("$1"); shift ;;
        --dir)
            shift; DIR_ARGS+=("$1"); shift ;;
        --dir-r)
            shift; DIR_R_ARGS+=("$1"); shift ;;
        --all)
            ALL=1; shift ;;
        --deploy=*)
            DEPLOY="${1#*=}"; shift ;;
        --device=*)
            DEVICE="${1#*=}"; shift ;;
        --dry-run)
            DRY_RUN=1; shift ;;
        --no-backup)
            NO_BACKUP=1; shift ;;
        --no-remount)
            NO_REMOUNT=1; shift ;;
        --verify)
            VERIFY=1; shift ;;
        -h|--help)
            usage ;;
        --*)
            echo "Unknown option: $1" >&2; exit 1 ;;
        *)
            FILE_ARGS+=("$1"); shift ;;
    esac
done

# Resolve DEPLOY default if not set explicitly
if [ -z "$DEPLOY" ]; then
    if [ -d "$ADAPTER_ROOT/out/deploy_package" ]; then
        DEPLOY="$ADAPTER_ROOT/out/deploy_package"
    else
        DEPLOY="$(cd "$(dirname "$0")/.." && pwd)/out/deploy_package"
    fi
fi

if [ ! -d "$DEPLOY" ]; then
    echo "ERROR: deploy package not found at $DEPLOY" >&2
    echo "       set ADAPTER_ROOT or pass --deploy=PATH" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Pass 2 — expand --dir / --dir-r / --all into the FILES list
# ---------------------------------------------------------------------------
FILES=()

# --file / positional args
for f in "${FILE_ARGS[@]}"; do
    FILES+=("$f")
done

# --dir PATH → every file directly inside PATH (no recursion, no backups)
for d in "${DIR_ARGS[@]}"; do
    if [ ! -d "$DEPLOY/$d" ]; then
        echo "ERROR: --dir target not found: $DEPLOY/$d" >&2
        exit 1
    fi
    while IFS= read -r f; do
        FILES+=("${f#$DEPLOY/}")
    done < <(find "$DEPLOY/$d" -mindepth 1 -maxdepth 1 -type f \
              ! -name "*.adapter_orig" \
              ! -name "*.before_refresh_*" 2>/dev/null | sort)
done

# --dir-r PATH → every file under PATH recursively
for d in "${DIR_R_ARGS[@]}"; do
    if [ ! -d "$DEPLOY/$d" ]; then
        echo "ERROR: --dir-r target not found: $DEPLOY/$d" >&2
        exit 1
    fi
    while IFS= read -r f; do
        FILES+=("${f#$DEPLOY/}")
    done < <(find "$DEPLOY/$d" -type f \
              ! -name "*.adapter_orig" \
              ! -name "*.before_refresh_*" 2>/dev/null | sort)
done

# --all → every file in DEPLOY (excluding backups + manifest)
if [ "$ALL" = "1" ]; then
    while IFS= read -r f; do
        FILES+=("${f#$DEPLOY/}")
    done < <(find "$DEPLOY" -type f \
              ! -name "*.adapter_orig" \
              ! -name "*.before_refresh_*" \
              ! -name "manifest.txt" 2>/dev/null | sort)
fi

if [ ${#FILES[@]} -eq 0 ]; then
    echo "ERROR: no files specified. Use --file/--dir/--dir-r/--all or pass paths positionally." >&2
    echo "       run with -h for usage." >&2
    exit 1
fi

# Deduplicate FILES, preserving order
mapfile -t FILES < <(printf '%s\n' "${FILES[@]}" | awk '!seen[$0]++')

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
log_info()  { printf '\033[36m[push]\033[0m %s\n' "$*"; }
log_ok()    { printf '\033[32m[push] OK  \033[0m %s\n' "$*"; }
log_warn()  { printf '\033[33m[push] WARN\033[0m %s\n' "$*" >&2; }
log_err()   { printf '\033[31m[push] ERR \033[0m %s\n' "$*" >&2; }
log_dry()   { printf '\033[35m[push] DRY \033[0m %s\n' "$*"; }

# ---------------------------------------------------------------------------
# hdc helpers
# ---------------------------------------------------------------------------
HDC=hdc
HDC_TARGET=""
[ -n "$DEVICE" ] && HDC_TARGET="-t $DEVICE"

hdc_shell() {
    # Wrap hdc shell so we can capture stdout cleanly. hdc on Windows
    # may add CR; strip it.
    $HDC $HDC_TARGET shell "$@" 2>&1 | tr -d '\r'
}

hdc_send() {
    local local_path="$1" remote_path="$2"
    $HDC $HDC_TARGET file send "$local_path" "$remote_path" 2>&1 | tr -d '\r'
}

# device_file_exists — does the device have this absolute path?
device_file_exists() {
    local p="$1"
    local out
    out=$(hdc_shell "test -f \"$p\" && echo Y || echo N")
    [ "$(echo "$out" | tail -1)" = "Y" ]
}

# device_md5 — md5sum on device, returns just the hash (or empty on failure)
device_md5() {
    local p="$1"
    hdc_shell "md5sum \"$p\" 2>/dev/null" | awk '{print $1}' | head -1
}

# local_md5 — md5sum on host
local_md5() {
    md5sum "$1" 2>/dev/null | awk '{print $1}'
}

# ---------------------------------------------------------------------------
# Pre-flight: hdc connectivity + remount
# ---------------------------------------------------------------------------
preflight() {
    log_info "Pre-flight: hdc list targets"
    local list_out
    list_out=$($HDC list targets 2>&1 | tr -d '\r')
    if echo "$list_out" | grep -q '\[Empty\]'; then
        log_err "no hdc devices connected — connect DAYU200 and retry"
        exit 1
    fi
    log_info "hdc targets: $(echo "$list_out" | head -3 | tr '\n' ' ')"

    if [ "$NO_REMOUNT" = "0" ]; then
        log_info "remount /system rw (mount -o remount,rw /system)"
        if [ "$DRY_RUN" = "0" ]; then
            local rmnt
            rmnt=$(hdc_shell "mount -o remount,rw /system && echo OK || echo FAIL")
            if echo "$rmnt" | grep -q OK; then
                log_ok "/system mounted rw"
            else
                log_warn "remount /system failed (output: $rmnt)"
                log_warn "  if device requires mount on /, also try: hdc shell mount -o remount,rw /"
                log_warn "  proceeding anyway — pushes will fail if /system is RO"
            fi
        else
            log_dry "hdc shell mount -o remount,rw /system"
        fi
    fi
}

# ---------------------------------------------------------------------------
# Per-file deploy: backup → push → optional verify
# ---------------------------------------------------------------------------
deploy_one() {
    local rel_path="$1"           # e.g. system/lib/platformsdk/libbms.z.so
    local local_path="$DEPLOY/$rel_path"
    local device_path="/$rel_path"

    if [ ! -f "$local_path" ]; then
        log_err "$rel_path: local file not found at $local_path"
        return 1
    fi

    # ---- Step 1: backup (if device file exists and --no-backup not set) ----
    if [ "$NO_BACKUP" = "0" ]; then
        if [ "$DRY_RUN" = "1" ]; then
            log_dry "check device: test -f $device_path"
            log_dry "if exists: cp $device_path ${device_path}.adapter_orig (only if backup absent)"
        elif device_file_exists "$device_path"; then
            local backup_path="${device_path}.adapter_orig"
            if device_file_exists "$backup_path"; then
                log_info "$rel_path: backup already exists at $backup_path"
            else
                log_info "$rel_path: creating backup at $backup_path"
                local cpout
                cpout=$(hdc_shell "cp \"$device_path\" \"$backup_path\" && echo OK || echo FAIL")
                if ! echo "$cpout" | grep -q OK; then
                    log_err "$rel_path: backup failed (output: $cpout)"
                    return 1
                fi
                if ! device_file_exists "$backup_path"; then
                    log_err "$rel_path: backup file not visible after cp — abort, refusing to overwrite"
                    return 1
                fi
                log_ok "$rel_path: backup created"
            fi
        else
            log_info "$rel_path: device file does not exist (new addition, no backup needed)"
        fi
    fi

    # ---- Step 2: ensure parent directory exists on device ----
    local device_dir
    device_dir=$(dirname "$device_path")
    if [ "$DRY_RUN" = "1" ]; then
        log_dry "hdc shell mkdir -p $device_dir"
    else
        hdc_shell "mkdir -p $device_dir" >/dev/null
    fi

    # ---- Step 3: push ----
    local size
    size=$(stat -c%s "$local_path" 2>/dev/null || echo "?")
    log_info "$rel_path: push ($size bytes)"
    if [ "$DRY_RUN" = "1" ]; then
        log_dry "hdc file send $local_path $device_path"
    else
        local sendout
        sendout=$(hdc_send "$local_path" "$device_path" 2>&1)
        if echo "$sendout" | grep -qiE "fail|error"; then
            log_err "$rel_path: push failed: $sendout"
            return 1
        fi
    fi

    # ---- Step 4: optional md5 verify ----
    if [ "$VERIFY" = "1" ] && [ "$DRY_RUN" = "0" ]; then
        local lh dh
        lh=$(local_md5 "$local_path")
        dh=$(device_md5 "$device_path")
        if [ "$lh" = "$dh" ] && [ -n "$lh" ]; then
            log_ok "$rel_path: md5 OK [$lh]"
        else
            log_err "$rel_path: md5 MISMATCH local=$lh device=$dh"
            return 1
        fi
    fi

    # ---- Step 5: post-push fixes for known files ----
    case "$rel_path" in
        system/bin/*)
            if [ "$DRY_RUN" = "1" ]; then
                log_dry "hdc shell chmod 755 $device_path"
            else
                hdc_shell "chmod 755 $device_path" >/dev/null
            fi
            log_ok "$rel_path: chmod 755 (executable)"
            ;;
        system/etc/init/*)
            if [ "$DRY_RUN" = "1" ]; then
                log_dry "hdc shell chmod 644 $device_path"
            else
                hdc_shell "chmod 644 $device_path" >/dev/null
            fi
            ;;
        *)
            ;;
    esac

    log_ok "$rel_path: deployed"
    return 0
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
echo "============================================================"
echo "  push_to_dayu200.sh"
echo "============================================================"
echo "  DEPLOY:    $DEPLOY"
echo "  DEVICE:    ${DEVICE:-<default>}"
echo "  FILES:     ${#FILES[@]} entries"
[ "$DRY_RUN"    = "1" ] && echo "  DRY_RUN:    yes"
[ "$NO_BACKUP"  = "1" ] && echo "  NO_BACKUP:  yes (DANGEROUS)"
[ "$NO_REMOUNT" = "1" ] && echo "  NO_REMOUNT: yes"
[ "$VERIFY"     = "1" ] && echo "  VERIFY:     md5 each push"
echo

preflight
echo

OK_COUNT=0
FAIL_COUNT=0
FAILED=()
# Disable set -e for the loop so a single failure doesn't kill the whole batch.
set +e
for rel in "${FILES[@]}"; do
    if deploy_one "$rel"; then
        OK_COUNT=$((OK_COUNT+1))
    else
        FAIL_COUNT=$((FAIL_COUNT+1))
        FAILED+=("$rel")
    fi
    echo
done
set -e

echo "============================================================"
echo "  Summary"
echo "============================================================"
echo "  Total:    ${#FILES[@]}"
echo "  OK:       $OK_COUNT"
echo "  Failed:   $FAIL_COUNT"
if [ $FAIL_COUNT -gt 0 ]; then
    echo "  Failed files:"
    for f in "${FAILED[@]}"; do echo "    - $f"; done
    exit 1
fi
echo "  EXIT 0"
exit 0
