# Derived from T46 check.py FIXTURE. Everything below is a local synthetic seam.
set -u
export TT_STATE_ROOT="$PWD/state" TT_RUNTIME="$PWD/runtime" TT_PROC="$PWD/proc"
export TT_OPERATOR_ROOT="$PWD" TT_STAGE="$PWD/stage" TT_SOCKET="$PWD/socket"
export TT_OWNER_UID=12345 TT_RECOVERY_EXECUTE=1 TT_EXPECT_BOOT=fixture-boot
export TT_PARENT_PID=43 TT_PARENT_BIRTH=90 TT_CHILD_PID=42 TT_CHILD_BIRTH=200
export TT_MAX_ATTEMPTS=1 TT_MAX_POLLS=1
mkdir "$TT_PROC/$$"
cp "$TT_PROC/42/stat" "$TT_PROC/$$/stat"
. "$PWD/functions.sh"
trace_action() { printf '{"event":"%s"}\n' "$1" >> trace.jsonl; }
parent_owned() { trace_action parent_owned_seam; return 0; }
capture_init() { trace_action capture_init_seam; }
capture_release() { trace_action capture_release_seam; }
capture_frame() { trace_action capture_frame_seam; capture_rc=125; capture_reason=synthetic_no_frame; return 1; }
kill() { trace_action FORBIDDEN_kill; exit 97; }
rb_signal() { trace_action FORBIDDEN_signal; exit 97; }
rb_script_signal() { trace_action FORBIDDEN_script_signal; exit 97; }
timeout() { trace_action FORBIDDEN_launch_or_probe; exit 97; }
sleep() { trace_action FORBIDDEN_retry; exit 97; }
# No identity decision is replaced. These external tools return synthetic metadata.
readlink() {
 trace_action readlink
 case "$1" in
  "$PROC/42/exe") echo /data/local/tmp/asx/appspawn-x;;
  "$PROC/42/ns/mnt") echo 'mnt:[2]';;
  "$PROC/1/ns/mnt") echo 'mnt:[1]';;
  *) trace_action FORBIDDEN_readlink; exit 97;;
 esac
}
stat() {
 trace_action stat
 case "$4" in "$RUNTIME/run.sh"|"$PROC/42/root/data/local/tmp/asx/run.sh") echo 77:88;;
 *) trace_action FORBIDDEN_stat; exit 97;; esac
}
sha256sum() {
 trace_action sha256sum
 [ "$1" = "$PROC/42/exe" ] || { trace_action FORBIDDEN_sha; exit 97; }
 printf '%s  synthetic-exe\n' "$RB_SPAWNER_SHA"
}
cat() {
 case "${1:-}" in "$PWD/"*) :;; *) trace_action FORBIDDEN_cat; exit 97;; esac
 if [ "$1" = "$PROC/42/stat" ]; then
  read t49_count < "$PWD/stat-count"
  t49_count=$((t49_count+1)); printf '%s\n' "$t49_count" > "$PWD/stat-count"
  command cat "$@"; t49_cat_rc=$?
  printf '{"event":"stat_read","ordinal":%s,"rc":%s}\n' "$t49_count" "$t49_cat_rc" >> trace.jsonl
  if { [ "$MODE" = first_missing ] && [ "$t49_count" = 5 ]; } ||
     { { [ "$MODE" = second_missing ] || [ "$MODE" = second_missing_existing ]; } && [ "$t49_count" = 6 ]; }; then
   # Only fixture files are removed: original rb_birth next fails its own -r check.
   command rm "$PROC/42/stat" "$PROC/42/status"
   command rmdir "$PROC/42"
   printf '{"event":"fixture_disappeared","after_stat":%s}\n' "$t49_count" >> trace.jsonl
  fi
  return "$t49_cat_rc"
 fi
 command cat "$@"
}
rb_birth() {
 # Observational wrapper delegates to the unchanged original body below.
 # It never chooses a birth value or failure code.
 t49_birth_value=$(fixture_original_rb_birth "$1"); t49_birth_rc=$?
 t49_trace_pid=$1; [ "$1" != "$$" ] || t49_trace_pid=SELF
 printf '{"event":"birth","pid":"%s","rc":%s,"value":"%s"}\n' \
  "$t49_trace_pid" "$t49_birth_rc" "$t49_birth_value" >> trace.jsonl
 [ -z "$t49_birth_value" ] || printf '%s\n' "$t49_birth_value"
 return "$t49_birth_rc"
}
main
exit $?
