#!/system/bin/sh
# Narrow discovery/signal guard for the existing Route B watchdog, not a new supervisor.
# No comm/name selection. PID/birth + UID + executable SHA + private root inode.
# Defaults are the exact #91 Route B paths; RB_PROC/RB_RUNTIME are fixture seams.
# #91 cc-wiki 2026-10-10: the owned-child uid is now DYNAMIC (RB_OWNER_UID, read from the installed
# host) instead of the hardcoded 20010053, so the self-heal guard still matches the Route B child
# after OpenHarmony assigns imehost a different uid. Everything else is the master cfab66ae8c logic.
# NOTE (board compat): rb_script_signal still uses `tr` (inherited from master); the OH board rootfs
# may lack tr in some domains — cx-bms to confirm in the su domain or swap for a NUL-safe read.
RB_PROC=${RB_PROC:-/proc}
RB_RUNTIME=${RB_RUNTIME:-/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d}
RB_SPAWNER_SHA=a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c
RB_OWNER_UID=${RB_OWNER_UID:-$(stat -c %u /data/app/el2/100/base/org.westlake.imehost 2>/dev/null)}
rb_birth(){
 case "$1" in ''|*[!0-9]*) return 1;; esac
 [ -r "$RB_PROC/$1/stat" ] || return 1
 v=$(cat "$RB_PROC/$1/stat"); rest=${v##*) }; set -- $rest
 [ "$1" != Z ] || return 1
 shift 19; echo "$1"
}
rb_uid(){
 while read -r label real effective saved fs; do
  [ "$label" = Uid: ] && { echo "$real:$effective:$saved:$fs"; return 0; }
 done < "$RB_PROC/$1/status"
 return 1
}
# ASCII/byte-safe JSON strings using the board-proven od tool; no tr/awk.
rb_json_bytes(){
 bytes=$(printf '%s' "$1" | od -An -v -tx1) || return 5
 for h in $bytes; do printf '\\u00%s' "$h" || return 5; done
}
rb_guard_json(){
 printf '{"phase":"%s","pid":"%s","birth":"%s","field":"%s","actual":"%s","expected":"%s"}\n' \
  "$(rb_json_bytes "${RB_AUDIT_PHASE:-strict}")" "$(rb_json_bytes "${RB_AUDIT_PID:-${p:-unknown}}")" "$(rb_json_bytes "${RB_AUDIT_BIRTH:-unknown}")" \
  "$(rb_json_bytes "$1")" "$(rb_json_bytes "$2")" "$(rb_json_bytes "$3")" >&2
}
rb_deny(){
 # Discovery-only subshell sets this flag. Reject identically without encoding.
 [ "${RB_AUDIT_QUIET:-0}" = 1 ] && return 1
 rb_guard_json "$1" "$2" "$3" || return 5; return 1
}
rb_owned(){
 p=$1; b=$(rb_birth "$p") || { rb_deny birth '<read-error-or-exited>' live; return 1; }
 uid=$(rb_uid "$p" 2>/dev/null) || { rb_deny uid '<read-error>' "$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID"; return 1; }
 [ "$uid" = "$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID" ] || { rb_deny uid "$uid" "$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID"; return 1; }
 exe=$(readlink "$RB_PROC/$p/exe" 2>/dev/null) || { rb_deny exe '<read-error>' exact_route_b_alias; return 1; }
 case "$exe" in /data/local/tmp/asx/asx-spawner|'/data/local/tmp/asx/asx-spawner (deleted)'|/data/local/tmp/asx/appspawn-x|'/data/local/tmp/asx/appspawn-x (deleted)') :;; *) rb_deny exe "$exe" exact_route_b_alias; return 1;; esac
 actual_sha=$(sha256sum "$RB_PROC/$p/exe" 2>/dev/null | cut -d' ' -f1)
 [ "$actual_sha" = "$RB_SPAWNER_SHA" ] || { rb_deny exe_sha "$actual_sha" "$RB_SPAWNER_SHA"; return 1; }
 own=$(stat -L -c '%d:%i' "$RB_RUNTIME/run.sh" 2>/dev/null) || { rb_deny physical_inode '<read-error>' readable; return 1; }
 view=$(stat -L -c '%d:%i' "$RB_PROC/$p/root/data/local/tmp/asx/run.sh" 2>/dev/null) || { rb_deny private_inode '<read-error>' "$own"; return 1; }
 [ -n "$own" ] && [ "$view" = "$own" ] || { rb_deny private_inode "$view" "$own"; return 1; }
 last_birth=$(rb_birth "$p") || { rb_deny birth_after '<read-error-or-exited>' "$b"; return 1; }
 [ "$last_birth" = "$b" ] || { rb_deny birth_after "$last_birth" "$b"; return 1; }
}
rb_owned_pids(){
 for row in "$RB_PROC"/[0-9]*; do
  [ -d "$row" ] || continue
  p=${row##*/}
  ( RB_AUDIT_QUIET=1; rb_owned "$p" ) && echo "$p"
 done
}
rb_signal(){
 p=$1; expected=$2; signal=$3
 [ -n "$expected" ] && [ "$(rb_birth "$p")" = "$expected" ] || return 1
 rb_owned "$p" || return 1
 [ "$(rb_birth "$p")" = "$expected" ] || return 1
 kill "-$signal" "$p"
}
# Supervisor/keeper: use the recorded PID+birth and exact script argument; never pidof.
rb_script_signal(){
 p=$1; expected=$2; script=$3
 [ -n "$expected" ] && [ "$(rb_birth "$p")" = "$expected" ] || return 1
 [ "$(rb_uid "$p")" = 0:0:0:0 ] || return 1
 [ "$(readlink "$RB_PROC/$p/exe" 2>/dev/null)" = /system/bin/sh ] || return 1
 tr '\000' '\n' < "$RB_PROC/$p/cmdline" | grep -Fxq "$script" || return 1
 [ "$(rb_birth "$p")" = "$expected" ] || return 1
 kill -15 "$p"
}
