#!/system/bin/sh
# Parent guard copied verbatim from accepted R1 9763171a. No signal path.
RB_PROC=/proc; RB_RUNTIME=$AUTH_RUNTIME; RB_OWNER_UID=$AUTH_UID; PROC=/proc; RUNTIME=$AUTH_RUNTIME
. "$HERE/route-b-owner.sh"
private_namespace() {
 mine=$(readlink "$PROC/$1/ns/mnt" 2>/dev/null) || return 1
 init=$(readlink "$PROC/1/ns/mnt" 2>/dev/null) || return 1
 [ -n "$mine" ] && [ "$mine" != "$init" ]
}
parent_owned() {
 p=$1; expected=$2
 [ "$(rb_birth "$p")" = "$expected" ] || return 1
 exe=$(readlink "$PROC/$p/exe" 2>/dev/null) || return 1
 case "$exe" in /data/local/tmp/asx/asx-spawner|'/data/local/tmp/asx/asx-spawner (deleted)') :;; *) return 1;; esac
 # Read-only parent acceptance; this role NEVER receives a signal.
 uid=$(rb_uid "$p") || return 1
 case "$uid" in 0:0:0:0|"$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID") :;; *) return 1;; esac
 [ "$(sha256sum "$PROC/$p/exe" 2>/dev/null | cut -d' ' -f1)" = "$RB_SPAWNER_SHA" ] || return 1
 physical=$(stat -L -c '%d:%i' "$RUNTIME/run.sh" 2>/dev/null) || return 1
 view=$(stat -L -c '%d:%i' "$PROC/$p/root/data/local/tmp/asx/run.sh" 2>/dev/null) || return 1
 [ -n "$physical" ] && [ "$physical" = "$view" ] || return 1
 private_namespace "$p" || return 1
 [ "$(rb_birth "$p")" = "$expected" ]
}
# Existing parent reuse must be tied to the CURRENT foreground host window.
foreground_window_id() {
 window_dump=$(timeout 2 hidumper -s WindowManagerService -a '-a' 2>/dev/null) || return 1
 window_row=$(printf '%s\n' "$window_dump" | grep '^imehost0[[:space:]]') || return 1
 [ "$(printf '%s\n' "$window_row" | wc -l)" -eq 1 ] || return 1
 set -- $window_row
 case "${4:-}" in ''|*[!0-9]*) return 1;; esac
 case "${8:--1}" in ''|-*|*[!0-9]*) return 1;; esac
 printf '%s\n' "$4"
}
verify_parent_window() {
 parent_owned "$1" "$2" || fail PARENT_BEFORE_ENV_CHANGED
 foreground_id=$(foreground_window_id) || fail FOREGROUND_HOST_NOT_READY
 # Board-side strings is actually proven available. Do not host-filter NUL HDC.
 fields=$(timeout 2 strings "$PROC/$1/environ") || fail ENVIRON_READER_FAILED
 wid_lines=$(printf '%s\n' "$fields" | grep -E '^WL_PARENT_ID=[0-9]+$') || fail PARENT_WINDOW_UNVERIFIABLE
 uid_lines=$(printf '%s\n' "$fields" | grep -E '^ASX_RUNTIME_OWNER_UID=[0-9]+$') || fail PARENT_UID_UNVERIFIABLE
 [ "$(printf '%s\n' "$wid_lines" | wc -l)" -eq 1 ] || fail DUPLICATE_WINDOW_FIELD
 [ "$(printf '%s\n' "$uid_lines" | wc -l)" -eq 1 ] || fail DUPLICATE_UID_FIELD
 [ "${wid_lines#WL_PARENT_ID=}" = "$foreground_id" ] || fail PARENT_WINDOW_CHANGED
 [ "${uid_lines#ASX_RUNTIME_OWNER_UID=}" = "$AUTH_UID" ] || fail PARENT_RUNTIME_UID_CHANGED
 parent_owned "$1" "$2" || fail PARENT_AFTER_ENV_CHANGED
}
