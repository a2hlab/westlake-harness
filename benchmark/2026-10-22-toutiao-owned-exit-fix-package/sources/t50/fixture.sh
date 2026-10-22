# T49-derived local external-I/O seams; main, child_owned, capture and deny intact.
set -u
export TT_STATE_ROOT="$PWD/state" TT_RUNTIME="$PWD/runtime" TT_PROC="$PWD/proc"
export TT_OPERATOR_ROOT="$PWD" TT_STAGE="$PWD/stage" TT_SOCKET="$PWD/socket"
export TT_OWNER_UID=12345 TT_RECOVERY_EXECUTE=1 TT_EXPECT_BOOT=fixture-boot
export TT_PARENT_PID=43 TT_PARENT_BIRTH=90 TT_CHILD_PID=42 TT_CHILD_BIRTH=200
export TT_MAX_ATTEMPTS=1 TT_MAX_POLLS=1
case "$MODE" in capture_*) TT_MAX_POLLS=2;; init_spawn) unset TT_CHILD_PID;; esac
mkdir "$TT_PROC/$$"
cp "$PWD/stat-live" "$TT_PROC/$$/stat"
. "$PWD/functions.sh"
trace_action() { command printf '{"event":"%s"}\n' "$1" >> trace.jsonl; }
parent_owned() {
 trace_action parent_owned_seam
 if [ "${attempt:-unset}" = 0 ]; then
  cp "$F/sequence" "$PWD/sequence-at-validation"
  cp "$F/instance.txt" "$PWD/instance-at-validation"
  command printf '%s\n' "$attempt" > "$PWD/attempt-at-validation"
 fi
 return 0
}
capture_init() {
 trace_action capture_directory_seam
 CAP="$PWD/capture"; mkdir "$CAP"
 capture_owner="$$ $self_birth $BOOT"; capture_file=; capture_dir_identity=77:88
 write_exact "$CAP/owner" "$capture_owner"
 capture_guard
}
kill() { trace_action FORBIDDEN_kill; exit 97; }
rb_signal() { trace_action FORBIDDEN_signal; exit 97; }
rb_script_signal() { trace_action FORBIDDEN_script_signal; exit 97; }
timeout() {
 case "$2" in
 snapshot_display) trace_action synthetic_snapshot; command printf 'synthetic pixels\n' > "$4";;
 "$F/screen-gate") trace_action synthetic_classifier; echo unknown;;
 sh)
  case "$3" in
   "$F/spawn.sh")
    trace_action synthetic_spawn; mkdir "$PROC/42"; cp "$PWD/stat-live" "$PROC/42/stat"; cp "$PWD/status-live" "$PROC/42/status"; echo 'result=0 pid=42';;
   "$F/readiness-probe.sh") trace_action synthetic_readiness;;
   *) trace_action FORBIDDEN_launch; exit 97;;
  esac;;
 *) trace_action FORBIDDEN_device; exit 97;;
 esac
}
sleep() { [ "$1" = 3 ] || { trace_action FORBIDDEN_retry; exit 97; }; trace_action synthetic_poll_wait; }
readlink() {
 trace_action readlink
 case "$1" in
  "$RB_PROC/42/exe") echo /data/local/tmp/asx/appspawn-x;;
  "$PROC/42/ns/mnt") echo 'mnt:[2]';;
  "$PROC/1/ns/mnt") echo 'mnt:[1]';;
  *) trace_action FORBIDDEN_readlink; exit 97;;
 esac
}
stat() {
 trace_action stat_metadata
 case "$*" in
  "-L -c %d:%i $RUNTIME/run.sh"|"-L -c %d:%i $RB_PROC/42/root/data/local/tmp/asx/run.sh") echo 77:88;;
  "-c %d:%i $CAP"|"-c %d:%i $CAP/"*) echo 77:88;;
  "-c %u:%g:%a $CAP") echo 0:0:700;;
  "-c %u $CAP/"*) echo 0;;
  *) trace_action FORBIDDEN_stat; exit 97;;
 esac
}
sha256sum() {
 [ "$1" = "$RB_PROC/42/exe" ] || { trace_action FORBIDDEN_sha; exit 97; }
 command printf '%s  synthetic-exe\n' "$RB_SPAWNER_SHA"
}
ls() {
 [ "$*" = "-1 $RB_PROC" ] || { trace_action FORBIDDEN_ls; exit 97; }
 trace_action classification_parent_listing
 [ "$MODE" != parent_unreadable ] || return 1
 command ls "$@"
}
printf() {
 # Actual closed-fd write failure, only at the diagnostic output boundary.
 if [ "$MODE" = write_failure ] && [ "${1:-}" = '%s\n' ] && [ "${2:-}" = "${diagnostic_expected:-UNSET}" ]; then
  trace_action diagnostic_write_fault
  command printf "$@" >&-
  return $?
 fi
 command printf "$@"
}
cat() {
 case "${1:-}" in "$PWD/"*) :;; *) trace_action FORBIDDEN_cat; exit 97;; esac
 if [ "$MODE" = read_failure ]; then
  case "$1" in "$F/guardian-refusal-"*) trace_action diagnostic_read_fault; command cat "$1/not-a-directory"; return $?;; esac
 fi
 if [ "$1" = "$RB_PROC/42/stat" ]; then
  read count < "$PWD/stat-count"; count=$((count+1)); command printf '%s\n' "$count" > "$PWD/stat-count"
  if [ "$MODE" = transient_live ] && [ "$count" = 7 ]; then
   trace_action transient_read_fault
   command cat "$PWD/absent-stat-read"; cat_rc=$?
  else
   command cat "$@"; cat_rc=$?
  fi
  command printf '{"event":"stat_read","ordinal":%s,"rc":%s}\n' "$count" "$cat_rc" >> trace.jsonl
  if [ "$count" = "$TRIGGER" ]; then
   command printf '{"event":"mutation","after_stat":%s,"kind":"%s"}\n' "$count" "$MUTATION" >> trace.jsonl
   case "$MUTATION" in
    absent) command rm "$RB_PROC/42/stat" "$RB_PROC/42/status"; command rmdir "$RB_PROC/42";;
    stat_missing) command rm "$RB_PROC/42/stat";;
    replace) command cp "$PWD/stat-replacement" "$RB_PROC/42/stat";;
    uid) command printf 'Uid: 9 9 9 9\n' > "$RB_PROC/42/status";;
    stop) command printf 'synthetic operator stop\n' > "$F/stop";;
   esac
  fi
  return "$cat_rc"
 fi
 if [ "$1" = "$RB_PROC/43/stat" ]; then trace_action parent_stat_read; fi
 command cat "$@"
}
rb_birth() {
 birth_value=$(fixture_original_rb_birth "$1"); birth_rc=$?
 trace_pid=$1; [ "$1" != "$$" ] || trace_pid=SELF
 command printf '{"event":"birth","pid":"%s","rc":%s,"value":"%s"}\n' "$trace_pid" "$birth_rc" "$birth_value" >> trace.jsonl
 [ -z "$birth_value" ] || command printf '%s\n' "$birth_value"
 return "$birth_rc"
}
main
main_rc=$?
command printf '{"attempt":"%s","seq":"%s","child":"%s","parent":"%s"}\n' "${attempt:-unset}" "$seq" "$child" "$parent" > main-end.json
exit "$main_rc"
