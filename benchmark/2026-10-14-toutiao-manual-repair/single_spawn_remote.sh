#!/system/bin/sh
# Source this body only through pinned render_owner.py commands under outer's lock.
set -eu
fail() { printf 'OWNER_REFUSE %s\n' "$*" >&2; exit 2; }
[ "$#" = 5 ] || fail arguments
action=$1; boot=$2; parent=$3; birth=$4; expected=$5
R=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d
T=$R/app-data/com.ss.android.article.news
V=/proc/$parent/root/data/data/com.ss.android.article.news
SPAWNER=a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c
case "$action" in preflight|apply|rollback|reconcile) :;; *) fail action;; esac
case "$parent:$birth" in *[!0-9:]*|:*) fail identity_arguments;; esac
meta() { stat -c '%d:%i|%u:%g|%a|%C' "$T"; }
identity() {
 [ "$(cat /proc/sys/kernel/random/boot_id)" = "$boot" ] || fail boot
 row=$(cat "/proc/$parent/stat") || fail parent_stat
 rest=${row##*) }; set -- $rest
 [ "$#" -ge 20 ] && [ "$1" != Z ] || fail parent_state
 shift 19
 [ "$1" = "$birth" ] || fail parent_birth
 [ "$(sha256sum /proc/$parent/exe | cut -d' ' -f1)" = "$SPAWNER" ] || fail parent_binary
 [ "$(stat -c %u /data/app/el2/100/base/org.westlake.imehost)" = 20011300 ] || fail host_uid
 ns=$(readlink /proc/$parent/ns/mnt) || fail namespace_read
 init=$(readlink /proc/1/ns/mnt) || fail init_namespace_read
 [ -n "$ns" ] && [ "$ns" != "$init" ] || fail namespace
 for p in /data /data/app /data/app/el2 /data/app/el2/100 /data/app/el2/100/base /data/app/el2/100/base/org.westlake.imehost /data/app/el2/100/base/org.westlake.imehost/files "$R" "$R/app-data" "$T"; do
  [ -d "$p" ] && [ ! -L "$p" ] || fail ancestor
 done
 [ ! -L "$V" ] && [ -d "$V" ] || fail view_type
 [ "$(stat -L -c '%d:%i' "$V")" = "$(stat -c '%d:%i' "$T")" ] || fail view_inode
 [ "$(stat -L -c '%d:%i' /proc/$parent/root/data/data)" = "$(stat -c '%d:%i' "$R/app-data")" ] || fail data_bind
 [ "$(stat -L -c '%d:%i' /proc/$parent/root/data/local/tmp/asx/run.sh)" = "$(stat -c '%d:%i' "$R/run.sh")" ] || fail runtime_bind
 # OH omits /proc/task/*/children. Use its existing PID/PPID ps interface.
 process_rows=$(ps -A -o PID,PPID) || fail ps_read
 header=0; rows=0; parent_rows=0
 while read -r row_pid row_ppid extra; do
  if [ "$header" = 0 ]; then
   [ "$row_pid:$row_ppid" = PID:PPID ] && [ -z "$extra" ] || fail ps_header
   header=1; continue
  fi
  [ -n "$row_pid" ] && [ -n "$row_ppid" ] && [ -z "$extra" ] || fail ps_fields
  case "$row_pid:$row_ppid" in *[!0-9:]*) fail ps_numbers;; esac
  [ "$row_pid" -gt 0 ] || fail ps_pid
  [ "$row_ppid" != "$parent" ] || fail live_child
  if [ "$row_pid" = "$parent" ]; then parent_rows=$((parent_rows+1)); fi
  rows=$((rows+1))
 done <<PS_ROWS
$process_rows
PS_ROWS
 [ "$header" = 1 ] && [ "$rows" -gt 0 ] && [ "$parent_rows" = 1 ] || fail ps_parent_missing_or_duplicate
}
identity
[ "$(meta)" = '66352:154615|20011300:20011300|755|u:object_r:appdat:s0' ] || fail repaired_owner_changed
check_window() {
 window_dump=$(timeout 2 hidumper -s WindowManagerService -a '-a') || fail window_read
 window_row=$(printf '%s\n' "$window_dump" | grep '^imehost0[[:space:]]') || fail host_window
 [ "$(printf '%s\n' "$window_row" | wc -l)" -eq 1 ] || fail window_ambiguous
 set -- $window_row
 [ "${4:-}" = 29 ] || fail host_WID_changed
 case "${8:--1}" in ''|-*|*[!0-9]*) fail host_not_visible;; esac
 fields=$(timeout 2 strings /proc/$parent/environ) || fail parent_environ
 wid=$(printf '%s\n' "$fields" | grep '^WL_PARENT_ID=') || fail parent_WID
 uid=$(printf '%s\n' "$fields" | grep '^ASX_RUNTIME_OWNER_UID=') || fail parent_UID
 [ "$wid" = WL_PARENT_ID=29 ] && [ "$uid" = ASX_RUNTIME_OWNER_UID=20011300 ] || fail parent_parameters
}
STAGE=/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d
check_inputs() {
 [ "$(sha256sum "$STAGE/host_spawn" | cut -d' ' -f1)" = 019acf9ec9f1b701b793e883c95ea5808cf74338b02088b024cf3634c6b56279 ] || fail host_spawn_SHA
 [ "$(sha256sum "$STAGE/request.bin" | cut -d' ' -f1)" = 011a16259c7735dcb088fab44f569bc222675855eb722bcf945c48e06c0214ca ] || fail request_SHA
 [ "$(sha256sum "$R/prepare_jit50.sh" | cut -d' ' -f1)" = b42a28e7a29a53c162a43ac25eaf52c24906f1afdd179c9414882772ccac34c8 ] || fail JIT_SHA
 [ "$(sha256sum /proc/$parent/root/data/local/tmp/asx/prepare_jit50.sh | cut -d' ' -f1)" = b42a28e7a29a53c162a43ac25eaf52c24906f1afdd179c9414882772ccac34c8 ] || fail parent_JIT_SHA
 [ "$(stat -L -c '%d:%i' /proc/$parent/root/data/local/tmp/asx/prepare_jit50.sh)" = "$(stat -c '%d:%i' "$R/prepare_jit50.sh")" ] || fail parent_JIT_inode
 [ -S /dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002 ] || fail socket
}
check_window
check_inputs
printf 'SINGLE_SPAWN_INTENT boot=%s parent=%s birth=%s preserve_parent=1\n' "$boot" "$parent" "$birth"
timeout 8 /bin/nsenter -t "$parent" -m -- /system/bin/sh /data/local/tmp/asx/prepare_jit50.sh || fail JIT_prepare
identity
check_window
check_inputs
[ "$(meta)" = '66352:154615|20011300:20011300|755|u:object_r:appdat:s0' ] || fail repaired_owner_changed
# Exact original real-spawn.sh argv; ONE request, never retries here.
"$STAGE/host_spawn" /dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002 "$STAGE/request.bin"
