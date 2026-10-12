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
uptime_s() { read up rest < "$PROC/uptime"; echo "${up%%.*}"; }
event() {
 printf '%s boot=%s seq=%s child=%s child_birth=%s parent=%s parent_birth=%s reason=%s\n' \
  "$(uptime_s)" "$BOOT" "$seq" "$child" "$child_birth" "$parent" "$parent_birth" "$*" >> "$F/events.log"
}
state() { printf '%s\n' "$1" > "$F/state"; event "$2"; }
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
child_owned() {
 p=$1; expected=$2
 [ "$(rb_birth "$p")" = "$expected" ] || return 1
 rb_owned "$p" || return 1
 private_namespace "$p" || return 1
 # Require the expected parent, not merely a process with the same executable.
 row=$(cat "$PROC/$p/stat") || return 1
 rest=${row##*) }; set -- $rest
 [ "${2:-none}" = "$parent" ] || return 1
 [ "$(rb_birth "$p")" = "$expected" ]
}
release_lock() {
 # Remove only this run's exact lock. Foreign/changed owner is retained.
 read lp lb lboot < "$F/lock/owner" || return
 [ "$lp:$lb:$lboot" = "$$:$self_birth:$BOOT" ] || return
 rm -f "$F/lock/owner"; rmdir "$F/lock" 2>/dev/null || :
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
 mkdir "$F/lock" 2>/dev/null || { event LOCK_CONFLICT_NO_TAKEOVER; return 2; }
 printf '%s %s %s\n' "$$" "$self_birth" "$BOOT" > "$F/lock/owner"
 trap release_lock EXIT
 trap 'state STOPPED supervisor_signal_no_app_control; exit 0' TERM INT
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
  fi
  child_owned "$child" "$child_birth" || { state OWNER_REFUSED child_identity; return 2; }
  attempt=$((attempt+1))
  seq=$(cat "$F/sequence" 2>/dev/null); seq=${seq:-0}
  case "$seq" in *[!0-9]*) state OWNER_REFUSED sequence_invalid; return 2;; esac
  seq=$((seq+1)); echo "$seq" > "$F/sequence"
  printf 'boot_id=%s\nchild=%s\nparent=%s\nbirth=%s\nparent_birth=%s\nseq=%s\nmode=preserve\n' \
   "$BOOT" "$child" "$parent" "$child_birth" "$parent_birth" "$seq" > "$F/instance.txt"
  state BOOTSTRAP data_preserved_no_rotation
  feed_count=0; ready=0
  while [ ! -e "$F/stop" ]; do
   [ "$(cat "$PROC/sys/kernel/random/boot_id")" = "$BOOT" ] || { state OWNER_REFUSED boot_changed; return 2; }
   # Only actual disappearance/zombie means exit. PID reuse is never cleanup.
   live_birth=$(rb_birth "$child") || live_birth=none
   if [ "$live_birth" = none ]; then event process_exit; break; fi
   [ "$live_birth" = "$child_birth" ] && child_owned "$child" "$child_birth" || { state OWNER_REFUSED child_identity_changed_no_signal; return 2; }
   polls=$((polls+1))
   if [ "$ready" = 0 ]; then
    label=unknown; capture_rc=0; classifier_rc=0
    # Same JPEG invocation as working manual evidence; never reuse an old frame.
    rm -f "$F/current.jpeg"
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
       ready=1; cp "$F/current.jpeg" "$F/feed-$seq.jpeg"
       state READY feed_confirmed_without_auto_consent
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
