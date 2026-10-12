#!/system/bin/sh
# Independent R1 candidate, NOT installed. Based on captured watchdog 9ae770bd.
# Preserve the known ownership helper; never signal a parent/spawner or touch UI.
set -u
HERE=$(dirname "$0")
D=${TT_OPERATOR_ROOT:-/data/local/tmp/operator45}
F=${TT_STATE_ROOT:-$D/selfheal48}
RUNTIME=${TT_RUNTIME:-/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d}
STAGE=${TT_STAGE:-/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d}
PROC=${TT_PROC:-/proc}
PKG=com.ss.android.article.news
SOCKET=${TT_SOCKET:-/dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002}
RB_PROC=$PROC; RB_RUNTIME=$RUNTIME
RB_OWNER_UID=${TT_OWNER_UID:-$(stat -c %u /data/app/el2/100/base/org.westlake.imehost 2>/dev/null)}
. "$HERE/route-b-owner.sh"
BOOT=unknown; seq=0; child=none; child_birth=none; parent=none; parent_birth=none
keep_lock=0; owner_verified=0
io_fail() {
 # Never repair/clean an app on control-plane I/O failure. Retain the lock.
 keep_lock=1
 printf 'R1-IO-FAIL boot=%s seq=%s child=%s child_birth=%s parent=%s parent_birth=%s reason=%s\n' \
  "$BOOT" "$seq" "$child" "$child_birth" "$parent" "$parent_birth" "$*" >&2
 # Best-effort invalidate an old READY; stderr + nonzero remain authoritative
 # if the state device is itself unwritable. Never follow a state symlink.
 if [ "$owner_verified" = 1 ] && [ -f "$F/state" ] && [ ! -L "$F/state" ]; then printf 'IO_FAILED\n' > "$F/state" 2>/dev/null || :; fi
 exit 5
}
control_file() {
 [ ! -L "$1" ] && { [ ! -e "$1" ] || [ -f "$1" ]; } || io_fail "control_path_not_regular $1"
}
write_exact() {
 control_file "$1"
 printf '%s\n' "$2" > "$1" || io_fail "write_failed $1"
 verify_exact "$1" "$2"
}
verify_exact() {
 control_file "$1"
 readback=$(cat "$1") || io_fail "readback_failed $1"
 expected_size=$(printf '%s\n' "$2" | wc -c) || io_fail "expected_size_failed $1"
 actual_size=$(wc -c < "$1") || io_fail "readback_size_failed $1"
 [ "$readback" = "$2" ] && [ "$actual_size" -eq "$expected_size" ] || io_fail "readback_mismatch $1"
}
uptime_s() { read up rest < "$PROC/uptime" || return 1; echo "${up%%.*}"; }
event() {
 control_file "$F/events.log"
 event_time=$(uptime_s) || io_fail uptime_read_failed
 event_line=$(printf '%s boot=%s seq=%s child=%s child_birth=%s parent=%s parent_birth=%s reason=%s' \
  "$event_time" "$BOOT" "$seq" "$child" "$child_birth" "$parent" "$parent_birth" "$*")
 printf '%s\n' "$event_line" >> "$F/events.log" || io_fail events_append_failed
 event_tail=$(tail -n 1 "$F/events.log") || io_fail events_readback_failed
 [ "$event_tail" = "$event_line" ] || io_fail events_readback_mismatch
}
state() {
 # Audit intent first; never publish READY after an audit write failure.
 event "transition_target=$1 $2"
 write_exact "$F/state" "$1"
}
instance() {
 instance_text=$(printf 'boot_id=%s\nchild=%s\nparent=%s\nbirth=%s\nparent_birth=%s\nseq=%s\nmode=preserve' \
  "$BOOT" "$child" "$parent" "$child_birth" "$parent_birth" "$seq")
 write_exact "$F/instance.txt" "$instance_text"
}
refuse() { echo "R1-REFUSE $*" >&2; return 1; }
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
child_owned() {
 p=$1; expected=$2; RB_AUDIT_PID=$p; RB_AUDIT_BIRTH=$expected; RB_AUDIT_PHASE=strict
 first_birth=$(rb_birth "$p") || { rb_deny birth '<read-error-or-exited>' "$expected"; return 1; }
 [ "$first_birth" = "$expected" ] || { rb_deny birth "$first_birth" "$expected"; return 1; }
 rb_owned "$p" || return 1
 mine=$(readlink "$PROC/$p/ns/mnt" 2>/dev/null) || { rb_deny namespace '<read-error>' private; return 1; }
 init=$(readlink "$PROC/1/ns/mnt" 2>/dev/null) || { rb_deny init_namespace '<read-error>' readable; return 1; }
 [ -n "$mine" ] && [ "$mine" != "$init" ] || { rb_deny namespace "$mine" "not:$init"; return 1; }
 row=$(cat "$PROC/$p/stat") || { rb_deny ppid '<read-error>' "$parent"; return 1; }
 rest=${row##*) }; set -- $rest
 [ "${2:-none}" = "$parent" ] || { rb_deny ppid "${2:-none}" "$parent"; return 1; }
 last_birth=$(rb_birth "$p") || { rb_deny birth_after '<read-error-or-exited>' "$expected"; return 1; }
 [ "$last_birth" = "$expected" ] || { rb_deny birth_after "$last_birth" "$expected"; return 1; }
}
release_lock() {
 [ "$keep_lock" = 0 ] || return 0
 # Remove only this run's exact lock. Foreign/changed owner is retained.
 [ -f "$F/lock/owner" ] && [ ! -L "$F/lock/owner" ] || return 0
 lock_readback=$(cat "$F/lock/owner") || return 0
 [ "$lock_readback" = "$$ $self_birth $BOOT" ] || return 0
 lock_size=$(wc -c < "$F/lock/owner") || return 0
 expected_size=$(printf '%s %s %s\n' "$$" "$self_birth" "$BOOT" | wc -c)
 [ "$lock_size" -eq "$expected_size" ] || return 0
 rm -f "$F/lock/owner" || io_fail lock_release_failed
 rmdir "$F/lock" || io_fail lock_directory_release_failed
}
preconditions() {
 [ "${TT_RECOVERY_EXECUTE:-0}" = 1 ] || { refuse EXECUTION_NOT_ARMED; return 1; }
 BOOT=$(cat "$PROC/sys/kernel/random/boot_id") || return 1
 [ -n "${TT_EXPECT_BOOT:-}" ] && [ "$BOOT" = "$TT_EXPECT_BOOT" ] || { refuse BOOT_MISMATCH; return 1; }
 case "$RB_OWNER_UID" in ''|0|*[!0-9]*) refuse OWNER_UID_INVALID; return 1;; esac
 # Existing stop always wins, including the captured historical stop.
 [ ! -e "$F/stop" ] || { refuse EXISTING_STOP; return 1; }
 case "$F" in "$RUNTIME"|"$RUNTIME"/*) refuse STATE_ROOT_OVERLAPS_USER_DATA; return 1;; esac
 # Existing control directory only; resolve aliases before any control-file write.
 [ -d "$F" ] || { refuse MISSING_OPERATOR_STATE; return 1; }
 state_dir=$(CDPATH= cd -P "$F" && pwd -P) || return 1
 data_dir=$(CDPATH= cd -P "$RUNTIME" && pwd -P) || return 1
 case "$state_dir" in "$data_dir"|"$data_dir"/*) refuse STATE_ROOT_OVERLAPS_USER_DATA; return 1;; esac
 for dir in app-data data webview-t-data; do
  [ -d "$RUNTIME/$dir" ] || { refuse "MISSING_PRESERVED_DATA $dir"; return 1; }
 done
 case "${TT_MAX_ATTEMPTS:-3}" in ''|0|*[!0-9]*) refuse ATTEMPT_LIMIT_INVALID; return 1;; esac
 case "${TT_MAX_POLLS:-0}" in ''|*[!0-9]*) refuse POLL_LIMIT_INVALID; return 1;; esac
 return 0
}
main() {
 preconditions || return 2
 mkdir -p "$F" || return 2
 self_birth=$(rb_birth "$$") || { refuse SELF_IDENTITY_UNREADABLE; return 2; }
 # Do not reclaim even a stale/ownerless lock: it needs separate review.
 mkdir "$F/lock" 2>/dev/null || { refuse LOCK_CONFLICT_NO_TAKEOVER; return 2; }
 write_exact "$F/lock/owner" "$$ $self_birth $BOOT"
 owner_verified=1
 trap release_lock EXIT
 trap 'state STOPPED supervisor_signal_no_app_control; exit 6' TERM INT
 # Check persistence before ANY launch. A present unreadable sequence is not 0.
 for control in sequence instance.txt state events.log; do control_file "$F/$control"; done
 if [ -e "$F/sequence" ]; then
  seq=$(cat "$F/sequence") || io_fail sequence_read_failed
  case "$seq" in ''|*[!0-9]*) io_fail sequence_invalid;; esac
 fi
 write_exact "$F/sequence" "$seq"
 instance
 state SUPERVISOR_STARTING control_persistence_checked_before_launch
 parent=${TT_PARENT_PID:-none}; parent_birth=${TT_PARENT_BIRTH:-none}
 if [ "$parent" != none ]; then
  parent_owned "$parent" "$parent_birth" || { state OWNER_REFUSED existing_parent_identity; return 2; }
 else
  # No implicit takeover of a socket/unknown old parent.
  [ ! -S "$SOCKET" ] || { state OWNER_REFUSED socket_without_parent_identity; return 2; }
  if ! timeout 15 sh "$F/start-parent.sh" > "$F/parent-start.txt" 2>&1; then
   state START_FAILED parent_command_nonzero; return 3
  fi
  parent=$(cat "$F/parent-start.txt"); parent_birth=$(rb_birth "$parent") || { state START_FAILED parent_not_alive; return 3; }
  parent_owned "$parent" "$parent_birth" || { state OWNER_REFUSED new_parent_identity; return 2; }
 fi
 attempt=0; polls=0
 while [ "$attempt" -lt "${TT_MAX_ATTEMPTS:-3}" ]; do
  verify_exact "$F/lock/owner" "$$ $self_birth $BOOT"
  [ ! -e "$F/stop" ] || { state STOPPED existing_stop; return 0; }
  [ "$(cat "$PROC/sys/kernel/random/boot_id")" = "$BOOT" ] || { state OWNER_REFUSED boot_changed; return 2; }
  parent_owned "$parent" "$parent_birth" || { state OWNER_REFUSED parent_identity_changed; return 2; }
  # Explicit attach is useful for a reviewed same-boot handoff; no warm data rotation.
  if [ "$attempt" = 0 ] && [ -n "${TT_CHILD_PID:-}" ]; then
   child=$TT_CHILD_PID; child_birth=${TT_CHILD_BIRTH:-none}
  else
   [ -z "$(rb_owned_pids)" ] || { state OWNER_REFUSED existing_child_without_attach_identity; return 2; }
   if ! timeout 15 sh "$F/spawn.sh" > "$F/spawn.txt" 2>&1; then
    state START_FAILED spawn_command_nonzero; return 3
   fi
   child=$(sed -n 's/.*result=0 pid=\([0-9][0-9]*\).*/\1/p' "$F/spawn.txt" | tail -1)
   child_birth=$(rb_birth "$child") || { state START_FAILED child_not_alive; return 3; }
   # New-spawn only: one fixed PID+birth. Never wait on attach/existing PIDs.
   report="$F/readiness-$attempt-$child-$child_birth.jsonl"
   control_file "$report"; [ ! -e "$report" ] || io_fail readiness_report_exists
   RB_AUDIT_PID=$child; RB_AUDIT_BIRTH=$child_birth; RB_AUDIT_PHASE=readiness_result
   readiness_rc=0
   (set -C; timeout 2 sh "$F/readiness-probe.sh" "$child" "$child_birth" "$parent" "$parent_birth" "$BOOT" "$$" "$self_birth" > "$report" 2>&1) || readiness_rc=$?
   if [ "$readiness_rc" != 0 ]; then
    rb_guard_json readiness_result "$readiness_rc" 'complete_readonly_probe_within_2_seconds' >> "$report" 2>&1 || io_fail readiness_result_write_failed
    state OWNER_REFUSED "child_readiness_rc=$readiness_rc report=$report app_parent_retained"; return 2
   fi
  fi
  child_owned "$child" "$child_birth" || { state OWNER_REFUSED child_identity; return 2; }
  attempt=$((attempt+1))
  seq=$(cat "$F/sequence") || io_fail sequence_read_failed
  case "$seq" in ''|*[!0-9]*) io_fail sequence_invalid;; esac
  seq=$((seq+1)); write_exact "$F/sequence" "$seq"
  instance
  state BOOTSTRAP data_preserved_no_rotation
  feed_count=0; ready=0
  while [ ! -e "$F/stop" ]; do
   verify_exact "$F/lock/owner" "$$ $self_birth $BOOT"
   [ "$(cat "$PROC/sys/kernel/random/boot_id")" = "$BOOT" ] || { state OWNER_REFUSED boot_changed; return 2; }
   # Only actual disappearance/zombie means exit. PID reuse is never cleanup.
   live_birth=$(rb_birth "$child") || live_birth=none
   if [ "$live_birth" = none ]; then
    if [ -d "$PROC/$child" ]; then
     # An unreadable/disappearing stat alone is not proof of process exit.
     row=$(cat "$PROC/$child/stat" 2>/dev/null) || { state OWNER_REFUSED identity_unreadable_no_relaunch; return 2; }
     rest=${row##*) }; set -- $rest
     [ "${1:-none}" = Z ] || { state OWNER_REFUSED identity_unreadable_no_relaunch; return 2; }
    fi
    event process_exit; break
   fi
   [ "$live_birth" = "$child_birth" ] && child_owned "$child" "$child_birth" || { state OWNER_REFUSED child_identity_changed_no_signal; return 2; }
   polls=$((polls+1))
   if [ "$ready" = 0 ]; then
    label=unknown; capture_rc=0; classifier_rc=0
    # Same JPEG invocation as working manual evidence; never reuse an old frame.
    control_file "$F/current.jpeg"
    rm -f "$F/current.jpeg" || io_fail stale_capture_remove_failed
    control_file "$F/snapshot.log"; control_file "$F/classifier.log"
    timeout 4 snapshot_display -f "$F/current.jpeg" > "$F/snapshot.log" 2>&1 || capture_rc=$?
    if [ "$capture_rc" = 0 ] && [ -s "$F/current.jpeg" ]; then
     label=$(timeout 2 "$F/screen-gate" "$F/current.jpeg" 2>"$F/classifier.log") || classifier_rc=$?
     [ "$classifier_rc" = 0 ] || label=unknown
    else label=snapshot_error; fi
    case "$label" in
     privacy) feed_count=0; state WAITING_FOR_USER_CONSENT privacy_no_touch;;
     feed)
      feed_count=$((feed_count+1))
      if [ "$feed_count" -ge 2 ]; then
       control_file "$F/feed-$seq.jpeg"
       cp "$F/current.jpeg" "$F/feed-$seq.jpeg" || io_fail feed_archive_failed
       cmp -s "$F/current.jpeg" "$F/feed-$seq.jpeg" || io_fail feed_archive_readback_failed
       state READY feed_confirmed_without_auto_consent
       ready=1
      else state BOOTSTRAP first_feed_observation; fi;;
     snapshot_error) feed_count=0; state UI_UNVERIFIED "snapshot_error_rc=$capture_rc alive_no_cleanup";;
     *) feed_count=0; state UI_UNVERIFIED "label=$label classifier_rc=$classifier_rc alive_no_cleanup";;
    esac
   fi
   # Test/observation envelope can end without terminating either process.
   if [ "${TT_MAX_POLLS:-0}" -gt 0 ] && [ "$polls" -ge "$TT_MAX_POLLS" ]; then event observation_limit_no_app_control; return 0; fi
   sleep 3
  done
  [ ! -e "$F/stop" ] || { state STOPPED existing_stop; return 0; }
  state RECOVERING child_exited_parent_preserved
  if [ "$attempt" -ge "${TT_MAX_ATTEMPTS:-3}" ]; then state RETRY_LIMIT attempts_exhausted_no_cleanup; return 4; fi
  event "retry_backoff_seconds=$((attempt*5))"
  sleep "$((attempt*5))"
 done
}
main "$@"
