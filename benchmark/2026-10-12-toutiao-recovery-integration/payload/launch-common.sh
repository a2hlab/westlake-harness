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
 window_row=$(hidumper -s WindowManagerService -a '-a' 2>/dev/null | grep '^imehost0[[:space:]]' | head -1)
 set -- $window_row
 case "${4:-}" in ''|*[!0-9]*) return 1;; esac
 case "${8:--1}" in ''|-*|*[!0-9]*) return 1;; esac
 printf '%s\n' "$4"
}
verify_parent_window() {
 foreground_id=$(foreground_window_id) || fail FOREGROUND_HOST_NOT_READY
 parent_window=$(grep -ao 'WL_PARENT_ID=[0-9]*' "$PROC/$1/environ" | head -1) || fail PARENT_WINDOW_UNVERIFIABLE
 [ "$parent_window" = "WL_PARENT_ID=$foreground_id" ] || fail PARENT_WINDOW_CHANGED
}
