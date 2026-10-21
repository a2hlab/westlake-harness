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
rb_json_bytes(){
 bytes=$(printf '%s' "$1" | od -An -v -tx1) || return 5
 for h in $bytes; do printf '\\u00%s' "$h" || return 5; done
}
rb_guard_json(){
 # One encoder process for all six NUL-delimited shell strings. Shell values
 # cannot contain NUL; all emitted value bytes retain the preceding JSON schema.
 audit_bytes=$(printf '%s\000' "${RB_AUDIT_PHASE:-strict}" "${RB_AUDIT_PID:-${p:-unknown}}" "${RB_AUDIT_BIRTH:-unknown}" "$1" "$2" "$3" | od -An -v -tx1) || return 5
 printf '{"phase":"' >&2 || return 5
 audit_field=0
 for audit_byte in $audit_bytes; do
  if [ "$audit_byte" = 00 ]; then
   audit_field=$((audit_field+1))
   case "$audit_field" in
    1) printf '","pid":"' >&2 || return 5;;
    2) printf '","birth":"' >&2 || return 5;;
    3) printf '","field":"' >&2 || return 5;;
    4) printf '","actual":"' >&2 || return 5;;
    5) printf '","expected":"' >&2 || return 5;;
    6) printf '"}\n' >&2 || return 5;;
    *) return 5;;
   esac
  else
   printf '\\u00%s' "$audit_byte" >&2 || return 5
  fi
 done
 [ "$audit_field" = 6 ]
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
rb_script_signal(){
 p=$1; expected=$2; script=$3
 [ -n "$expected" ] && [ "$(rb_birth "$p")" = "$expected" ] || return 1
 [ "$(rb_uid "$p")" = 0:0:0:0 ] || return 1
 [ "$(readlink "$RB_PROC/$p/exe" 2>/dev/null)" = /system/bin/sh ] || return 1
 tr '\000' '\n' < "$RB_PROC/$p/cmdline" | grep -Fxq "$script" || return 1
 [ "$(rb_birth "$p")" = "$expected" ] || return 1
 kill -15 "$p"
}
cev_decode() {
	cd_s=$1; cd_out=
	while [ -n "$cd_s" ]; do
		case "$cd_s" in
		?u00??*)
			cd_hh=${cd_s#?u00}; cd_hh=${cd_hh%"${cd_hh#??}"}
			case "$cd_hh" in
			[0-9a-fA-F][0-9a-fA-F])
				cd_out="$cd_out$(printf "\\$(printf '%03o' "0x$cd_hh")")"
				cd_s=${cd_s#??????}
				continue;;
			esac
			;;
		esac
		cd_out="$cd_out${cd_s%"${cd_s#?}"}"; cd_s=${cd_s#?}
	done
	printf '%s' "$cd_out"
}
owned_failure_kind() {
	ofk_last=$(printf '%s\n' "$1" | grep '"field":' | tail -n 1)
	[ -n "$ofk_last" ] || { echo mismatch; return 0; }
	ofk_f=${ofk_last#*\"field\":\"}; ofk_f=${ofk_f%%\"*}
	ofk_a=${ofk_last#*\"actual\":\"}; ofk_a=${ofk_a%%\"*}
	ofk_field=$(cev_decode "$ofk_f"); ofk_actual=$(cev_decode "$ofk_a")
	case "$ofk_field" in
	birth|birth_after|uid|exe|namespace|private_inode|ppid)
		case "$ofk_actual" in '<'*) echo death; return 0;; esac;;
	exe_sha)
		[ -n "$ofk_actual" ] || { echo death; return 0; };;
	esac
	echo mismatch
}
cev_parse_stat() {
	cps_pid=$1; cps_birth=$2; cps_row=$3
	[ -n "$cps_row" ] || { echo refuse:stat_empty; return 0; }
	cps_f1=${cps_row%% *}
	[ "$cps_f1" = "$cps_pid" ] || { echo refuse:stat_pid_mismatch; return 0; }
	# comm is parenthesised and may contain spaces: split after the LAST ") ".
	case "$cps_row" in *") "*) :;; *) echo refuse:stat_malformed; return 0;; esac
	cps_rest=${cps_row##*) }
	# shellcheck disable=SC2086
	set -- $cps_rest
	# After ") ": $1=state ... $20=starttime (stat field 22). Need at least 20 fields.
	[ "$#" -ge 20 ] || { echo refuse:stat_short; return 0; }
	cps_state=$1; cps_start=${20}
	case "$cps_start" in ''|*[!0-9]*) echo refuse:stat_malformed_starttime; return 0;; esac
	# Different birth under the same pid == PID reuse: never an exit of OUR child.
	[ "$cps_start" = "$cps_birth" ] || { echo "refuse:pid_reused_birth_$cps_start"; return 0; }
	# Same birth but not a zombie: alive while ownership failed => identity change.
	[ "$cps_state" = Z ] || { echo "refuse:alive_ownership_failed_state_$cps_state"; return 0; }
	echo exited
}
cev_root_verified() {
	crv_b=$(cat "$1/sys/kernel/random/boot_id" 2>/dev/null) || return 1
	[ -n "$crv_b" ] || return 1
	case "$crv_b" in *[!0-9a-f-]*) return 1;; esac
	[ -z "$2" ] || [ "$crv_b" = "$2" ]
}
cev_pid_listed() {
	cpl_root=$1; cpl_pid=$2
	[ -d "$cpl_root" ] || return 2
	cpl_err=$( { ls -1 "$cpl_root" >/dev/null; } 2>&1 ); cpl_rc=$?
	[ "$cpl_rc" = 0 ] || return 2
	[ -z "$cpl_err" ] || return 2
	cpl_list=$(ls -1 "$cpl_root" 2>/dev/null) || return 2
	[ -n "$cpl_list" ] || return 2
	for cpl_e in $cpl_list; do
		[ "$cpl_e" = "$cpl_pid" ] && return 0
	done
	return 1
}
child_exit_verdict() {
	cev_pid=$1; cev_birth=$2; cev_boot=${3:-}
	case "$cev_pid" in ''|*[!0-9]*) echo refuse:bad_pid_argument; return 0;; esac
	case "$cev_birth" in ''|*[!0-9]*) echo refuse:bad_birth_argument; return 0;; esac
	cev_proc=${PROC:-/proc}
	# 1) ONE complete stat read first (no `-d` pre-test: a dir that exists at the test
	#    and is gone at the read is exactly the race we must not misjudge).
	if cev_row=$(cat "$cev_proc/$cev_pid/stat" 2>/dev/null); then
		cev_parse_stat "$cev_pid" "$cev_birth" "$cev_row"; return 0
	fi
	# 2) Stat read failed: absence may only be proven on the IDENTITY-VERIFIED proc
	#    root (boot_id readable and equal to the monitored boot), via a SUCCESSFUL
	#    complete PID listing that does not contain the pid.
	cev_root_verified "$cev_proc" "$cev_boot" || { echo unknown; return 0; }
	cev_pid_listed "$cev_proc" "$cev_pid"; cev_l=$?
	case "$cev_l" in
	1) echo exited; return 0;;          # verified root listed, pid confirmed absent
	2) echo unknown; return 0;;         # listing failed: prove nothing
	esac
	# 3) Pid is still listed: re-read; only same-birth Z is an exit, else unknown.
	if cev_row=$(cat "$cev_proc/$cev_pid/stat" 2>/dev/null); then
		cev_parse_stat "$cev_pid" "$cev_birth" "$cev_row"; return 0
	fi
	echo unknown
}
rc_retire_child() { ret_key="$BOOT $seq $child $child_birth"; event child_retired "key=$BOOT/$seq/$child/$child_birth strict_exited"; }
rc_retired_current() { [ -n "$ret_key" ] && [ "$ret_key" = "$BOOT $seq $child $child_birth" ]; }
rc_retire_clear() { [ -z "$ret_key" ] || { ret_key=; event child_retirement_cleared "$1"; }; }
uptime_s() { read up rest < "$PROC/uptime" || return 1; echo "${up%%.*}"; }
refuse() { echo "R1-REFUSE $*" >&2; return 1; }
rc_send_term() { kill -15 "$1"; }
rc_run_start_parent() { timeout 15 sh "$F/start-parent.sh" > "$1" 2>&1; }
rc_file_id() { stat -c '%d:%i' "$1" 2>/dev/null; }
rc_proc_live() { [ "$(rb_birth "$$" 2>/dev/null)" = "$self_birth" ]; }
rc_stop_present() { [ -e "$F/stop" ] || [ -L "$F/stop" ]; }
rc_sleep() { sleep 1; }
rc_event() { event "$@"; }
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
parent_window_reason() {
 parent_owned "$1" "$2" || { echo parent_identity; return 0; }
 pwr_fg=$3
 case "$pwr_fg" in ''|*[!0-9]*) echo focus_wid_invalid; return 0;; esac
 pwr_fields=$(timeout 2 strings "$PROC/$1/environ" 2>/dev/null) || { echo parent_fields_unreadable; return 0; }
 pwr_wid=$(printf '%s\n' "$pwr_fields" | grep -E '^WL_PARENT_ID=[0-9]+$') || { echo parent_wid_missing; return 0; }
 pwr_uid=$(printf '%s\n' "$pwr_fields" | grep -E '^ASX_RUNTIME_OWNER_UID=[0-9]+$') || { echo parent_uid_missing; return 0; }
 [ "$(printf '%s\n' "$pwr_wid" | wc -l)" -eq 1 ] || { echo parent_wid_ambiguous; return 0; }
 [ "$(printf '%s\n' "$pwr_uid" | wc -l)" -eq 1 ] || { echo parent_uid_ambiguous; return 0; }
 [ "${pwr_uid#ASX_RUNTIME_OWNER_UID=}" = "$RB_OWNER_UID" ] || { echo parent_uid_mismatch; return 0; }
 parent_owned "$1" "$2" || { echo parent_identity; return 0; }
 [ "${pwr_wid#WL_PARENT_ID=}" = "$pwr_fg" ] && { echo match; return 0; }
 echo wid_mismatch
}
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
rc_stat_ppid() { # <pid>: ppid; rc 3 = entry vanished, rc 1 = unreadable or malformed existing entry
 sp_pid=$1
 sp_raw=$(cat "$PROC/$sp_pid/stat" 2>/dev/null) || { [ -e "$PROC/$sp_pid" ] || [ -L "$PROC/$sp_pid" ] || return 3; return 1; }
 case "$sp_raw" in "$sp_pid ("*") "*) :;; *) return 1;; esac
 sp_rest=${sp_raw##*) }; set -- $sp_rest
 [ "$#" -ge 20 ] || return 1
 case "$1" in R|S|D|Z|T|t|X|x|K|W|P|I) :;; *) return 1;; esac
 case "$2" in ''|*[!0-9]*) return 1;; esac
 echo "$2"
}
rc_direct_children() { # <parent>: child PIDs; rc 1 unless the enumeration is complete
 rc_proc_live || return 1
 dc_parent=$1; dc_seen=0
 for dc_row in "$PROC"/[0-9]*; do
  [ -e "$dc_row" ] || [ -L "$dc_row" ] || continue
  dc_pid=${dc_row##*/}
  case "$dc_pid" in *[!0-9]*) continue;; esac
  dc_seen=$((dc_seen+1))
  dc_pp=$(rc_stat_ppid "$dc_pid"); dc_rc=$?
  [ "$dc_rc" = 3 ] && continue
  [ "$dc_rc" = 0 ] || return 1
  [ "$dc_pp" = "$dc_parent" ] && echo "$dc_pid"
 done
 [ "$dc_seen" -gt 0 ] || return 1
 return 0
}
rc_owned_pids_strict() { # owned route-b processes; rc 1 if any existing entry cannot be classified
 rc_proc_live || return 1
 op_seen=0; op_want="$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID"
 for op_row in "$PROC"/[0-9]*; do
  [ -e "$op_row" ] || [ -L "$op_row" ] || continue
  op_p=${op_row##*/}
  case "$op_p" in *[!0-9]*) continue;; esac
  op_seen=$((op_seen+1))
  op_uid=$(rb_uid "$op_p" 2>/dev/null) || { [ -e "$op_row" ] && return 1; continue; }
  [ "$op_uid" = "$op_want" ] || continue
  if ( RB_AUDIT_QUIET=1; rb_owned "$op_p" ) 2>/dev/null; then echo "$op_p"; continue; fi
  [ -e "$op_row" ] || continue
  # Same uid but not owned: only a readable non-route-b exe is decisive; anything else is unknown.
  op_exe=$(readlink "$PROC/$op_p/exe" 2>/dev/null) || return 1
  case "$op_exe" in /data/local/tmp/asx/asx-spawner|'/data/local/tmp/asx/asx-spawner (deleted)'|/data/local/tmp/asx/appspawn-x|'/data/local/tmp/asx/appspawn-x (deleted)') return 1;; esac
 done
 [ "$op_seen" -gt 0 ] || return 1
 return 0
}
rc_socket_inode_of() { # <pid>: inode of the unique LISTENING stream/seqpacket row for $SOCKET in its net view
 si_line=$(grep -E " $SOCKET\$" "$PROC/$1/net/unix" 2>/dev/null) || return 1
 [ "$(printf '%s\n' "$si_line" | wc -l)" -eq 1 ] || return 1
 set -- $si_line
 [ "$#" -eq 8 ] || return 1
 [ "$4" = 00010000 ] || return 1
 case "$5" in 0001|0005) :;; *) return 1;; esac
 [ "$6" = 01 ] || return 1
 [ "$8" = "$SOCKET" ] || return 1
 case "$7" in ''|*[!0-9]*) return 1;; esac
 echo "$7"
}
rc_fd_holders() { # <inode>: PIDs holding socket:[inode]; rc 1 unless every existing fd entry was read
 rc_proc_live || return 1
 fh_seen=0
 for fh_row in "$PROC"/[0-9]*; do
  [ -e "$fh_row" ] || [ -L "$fh_row" ] || continue
  case "${fh_row##*/}" in *[!0-9]*) continue;; esac
  fh_seen=$((fh_seen+1))
  if [ ! -d "$fh_row/fd" ]; then [ -e "$fh_row" ] && return 1; continue; fi
  fh_list=$(ls "$fh_row/fd" 2>/dev/null) || { [ -e "$fh_row" ] && return 1; continue; }
  for fh_fd in $fh_list; do
   fh_l=$(readlink "$fh_row/fd/$fh_fd" 2>/dev/null) || { if [ -e "$fh_row/fd/$fh_fd" ] || [ -L "$fh_row/fd/$fh_fd" ]; then return 1; fi; continue; }
   [ "$fh_l" = "socket:[$1]" ] && { echo "${fh_row##*/}"; break; }
  done
 done
 [ "$fh_seen" -gt 0 ] || return 1
 return 0
}
rc_epoch_binding() { # <pid> <birth>: "mntns=.. sock=.. sockfile=.." of a parent proven to own the listener alone
 eb_ns=$(readlink "$PROC/$1/ns/mnt" 2>/dev/null) || return 1
 [ -n "$eb_ns" ] || return 1
 eb_sock=$(rc_socket_inode_of "$1") || return 1
 # Same listener visible in the guardian's own net view, so a later empty view is meaningful.
 [ "$(rc_socket_inode_of "$$")" = "$eb_sock" ] || return 1
 eb_h=$(rc_fd_holders "$eb_sock") || return 1
 [ "$(echo $eb_h)" = "$1" ] || return 1
 eb_file=$(rc_file_id "$SOCKET") || return 1
 [ "$(rb_birth "$1" 2>/dev/null)" = "$2" ] || return 1
 echo "mntns=$eb_ns sock=$eb_sock sockfile=$eb_file"
}
rc_epoch_field() { # <record> <key>: value of key=value token
 for ef_tok in $1; do case "$ef_tok" in "$2="*) echo "${ef_tok#"$2="}"; return 0;; esac; done
 return 1
}
rc_record_bootstrap_epoch() { # after the guardian itself started the parent; never fatal for r3 first launch
 rb_bind=$(rc_epoch_binding "$parent" "$parent_birth") || { write_exact "$F/parent-epoch" "phase=unbound parent=$parent:$parent_birth"; return 0; }
 write_exact "$F/parent-epoch" "phase=bound parent=$parent:$parent_birth $rb_bind"
}
rc_wait_exit() { # <pid> <birth>: 0 entry gone in a live proc view, 2 same process, 3 pid reused, 1 unknown
 we_n=0
 while :; do
  if we_b=$(rb_birth "$1" 2>/dev/null); then
   [ "$we_b" = "$2" ] || return 3
   we_last=2
  elif [ ! -e "$PROC/$1" ] && [ ! -L "$PROC/$1" ]; then
   rc_proc_live && return 0
   return 1
  else
   we_last=1
  fi
  [ "$we_n" -lt 50 ] || return "$we_last"
  sleep .1; we_n=$((we_n+1))
 done
}
rc_parent_epoch_switch() {
 pe_wid=$1; rc_epoch_reason=
 [ "$rc_epoch_hold" = 0 ] || { rc_epoch_reason=epoch_hold; return 2; }
 pe_old=$parent; pe_ob=$parent_birth
 parent_owned "$pe_old" "$pe_ob" || { rc_epoch_reason=old_parent_identity; return 1; }
 # Signal authority is the guardian's own recorded epoch, not read-only matching: the record must name
 # this exact parent and its bound namespace/listener/socket file must be unchanged now.
 pe_rec=$(cat "$F/parent-epoch" 2>/dev/null) || { rc_epoch_reason=epoch_record_missing; return 1; }
 case "$(rc_epoch_field "$pe_rec" phase)" in bound|switched) :;; *) rc_epoch_reason=epoch_not_bound; return 1;; esac
 [ "$(rc_epoch_field "$pe_rec" parent)" = "$pe_old:$pe_ob" ] || { rc_epoch_reason=epoch_parent_mismatch; return 1; }
 pe_now=$(rc_epoch_binding "$pe_old" "$pe_ob") || { rc_epoch_reason=socket_owner_unknown; return 1; }
 [ "$pe_now" = "mntns=$(rc_epoch_field "$pe_rec" mntns) sock=$(rc_epoch_field "$pe_rec" sock) sockfile=$(rc_epoch_field "$pe_rec" sockfile)" ] || { rc_epoch_reason=epoch_binding_changed; return 1; }
 pe_sock=$(rc_epoch_field "$pe_rec" sock); pe_sockfile=$(rc_epoch_field "$pe_rec" sockfile)
 pe_kids=$(rc_direct_children "$pe_old") || { rc_epoch_reason=children_unknown; return 1; }
 [ -z "$pe_kids" ] || { rc_epoch_reason="children_present:$(echo $pe_kids)"; return 1; }
 pe_owned=$(rc_owned_pids_strict) || { rc_epoch_reason=owned_enumeration_unknown; return 1; }
 [ -z "$pe_owned" ] || { rc_epoch_reason="owned_present:$(echo $pe_owned)"; return 1; }
 write_exact "$F/parent-epoch" "phase=stopping old=$pe_old:$pe_ob wid=$pe_wid sock=$pe_sock sockfile=$pe_sockfile"
 # Last look immediately before the signal. Children are only created by host_spawn requests this
 # single-threaded guardian sends under its lock, so none is requested between here and the TERM.
 parent_owned "$pe_old" "$pe_ob" || { rc_epoch_reason=old_parent_identity_before_signal; return 2; }
 pe_kids=$(rc_direct_children "$pe_old") || { rc_epoch_reason=children_unknown_before_signal; return 2; }
 [ -z "$pe_kids" ] || { rc_epoch_reason="children_present_before_signal:$(echo $pe_kids)"; return 2; }
 rc_epoch_hold=1   # from here on any failure is partial: never start a second parent
 rc_event parent_epoch_stop "old=$pe_old:$pe_ob wid=$pe_wid sock=$pe_sock"
 rc_send_term "$pe_old" || { rc_epoch_reason=old_parent_signal_failed; return 2; }
 rc_wait_exit "$pe_old" "$pe_ob"; pe_exit=$?
 case "$pe_exit" in
 0) : ;;
 2) rc_epoch_reason=old_parent_not_exited; return 2;;
 3) rc_epoch_reason=old_parent_pid_reused; return 2;;
 *) rc_epoch_reason=old_parent_exit_unknown; return 2;;
 esac
 pe_holders=$(rc_fd_holders "$pe_sock") || { rc_epoch_reason=socket_holders_unknown_after_exit; return 2; }
 [ -z "$pe_holders" ] || { rc_epoch_reason="socket_still_held:$(echo $pe_holders)"; return 2; }
 # The pathname must still be the recorded file and no process may listen on it any more.
 [ -e "$SOCKET" ] || [ -L "$SOCKET" ] || { rc_epoch_reason=socket_file_vanished; return 2; }
 [ "$(rc_file_id "$SOCKET")" = "$pe_sockfile" ] || { rc_epoch_reason=socket_file_replaced; return 2; }
 [ -r "$PROC/$$/net/unix" ] || { rc_epoch_reason=socket_listener_after_exit_unknown; return 2; }
 pe_l=$(grep -c -E " $SOCKET\$" "$PROC/$$/net/unix" 2>/dev/null)
 [ "$pe_l" = 0 ] || { rc_epoch_reason="socket_listener_after_exit:${pe_l:-unknown}"; return 2; }
 rm -f "$SOCKET" || { rc_epoch_reason=socket_unlink_failed; return 2; }
 pe_out="$F/parent-start-epoch.txt"
 rc_run_start_parent "$pe_out" || { rc_epoch_reason=new_parent_start_nonzero; return 2; }
 pe_new=$(cat "$pe_out" 2>/dev/null) || { rc_epoch_reason=new_parent_output_unreadable; return 2; }
 case "$pe_new" in ''|*[!0-9]*) rc_epoch_reason=new_parent_pid_invalid; return 2;; esac
 pe_nb=$(rb_birth "$pe_new") || { rc_epoch_reason=new_parent_not_alive; return 2; }
 parent_owned "$pe_new" "$pe_nb" || { rc_epoch_reason=new_parent_identity; return 2; }
 # start-parent.sh re-reads the foreground WID itself; the new parent must be bound to the exact
 # WID that triggered this switch (same WID gate as host focus), else no spawn.
 pe_bound=$(verify_parent_window_soft "$pe_new" "$pe_nb" "$pe_wid") || { rc_epoch_reason="new_parent_wid_$(parent_window_reason "$pe_new" "$pe_nb" "$pe_wid")"; return 2; }
 [ "$pe_bound" = "$pe_wid" ] || { rc_epoch_reason=new_parent_wid_mismatch; return 2; }
 pe_nbind=$(rc_epoch_binding "$pe_new" "$pe_nb") || { rc_epoch_reason=new_parent_socket_unproven; return 2; }
 write_exact "$F/parent-epoch" "phase=switched old=$pe_old:$pe_ob parent=$pe_new:$pe_nb wid=$pe_wid $pe_nbind"
 parent=$pe_new; parent_birth=$pe_nb
 # spawn.sh reads TT_PARENT_PID/TT_PARENT_BIRTH from the environment unless AUTH_PARENT_MODE=new
 # (then from parent-identity, which start-parent.sh rewrote and read back); keep both in step.
 TT_PARENT_PID=$pe_new; TT_PARENT_BIRTH=$pe_nb; export TT_PARENT_PID TT_PARENT_BIRTH
 instance
 rc_epoch_hold=0
 rc_event parent_epoch_switched "old=$pe_old:$pe_ob new=$pe_new:$pe_nb wid=$pe_wid"
 return 0
}
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
rc_capture_wms() {
 cw_out=$1
 control_file "$cw_out"
 rm -f "$cw_out" 2>/dev/null || :
 timeout 2 hidumper -s WindowManagerService -a '-a' > "$cw_out" 2>/dev/null || { rm -f "$cw_out" 2>/dev/null || :; return 1; }
 [ -s "$cw_out" ] || { rm -f "$cw_out" 2>/dev/null || :; return 1; }
 return 0
}
rc_focus_state() {
 rc_focus_reason=
 rc_capture_wms "$F/wms-focus.txt" || { rc_focus_result=error; return 0; }
 fs_focus=$(rc_parse_focus "$F/wms-focus.txt")
 [ "$fs_focus" != error ] || { rc_focus_result=error; return 0; }
 # shellcheck disable=SC2086
 set -- $fs_focus
 fs_name=${1:-}; fs_pid=${2:-}; fs_wid=${3:-}
 if [ "$fs_name" = imehost0 ]; then
  rc_verify_window_process "$fs_pid" "$RB_OWNER_UID" org.westlake.imehost || { rc_focus_reason=host_process_unverified; rc_focus_result=other; return 0; }
  fs_host_birth=$RC_WINDOW_BIRTH
  if ! fs_fg=$(verify_parent_window_soft "$parent" "$parent_birth" "$fs_wid"); then
   rc_focus_reason=$(parent_window_reason "$parent" "$parent_birth" "$fs_wid")
   if [ "$rc_focus_reason" = wid_mismatch ] && [ "$(rb_birth "$fs_pid")" = "$fs_host_birth" ]; then
    rc_focus_result="newhost $fs_wid"; return 0
   fi
   rc_focus_result=other; return 0
  fi
  [ "$(rb_birth "$fs_pid")" = "$fs_host_birth" ] || { rc_focus_reason=host_birth_changed; rc_focus_result=other; return 0; }
  [ "$fs_fg" = "$fs_wid" ] || { rc_focus_reason=parent_window_mismatch; rc_focus_result=other; return 0; }
  rc_focus_result="host $fs_wid"; return 0
 fi
 if rc_desktop_name "$fs_name"; then
  rc_verify_desktop "$fs_pid" || { rc_focus_reason=desktop_unverified; rc_focus_result=other; return 0; }
  rc_focus_result=desktop; return 0
 fi
 rc_focus_result=other
 return 0
}
rc_owned_window_present() {
 rc_capture_wms "$F/wms-owned.txt" || { rc_owned_result=unknown; return 0; }
 # r4b: an incomplete owned-process enumeration is unknown, never an empty set (T37 rc7-as-empty).
 ow_extra=$(rc_owned_pids_strict) || { rc_owned_result=unknown; return 0; }
 rc_owned_result=$(rc_parse_owned_window "$F/wms-owned.txt" "$child $ow_extra") || rc_owned_result=unknown
 # r3: a retired PID may now belong to a stranger; a window matched only through it is
 # unattributable (unknown, never owned and never no). The retired PID stays in the set.
 if [ "$rc_owned_result" = yes ] && rc_retired_current; then
  ow_other=$(rc_parse_owned_window "$F/wms-owned.txt" "$ow_extra") || ow_other=unknown
  [ "$ow_other" = yes ] || rc_owned_result=unknown
 fi
 return 0
}
rc_verdict_to_state() {
 case "$1" in
  exited) echo gone;;
  unknown) echo unknown;;
  *) echo invalid;;
 esac
}
rc_child_state() {
 [ -n "$child" ] && [ "$child" != none ] || { echo gone; return 0; }
 # r3: the exact strictly-exited instance is gone; its PID is not re-read (reuse-safe).
 if rc_retired_current; then echo gone; return 0; fi
 cs_b=$(rb_birth "$child" 2>/dev/null) || {
  # First read failed: same verdict as the monitor (r2 race fix); unknown stays unknown.
  rc_verdict_to_state "$(child_exit_verdict "$child" "$child_birth" "$BOOT")"; return 0
 }
 # A different birth on the first read is PID reuse: invalid, never laundered.
 [ "$cs_b" = "$child_birth" ] || { echo invalid; return 0; }
 cs_err=$(child_owned "$child" "$child_birth" 2>&1 >/dev/null) && { echo alive; return 0; }
 # Ownership failed after a matching read: only a child-death related read failure
 # is classified; a confirmed value mismatch is invalid regardless of what follows.
 case "$(owned_failure_kind "$cs_err")" in
  death) rc_verdict_to_state "$(child_exit_verdict "$child" "$child_birth" "$BOOT")";;
  *) echo invalid;;
 esac
}
do_one_launch() {
 do_reason=; do_spawn_started=0
 verify_exact "$F/lock/owner" "$$ $self_birth $BOOT"
 do_owned=$(rc_owned_pids_strict) || { do_reason=owned_enumeration_unknown; return 2; }
 [ -z "$do_owned" ] || { do_reason=existing_child_without_attach_identity; return 2; }
 do_spawn_started=1
 rc_retire_clear spawn_started
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
monitor_child() {
 state BOOTSTRAP data_preserved_no_rotation
 feed_count=0; ready=0
 while [ ! -e "$F/stop" ]; do
  verify_exact "$F/lock/owner" "$$ $self_birth $BOOT"
  [ "$(cat "$PROC/sys/kernel/random/boot_id")" = "$BOOT" ] || { state OWNER_REFUSED boot_changed; return 2; }
  live_birth=$(rb_birth "$child") || live_birth=none
  if [ "$live_birth" = none ]; then
   # First read failed (zombie / absent / unreadable): ONE complete stat read decides.
   # exited only for confirmed-absent or same-pid+same-birth+Z; everything else
   # (PID reuse, malformed, unreadable) stays refused. (r2: the old Z branch did not
   # verify the birth.)
   exit_v=$(child_exit_verdict "$child" "$child_birth" "$BOOT")
   case "$exit_v" in
    exited) event process_exit "first_read_$exit_v"; rc_retire_child; return 0;;
    *) state OWNER_REFUSED "identity_unreadable_or_reused_no_relaunch verdict=$exit_v"; return 2;;
   esac
  fi
  # A different birth on the FIRST read is PID reuse: refuse outright. It can never be
  # laundered into an exit by a later disappearance (ownership guard is not consulted).
  [ "$live_birth" = "$child_birth" ] || { state OWNER_REFUSED child_identity_changed_no_signal; return 2; }
  # Run the frozen ownership guard, keeping its deny JSON (stderr) for classification
  # AND re-emitting it on stderr so the original audit trail is unchanged.
  owned_err=$(child_owned "$child" "$child_birth" 2>&1 >/dev/null); owned_rc=$?
  if [ "$owned_rc" != 0 ]; then
   [ -z "$owned_err" ] || printf '%s\n' "$owned_err" >&2
   case "$(owned_failure_kind "$owned_err")" in
    death)
     # Only a child-death related read failure may be classified. A proven exit
     # enters the manual-icon wait; reuse / malformed / unknown stays refused.
     exit_v=$(child_exit_verdict "$child" "$child_birth" "$BOOT")
     case "$exit_v" in
      exited) event process_exit during_ownership_check; rc_retire_child; return 0;;
      *) state OWNER_REFUSED "child_identity_changed_no_signal verdict=$exit_v"; return 2;;
     esac;;
    *)
     # Confirmed value mismatch (uid/exe/inode/ns/ppid, or a different numeric birth
     # between reads): fixed refuse, the verdict is NOT consulted, so a later
     # disappearance can never launder it into an exit.
     state OWNER_REFUSED "child_identity_changed_no_signal confirmed_mismatch_no_verdict"; return 2;;
   esac
  fi
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
  rc_record_bootstrap_epoch
 fi
 polls=0
 # Original first-launch chain: exactly one spawn, unchanged behaviour.
 verify_exact "$F/lock/owner" "$$ $self_birth $BOOT"
 [ ! -e "$F/stop" ] || { state STOPPED existing_stop; return 0; }
 [ "$(cat "$PROC/sys/kernel/random/boot_id")" = "$BOOT" ] || { state OWNER_REFUSED boot_changed; return 2; }
 parent_owned "$parent" "$parent_birth" || { state OWNER_REFUSED parent_identity_changed; return 2; }
 if [ -n "${TT_CHILD_PID:-}" ]; then
  child=$TT_CHILD_PID; child_birth=${TT_CHILD_BIRTH:-none}
  rc_retire_clear adopt
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
rc_reentry_loop() {
	rc_arm=UNARMED
	rc_hold=0
	rc_gate_reason=
	while :; do
		# Stop always wins and is never deleted or signalled away.
		if rc_stop_present; then
			rc_event STOPPED existing_stop_no_delete
			return 0
		fi
		# Changed boot / lost lock / lost-or-reused parent is fatal: retain the lock
		# (caller EXIT trap), never signal the parent, never touch stop.
		if ! rc_gates_ok; then
			keep_lock=1
			rc_event OWNER_REFUSED "gate=${rc_gate_reason:-unknown}_no_signal_no_stop_delete"
			return 2
		fi

		rc_focus_result=error
        rc_focus_state
        rc_focus_status=$?
        [ "$rc_focus_status" = 0 ] || { keep_lock=1; return 2; }
        rc_focus=$rc_focus_result
		# shellcheck disable=SC2086
		set -- $rc_focus
		rc_fkind=${1:-error}
		rc_fwid=${2:-}

		case "$rc_fkind" in
		error)
				# A gap cannot prove a desktop-to-host transition. Require a new desktop.
				rc_arm=UNARMED
			rc_sleep
			continue
			;;
		other)
			# A non-desktop, non-host focused window cancels any pending qualification.
			# r4: an explicit reason from rc_focus_state is logged once per change (no silent other).
			if [ -n "${rc_focus_reason:-}" ] && [ "${rc_focus_reason:-}" != "${rc_last_other_reason:-}" ]; then
				rc_event focus_other "reason=$rc_focus_reason"
			fi
			rc_last_other_reason=${rc_focus_reason:-}
			rc_arm=UNARMED
			rc_sleep
			continue
			;;
		desktop)
			# Verified desktop focus arms the trigger. Quiet on repeats.
			[ "$rc_arm" = DESKTOP_SEEN ] || rc_arm=DESKTOP_SEEN
			rc_sleep
			continue
			;;
		host|newhost)
			rc_last_other_reason=
			if [ "$rc_arm" != DESKTOP_SEEN ]; then
				# Host foreground without a preceding desktop focus (host-at-start,
				# notification->host, or already consumed): consume silently, no spawn.
				rc_arm=HOST_CONSUMED
				rc_sleep
				continue
			fi
			# Genuine desktop->host transition: at most one spawn.
			rc_arm=HOST_CONSUMED

			if [ "$rc_hold" = 1 ]; then
				rc_event reentry_hold_fail_closed "wid=$rc_fwid"
				rc_sleep
				continue
			fi

				rc_child=$(rc_child_state 2>/dev/null) || rc_child=unknown
				if [ "$rc_child" = invalid ]; then
					keep_lock=1
					rc_event OWNER_REFUSED child_identity_no_spawn
					return 2
				fi
			rc_owned_result=unknown
                rc_owned_window_present
                rc_owned_status=$?
                [ "$rc_owned_status" = 0 ] || { keep_lock=1; return 2; }
                rc_win=$rc_owned_result
			if [ "$rc_child" != gone ] || [ "$rc_win" != no ]; then
				# Child alive, any owned (incl. hidden) window, or indeterminate:
				# consume, do NOT terminate, do NOT spawn.
				rc_event consume_live_or_window "child=$rc_child win=$rc_win wid=$rc_fwid"
				rc_sleep
				continue
			fi

			# Re-verify gates immediately before the single spawn.
			if ! rc_gates_ok; then
					keep_lock=1
					rc_event refuse_gate "gate=${rc_gate_reason:-unknown}_no_spawn_no_signal"
					return 2
			fi
			if [ "$rc_fkind" = newhost ]; then
				# r4: recreated host. Switch the parent epoch once (exact old parent, no child,
				# proven socket owner), then fall through to the unchanged single spawn.
				rc_parent_epoch_switch "$rc_fwid"
				rc_epoch_rc=$?
				case "$rc_epoch_rc" in
				0) : ;;
				1)
					rc_event parent_epoch_refused "reason=${rc_epoch_reason:-unknown} wid=$rc_fwid"
					rc_arm=UNARMED
					rc_sleep
					continue
					;;
				*)
					# Partial/unknown after an action: sticky hold, never a second parent or spawn.
					rc_hold=1
					rc_event parent_epoch_partial_hold "reason=${rc_epoch_reason:-unknown} wid=$rc_fwid"
					rc_arm=UNARMED
					rc_sleep
					continue
					;;
				esac
				if ! rc_gates_ok; then
					keep_lock=1
					rc_event refuse_gate "gate=${rc_gate_reason:-unknown}_after_epoch_no_spawn"
					return 2
				fi
			fi

				# Both calls run in this shell: child/birth/seq and fatal exits persist.
				rc_spawn_result=
				rc_do_spawn
				rc_spawn_rc=$?
				rc_spawn=$rc_spawn_result
				rc_classify_spawn "$rc_spawn_rc" "$rc_spawn"
			case "$rc_sres" in
			ok)
				rc_event reentry_spawn_ok "$rc_spawn"
				# Supervise the fresh child until it exits; a live child means later
				# host edges are consumed, so no second spawn while it lives.
				if ! rc_after_spawn_ok "$rc_spawn_pid" "$rc_spawn_birth"; then
					# Identity / IO failure during supervision is fatal; propagate up.
					keep_lock=1
					rc_event SUPERVISOR_FAILED child_identity_or_io_no_signal
					return 2
				fi
				# Child confirmed gone: require a fresh desktop->host for the next spawn.
				rc_arm=UNARMED
				;;
			fail)
				# Proven no child was created: wait for the NEXT desktop->host tap.
				rc_event reentry_spawn_fail "$rc_spawn"
				rc_arm=UNARMED
				;;
			*)
				# Unknown child status => fail closed: sticky hold, never spawn again.
				rc_hold=1
				rc_event reentry_spawn_unknown_hold "$rc_spawn"
				rc_arm=UNARMED
				;;
			esac
			rc_sleep
			continue
			;;
		*)
				# Unexpected tokens cancel any earlier qualification.
				rc_arm=UNARMED
			rc_sleep
			continue
			;;
		esac
	done
}
rc_classify_spawn() {
 _rc_rc=$1
 _rc_line=$2
 rc_sres=unknown; rc_spawn_pid=; rc_spawn_birth=
 case "$_rc_line" in
 *"
"*) return 0;;
 esac
 # Disable pathname expansion for untrusted protocol text; restore caller flags.
 case $- in *f*) _rc_glob_off=1;; *) _rc_glob_off=0; set -f;; esac
 set -- $_rc_line
 [ "$_rc_glob_off" = 1 ] || set +f
 if [ "$_rc_rc" = 0 ] && [ "$#" = 3 ] && [ "$1" = ok ]; then
  case "$2" in ''|0|1|*[!0-9]*) return 0;; esac
  case "$3" in ''|*[!0-9]*) return 0;; esac
  rc_spawn_pid=$2; rc_spawn_birth=$3; rc_sres=ok
 elif [ "$_rc_rc" = 0 ] && [ "$#" = 2 ] && [ "$1" = fail ]; then
  rc_sres=fail
 fi
 return 0
}
#!/system/bin/sh
# File interface compatible with reentry-seams.sh@900c54a2.
# Table rules reused from candidate-r3/strict_wm.sh. No device calls, awk or Python.
rc_isnat() { case "$1" in ''|*[!0-9]*) return 1;; *) return 0;; esac; }
rc_isint() {
 case "$1" in
 ''|-) return 1;;
 -*) rc_isnat "${1#-}";;
 *) rc_isnat "$1";;
 esac
}

