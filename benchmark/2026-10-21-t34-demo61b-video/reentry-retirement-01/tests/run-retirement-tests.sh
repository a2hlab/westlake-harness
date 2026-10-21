#!/bin/sh
# T34-RETIRE r3 offline tests. Sources the WHOLE actual r3 watchdog (main call removed)
# with the deployed r2 helpers (route-b-owner, exit-verdict, reentry-seams,
# reentry-common; unchanged by r3). Real: rc_reentry_loop, rc_gates_ok, rc_child_state,
# rc_owned_window_present (+ real rc_parse_owned_window), monitor_child, do_one_launch,
# rc_do_spawn, rc_after_spawn_ok, event/state/instance/write_exact, rb_birth,
# child_exit_verdict, owned_failure_kind. Stubbed device seams only: rc_focus_state
# (scripted), rc_capture_wms (fixture copy), rb_owned_pids, parent_owned, child_owned
# (birth-checked ownership guard), capture_frame/context, sleep. Fake /proc.
# No device, no network, no signal. Exits non-zero on any mismatch.
set -u
HERE=$(CDPATH= cd -P "$(dirname "$0")" && pwd -P)
NEW=$(CDPATH= cd -P "$HERE/.." && pwd -P)
REPO=$(CDPATH= cd -P "$NEW/../../.." && pwd -P)
R3=${RETIRE_UNDER_TEST:-"$NEW/src/watchdog-reentry-r3.sh"}
R2P="$REPO/benchmark/2026-10-19-toutiao-icon-reentry/candidate-payload-r2/payload"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/rc-retire.XXXXXX") || { echo "mktemp failed" >&2; exit 2; }
trap 'chmod -R u+rwx "$WORK" 2>/dev/null; rm -rf "$WORK"' EXIT
pass=0; fail=0
ok() { pass=$((pass + 1)); printf 'PASS %s\n' "$1"; }
no() { fail=$((fail + 1)); printf 'FAIL %s : %s\n' "$1" "$2"; }
eq() { if [ "$2" = "$3" ]; then ok "$1"; else no "$1" "expected [$2] got [$3]"; fi; }

BOOT0=80b23c89-01e7-4865-88c7-b8b75e0b4a83
PROC="$WORK/proc"; F="$WORK/F"
mkdir -p "$PROC/sys/kernel/random" "$F"
printf '%s\n' "$BOOT0" > "$PROC/sys/kernel/random/boot_id"; printf '7024.50 1.00\n' > "$PROC/uptime"
export TT_PROC="$PROC" TT_STATE_ROOT="$F" TT_RUNTIME="$WORK/rt" TT_OWNER_UID=20011206
# Source the actual r3 body: drop only the final main call; helpers come from r2 payload.
grep -c '^main "\$@"$' "$R3" | grep -qx 1 || { echo "r3 main line not unique" >&2; exit 2; }
sed -e '$d' -e "s#^HERE=.*#HERE='$R2P'#" "$R3" > "$WORK/r3-under-test.sh"
. "$WORK/r3-under-test.sh"
set +u
for fn in rc_reentry_loop rc_gates_ok rc_child_state rc_owned_window_present monitor_child do_one_launch rc_retire_child rc_retired_current rc_retire_clear; do
	command -v "$fn" >/dev/null 2>&1 && continue
	# Negative control only (RETIRE_UNDER_TEST=r2): r2 has no retirement; inert stand-ins.
	[ -n "${RETIRE_UNDER_TEST:-}" ] || { echo "$fn missing" >&2; exit 2; }
	case $fn in rc_retire_child|rc_retire_clear) eval "$fn() { :; }";; rc_retired_current) eval "$fn() { return 1; }";; *) echo "$fn missing" >&2; exit 2;; esac
done
ret_key=
BOOT=$BOOT0

