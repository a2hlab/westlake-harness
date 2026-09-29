#!/bin/bash
# swap_installer.sh — replace libapk_installer.so on a board, safely.
#
# Encodes the #42/#55 hard-won sequence:
#   backup both paths -> swap -> restart foundation -> screenshot black-check
#   (36627 B sentinel) -> on black: full reboot -> reproduce.sh check ->
#   (on check fail: restore + B5 JAR redeploy hint) -> verify hash under
#   /proc/<foundation pid>/root for BOTH paths -> final non-black desktop
#   screenshot (rule written in RESULTS-KIT-BUILD.md, #42).
#
# Usage:
#   swap_installer.sh <serial> <installer.so> [--rollback] [--dry-run]
#     --rollback  restore the backup taken before the swap (or the most
#                 recent backup dir) instead of installing a new library
#     --dry-run   print every step with resolved paths, touch nothing
#
# Exit codes: 0 ok, 1 usage, 2 transport/hash failure, 3 screen stayed black.
set -uo pipefail

SERIAL="${1:-}"; INSTALLER="${2:-}"; MODE="${3:-}"
HDC="${HDC:-/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh}"
# hdc_mac.sh is a wrapper that must run inside the a2hlab VM (orb)
VM_RUNNER="${VM_RUNNER:-orb -m a2hlab bash -c}"
CHECK_SCRIPT="${CHECK_SCRIPT:-/Users/zhaoyue/orca/workspaces/westlake-bms-suite/.agents/skills/reproduce-helloworld/scripts/reproduce.sh}"
PATHS=("/system/lib64/libapk_installer.so" "/system/lib64/platformsdk/libapk_installer.so")
BACKUP_ROOT="/data/local/tmp/installer-backups"
BLACK_SIZE=36627

say()  { printf '[swap_installer] %s\n' "$*"; }
die()  { printf '[swap_installer] FAIL(%s): %s\n' "$1" "$2" >&2; exit "$1"; }

if [ -z "$SERIAL" ] || [ -z "$INSTALLER" ] && [ "$MODE" != "--rollback" ]; then
    echo "usage: $0 <serial> <installer.so> [--rollback|--dry-run]" >&2
    exit 1
fi
DRY=0; ROLLBACK=0
for a in "${@:3}"; do
    case "$a" in
        --dry-run)  DRY=1 ;;
        --rollback) ROLLBACK=1 ;;
        *) echo "unknown flag: $a" >&2; exit 1 ;;
    esac
done

h() { $VM_RUNNER "'$HDC' -t '$SERIAL' shell '$1'" 2>/dev/null; }

# ---- 0. board alive + current hashes ----
say "board $SERIAL: current installer hashes"
CUR=$(h "sha256sum ${PATHS[0]} ${PATHS[1]}")
[ -n "$CUR" ] || die 2 "cannot read current hashes (board alive?)"
printf '%s\n' "$CUR" | sed 's/^/    /'