# One complete read; output: name pid wid z owned(yes|no).
# Subshell confines parser variables and noglob to this validator.
rc_validate_wms() (
 set -f
 [ "$#" = 2 ] && [ -f "$1" ] && [ -r "$1" ] || return 1
 rc_file=$1; rc_owned=$2
 for rc_pid in $rc_owned; do
  rc_isnat "$rc_pid" && [ "$rc_pid" -gt 0 ] || return 1
 done
 rc_header=0; rc_footer=0; rc_focuses=0; rc_all=0; rc_high=0
 rc_count=0; rc_total=0; rc_focus=; rc_rows=; rc_ids=' '; rc_result=no
 rc_boot=0; rc_remote=0
 while IFS= read -r rc_line || [ -n "$rc_line" ]; do
  set -- $rc_line
  [ "$#" -gt 0 ] || continue
  case "$1" in -*) continue;; esac
  if [ "$1" = WindowName ]; then
   [ "$rc_header" = 0 ] && [ "$rc_footer" = 0 ] && [ "$#" -ge 10 ] || return 1
   [ "$1:$2:$3:$4:$5:$6:$7:$8:$9" = WindowName:DisplayId:Pid:WinId:Type:Mode:Flag:ZOrd:Orientation ] && [ "${10}" = '[' ] || return 1
   rc_header=1; continue
  fi
  if [ "$rc_header" = 0 ]; then
   # Optional original capture envelope: one kernel boot UUID before WMS.
   [ "$rc_boot" = 0 ] && [ "$#" = 1 ] && [ "${#1}" = 36 ] || return 1
   case "$1" in *[!0-9a-f-]*) return 1;; esac
   case "$1" in ????????-????-????-????-????????????) :;; *) return 1;; esac
   rc_boot=1; continue
  fi
  case "$1" in
   Focus)
    [ "$rc_footer" = 0 ] && [ "$rc_focuses" = 0 ] && [ "$#" = 3 ] && [ "$2" = window: ] && rc_isnat "$3" || return 1
    rc_focuses=1; rc_focus=$3; continue;;
   All)
    [ "$rc_all" = 0 ] && [ "$#" = 3 ] && [ "$2:$3" = Focus:window: ] || return 1
    rc_all=1; continue;;
   DisplayId:)
    [ "$#" = 4 ] && [ "$3" = WindowId: ] && rc_isnat "$2" && rc_isnat "$4" || return 1
    [ "$2" = 0 ] || return 1
    continue;;
   SingleHand:)
    [ "$#" = 4 ] || return 1
    continue;;
   Total)
    [ "$rc_footer" = 0 ] && [ "$rc_focuses" = 1 ] && [ "$#" = 4 ] && [ "$2:$3" = window:num: ] && rc_isnat "$4" && [ "$4" -gt 0 ] || return 1
    rc_total=$4; rc_footer=1; continue;;
   Highlighted)
    [ "$rc_high" = 0 ] && [ "$#" = 3 ] && [ "$2" = windows: ] && rc_isnat "$3" || return 1
    rc_high=1; continue;;
   WMS_REMOTE_RC=*)
    [ "$rc_remote" = 0 ] && [ "$rc_footer" = 1 ] && [ "$#" = 1 ] && [ "$1" = WMS_REMOTE_RC=0 ] || return 1
    rc_remote=1; continue;;
  esac
  # Every other nonblank line is a data row, never silently skipped.
  [ "$rc_footer" = 0 ] && [ "$rc_focuses" = 0 ] && [ "$#" -ge 15 ] || return 1
  [ "${10}" = '[' ] && [ "${15}" = ']' ] || return 1
  for rc_num in "$2" "$3" "$4" "$5" "$6" "$7" "$9"; do rc_isnat "$rc_num" || return 1; done
  rc_isint "$8" || return 1
  for rc_num in "${11}" "${12}" "${13}" "${14}"; do rc_isint "$rc_num" || return 1; done
  [ "$3" -gt 0 ] && [ "$4" -gt 0 ] || return 1
  case "$rc_ids" in *" $4 "*) return 1;; esac
  rc_ids="$rc_ids$4 "
  rc_count=$((rc_count + 1))
  rc_rows="$rc_rows$1 $3 $4 $8