# ---- stubbed device seams (everything else is the real r3/r2 code) ----
sleep() { :; }; rc_sleep() { :; }
capture_frame() { CAPTURES=$((CAPTURES + 1)); return "${CAPTURE_RC:-1}"; }
capture_context() { :; }
PARENT_OK=1; PARENT_CALLS=0
parent_owned() { PARENT_CALLS=$((PARENT_CALLS + 1)); [ "$PARENT_OK" = 1 ]; }
OWNED_EXTRA=; rb_owned_pids() { [ -z "$OWNED_EXTRA" ] || printf '%s\n' $OWNED_EXTRA; }
OWN_MODE=birth
child_owned() { # ownership guard: birth equality via real rb_birth, death encoded with the REAL rb_deny
	case "$OWN_MODE" in
	vanish) rm -rf "$PROC/$1"; rb_deny birth_after '<read-error-or-exited>' "$2"; return 1;;
	esac
	b=$(rb_birth "$1") || { rb_deny birth '<read-error-or-exited>' "$2"; return 1; }
	[ "$b" = "$2" ] || { rb_deny birth "$b" "$2"; return 1; }
}
FOCUS_FILE="$WORK/focus"; FOCUS_I=0
rc_focus_state() { FOCUS_I=$((FOCUS_I + 1)); rc_focus_result=$(sed -n "${FOCUS_I}p" "$FOCUS_FILE"); [ -n "$rc_focus_result" ] || { : > "$F/stop"; rc_focus_result=error; }; return 0; }
WMS_SRC="$WORK/wms.txt"
rc_capture_wms() { cp "$WMS_SRC" "$1"; }
make_dump() { # <file> [extra rows...]: desktop+host, then optional child rows
	f=$1; shift
	{
		printf '%s\n\n' "$BOOT0"
		printf -- '----------------------------------WindowManagerService----------------------------------\n'
		printf 'WindowName DisplayId Pid WinId Type Mode Flag ZOrd Orientation [ x y w h ]\n'
		printf 'SCBDesktop6 0 2393 11 2001 1 0 2 0 [ 0 0 1200 1920 ]\n'
		printf 'imehost0 0 4920 30 1 1 0 101 0 [ 0 0 1200 1920 ]\n'
		for r in "$@"; do printf '%s\n' "$r"; done
		printf 'Focus window: 30\nAll Focus window: \nDisplayId: 0 WindowId: 30\nTotal window num: 30\nHighlighted windows: 30\nWMS_REMOTE_RC=0\n'
	} > "$f"
}
stat_row() { # <pid> <state> <birth> <ppid>
	printf '%s (id.article.news) %s %s 5402 0 0 -1 1077936448 920061 5333 8232 0 23249 10693 4 74 20 0 332 0 %s 246606372864 259552 18446744073709551615 0 0 0 0 0 0 4612 4097 1073841402 0 0 0 17 5 0 0 0 0 0\n' "$1" "$2" "$4" "$3"
}
put_proc() { rm -rf "$PROC/$1"; mkdir -p "$PROC/$1"; stat_row "$1" "$2" "$3" "$PARENT" > "$PROC/$1/stat"; }
PARENT=5177; PARENT_B=5834; CHILD=7172; CB=7475
reset_all() {
	rm -rf "$F"; mkdir -p "$F/lock"; rm -rf "$PROC/$CHILD" "$PROC/8001"
	printf '%s\n' "$BOOT0" > "$PROC/sys/kernel/random/boot_id"
	self_birth=3933; BOOT=$BOOT0; printf '%s %s %s\n' "$$" "$self_birth" "$BOOT" > "$F/lock/owner"
	: > "$F/events.log"; : > "$F/state"; printf '1\n' > "$F/sequence"
	parent=$PARENT; parent_birth=$PARENT_B; child=$CHILD; child_birth=$CB; seq=1
	instance; INST0=$(cat "$F/instance.txt")
	ret_key=; keep_lock=0; owner_verified=1; polls=0; TT_MAX_POLLS=0; CAPTURES=0; CAPTURE_RC=1
	PARENT_OK=1; PARENT_CALLS=0; OWNED_EXTRA=; OWN_MODE=birth; FOCUS_I=0; : > "$FOCUS_FILE"
	make_dump "$WMS_SRC"
	SPAWNS=0; printf '#!/bin/sh\nexit 1\n' > "$F/spawn.sh"; printf '#!/bin/sh\nexit 0\n' > "$F/readiness-probe.sh"
}
evc() { grep -c -- "$1" "$F/events.log" 2>/dev/null || true; }
focus() { printf '%s\n' "$@" > "$FOCUS_FILE"; }
loop() { ( rc_reentry_loop; echo "rc=$?" > "$WORK/looprc"; printf '%s\n' "$ret_key" > "$WORK/loopkey" ) 2>/dev/null; LRC=$(cat "$WORK/looprc"); }
spawn_ok_script() { # fake spawn.sh: creates the new child in fake /proc
	printf '#!/bin/sh\necho SPAWNED >> "%s/spawns"\nmkdir -p "%s/8001"\nprintf "%%s\\n" "%s" > "%s/8001/stat"\necho "HOST_SPAWN result=0 pid=8001"\n' \
		"$WORK" "$PROC" "$(stat_row 8001 S 9100 "$PARENT")" "$PROC" > "$F/spawn.sh"
}
spawns() { if [ -f "$WORK/spawns" ]; then grep -c SPAWNED "$WORK/spawns"; else echo 0; fi; }

