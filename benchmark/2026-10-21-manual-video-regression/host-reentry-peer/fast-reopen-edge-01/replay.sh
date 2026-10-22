#!/bin/sh
# Pure common-function replay. No watchdog, process, filesystem or device seams.
set -u
. ./common.snapshot.sh
scenario=$1
ticks=0
spawn_calls=0
after_calls=0
epoch_calls=0
child_status=gone
keep_lock=0

# Only history labels are modeled here, NOT execution of production monitor_child.
# Its relevant production property is that it does not call rc_focus_state.
mock_supervision_history() {
 case "$scenario" in
 missed_during_supervision)
  printf '%s\n' 'HISTORY child_exit -> desktop -> manual_icon -> host; no focus samples during supervision'
  ;;
 desktop_then_host)
  printf '%s\n' 'HISTORY child_exit; desktop and manual_icon occur during focus sampling'
  ;;
 host_at_start_no_manual_event)
  printf '%s\n' 'HISTORY no manual event; host already focused when loop starts'
  ;;
 *) return 64;;
 esac
}

rc_stop_present() { [ "$ticks" -ge 4 ]; }
rc_gates_ok() { return 0; }
rc_sleep() { :; }
rc_event() { printf 'EVENT %s\n' "$*"; }
rc_child_state() { printf '%s\n' "$child_status"; }
rc_owned_window_present() { rc_owned_result=no; return 0; }
rc_focus_state() {
 ticks=$((ticks+1))
 rc_focus_result='host 30'
 if [ "$scenario" = desktop_then_host ] && [ "$ticks" = 1 ]; then
  rc_focus_result=desktop
 fi
 printf 'FOCUS tick=%s value=%s\n' "$ticks" "$rc_focus_result"
 return 0
}
rc_do_spawn() {
 spawn_calls=$((spawn_calls+1))
 child_status=alive
 rc_spawn_result='ok 8080 222'
 return 0
}
rc_after_spawn_ok() { after_calls=$((after_calls+1)); return 0; }
rc_parent_epoch_switch() {
 epoch_calls=$((epoch_calls+1))
 return 91
}

mock_supervision_history || exit $?
printf '%s\n' 'LOOP_BEGIN'
rc_reentry_loop
loop_rc=$?
printf 'RESULT rc=%s spawns=%s after=%s epochs=%s arm=%s ticks=%s\n' \
 "$loop_rc" "$spawn_calls" "$after_calls" "$epoch_calls" "$rc_arm" "$ticks"
exit "$loop_rc"