"
  for rc_pid in $rc_owned; do [ "$3" != "$rc_pid" ] || rc_result=yes; done
 done < "$rc_file"
 [ "$rc_header" = 1 ] && [ "$rc_footer" = 1 ] && [ "$rc_focuses" = 1 ] && [ "$rc_count" -gt 0 ] || return 1
 # Real OH totals may exceed printed rows. Equality would reject valid captures.
 [ "$rc_total" -ge "$rc_count" ] || return 1
 rc_hits=0; rc_match=
 while read -r rc_name rc_pid rc_wid rc_z; do
  [ "$rc_wid" = "$rc_focus" ] || continue
  rc_hits=$((rc_hits + 1)); rc_match="$rc_name $rc_pid $rc_wid $rc_z"
 done <<ROWS
$rc_rows
ROWS
 [ "$rc_hits" = 1 ] || return 1
 printf '%s %s\n' "$rc_match" "$rc_result"
)

# <dumpfile> -> "name pid wid z" or "error". Only visible focused rows qualify.
rc_parse_focus() {
 rc_valid=$(rc_validate_wms "$1" '') || { echo error; return 0; }
 set -- $rc_valid
 [ "$#" = 5 ] || { echo error; return 0; }
 case "$4" in -*) echo error; return 0;; esac
 printf '%s %s %s %s\n' "$1" "$2" "$3" "$4"
}