# ===== 1. strict exit retires; PID reuse no longer kills the guardian =====
reset_all; rm -f "$WORK/spawns"
monitor_child 2>/dev/null; eq retire.first_read.rc 0 "$?"
eq retire.first_read.key "$BOOT0 1 $CHILD $CB" "$ret_key"
eq retire.first_read.event 1 "$(evc 'child_retired key=')"
eq retire.instance_unchanged "$INST0" "$(cat "$F/instance.txt")"
put_proc "$CHILD" S 99999   # same numeric PID reused with a different birth
eq retire.reuse.child_state gone "$(rc_child_state)"
rc_gates_ok; eq retire.reuse.gates_ok 0 "$?"
[ "$PARENT_CALLS" -ge 1 ] && ok retire.gates.parent_checked || no retire.gates.parent_checked "$PARENT_CALLS"
spawn_ok_script; TT_MAX_POLLS=1; focus desktop "host 30"
loop
eq retire.loop.one_spawn 1 "$(spawns)"
eq retire.loop.spawn_ok_event 1 "$(evc reentry_spawn_ok)"
eq retire.loop.cleared 1 "$(evc 'child_retirement_cleared spawn_started')"
eq retire.loop.no_owner_refused 0 "$(evc OWNER_REFUSED)"
eq retire.loop.key_cleared "" "$(cat "$WORK/loopkey")"
# Second strict branch: exited during the ownership check.
reset_all; put_proc "$CHILD" S "$CB"; OWN_MODE=vanish
monitor_child 2>/dev/null; eq retire.ownership_branch.rc 0 "$?"
eq retire.ownership_branch.key "$BOOT0 1 $CHILD $CB" "$ret_key"
eq retire.ownership_branch.event 1 "$(evc 'process_exit during_ownership_check')"
# Retired, but boot / lock / parent drift still refuse (gates run before the child check).
reset_all; monitor_child 2>/dev/null; put_proc "$CHILD" S 99999
printf 'other-boot\n' > "$PROC/sys/kernel/random/boot_id"; rc_gates_ok; eq retire.boot_drift.refused 1 "$?"; eq retire.boot_drift.reason boot_changed "$rc_gate_reason"
printf '%s\n' "$BOOT0" > "$PROC/sys/kernel/random/boot_id"
printf '1 2 %s\n' "$BOOT0" > "$F/lock/owner"; rc_gates_ok; eq retire.lock_drift.reason lock_foreign "$rc_gate_reason"
printf '%s %s %s\n' "$$" "$self_birth" "$BOOT" > "$F/lock/owner"
PARENT_OK=0; rc_gates_ok; eq retire.parent_drift.reason parent_identity "$rc_gate_reason"

# ===== 2. not retired, or any key field mismatch: original refusal =====
reset_all; put_proc "$CHILD" S 99999
eq unretired.reuse.invalid invalid "$(rc_child_state)"
rc_gates_ok; eq unretired.gate.reason child_identity "$rc_gate_reason"
spawn_ok_script; rm -f "$WORK/spawns"; focus desktop "host 30"; loop
eq unretired.loop.rc rc=2 "$LRC"; eq unretired.loop.no_spawn 0 "$(spawns)"
eq unretired.loop.refused 1 "$(evc 'OWNER_REFUSED gate=child_identity_no_signal_no_stop_delete')"
for kf in boot seq pid birth; do
	reset_all; monitor_child 2>/dev/null; put_proc "$CHILD" S 99999
	case $kf in
	boot) ret_key="other-boot 1 $CHILD $CB";; seq) ret_key="$BOOT0 2 $CHILD $CB";;
	pid) ret_key="$BOOT0 1 9999 $CB";; birth) ret_key="$BOOT0 1 $CHILD 1";;
	esac
	eq "keymismatch.$kf.invalid" invalid "$(rc_child_state)"