STAMP=$(date +%Y%m%dT%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$STAMP"

# ---- 1. backup both paths ----
say "backup -> $BACKUP_DIR"
if [ "$DRY" = 1 ]; then
    echo "    (dry-run) h: mkdir -p $BACKUP_DIR && cp ${PATHS[0]} ${PATHS[1]} -> $BACKUP_DIR/"
else
    h "mkdir -p $BACKUP_DIR" >/dev/null
    for p in "${PATHS[@]}"; do
        h "cp $p $BACKUP_DIR/$(basename "$(dirname "$p")").so" >/dev/null \
            || die 2 "backup failed for $p"
    done
fi

if [ "$ROLLBACK" = 1 ]; then
    SRC_DIR="${BACKUP_DIR}"
    [ -n "$(h "ls $SRC_DIR 2>/dev/null")" ] || SRC_DIR=$(h "ls -t $BACKUP_ROOT | head -1" | tr -d '\r')
    SRC_DIR="$BACKUP_ROOT/$SRC_DIR"
    say "rollback from $SRC_DIR"
fi

# ---- 2. swap ----
if [ "$ROLLBACK" = 1 ]; then
    say "swap: rollback (lib64 <- $SRC_DIR/lib64.so, platformsdk <- $SRC_DIR/platformsdk.so)"
    [ "$DRY" = 1 ] || {
        h "mount -o rw,remount /"
        h "cp $SRC_DIR/lib64.so ${PATHS[0]}"     >/dev/null || die 2 "rollback cp failed (${PATHS[0]})"
        h "cp $SRC_DIR/platformsdk.so ${PATHS[1]}" >/dev/null || die 2 "rollback cp failed (${PATHS[1]}"
        h "chmod 0755 ${PATHS[0]} ${PATHS[1]}"; h "chown root:root ${PATHS[0]} ${PATHS[1]}"
        h "mount -o ro,remount /"
    }
else
    say "send $INSTALLER -> /data/local/tmp/installer-new.so"
    [ "$DRY" = 1 ] || $VM_RUNNER "'$HDC' -t '$SERIAL' file send '$INSTALLER' /data/local/tmp/installer-new.so" >/dev/null 2>&1 \
        || die 2 "file send failed"
    say "swap both paths (rw remount -> cp -> perms -> ro remount)"
    [ "$DRY" = 1 ] || {
        h "mount -o rw,remount /"
        for p in "${PATHS[@]}"; do
            h "cp /data/local/tmp/installer-new.so $p" >/dev/null || die 2 "cp failed ($p)"
        done
        h "chmod 0755 ${PATHS[0]} ${PATHS[1]}"; h "chown root:root ${PATHS[0]} ${PATHS[1]}"
        h "mount -o ro,remount /"
    }
fi

# ---- 3. restart foundation ----
say "restart foundation"
[ "$DRY" = 1 ] || {
    h "begetctl stop_service foundation" >/dev/null 2>&1; sleep 3
    h "begetctl start_service foundation" >/dev/null 2>&1; sleep 6
}
FP=$(h "pgrep -f foundation | head -1" | tr -d '\r')
say "foundation pid: $FP"
[ -n "$FP" ] || die 2 "foundation not running after restart"

# ---- 4. verify hash under /proc/<pid>/root for both paths ----
say "hash check under /proc/$FP/root"
if [ "$DRY" = 0 ]; then
    WANT=$( [ "$ROLLBACK" = 1 ] && echo "(backup sha)" || shasum -a 256 "$INSTALLER" | awk '{print $1}' )
    [ "$ROLLBACK" = 1 ] || [ -n "$WANT" ] || die 2 "cannot hash local installer"
    OK=0
    for p in "${PATHS[@]}"; do
        GOT=$(h "sha256sum /proc/$FP/root$p" | awk '{print $1}' | tr -d '\r')
        say "    $p -> ${GOT:0:16}"
        if [ "$ROLLBACK" = 0 ] && [ "$GOT" != "$WANT" ]; then die 2 "hash mismatch at $p (want ${WANT:0:16})"; fi
    done
else
    for p in "${PATHS[@]}"; do say "    (dry-run) sha256sum /proc/$FP/root$p"; done
fi

# ---- 5. black-screen check (36627 B sentinel) ----
say "screen check (black sentinel = ${BLACK_SIZE} B)"
RAW=$(h "power-shell wakeup >/dev/null 2>&1; sleep 2; snapshot_display -f /data/local/tmp/swap-check.jpeg >/dev/null 2>&1; stat -c %s /data/local/tmp/swap-check.jpeg" | tr -d '\r')
SIZE=$(printf '%s\n' "$RAW" | grep -E '^[0-9]+$' | tail -1)
say "    screenshot size: ${SIZE:-none}"
BLACK_WAS=0
if [ "${SIZE:-0}" = "$BLACK_SIZE" ]; then
    BLACK_WAS=1
    say "    BLACK — full reboot per playbook"
    [ "$DRY" = 1 ] || {
        h "reboot" >/dev/null 2>&1
        for i in $(seq 1 12); do sleep 10; $VM_RUNNER "'$HDC' list targets" 2>/dev/null | grep -q "$SERIAL" && break; done
        sleep 40
        h "power-shell wakeup" >/dev/null 2>&1; sleep 3
        FP=$(h "pgrep -f foundation | head -1" | tr -d '\r'); say "    foundation after reboot: $FP"
        SIZE=$(h "snapshot_display -f /data/local/tmp/swap-check2.jpeg >/dev/null 2>&1; stat -c %s /data/local/tmp/swap-check2.jpeg" | tr -d '\r' | grep -E '^[0-9]+$' | tail -1)
        say "    post-reboot screenshot size: ${SIZE:-none}"
        [ "${SIZE:-0}" != "$BLACK_SIZE" ] || die 3 "screen still black after reboot"
    }
fi

# ---- 6. reproduce.sh check (only after the black/reboot path per #55 playbook) ----
if [ "${BLACK_WAS:-0}" = 1 ] && [ "$DRY" = 0 ]; then
    say "post-reboot reproduce.sh check"
    if ! bash "$CHECK_SCRIPT" check "$SERIAL" 2>&1 | grep -q "REPRODUCE_HELLOWORLD_CHECK=PASS"; then
        say "    check FAILED — restore required per playbook:"
        say "      bash $CHECK_SCRIPT restore $SERIAL   (then redeploy the B5 JAR overlay)"
        die 3 "reproduce check failed after reboot"
    fi
    say "    check PASS"
fi
if [ "$DRY" = 1 ]; then
    say "(dry-run) would run: $CHECK_SCRIPT check $SERIAL  (only after reboot path)"
else
    say "final desktop screenshot"
    h "snapshot_display -f /data/local/tmp/swap-desk.jpeg" >/dev/null 2>&1
    D=$(h "stat -c %s /data/local/tmp/swap-desk.jpeg" | tr -d '\r' | grep -E '^[0-9]+$' | tail -1)
    say "    desktop jpeg: ${D:-none} B (must NOT be ${BLACK_SIZE})"
    [ "${D:-0}" != "$BLACK_SIZE" ] || die 3 "final desktop screenshot is black"
fi
say "DONE"