# <dumpfile> <owned child pids> -> yes/no/unknown. Hidden child windows count.
rc_parse_owned_window() {
 rc_valid=$(rc_validate_wms "$1" "$2") || { echo unknown; return 0; }
 set -- $rc_valid
 [ "$#" = 5 ] || { echo unknown; return 0; }
 printf '%s\n' "$5"
}

# Classification only; caller must verify process identity and parent WID.
rc_classify_focus() {
 rc_focus_arg=$1; rc_desk_arg=$2; rc_host_arg=$3; rc_hostwid_arg=$4
 case "$rc_focus_arg" in error|'') echo error; return 0;; esac
 set -- $rc_focus_arg
 [ "$#" = 4 ] && rc_isnat "$2" && rc_isnat "$3" && rc_isnat "$4" || { echo error; return 0; }
 if [ -n "$rc_desk_arg" ] && [ "$1" = "$rc_desk_arg" ]; then echo desktop
 elif [ "$1" = "$rc_host_arg" ] && [ "$3" = "$rc_hostwid_arg" ]; then echo "host $3"
 else echo other
 fi
}


set -u
F=$1; PROC=$F/proc; BOOT=fixture; self_birth=1; child=7172; child_birth=7475
parent=5177; parent_birth=5834; seq=1; ret_key='fixture 1 7172 7475'
keep_lock=0; polls=0; owner_verified=1; RB_OWNER_UID=20011206
RUNTIME=$F/runtime; RB_SPAWNER_SHA=synthetic; enum_rc=0; phase=exited
parent_rc=0; spawn_calls=0; ticks=0; max_ticks=4; fail_spawn=0; bound_wid=30
mkdir -p "$F/lock" "$PROC/sys/kernel/random"
echo "$BOOT" > "$PROC/sys/kernel/random/boot_id"
printf '%s %s %s\n' "$$" "$self_birth" "$BOOT" > "$F/lock/owner"
echo 1 > "$F/sequence"
parent_owned() { return "$parent_rc"; }
rb_birth() { if [ "$1" = 8080 ]; then echo 222; elif [ "$phase" = reused ]; then echo 9999; elif [ "$phase" = alive ]; then echo 7475; else return 1; fi; }
child_owned() { return 0; }
child_exit_verdict() { echo exited; }
rb_owned_pids() { return "$enum_rc"; }
event() { printf 'EVENT %s\n' "$*"; }
state() { printf 'STATE %s\n' "$*"; }
control_file() { :; }
io_fail() { echo "IO_FAIL $*"; exit 70; }
verify_exact() { [ "$(cat "$1")" = "$2" ]; }
rb_guard_json() { :; }
timeout() {
 case "$*" in
  *strings*) printf 'WL_PARENT_ID=%s\nASX_RUNTIME_OWNER_UID=20011206\n' "$bound_wid";;
  *spawn.sh*) spawn_calls=$((spawn_calls+1)); [ "$fail_spawn" = 0 ] || return 1; echo 'HOST_SPAWN result=0 pid=8080';;
  *) :;;
 esac
}
rc_capture_wms() { return 0; }
rc_verify_window_process() { RC_WINDOW_BIRTH=7475; return 0; }
rc_stop_present() { [ "$ticks" -ge "$max_ticks" ]; }
rc_sleep() { :; }
rc_after_spawn_ok() { return 0; }
loop_focus() { ticks=$((ticks+1)); case "$ticks" in 1|3|5) rc_focus_result=desktop;; *) rc_focus_result='host 30';; esac; }
printf '%s\n' 'WindowName DisplayId Pid WinId Type Mode Flag ZOrd Orientation [ x y w h ]' 'imehost0 0 55 30 1 1 0 1 0 [ 0 0 100 100 ]' 'Focus window: 30' 'All Focus window:' 'DisplayId: 0 WindowId: 30' 'Total window num: 1' 'Highlighted windows: 30' > "$F/wms-owned.txt"
cp "$F/wms-owned.txt" "$F/wms-focus.txt"