done

# ===== 3. observation limit / stop / unknown / capture failure never retire =====
reset_all; put_proc "$CHILD" S "$CB"; TT_MAX_POLLS=1
monitor_child 2>/dev/null; eq nolimit.rc 0 "$?"; eq nolimit.no_key "" "$ret_key"; eq nolimit.event 1 "$(evc observation_limit_no_app_control)"
eq nolimit.capture_failed_seen 1 "$CAPTURES"; eq nolimit.snapshot_error_state 1 "$(evc 'UI_UNVERIFIED snapshot_error')"
reset_all; put_proc "$CHILD" S "$CB"; : > "$F/stop"
monitor_child 2>/dev/null; eq nostop.rc 0 "$?"; eq nostop.no_key "" "$ret_key"; eq nostop.stopped 1 "$(evc 'STOPPED existing_stop')"
reset_all; put_proc "$CHILD" S 99999
monitor_child 2>/dev/null; eq noreuse.rc 2 "$?"; eq noreuse.no_key "" "$ret_key"
reset_all; put_proc "$CHILD" S "$CB"; chmod 000 "$PROC/$CHILD/stat"
if cat "$PROC/$CHILD/stat" >/dev/null 2>&1; then echo "SKIP unknown.unreadable (running as root)"; else
	monitor_child 2>/dev/null; eq nounknown.rc 2 "$?"; eq nounknown.no_key "" "$ret_key"
fi
chmod -R u+rwx "$PROC/$CHILD" 2>/dev/null
# Stop wins in the loop even while retired.
reset_all; monitor_child 2>/dev/null; : > "$F/stop"; focus desktop "host 30"; loop
eq stop.loop.rc rc=0 "$LRC"; eq stop.loop.stopped 1 "$(evc 'STOPPED existing_stop_no_delete')"

# ===== 4. old / other owned / unknown windows keep blocking =====
reset_all; monitor_child 2>/dev/null; put_proc "$CHILD" S 99999
make_dump "$WMS_SRC" "com.ss.android.artic 0 $CHILD 32 1001 1 0 -1 0 [ 0 0 1200 1920 ]"
rc_owned_result=x; rc_owned_window_present; eq window.retired_pid.unknown unknown "$rc_owned_result"
eq window.child_field_kept "$CHILD" "$child"
rm -f "$WORK/spawns"; spawn_ok_script; focus desktop "host 30"; loop
eq window.retired_pid.no_spawn 0 "$(spawns)"; eq window.retired_pid.consume 1 "$(evc 'consume_live_or_window child=gone win=unknown')"
OWNED_EXTRA=8555; make_dump "$WMS_SRC" "PopupWindow:4bc 0 8555 35 1001 1 0 -1 0 [ 0 0 1 1920 ]"
rc_owned_window_present; eq window.other_owned.yes yes "$rc_owned_result"
make_dump "$WMS_SRC" "com.ss.android.artic 0 $CHILD 32 1001 1 0 -1 0 [ 0 0 1200 1920 ]" "PopupWindow:4bc 0 8555 35 1001 1 0 -1 0 [ 0 0 1 1920 ]"
rc_owned_window_present; eq window.both.yes yes "$rc_owned_result"
rm -f "$WORK/spawns"; focus desktop "host 30"; FOCUS_I=0; loop; eq window.other_owned.no_spawn 0 "$(spawns)"
OWNED_EXTRA=; printf 'garbage\n' > "$WMS_SRC"; rc_owned_window_present; eq window.unreadable.unknown unknown "$rc_owned_result"
rm -f "$WORK/spawns"; FOCUS_I=0; loop; eq window.unreadable.no_spawn 0 "$(spawns)"
# Not retired: a window of the (alive) child is still owned=yes (r2 semantics kept).
reset_all; put_proc "$CHILD" S "$CB"; make_dump "$WMS_SRC" "com.ss.android.artic 0 $CHILD 32 1001 1 0 -1 0 [ 0 0 1200 1920 ]"
rc_owned_window_present; eq window.unretired.yes yes "$rc_owned_result"
# Host edge without a preceding desktop never spawns, even when retired.
reset_all; monitor_child 2>/dev/null; rm -f "$WORK/spawns"; spawn_ok_script; focus "host 30" "host 30"; loop
eq edge.no_desktop.no_spawn 0 "$(spawns)"

