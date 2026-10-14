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
before=$(meta) || fail metadata
case "$before" in *[!0-9a-zA-Z_:.'|'\-]*) fail metadata_encoding;; esac
if [ "$action" = preflight ]; then
 [ "$expected" = - ] || fail preflight_expected
 case "$before" in *'|0:0|755|u:object_r:appdat:s0') :;; *) fail preimage_owner_mode_label;; esac
 [ ! -e "$T/app_webview" ] && [ ! -L "$T/app_webview" ] || fail webview_already_present
else
 IFS='|' read -r inode original_owner original_mode original_label extra <<META_FIELDS
$expected
META_FIELDS
 [ -n "$inode" ] && [ -n "$original_owner" ] && [ -n "$original_mode" ] && [ -n "$original_label" ] && [ -z "$extra" ] || fail expected_fields
 if [ "$action" = reconcile ]; then
  case "$expected" in *'|0:0|755|u:object_r:appdat:s0') :;; *) fail reconcile_original;; esac
  desired="$inode|20011300:20011300|$original_mode|$original_label"
  [ "$before" = "$desired" ] || fail reconcile_not_exact_after
  identity
  [ "$(meta)" = "$desired" ] || fail reconcile_readback
 else
 [ "$before" = "$expected" ] || fail preimage_CAS
 case "$action:$before" in
  apply:*'|0:0|755|u:object_r:appdat:s0') owner=20011300:20011300;;
  rollback:*'|20011300:20011300|755|u:object_r:appdat:s0') owner=0:0;;
  *) fail unauthorized_metadata;;
 esac
 [ "$action" != apply ] || { [ ! -e "$T/app_webview" ] && [ ! -L "$T/app_webview" ] || fail webview_already_present; }
 desired="$inode|$owner|$original_mode|$original_label"
 identity
 [ "$(meta)" = "$expected" ] || fail final_CAS
 printf 'OWNER_INTENT action=%s before=%s after=%s\n' "$action" "$before" "$desired"
 # One nonrecursive ownership operation. -h never follows a raced final symlink.
 chown -h "$owner" "$T" || fail chown
 [ "$(meta)" = "$desired" ] || fail readback
 identity
 fi
fi
after=$(meta) || fail final_metadata
printf '{"schema":"toutiao-owner-observation/v1","status":"VERIFIED","action":"%s","boot_id":"%s","parent_pid":%s,"parent_birth":%s,"before":"%s","after":"%s","authorized_before":"%s"}\n' "$action" "$boot" "$parent" "$birth" "$before" "$after" "$expected"
