#!/bin/sh
# Offline state-machine tests for the FINAL reentry loop (src/reentry-common.sh,
# adapter sha 43d7b073) driven through its real current-shell seam contract
# (rc_focus_result / rc_owned_result / rc_spawn_result + rc_classify_spawn).
# No device, no awk, no python. Exits non-zero on any mismatch.
#
# Each scenario is a list of per-poll steps "focus child owned spawn spawnrc":
#   focus   : desktop | host | other | error | errorfatal
#   child   : gone | alive | unknown | invalid   (rc_child_state output)
#   owned   : yes | no | unknown                 (rc_owned_result)
#   spawn   : ok:PID:BIRTH | fail:REASON | unknown:REASON | -
#   spawnrc : 0 | <nonzero>
# rc_stop_present ends the loop when the steps are exhausted or the next step is
# the literal line "stop". Gate refusal is driven by GATE_OK=1.
set -u
HERE=$(CDPATH= cd -P "$(dirname "$0")" && pwd -P)
BASE=$(CDPATH= cd -P "$HERE/.." && pwd -P)
. "$BASE/src/reentry-common.sh"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/rc-loop.XXXXXX") || { echo "mktemp failed" >&2; exit 2; }
trap 'rm -rf "$WORK"' EXIT
STEPFILE="$WORK/steps"; EVENTS="$WORK/events"

pass=0; fail=0
ok() { pass=$((pass + 1)); printf 'PASS %s\n' "$1"; }
no() { fail=$((fail + 1)); printf 'FAIL %s : %s\n' "$1" "$2"; }
eq() { if [ "$2" = "$3" ]; then ok "$1"; else no "$1" "expected [$2] got [$3]"; fi; }

# --- Seams (current shell; match the final contract) ---
CUR=0; NSTEPS=0; SPAWN_ATTEMPTS=0; SPAWN_OK=0; SUPERVISE=0; GATE_OK=0
_line=
rc_stop_present() {
	[ "$CUR" -ge "$NSTEPS" ] && return 0
	_nxt=$(sed -n "$((CUR + 1))p" "$STEPFILE")
	[ "$_nxt" = stop ]
}
rc_gates_ok() { rc_gate_reason=; [ "$GATE_OK" = 0 ] || { rc_gate_reason=test_gate; return 1; }; return 0; }
rc_focus_state() {
	CUR=$((CUR + 1)); _line=$(sed -n "${CUR}p" "$STEPFILE")
	set -- $_line
	_f=${1:-error}; STEP_CHILD=${2:-gone}; STEP_OWNED=${3:-no}; STEP_SPAWN=${4:--}; STEP_SPAWNRC=${5:-0}
	[ "$_f" != errorfatal ] || return 1
	if [ "$_f" = host ]; then rc_focus_result="host 33"; else rc_focus_result=$_f; fi
	return 0
}
rc_child_state() { printf '%s\n' "${STEP_CHILD:-gone}"; }
rc_owned_window_present() { rc_owned_result=${STEP_OWNED:-no}; return 0; }
rc_do_spawn() {
	SPAWN_ATTEMPTS=$((SPAWN_ATTEMPTS + 1))
	case "${STEP_SPAWN:--}" in
	ok:*) rc_spawn_result="ok ${STEP_SPAWN#ok:}"; rc_spawn_result=$(printf '%s' "$rc_spawn_result" | tr ':' ' ');;
	fail:*) rc_spawn_result="fail ${STEP_SPAWN#fail:}";;
	unknown:*) rc_spawn_result="unknown ${STEP_SPAWN#unknown:}";;
	*) rc_spawn_result="";;
	esac
	return "${STEP_SPAWNRC:-0}"
}
rc_after_spawn_ok() { SUPERVISE=$((SUPERVISE + 1)); return 0; }
rc_event() { printf '%s\n' "$*" >> "$EVENTS"; [ "${1:-}" != reentry_spawn_ok ] || SPAWN_OK=$((SPAWN_OK + 1)); }
rc_sleep() { :; }

run() { # <steps-as-newlines>
	printf '%s\n' "$1" > "$STEPFILE"
	NSTEPS=$(grep -c '' "$STEPFILE")
	CUR=0; SPAWN_ATTEMPTS=0; SPAWN_OK=0; SUPERVISE=0; GATE_OK=${GATE_OK:-0}
	: > "$EVENTS"
	rc_reentry_loop; LOOP_RC=$?
}
ev_count() { grep -c "^$1" "$EVENTS" 2>/dev/null || true; }

# ---- S1: zero spawn before a desktop->host transition, exactly one after ----
# host-at-start consumed; then desktop arms; then host fires once.
run 'host gone no - 0
desktop gone no - 0
host gone no ok:200:20 0'
eq s1.attempts 1 "$SPAWN_ATTEMPTS"
eq s1.ok 1 "$SPAWN_OK"

