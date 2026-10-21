#!/system/bin/sh
# PURE READ-ONLY worker. Caller MUST wrap the whole worker in timeout2.
# Never sources an old overlay, signals a process, launches or changes data.
set -u
command -v od >/dev/null || { printf '{"field":"audit_tool","actual":"missing_od","expected":"od"}\n' >&2; exit 5; }
HERE=$(dirname "$0")
PROC=/proc
RUNTIME=${TT_RUNTIME:-/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d}
RB_PROC=$PROC; RB_RUNTIME=$RUNTIME; RB_OWNER_UID=${TT_OWNER_UID:-}
. "$HERE/route-b-owner.sh"
child_pid=${1:-}; child_birth=${2:-}; parent=${3:-}; parent_birth=${4:-}
expected_boot=${5:-}; guardian=${6:-}; guardian_birth=${7:-}
RB_AUDIT_PHASE=readiness; RB_AUDIT_PID=$child_pid; RB_AUDIT_BIRTH=$child_birth
reject(){ rb_guard_json "$1" "$2" "$3" || exit 5; exit 2; }
for numeric in "$child_pid" "$child_birth" "$parent" "$parent_birth" "$guardian" "$guardian_birth" "$RB_OWNER_UID"; do
 case "$numeric" in ''|0|*[!0-9]*) reject arguments invalid positive_integer;; esac
done
[ "$child_pid" != "$parent" ] && [ "$child_pid" != 1 ] || reject pid "$child_pid" new_child_only
private_namespace() {
 mine=$(readlink "$PROC/$1/ns/mnt" 2>/dev/null) || return 1
 init=$(readlink "$PROC/1/ns/mnt" 2>/dev/null) || return 1
 [ -n "$mine" ] && [ "$mine" != "$init" ]
}
parent_owned() {
 p=$1; expected=$2
 [ "$(rb_birth "$p")" = "$expected" ] || return 1
 exe=$(readlink "$PROC/$p/exe" 2>/dev/null) || return 1
 case "$exe" in /data/local/tmp/asx/asx-spawner|'/data/local/tmp/asx/asx-spawner (deleted)'|/data/local/tmp/asx/appspawn-x|'/data/local/tmp/asx/appspawn-x (deleted)') :;; *) return 1;; esac
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
context_guard(){
 actual_boot=$(cat "$PROC/sys/kernel/random/boot_id") || reject boot '<read-error>' "$expected_boot"
 [ "$actual_boot" = "$expected_boot" ] || reject boot "$actual_boot" "$expected_boot"
 [ ! -e "$HERE/stop" ] && [ ! -L "$HERE/stop" ] || reject stop present absent
 case "$HERE" in */boots/*) root=${HERE%/boots/*}; [ ! -e "$root/stop" ] && [ ! -L "$root/stop" ] || reject candidate_stop present absent;; esac
 [ -f "$HERE/lock/owner" ] && [ ! -L "$HERE/lock/owner" ] || reject lock '<unreadable-or-symlink>' exact_owner
 owner=$(cat "$HERE/lock/owner") || reject lock '<read-error>' exact_owner
 [ "$owner" = "$guardian $guardian_birth $expected_boot" ] || reject lock "$owner" "$guardian $guardian_birth $expected_boot"
 size=$(wc -c < "$HERE/lock/owner") || reject lock_size '<read-error>' exact_bytes
 required=$(printf '%s %s %s\n' "$guardian" "$guardian_birth" "$expected_boot" | wc -c)
 [ "$size" -eq "$required" ] || reject lock_size "$size" "$required"
 actual_guardian=$(rb_birth "$guardian") || reject guardian_birth '<read-error-or-exited>' "$guardian_birth"
 [ "$actual_guardian" = "$guardian_birth" ] || reject guardian_birth "$actual_guardian" "$guardian_birth"
 parent_owned "$parent" "$parent_birth" 2>/dev/null || reject parent_guard nonzero original_complete_parent_guard
}
round=0
while [ "$round" -lt 20 ]; do
 context_guard
 before=$(rb_birth "$child_pid" 2>/dev/null) || reject birth '<read-error-or-exited>' "$child_birth"
 [ "$before" = "$child_birth" ] || reject birth "$before" "$child_birth"
 child_uid=$(rb_uid "$child_pid" 2>/dev/null) || reject uid '<read-error>' "$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID"
 exe=$(readlink "$PROC/$child_pid/exe" 2>/dev/null) || reject exe '<read-error>' exact_route_b_alias
 case "$exe" in /data/local/tmp/asx/asx-spawner|'/data/local/tmp/asx/asx-spawner (deleted)'|/data/local/tmp/asx/appspawn-x|'/data/local/tmp/asx/appspawn-x (deleted)') :;; *) reject exe "$exe" exact_route_b_alias;; esac
 exe_sha=$(sha256sum "$PROC/$child_pid/exe" 2>/dev/null | cut -d' ' -f1)
 [ "$exe_sha" = "$RB_SPAWNER_SHA" ] || reject exe_sha "$exe_sha" "$RB_SPAWNER_SHA"
 ns=$(readlink "$PROC/$child_pid/ns/mnt" 2>/dev/null) || reject namespace '<read-error>' private
 init_ns=$(readlink "$PROC/1/ns/mnt" 2>/dev/null) || reject init_namespace '<read-error>' readable
 [ -n "$ns" ] && [ "$ns" != "$init_ns" ] || reject namespace "$ns" "not:$init_ns"
 physical=$(stat -L -c '%d:%i' "$RUNTIME/run.sh" 2>/dev/null) || reject physical_inode '<read-error>' readable
 view=$(stat -L -c '%d:%i' "$PROC/$child_pid/root/data/local/tmp/asx/run.sh" 2>/dev/null) || reject private_inode '<read-error>' "$physical"
 [ -n "$physical" ] && [ "$view" = "$physical" ] || reject private_inode "$view" "$physical"
 statrow=$(cat "$PROC/$child_pid/stat") || reject ppid '<read-error>' "$parent"
 rest=${statrow##*) }; set -- $rest
 [ "${2:-none}" = "$parent" ] || reject ppid "${2:-none}" "$parent"
 after=$(rb_birth "$child_pid" 2>/dev/null) || reject birth_after '<read-error-or-exited>' "$child_birth"
 [ "$after" = "$child_birth" ] || reject birth_after "$after" "$child_birth"
 context_guard
 case "$child_uid" in
  "$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID")
   # Success must leave the 2-second envelope without diagnostic subprocesses.
   # The caller still runs the final original complete child_owned guard.
   exit 0;;
  0:0:0:0)
   RB_AUDIT_PHASE=readiness_pending
   rb_guard_json uid "$child_uid" "$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID" || exit 5
   RB_AUDIT_PHASE=readiness
   round=$((round+1))
   [ "$round" -lt 20 ] || reject readiness_timeout root_uid_never_ready within_2_seconds
   sleep .1;;
  *) reject uid "$child_uid" "$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID";;
 esac
done
reject readiness_timeout root_uid_never_ready within_2_seconds
