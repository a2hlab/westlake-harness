#!/system/bin/sh
# Durable manual-icon-reentry guardian. DERIVED from the sealed base watchdog
# 2b635ef1ea9e00546e1306b0fe6872a415a8c7d5653e19f9fb42fca04386db4a (capture-feed
# payload). All frozen helpers are copied VERBATIM; the only behavioural change is
# the launch TAIL: the base auto-respawned up to TT_MAX_ATTEMPTS on child exit,
# this variant does the FIRST launch unchanged and then waits for a manual
# desktop->host icon tap for every later launch (see reentry-common.sh).
# Preserves ownership guards, readiness-probe, and the private capture gate.
# Never signals a parent/spawner or touches UI. No awk, no python.
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
# Desktop (SceneBoard) focus identity used to ARM the reentry trigger. Name is the
# WMS desktop suffix is dynamic; UID/cmdline/exe and birth are checked.
# Outer MUST confirm these on 61b before arming (see OPERATIONS.md).
# Observed on 61b: SCBDesktop6; only a nonempty numeric suffix is accepted.
# 61b raw identity observation: SceneBoard UID 20010018, cmdline below.
# An explicitly empty override is rejected; no optional UID bypass.
RC_DESKTOP_UID=${TT_DESKTOP_UID-20010018}
. "$HERE/route-b-owner.sh"
. "$HERE/reentry-seams.sh"
. "$HERE/reentry-common.sh"
BOOT=unknown; seq=0; child=none; child_birth=none; parent=none; parent_birth=none
keep_lock=0; owner_verified=0; parent_wid=
# --- BEGIN frozen helpers (verbatim from base watchdog 2b635ef1) ------------------
io_fail() {
 keep_lock=1
 printf 'R1-IO-FAIL boot=%s seq=%s child=%s child_birth=%s parent=%s parent_birth=%s reason=%s\n' \
  "$BOOT" "$seq" "$child" "$child_birth" "$parent" "$parent_birth" "$*" >&2
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
capture_init() {
 capture_base=$(CDPATH= cd -P /data/local/tmp && pwd -P) || io_fail capture_base_unreadable
 [ "$capture_base" = /data/local/tmp ] || io_fail capture_base_alias
 case "$BOOT" in ''|*[!0-9a-f-]*) io_fail capture_boot_invalid;; esac
 CAP="/data/local/tmp/westlake-toutiao-capture-$BOOT-$$-$self_birth"
 capture_owner="$$ $self_birth $BOOT"
 capture_file=
 [ ! -e "$CAP" ] && [ ! -L "$CAP" ] || io_fail capture_directory_exists
 capture_umask=$(umask); umask 077
 mkdir "$CAP" || io_fail capture_directory_create_failed
 capture_dir_identity=$(stat -c '%d:%i' "$CAP") || io_fail capture_directory_identity_failed
 [ -n "$capture_dir_identity" ] || io_fail capture_directory_identity_empty
 umask "$capture_umask"
 write_exact "$CAP/owner" "$capture_owner"
 capture_guard
}
capture_guard() {
 [ -d "$CAP" ] && [ ! -L "$CAP" ] || io_fail capture_directory_changed
 [ -n "${capture_dir_identity:-}" ] || io_fail capture_directory_identity_missing
 capture_dir_now=$(stat -c '%d:%i' "$CAP") || io_fail capture_directory_identity_read_failed
 [ "$capture_dir_now" = "$capture_dir_identity" ] || io_fail capture_directory_identity_changed
 capture_real=$(CDPATH= cd -P "$CAP" && pwd -P) || io_fail capture_directory_unreadable
 [ "$capture_real" = "$CAP" ] || io_fail capture_directory_alias
 capture_meta=$(stat -c '%u:%g:%a' "$CAP") || io_fail capture_directory_metadata_failed
 [ "$capture_meta" = 0:0:700 ] || io_fail capture_directory_metadata_changed
 verify_exact "$CAP/owner" "$capture_owner"
 for capture_entry in "$CAP"/* "$CAP"/.[!.]* "$CAP"/..?*; do
  [ -e "$capture_entry" ] || [ -L "$capture_entry" ] || continue
  case "$capture_entry" in "$CAP/owner"|"$capture_file") :;; *) io_fail capture_directory_unknown_entry;; esac
 done
}
capture_context() {
 capture_guard
 verify_exact "$F/lock/owner" "$$ $self_birth $BOOT"
 [ "$(cat "$PROC/sys/kernel/random/boot_id")" = "$BOOT" ] || io_fail capture_boot_changed
 [ ! -e "$F/stop" ] && [ ! -L "$F/stop" ] || { capture_rc=126; capture_reason=stop_during_capture; return 1; }
 child_owned "$child" "$child_birth" || { capture_rc=126; capture_reason=child_identity_during_capture; return 1; }
}
capture_remove_file() {
 capture_guard
 if [ -e "$capture_file" ] || [ -L "$capture_file" ]; then
  [ -f "$capture_file" ] && [ ! -L "$capture_file" ] || io_fail capture_output_not_regular
  [ "$(stat -c '%u' "$capture_file")" = 0 ] || io_fail capture_output_foreign_owner
  rm -f "$capture_file" || io_fail capture_output_cleanup_failed
  [ ! -e "$capture_file" ] && [ ! -L "$capture_file" ] || io_fail capture_output_cleanup_readback_failed
 fi
}
capture_frame() {
 capture_rc=0; capture_reason=none
 capture_context || return 1
 capture_file="$CAP/current-$seq-$polls.jpeg"
 [ ! -e "$capture_file" ] && [ ! -L "$capture_file" ] || io_fail capture_output_exists
 control_file "$F/current.jpeg"
 rm -f "$F/current.jpeg" || io_fail stale_capture_remove_failed
 [ ! -e "$F/current.jpeg" ] && [ ! -L "$F/current.jpeg" ] || io_fail stale_capture_remove_readback_failed
 control_file "$F/snapshot.log"; control_file "$F/classifier.log"
 timeout 4 snapshot_display -f "$capture_file" > "$F/snapshot.log" 2>&1 || capture_rc=$?
 capture_guard
 if [ "$capture_rc" != 0 ] || [ ! -f "$capture_file" ] || [ -L "$capture_file" ] || [ ! -s "$capture_file" ]; then
  [ "$capture_rc" != 0 ] || capture_rc=125
  capture_reason=snapshot_failed_missing_empty_or_link
  capture_remove_file
  return 1
 fi
 [ "$(stat -c '%u' "$capture_file")" = 0 ] || io_fail capture_output_foreign_owner
 capture_identity=$(stat -c '%d:%i' "$capture_file") || io_fail capture_output_identity_failed
 capture_context || { capture_remove_file; return 1; }
 control_file "$F/current.jpeg"
 cp "$capture_file" "$F/current.jpeg" || io_fail capture_archive_copy_failed
 control_file "$F/current.jpeg"
 [ -f "$F/current.jpeg" ] && [ -s "$F/current.jpeg" ] || io_fail capture_archive_empty
 cmp -s "$capture_file" "$F/current.jpeg" || io_fail capture_archive_readback_failed
 [ "$(stat -c '%d:%i' "$capture_file")" = "$capture_identity" ] || io_fail capture_output_identity_changed
 capture_remove_file
 capture_context || return 1
}
capture_release() {
 [ -n "${CAP:-}" ] || return 0
 capture_guard
 rm -f "$CAP/owner" || io_fail capture_owner_cleanup_failed
 rmdir "$CAP" || io_fail capture_directory_cleanup_failed_unknown_preserved
 CAP=
}
release_lock() {
 [ "$keep_lock" = 0 ] || return 0
 [ -f "$F/lock/owner" ] && [ ! -L "$F/lock/owner" ] || return 0
 lock_readback=$(cat "$F/lock/owner") || return 0
 [ "$lock_readback" = "$$ $self_birth $BOOT" ] || return 0
 lock_size=$(wc -c < "$F/lock/owner") || return 0
 expected_size=$(printf '%s %s %s\n' "$$" "$self_birth" "$BOOT" | wc -c)
 [ "$lock_size" -eq "$expected_size" ] || return 0
 capture_release
 rm -f "$F/lock/owner" || io_fail lock_release_failed
 rmdir "$F/lock" || io_fail lock_directory_release_failed
}
preconditions() {
 [ "${TT_RECOVERY_EXECUTE:-0}" = 1 ] || { refuse EXECUTION_NOT_ARMED; return 1; }
 BOOT=$(cat "$PROC/sys/kernel/random/boot_id") || return 1
 [ -n "${TT_EXPECT_BOOT:-}" ] && [ "$BOOT" = "$TT_EXPECT_BOOT" ] || { refuse BOOT_MISMATCH; return 1; }
 case "$RB_OWNER_UID" in ''|0|*[!0-9]*) refuse OWNER_UID_INVALID; return 1;; esac
 [ ! -e "$F/stop" ] || { refuse EXISTING_STOP; return 1; }
 case "$F" in "$RUNTIME"|"$RUNTIME"/*) refuse STATE_ROOT_OVERLAPS_USER_DATA; return 1;; esac
 [ -d "$F" ] || { refuse MISSING_OPERATOR_STATE; return 1; }
 state_dir=$(CDPATH= cd -P "$F" && pwd -P) || return 1
 data_dir=$(CDPATH= cd -P "$RUNTIME" && pwd -P) || return 1
 case "$state_dir" in "$data_dir"|"$data_dir"/*) refuse STATE_ROOT_OVERLAPS_USER_DATA; return 1;; esac
 for dir in app-data data webview-t-data; do
  [ -d "$RUNTIME/$dir" ] || { refuse "MISSING_PRESERVED_DATA $dir"; return 1; }
 done
 case "$RC_DESKTOP_UID" in ''|0|*[!0-9]*) refuse DESKTOP_UID_INVALID; return 1;; esac
 case "${TT_MAX_POLLS:-0}" in ''|*[!0-9]*) refuse POLL_LIMIT_INVALID; return 1;; esac
 return 0
}
# --- END frozen helpers ----------------------------------------------------------

# Soft parent-window verification (return instead of fail) for the reentry focus seam.
# Mirrors launch-common.sh verify_parent_window without the fatal `fail` path.
verify_parent_window_soft() {
 parent_owned "$1" "$2" || return 1
 vpw_fg=$3
 case "$vpw_fg" in ''|*[!0-9]*) return 1;; esac
 vpw_fields=$(timeout 2 strings "$PROC/$1/environ" 2>/dev/null) || return 1
 vpw_wid=$(printf '%s\n' "$vpw_fields" | grep -E '^WL_PARENT_ID=[0-9]+$') || return 1
 vpw_uid=$(printf '%s\n' "$vpw_fields" | grep -E '^ASX_RUNTIME_OWNER_UID=[0-9]+$') || return 1
 [ "$(printf '%s\n' "$vpw_wid" | wc -l)" -eq 1 ] || return 1
 [ "$(printf '%s\n' "$vpw_uid" | wc -l)" -eq 1 ] || return 1
 [ "${vpw_wid#WL_PARENT_ID=}" = "$vpw_fg" ] || return 1
 [ "${vpw_uid#ASX_RUNTIME_OWNER_UID=}" = "$RB_OWNER_UID" ] || return 1
 parent_owned "$1" "$2" || return 1
 printf '%s\n' "$vpw_fg"
}
# Verify the focused OH process, independently of Route-B parent ownership.
# Both command names, UIDs and appspawn exe come from the recorded 61b observation.
# Process-title storage can contain NUL padding, but no extra argv/bytes are allowed.
rc_verify_window_process() {
 wpg_pid=$1; wpg_uid=$2; wpg_command=$3
 case "$wpg_pid:$wpg_uid" in *[!0-9:]*|:*|*:) return 1;; esac
 wpg_birth=$(rb_birth "$wpg_pid") || return 1
 wpg_uids=$(rb_uid "$wpg_pid") || return 1
 [ "$wpg_uids" = "$wpg_uid:$wpg_uid:$wpg_uid:$wpg_uid" ] || return 1
 [ "$(readlink "$PROC/$wpg_pid/exe")" = /system/bin/appspawn ] || return 1
 wpg_raw=$(od -An -v -tx1 "$PROC/$wpg_pid/cmdline") || return 1
 wpg_expected=$(printf '%s' "$wpg_command" | od -An -v -tx1) || return 1
 wpg_hex=; for wpg_byte in $wpg_raw; do wpg_hex=$wpg_hex$wpg_byte; done
 wpg_prefix=; for wpg_byte in $wpg_expected; do wpg_prefix=$wpg_prefix$wpg_byte; done
 case "$wpg_hex" in "$wpg_prefix"00*) wpg_tail=${wpg_hex#"$wpg_prefix"};; *) return 1;; esac
 case "$wpg_tail" in *[!0]*) return 1;; esac
 [ "$(rb_birth "$wpg_pid")" = "$wpg_birth" ] || return 1
 RC_WINDOW_BIRTH=$wpg_birth
 return 0
}
rc_verify_desktop() {
 rc_verify_window_process "$1" "$RC_DESKTOP_UID" com.ohos.sceneboard
}
rc_desktop_name() {
 case "$1" in SCBDesktop*) rdn_suffix=${1#SCBDesktop};; *) return 1;; esac
 case "$rdn_suffix" in ''|*[!0-9]*) return 1;; esac
 return 0
}

# --- Reentry production seams (wrap device primitives; parsing via reentry-seams.sh) ---
rc_stop_present() { [ -e "$F/stop" ] || [ -L "$F/stop" ]; }
# Sampled edges: normal manual Home -> icon taps; sub-second switches may be missed.
rc_sleep() { sleep 1; }
rc_event() { event "$@"; }
rc_gates_ok() {
 rc_gate_reason=
 lo=$(cat "$F/lock/owner" 2>/dev/null) || { rc_gate_reason=lock_unreadable; return 1; }
 [ "$lo" = "$$ $self_birth $BOOT" ] || { rc_gate_reason=lock_foreign; return 1; }
 [ "$(cat "$PROC/sys/kernel/random/boot_id" 2>/dev/null)" = "$BOOT" ] || { rc_gate_reason=boot_changed; return 1; }
 parent_owned "$parent" "$parent_birth" || { rc_gate_reason=parent_identity; return 1; }
 cg_child=$(rc_child_state) || { rc_gate_reason=child_unreadable; return 1; }
 [ "$cg_child" != invalid ] || { rc_gate_reason=child_identity; return 1; }
 return 0
}
# Capture one WMS dump into a verified control file, then parse from the file
# (avoids $()-wrapped case and keeps the real dump auditable). Echoes the path or
# empty on failure.
rc_capture_wms() {
 cw_out=$1
 control_file "$cw_out"
 rm -f "$cw_out" 2>/dev/null || :
 timeout 2 hidumper -s WindowManagerService -a '-a' > "$cw_out" 2>/dev/null || { rm -f "$cw_out" 2>/dev/null || :; return 1; }
 [ -s "$cw_out" ] || { rm -f "$cw_out" 2>/dev/null || :; return 1; }
 return 0
}
rc_focus_state() {
 rc_capture_wms "$F/wms-focus.txt" || { rc_focus_result=error; return 0; }
 fs_focus=$(rc_parse_focus "$F/wms-focus.txt")
 [ "$fs_focus" != error ] || { rc_focus_result=error; return 0; }
 # shellcheck disable=SC2086
 set -- $fs_focus
 fs_name=${1:-}; fs_pid=${2:-}; fs_wid=${3:-}
 if [ "$fs_name" = imehost0 ]; then
  rc_verify_window_process "$fs_pid" "$RB_OWNER_UID" org.westlake.imehost || { rc_focus_result=other; return 0; }
  fs_host_birth=$RC_WINDOW_BIRTH
  fs_fg=$(verify_parent_window_soft "$parent" "$parent_birth" "$fs_wid") || { rc_focus_result=other; return 0; }
  [ "$(rb_birth "$fs_pid")" = "$fs_host_birth" ] || { rc_focus_result=other; return 0; }
  [ "$fs_fg" = "$fs_wid" ] || { rc_focus_result=other; return 0; }
  rc_focus_result="host $fs_wid"; return 0
 fi
 if rc_desktop_name "$fs_name"; then
  rc_verify_desktop "$fs_pid" || { rc_focus_result=other; return 0; }
  rc_focus_result=desktop; return 0
 fi
 rc_focus_result=other
 return 0
}
rc_owned_window_present() {
 rc_capture_wms "$F/wms-owned.txt" || { rc_owned_result=unknown; return 0; }
 ow_extra=$(rb_owned_pids 2>/dev/null) || ow_extra=
 rc_owned_result=$(rc_parse_owned_window "$F/wms-owned.txt" "$child $ow_extra") || rc_owned_result=unknown
 return 0
}
rc_child_state() {
 [ -n "$child" ] && [ "$child" != none ] || { echo gone; return 0; }
 cs_b=$(rb_birth "$child" 2>/dev/null) || {
  if [ ! -d "$PROC/$child" ]; then echo gone; return 0; fi
  cs_row=$(cat "$PROC/$child/stat" 2>/dev/null) || { echo unknown; return 0; }
  cs_rest=${cs_row##*) }; set -- $cs_rest
  [ "${20:-none}" = "$child_birth" ] || { echo invalid; return 0; }
  if [ "${1:-none}" = Z ]; then echo gone; else echo unknown; fi
  return 0
 }
 [ "$cs_b" = "$child_birth" ] || { echo invalid; return 0; }
 if child_owned "$child" "$child_birth" >/dev/null 2>&1; then echo alive; else echo invalid; fi
}
# One fresh spawn + readiness (NO monitor). Sets child/child_birth on success.
do_one_launch() {
 do_reason=; do_spawn_started=0
 verify_exact "$F/lock/owner" "$$ $self_birth $BOOT"
 [ -z "$(rb_owned_pids)" ] || { do_reason=existing_child_without_attach_identity; return 2; }
 do_spawn_started=1
 if ! timeout 15 sh "$F/spawn.sh" > "$F/spawn.txt" 2>&1; then do_reason=spawn_command_nonzero; return 3; fi
 child=$(sed -n 's/.*result=0 pid=\([0-9][0-9]*\).*/\1/p' "$F/spawn.txt" | tail -1)
 child_birth=$(rb_birth "$child") || { do_reason=child_not_alive; return 4; }
 report="$F/readiness-reentry-$child-$child_birth.jsonl"
 control_file "$report"; [ ! -e "$report" ] || io_fail readiness_report_exists
 RB_AUDIT_PID=$child; RB_AUDIT_BIRTH=$child_birth; RB_AUDIT_PHASE=readiness_result
 readiness_rc=0
 (set -C; timeout 2 sh "$F/readiness-probe.sh" "$child" "$child_birth" "$parent" "$parent_birth" "$BOOT" "$$" "$self_birth" > "$report" 2>&1) || readiness_rc=$?
 if [ "$readiness_rc" != 0 ]; then
  rb_guard_json readiness_result "$readiness_rc" 'complete_readonly_probe_within_2_seconds' >> "$report" 2>&1 || io_fail readiness_result_write_failed
  do_reason="child_readiness_rc=$readiness_rc"; return 5
 fi
 child_owned "$child" "$child_birth" || { do_reason=child_identity; return 6; }
 seq=$(cat "$F/sequence") || io_fail sequence_read_failed
 case "$seq" in ''|*[!0-9]*) io_fail sequence_invalid;; esac
 seq=$((seq+1)); write_exact "$F/sequence" "$seq"
 instance
 return 0
}
# Current-shell protocol: no stdout capture, so child/birth/seq and io_fail persist.
# Once spawn.sh is entered, missing output/timeout does NOT prove no child exists.
rc_do_spawn() {
 rc_spawn_result=
 do_one_launch; dls_rc=$?
 if [ "$dls_rc" = 0 ]; then rc_spawn_result="ok $child $child_birth"; return 0; fi
 if [ "$do_spawn_started" = 1 ]; then
  rc_spawn_result="unknown ${do_reason:-spawn_indeterminate}"
 else
  rc_spawn_result="fail ${do_reason:-spawn_refused_pre_host_spawn}"
 fi
 return 0
}
# Supervise a confirmed child until it exits. Returns 0 on clean exit, nonzero on
# identity/IO issues (propagated up by the reentry loop). Mirrors the base inner loop.
monitor_child() {
 state BOOTSTRAP data_preserved_no_rotation
 feed_count=0; ready=0
 while [ ! -e "$F/stop" ]; do
  verify_exact "$F/lock/owner" "$$ $self_birth $BOOT"
  [ "$(cat "$PROC/sys/kernel/random/boot_id")" = "$BOOT" ] || { state OWNER_REFUSED boot_changed; return 2; }
  live_birth=$(rb_birth "$child") || live_birth=none
  if [ "$live_birth" = none ]; then
   if [ -d "$PROC/$child" ]; then
    row=$(cat "$PROC/$child/stat" 2>/dev/null) || { state OWNER_REFUSED identity_unreadable_no_relaunch; return 2; }
    rest=${row##*) }; set -- $rest
    [ "${1:-none}" = Z ] || { state OWNER_REFUSED identity_unreadable_no_relaunch; return 2; }
   fi
   event process_exit; return 0
  fi
  [ "$live_birth" = "$child_birth" ] && child_owned "$child" "$child_birth" || { state OWNER_REFUSED child_identity_changed_no_signal; return 2; }
  polls=$((polls+1))
  if [ "$ready" = 0 ]; then
   label=unknown; capture_rc=0; classifier_rc=0
   if capture_frame; then
    label=$(timeout 2 "$F/screen-gate" "$F/current.jpeg" 2>"$F/classifier.log") || classifier_rc=$?
    [ "$classifier_rc" = 0 ] || label=unknown
    capture_context || label=unknown
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
    snapshot_error) feed_count=0; state UI_UNVERIFIED "snapshot_error_rc=$capture_rc reason=$capture_reason alive_no_cleanup";;
    *) feed_count=0; state UI_UNVERIFIED "label=$label classifier_rc=$classifier_rc alive_no_cleanup";;
   esac
  fi
  if [ "${TT_MAX_POLLS:-0}" -gt 0 ] && [ "$polls" -ge "$TT_MAX_POLLS" ]; then event observation_limit_no_app_control; return 0; fi
  sleep 3
 done
 state STOPPED existing_stop; return 0
}
# After a confirmed reentry spawn, supervise it; propagate fatal rc upward.
rc_after_spawn_ok() {
 [ "$#" = 2 ] && [ "$1" = "$child" ] && [ "$2" = "$child_birth" ] || return 2
 child_owned "$child" "$child_birth" || return 2
 monitor_child; mc_rc=$?
 [ "$mc_rc" = 0 ] || return "$mc_rc"
 # If a stop appeared during supervision, surface it so the loop ends cleanly.
 [ ! -e "$F/stop" ] || return 0
 return 0
}