# ---- counterexample: host already foreground (post-crash), never a tap ----
run 'host gone no - 0
host gone no - 0
host gone no - 0'
eq xcrash.host_at_start.nospawn 0 "$SPAWN_ATTEMPTS"

# ---- counterexample: notification -> host (no desktop between) ----
run 'other gone no - 0
host gone no - 0'
eq xnotif.nospawn 0 "$SPAWN_ATTEMPTS"

# ---- counterexample: WMS error cancels a pending arm (fail closed) ----
run 'desktop gone no - 0
error gone no - 0
host gone no - 0'
eq xwmserr.nospawn 0 "$SPAWN_ATTEMPTS"

# ---- S2: child still alive -> consume, no spawn, no TERM ----
run 'desktop alive no - 0
host alive no - 0'
eq s2.alive.nospawn 0 "$SPAWN_ATTEMPTS"
eq s2.alive.consume 1 "$(ev_count consume_live_or_window)"

# ---- S2: a hidden owned window present -> consume, no spawn ----
run 'desktop gone yes - 0
host gone yes - 0'
eq s2.window.nospawn 0 "$SPAWN_ATTEMPTS"
eq s2.window.consume 1 "$(ev_count consume_live_or_window)"

# ---- S3: gate failure (boot change / PID reuse / parent mismatch) refuses ----
GATE_OK=1
run 'desktop gone no ok:200:20 0'
GATE_OK=0
eq s3.refuse.nospawn 0 "$SPAWN_ATTEMPTS"
eq s3.refuse.rc 2 "$LOOP_RC"
eq s3.refuse.event 1 "$(ev_count OWNER_REFUSED)"

# ---- S3: existing stop wins, no spawn, returns 0 (stop never deleted here) ----
run 'stop'
eq s3.stop.nospawn 0 "$SPAWN_ATTEMPTS"
eq s3.stop.rc 0 "$LOOP_RC"
eq s3.stop.event 1 "$(ev_count STOPPED)"

# ---- S3: child identity invalid -> fatal refuse, no spawn, no signal ----
run 'desktop invalid no - 0
host invalid no - 0'
eq s3.invalid.nospawn 0 "$SPAWN_ATTEMPTS"
eq s3.invalid.rc 2 "$LOOP_RC"

# ---- S4: 21 independent taps each spawn once (no 20-cap exit) ----
i=1; steps=""
while [ "$i" -le 21 ]; do
	steps="${steps}desktop gone no - 0
host gone no ok:$((200 + i)):$((20 + i)) 0
"
	i=$((i + 1))
done
run "$steps"
eq s4.21.attempts 21 "$SPAWN_ATTEMPTS"
eq s4.21.ok 21 "$SPAWN_OK"

# ---- S4: a launch FAIL does not auto-retry until the NEXT desktop->host tap ----
# desktop,host(fail) -> fail ; host (no desktop) -> consumed, NO retry ;
# desktop,host(ok)   -> one more spawn. (spawn outcome is on the HOST line.)
run 'desktop gone no - 0
host gone no fail:boom 0
host gone no ok:201:21 0
desktop gone no - 0
host gone no ok:202:22 0'
eq s4.fail.attempts 2 "$SPAWN_ATTEMPTS"
eq s4.fail.ok 1 "$SPAWN_OK"
eq s4.fail.failevent 1 "$(ev_count reentry_spawn_fail)"

# ---- unknown child status -> sticky hold, never spawn again (fail closed) ----
run 'desktop gone no - 0
host gone no unknown:boom 0
desktop gone no - 0
host gone no ok:204:24 0'
eq s4.unknown.attempts 1 "$SPAWN_ATTEMPTS"
eq s4.unknown.hold 1 "$(ev_count reentry_spawn_unknown_hold)"
eq s4.unknown.heldevent 1 "$(ev_count reentry_hold_fail_closed)"

# ---- spawn rc nonzero but text says ok -> classified unknown -> hold ----
run 'desktop gone no - 0
host gone no ok:206:26 5
desktop gone no - 0
host gone no ok:207:27 0'
eq spawnrc.nonzero.nook 0 "$SPAWN_OK"
eq spawnrc.nonzero.hold 1 "$(ev_count reentry_spawn_unknown_hold)"

# ---- quiet invariant: desktop-only polls emit NO decision events; only the ----
# terminal STOPPED line is written when the scripted steps run out.
run 'desktop gone no - 0
desktop gone no - 0
desktop gone no - 0'
eq quiet.only_stop 1 "$(grep -c '' "$EVENTS")"
eq quiet.is_stop 1 "$(ev_count STOPPED)"

printf '\nreentry-tests: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" = 0 ]