rc_epoch_hold=0; rc_epoch_reason=; terms=0; starts=0; unlinks=0
SOCKET=$F/socket; touch "$SOCKET"; stop_mode=exited; kids=; holders=5177
rc_direct_children() { [ "$kids" != unknown ] || return 1; [ -z "$kids" ] || echo "$kids"; return 0; }
rc_socket_inode_of() { echo 333; }
rc_fd_holders() { [ -z "$holders" ] || echo "$holders"; return 0; }
stat() { echo 1:20; }
sleep() { :; }
rc_send_term() { terms=$((terms+1)); holders=; echo ACTION_TERM; }
rb_birth() {
 if [ "$1" = 5177 ]; then
  if [ "$terms" = 0 ] || [ "$stop_mode" = alive ]; then echo 5834; return 0; fi
  if [ "$stop_mode" = reused ]; then echo 9999; return 0; fi
  return 1
 fi
 echo 222
}
rm() { if [ "$1" = -f ] && [ "${2:-}" = "$SOCKET" ]; then unlinks=$((unlinks+1)); echo ACTION_UNLINK; fi; command rm "$@"; }
rc_run_start_parent() { starts=$((starts+1)); bound_wid=$pe_wid; echo ACTION_START; echo 8080 > "$1"; return 0; }
summary() { echo RESULT rc=$r terms=$terms unlinks=$unlinks starts=$starts reason=$rc_epoch_reason parent=$parent hold=$rc_epoch_hold; }