main() {
 preconditions || return 2
 mkdir -p "$F" || return 2
 self_birth=$(rb_birth "$$") || { refuse SELF_IDENTITY_UNREADABLE; return 2; }
 mkdir "$F/lock" 2>/dev/null || { refuse LOCK_CONFLICT_NO_TAKEOVER; return 2; }
 write_exact "$F/lock/owner" "$$ $self_birth $BOOT"
 owner_verified=1
 trap release_lock EXIT
 trap 'state STOPPED supervisor_signal_no_app_control; exit 6' TERM INT
 for control in sequence instance.txt state events.log; do control_file "$F/$control"; done
 if [ -e "$F/sequence" ]; then
  seq=$(cat "$F/sequence") || io_fail sequence_read_failed
  case "$seq" in ''|*[!0-9]*) io_fail sequence_invalid;; esac
 fi
 write_exact "$F/sequence" "$seq"
 instance
 state SUPERVISOR_STARTING control_persistence_checked_before_launch
 capture_init
 parent=${TT_PARENT_PID:-none}; parent_birth=${TT_PARENT_BIRTH:-none}
 if [ "$parent" != none ]; then
  parent_owned "$parent" "$parent_birth" || { state OWNER_REFUSED existing_parent_identity; return 2; }
 else
  [ ! -S "$SOCKET" ] || { state OWNER_REFUSED socket_without_parent_identity; return 2; }
  if ! timeout 15 sh "$F/start-parent.sh" > "$F/parent-start.txt" 2>&1; then
   state START_FAILED parent_command_nonzero; return 3
  fi
  parent=$(cat "$F/parent-start.txt"); parent_birth=$(rb_birth "$parent") || { state START_FAILED parent_not_alive; return 3; }
  parent_owned "$parent" "$parent_birth" || { state OWNER_REFUSED new_parent_identity; return 2; }
 fi
 polls=0
 # Original first-launch chain: exactly one spawn, unchanged behaviour.
 verify_exact "$F/lock/owner" "$$ $self_birth $BOOT"
 [ ! -e "$F/stop" ] || { state STOPPED existing_stop; return 0; }
 [ "$(cat "$PROC/sys/kernel/random/boot_id")" = "$BOOT" ] || { state OWNER_REFUSED boot_changed; return 2; }
 parent_owned "$parent" "$parent_birth" || { state OWNER_REFUSED parent_identity_changed; return 2; }
 if [ -n "${TT_CHILD_PID:-}" ]; then
  child=$TT_CHILD_PID; child_birth=${TT_CHILD_BIRTH:-none}
  child_owned "$child" "$child_birth" || { state OWNER_REFUSED child_identity; return 2; }
  seq=$(cat "$F/sequence") || io_fail sequence_read_failed
  case "$seq" in ''|*[!0-9]*) io_fail sequence_invalid;; esac
  seq=$((seq+1)); write_exact "$F/sequence" "$seq"; instance
 else
  do_one_launch; first_rc=$?
  if [ "$first_rc" != 0 ]; then
   if [ "$do_spawn_started" = 1 ]; then
    state OWNER_REFUSED "first_launch_indeterminate_${do_reason:-spawn} app_parent_retained"; return 2
   fi
   state START_FAILED "first_launch_${do_reason:-spawn}"; return 3
  fi
 fi
 # Supervise the first child to exit, then hand off to manual reentry.
 if ! monitor_child; then return 2; fi
 [ ! -e "$F/stop" ] || { state STOPPED existing_stop; return 0; }
 # DERIVED TAIL: wait for a manual desktop->host icon tap for every later launch.
 state AWAITING_REENTRY child_exited_wait_manual_icon
 rc_reentry_loop
}
main "$@"