# ===== 5. new instance clears retirement and is fully guarded again =====
reset_all; monitor_child 2>/dev/null; rm -f "$WORK/spawns"; spawn_ok_script; TT_MAX_POLLS=1
focus desktop "host 30" "host 30" desktop "host 30"
( rc_reentry_loop >/dev/null 2>&1; echo "rc=$?" > "$WORK/looprc"; printf '%s|%s %s %s\n' "$ret_key" "$child" "$child_birth" "$seq" > "$WORK/loopkey" ) 2>/dev/null
eq newinst.one_spawn_live_child_consumes_later_edges 1 "$(spawns)"
[ "$(evc 'consume_live_or_window child=alive')" -ge 1 ] && ok newinst.later_edge_consumed_alive || no newinst.later_edge_consumed_alive "$(evc consume_live_or_window)"
eq newinst.new_child_bound "|8001 9100 2" "$(cat "$WORK/loopkey")"
eq newinst.instance_rebound 1 "$(grep -c '^child=8001$' "$F/instance.txt")"
# The new live child is not covered by the old retirement: reuse of its PID is refused.
reset_all; monitor_child 2>/dev/null; spawn_ok_script; TT_MAX_POLLS=1
rc_do_spawn; eq newinst.direct.ok "ok 8001 9100" "$rc_spawn_result"; eq newinst.direct.key_cleared "" "$ret_key"
put_proc 8001 S 12345; eq newinst.reuse.invalid invalid "$(rc_child_state)"
# Adopt clears too (real main adopt branch is exercised via its exact line).
reset_all; monitor_child 2>/dev/null; rc_retire_clear adopt; eq adopt.cleared "" "$ret_key"; eq adopt.event 1 "$(evc 'child_retirement_cleared adopt')"
grep -q '^  rc_retire_clear adopt$' "$R3" && ok adopt.line_in_main || no adopt.line_in_main missing
# Spawn result unknown: sticky hold / fail-closed, never a retirement-based retry.
reset_all; monitor_child 2>/dev/null; put_proc "$CHILD" S 99999; rm -f "$WORK/spawns"
printf '#!/bin/sh\necho SPAWNED >> "%s/spawns"\nexit 7\n' "$WORK" > "$F/spawn.sh"
focus desktop "host 30" desktop "host 30" desktop "host 30"; loop
eq unknown.one_attempt 1 "$(spawns)"; eq unknown.cleared 1 "$(evc 'child_retirement_cleared spawn_started')"
eq unknown.unknown_event 1 "$(evc reentry_spawn_unknown_hold)"
eq unknown.no_second_spawn_ok 0 "$(evc reentry_spawn_ok)"

# ===== 6. source / receipt structure =====
eq src.r2_watchdog_unchanged 41f1bf653f4becf3bb40a1a754f8e0c35520ce9fa6a0eb3da84c01ef96e64a28 \
	"$( (sha256sum "$R2P/watchdog.sh" 2>/dev/null || shasum -a 256 "$R2P/watchdog.sh") | cut -d' ' -f1)"
eq src.r2_common_unchanged 43d7b073467708770c8c69724633666e410d45581f8c0099d5098c31215e78ab \
	"$( (sha256sum "$R2P/reentry-common.sh" 2>/dev/null || shasum -a 256 "$R2P/reentry-common.sh") | cut -d' ' -f1)"
eq src.retire_calls_two_exited_branches 2 "$(grep -c 'exited) event process_exit .*; rc_retire_child; return 0;;' "$R3")"
eq src.no_kill_added 0 "$(grep -c '\bkill\b' "$NEW/r2-to-r3.diff" 2>/dev/null | grep -c '^[1-9]' || true)"

printf '\n%s passed, %s failed\n' "$pass" "$fail"
[ "$fail" = 0 ]