kill() { echo UNEXPECTED_DIRECT_SIGNAL >&2; return 99; }

# Synthetic OS adapter for the recorded-epoch interface. No production function replaced here.
# Production rc_epoch_binding, rc_wait_exit, record parsing and signal guards stay real.
RB_PROC=$PROC; RB_RUNTIME=$RUNTIME
fixture_stat() { printf '%s (fixture) S %s 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 %s\n' "$1" "$2" "$3"; }
fixture_process() {
 mkdir -p "$PROC/$1/ns" "$PROC/$1/net" "$PROC/$1/fd"
 fixture_stat "$1" 1 "$2" > "$PROC/$1/stat"
 ln -s 'mnt:[100]' "$PROC/$1/ns/mnt"
}
fixture_process "$$" 1
fixture_process 5177 5834
ln -s 'socket:[333]' "$PROC/5177/fd/4"
printf 'Num RefCount Protocol Flags Type St Inode Path\nx: 00000002 00000000 00010000 0001 01 333 %s\n' "$SOCKET" > "$PROC/$$/net/unix"
cp "$PROC/$$/net/unix" "$PROC/5177/net/unix"
printf 'phase=bound parent=5177:5834 mntns=mnt:[100] sock=333 sockfile=1:20\n' > "$F/parent-epoch"
rc_owned_pids_strict() { return "$enum_rc"; }
rb_birth() {
 if [ "$1" = "$$" ]; then [ -r "$PROC/$$/stat" ] || return 1; echo 1; return 0; fi
 if [ "$1" = 5177 ]; then
  if [ "$terms" = 0 ] || [ "$stop_mode" = alive ]; then echo 5834; return 0; fi
  if [ "$stop_mode" = reused ]; then echo 9999; return 0; fi
  return 1
 fi
 echo 222
}
rc_send_term() {
 terms=$((terms+1)); echo ACTION_TERM
 case "$stop_mode" in
 exited) command rm -rf "$PROC/5177"; holders=; : > "$PROC/$$/net/unix";;
 unreadable) command rm -f "$PROC/5177/stat"; holders=;;
 reused) fixture_stat 5177 1 9999 > "$PROC/5177/stat"; holders=;;
 alive) :;;
 esac
}
fixture_start() {
 starts=$((starts+1)); bound_wid=$pe_wid; holders=$1
 echo ACTION_START; fixture_process "$1" 222
 printf 'Num RefCount Protocol Flags Type St Inode Path\nx: 00000002 00000000 00010000 0001 01 333 %s\n' "$SOCKET" > "$PROC/$$/net/unix"
 cp "$PROC/$$/net/unix" "$PROC/$1/net/unix"
 echo "$1" > "$2"
}
rc_run_start_parent() { fixture_start 8080 "$1"; }

rc_socket_inode_of() { # <pid>: inode of the unique LISTENING stream/seqpacket row for $SOCKET in its net view
 si_line=$(grep -E " $SOCKET\$" "$PROC/$1/net/unix" 2>/dev/null) || return 1
 [ "$(printf '%s\n' "$si_line" | wc -l)" -eq 1 ] || return 1
 set -- $si_line
 [ "$#" -eq 8 ] || return 1
 [ "$4" = 00010000 ] || return 1
 case "$5" in 0001|0005) :;; *) return 1;; esac
 [ "$6" = 01 ] || return 1
 [ "$8" = "$SOCKET" ] || return 1
 case "$7" in ''|*[!0-9]*) return 1;; esac
 echo "$7"
}
mkdir -p "$PROC/5177/net"; echo "x: 00000002 00000000 00000000 0001 03 333 $SOCKET" > "$PROC/5177/net/unix"; found=$(rc_socket_inode_of 5177); echo RESULT rc=$? inode=$found
