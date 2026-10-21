#!/bin/sh
# T36 r4b offline replay (revision after T37 counterexamples; r4 9072bbfb test kept as run-epoch-tests.sh). Sources the WHOLE r4 watchdog (main call removed) with the unchanged r2/r3
# helpers and the r4 reentry-common. Real: rc_reentry_loop, rc_focus_state (section A),
# parent_window_reason, verify_parent_window_soft, rc_parent_epoch_switch, rc_direct_children,
# rc_socket_inode_of, rc_fd_holders, rc_gates_ok, rc_child_state, rc_owned_window_present,
# monitor_child, do_one_launch, rc_do_spawn, event/state/instance/write_exact, rb_birth.
# Stubbed device seams only: rc_send_term, rc_run_start_parent, rc_file_id (host stat syntax),
# parent_owned (birth-checked), child_owned, rb_owned_pids, rc_verify_window_process (section A),
# rc_focus_state (section B, scripted), rc_capture_wms (fixture), capture_*, sleep. Fake /proc.
# No device, no network, no real signal. Exits non-zero on any mismatch.
set -u
HERE=$(CDPATH= cd -P "$(dirname "$0")" && pwd -P)
CAND=$(CDPATH= cd -P "$HERE/.." && pwd -P)
REPO=$(CDPATH= cd -P "$CAND/../../.." && pwd -P)
R4=${EPOCH_UNDER_TEST:-"$CAND/src/watchdog-reentry-r4b.sh"}
R2P="$REPO/benchmark/2026-10-19-toutiao-icon-reentry/candidate-payload-r2/payload"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/rc-epoch.XXXXXX") || exit 2
trap 'chmod -R u+rwx "${WORK:?}" 2>/dev/null; rm -rf "${WORK:?}"' EXIT
pass=0; fail=0
ok() { pass=$((pass + 1)); printf 'PASS %s\n' "$1"; }
no() { fail=$((fail + 1)); printf 'FAIL %s : %s\n' "$1" "$2"; }
eq() { if [ "$2" = "$3" ]; then ok "$1"; else no "$1" "expected [$2] got [$3]"; fi; }
mkdir "$WORK/helpers"; cp "$R2P"/*.sh "$WORK/helpers/"
cp "${COMMON_UNDER_TEST:-$CAND/src/reentry-common-r4.sh}" "$WORK/helpers/reentry-common.sh"
BOOT0=be4badc3-5a79-4fa8-8758-e6aacc0ca05f
PROC="$WORK/proc"; F="$WORK/F"; SOCK="$WORK/sock"
mkdir -p "$PROC/sys/kernel/random" "$F"
printf '%s\n' "$BOOT0" > "$PROC/sys/kernel/random/boot_id"; printf '23350.00 1.00\n' > "$PROC/uptime"
export TT_PROC="$PROC" TT_STATE_ROOT="$F" TT_RUNTIME="$WORK/rt" TT_OWNER_UID=20011206 TT_SOCKET="$SOCK"
grep -c '^main "\$@"$' "$R4" | grep -qx 1 || { echo "main line not unique" >&2; exit 2; }
sed -e '$d' -e "s#^HERE=.*#HERE='$WORK/helpers'#" "$R4" > "$WORK/r4-under-test.sh"
. "$WORK/r4-under-test.sh"
set +u
for fn in rc_parent_epoch_switch parent_window_reason rc_direct_children rc_socket_inode_of rc_fd_holders rc_owned_pids_strict rc_wait_exit rc_epoch_binding rc_proc_live; do
	command -v "$fn" >/dev/null 2>&1 || { echo "$fn missing" >&2; exit 2; }
done
BOOT=$BOOT0
rmproc() { rm -rf "${PROC:?}/${1:?}"; }
# ---- stubbed device seams ----
sleep() { :; }; rc_sleep() { :; }
capture_frame() { return 1; }; capture_context() { :; }
rc_file_id() { if stat -c '%d:%i' "$1" >/dev/null 2>&1; then stat -c '%d:%i' "$1"; else stat -f '%d:%i' "$1" 2>/dev/null; fi; }
PARENT_BAD=0
parent_owned() { [ "$PARENT_BAD" = 0 ] && [ "$(rb_birth "$1")" = "$2" ]; }
OWNED_EXTRA=; rb_owned_pids() { echo "rb_owned_pids must not be used by r4b" >&2; return 99; }
rb_owned() { [ -e "$PROC/$1/route-b-owned" ]; }   # stands for the exe/SHA/run-inode checks
child_owned() { b=$(rb_birth "$1") || { rb_deny birth '<read-error-or-exited>' "$2"; return 1; }; [ "$b" = "$2" ] || { rb_deny birth "$b" "$2"; return 1; }; }
TERM_MODE=exit
rc_send_term() {
	echo "$1" >> "$WORK/terms"
	case "$TERM_MODE" in
	exit) rmproc "$1"; : > "$PROC/$$/net/unix";;
	stay) :;;
	fail) return 1;;
	replace) rmproc "$1"; : > "$PROC/$$/net/unix"; rm -f "${SOCK:?}"; : > "$SOCK";;
	holder) rmproc "$1"; : > "$PROC/$$/net/unix"; mkpid 9300 1 0; ln -s "socket:[4242]" "$PROC/9300/fd/4";;
	zombie) printf '%s (appspawn-x) Z 1 0 0 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 %s 0 0\n' "$1" "$PARENT_B" > "$PROC/$1/stat";;
	reuse) rmproc "$1"; : > "$PROC/$$/net/unix"; mkpid "$1" 1 0 7777;;
	listener) rmproc "$1";;
	esac
}
START_MODE=ok
rc_run_start_parent() {
	echo start >> "$WORK/starts"
	# start-parent.sh is what rewrites run.sh (new inode): record what it would see at that moment.
	{ [ -d "$PROC/$PARENT" ] && echo old_parent_alive; [ -e "$SOCK" ] && echo socket_present; } >> "$WORK/start_violations"
	case "$START_MODE" in
	ok) new_parent; printf 'WL_PARENT_ID=%s\nASX_RUNTIME_OWNER_UID=20011206\n' "${NEW_WID:-66}" > "$PROC/6100/environ"; printf '6100 6200\n' > "$F/parent-identity"; echo 6100 > "$1";;
	nonzero) return 3;;
	garbage) echo x > "$1";;
	dead) echo 6100 > "$1";;
	ok_epoch_unwritable) new_parent
	    printf 'WL_PARENT_ID=66\nASX_RUNTIME_OWNER_UID=20011206\n' > "$PROC/6100/environ"; printf '6100 6200\n' > "$F/parent-identity"
	    rm -f "${F:?}/parent-epoch"; mkdir "$F/parent-epoch"; echo 6100 > "$1";;
	esac
}
FOCUS_FILE="$WORK/focus"; FOCUS_I=0
script_focus() { FOCUS_I=$((FOCUS_I + 1)); rc_focus_result=$(sed -n "${FOCUS_I}p" "$FOCUS_FILE"); [ -n "$rc_focus_result" ] || { : > "$F/stop"; rc_focus_result=error; }; return 0; }
WMS_SRC="$WORK/wms.txt"; rc_capture_wms() { cp "$WMS_SRC" "$1"; }
make_dump() { # <file> <host wid> [extra rows]
	f=$1; w=$2; shift 2
	{
		printf '%s\n\n' "$BOOT0"
		printf -- '----------------------------------WindowManagerService----------------------------------\n'
		printf 'WindowName DisplayId Pid WinId Type Mode Flag ZOrd Orientation [ x y w h ]\n'
		printf 'SCBDesktop6 0 2389 11 2001 1 0 2 0 [ 0 0 1200 1920 ]\n'
		printf 'imehost0 0 22069 %s 1 1 0 101 0 [ 0 0 1200 1920 ]\n' "$w"
		for r in "$@"; do printf '%s\n' "$r"; done
		printf 'Focus window: %s\nAll Focus window: \nDisplayId: 0 WindowId: %s\nTotal window num: 30\nHighlighted windows: %s\nWMS_REMOTE_RC=0\n' "$w" "$w" "$w"
	} > "$f"
}
stat_row() { # <pid> <state> <birth> <ppid>
	printf '%s (id.article.news) %s %s 5402 0 0 -1 1077936448 920061 5333 8232 0 23249 10693 4 74 20 0 332 0 %s 246606372864 259552 18446744073709551615 0 0 0 0 0 0 4612 4097 1073841402 0 0 0 17 5 0 0 0 0 0\n' "$1" "$2" "$4" "$3"
}
PARENT=5089; PARENT_B=5573; CHILD=7140; CB=7507; OWNER=20011206
mkpid() { # <pid> <ppid> <uid> [birth]: complete fake /proc entry (stat, status, fd dir)
	mkdir -p "$PROC/$1/fd"; stat_row "$1" S "${4:-1}" "$2" > "$PROC/$1/stat"
	printf 'Name:\tx\nUid:\t%s\t%s\t%s\t%s\n' "$3" "$3" "$3" "$3" > "$PROC/$1/status"
}
LROW() { printf 'Num RefCount Protocol Flags Type St Inode Path\n0000000000000000: 00000002 00000000 00010000 0001 01 %s %s\n' "$1" "$SOCK"; }
new_parent() { # what start-parent.sh leaves behind: parent 6100/6200 owning a fresh listener 5151
	mkpid 6100 1 0 6200; mkdir -p "$PROC/6100/ns" "$PROC/6100/net"; ln -s "mnt:[4026533100]" "$PROC/6100/ns/mnt"
	LROW 5151 > "$PROC/6100/net/unix"; LROW 5151 > "$PROC/$$/net/unix"; ln -s "socket:[5151]" "$PROC/6100/fd/3"; : > "$SOCK"
}
put_parent() {
	rmproc "$PARENT"; mkpid "$PARENT" 1 0 "$PARENT_B"; mkdir -p "$PROC/$PARENT/net" "$PROC/$PARENT/ns"
	ln -s "mnt:[4026532999]" "$PROC/$PARENT/ns/mnt"
	LROW 4242 > "$PROC/$PARENT/net/unix"; LROW 4242 > "$PROC/$$/net/unix"
	ln -s "socket:[4242]" "$PROC/$PARENT/fd/3"
	printf 'WL_PARENT_ID=30\nASX_RUNTIME_OWNER_UID=20011206\n' > "$PROC/$PARENT/environ"
}
put_child() { mkpid "$1" "$PARENT" "$OWNER" "$2"; : > "$PROC/$1/route-b-owned"; }
reset_all() {
	for d in "$PROC"/[0-9]*; do [ -d "$d" ] && rmproc "${d##*/}"; done
	rm -rf "${F:?}"; rm -f "$WORK/terms" "$WORK/starts" "$WORK/spawns" "$WORK/start_violations"; mkdir -p "$F/lock"
	printf '%s\n' "$BOOT0" > "$PROC/sys/kernel/random/boot_id"
	self_birth=3869; BOOT=$BOOT0; printf '%s %s %s\n' "$$" "$self_birth" "$BOOT" > "$F/lock/owner"
	: > "$F/events.log"; : > "$F/state"; printf '1\n' > "$F/sequence"
	mkpid "$$" 1 0 3869; mkdir -p "$PROC/$$/net"   # guardian's own entry: live-view witness
	put_parent; : > "$SOCK"
	printf 'phase=bound parent=%s:%s mntns=mnt:[4026532999] sock=4242 sockfile=%s\n' "$PARENT" "$PARENT_B" "$(rc_file_id "$SOCK")" > "$F/parent-epoch"
	parent=$PARENT; parent_birth=$PARENT_B; child=$CHILD; child_birth=$CB; seq=1
	instance; ret_key=; keep_lock=0; owner_verified=1; polls=0; TT_MAX_POLLS=1; rc_epoch_hold=0
	PARENT_BAD=0; OWNED_EXTRA=; TERM_MODE=exit; START_MODE=ok; NEW_WID=66; FOCUS_I=0; : > "$FOCUS_FILE"
	make_dump "$WMS_SRC" 66
	printf '#!/bin/sh\nexit 0\n' > "$F/readiness-probe.sh"
	printf '#!/bin/sh\necho SPAWNED >> "%s/spawns"\nmkdir -p "%s/8001/fd"\nprintf "%%s\\n" "%s" > "%s/8001/stat"\nprintf "Uid:\\t%s\\t%s\\t%s\\t%s\\n" > "%s/8001/status"\n: > "%s/8001/route-b-owned"\necho "HOST_SPAWN result=0 pid=8001"\n' \
		"$WORK" "$PROC" "$(stat_row 8001 S 9100 6100)" "$PROC" "$OWNER" "$OWNER" "$OWNER" "$OWNER" "$PROC" "$PROC" > "$F/spawn.sh"
}
retire() { monitor_child >/dev/null 2>&1; }   # child absent -> strict exited -> retired
cnt() { if [ -f "$1" ]; then grep -c . "$1"; else echo 0; fi; }
evc() { grep -c -- "$1" "$F/events.log" 2>/dev/null || true; }
focus() { printf '%s\n' "$@" > "$FOCUS_FILE"; }
loop() { # subshell exit code is the loop rc, or io_fail's exit 5 (which never returns)
	rm -f "$WORK/loopparent"
	( rc_focus_state() { script_focus; }; rc_reentry_loop; lr=$?; printf '%s %s %s\n' "$parent" "$parent_birth" "$rc_epoch_hold" > "$WORK/loopparent"; exit "$lr" ) >/dev/null 2>&1
	LRC="rc=$?"
}
sockstate() { if [ -e "$SOCK" ]; then echo yes; else echo no; fi; }

# ===== A. classification by the real rc_focus_state =====
reset_all
rc_verify_window_process() { RC_WINDOW_BIRTH=2344035; return 0; }
mkdir -p "$PROC/22069"; stat_row 22069 S 2344035 374 > "$PROC/22069/stat"
make_dump "$WMS_SRC" 66; rc_focus_reason=; rc_focus_state; eq A.newhost.result "newhost 66" "$rc_focus_result"; eq A.newhost.reason wid_mismatch "$rc_focus_reason"
make_dump "$WMS_SRC" 30; rc_focus_state; eq A.same_wid.host "host 30" "$rc_focus_result"
printf 'ASX_RUNTIME_OWNER_UID=20011206\n' > "$PROC/$PARENT/environ"; make_dump "$WMS_SRC" 66; rc_focus_state
eq A.wid_missing.other other "$rc_focus_result"; eq A.wid_missing.reason parent_wid_missing "$rc_focus_reason"
printf 'WL_PARENT_ID=30\nASX_RUNTIME_OWNER_UID=1\n' > "$PROC/$PARENT/environ"; rc_focus_state
eq A.uid_mismatch.other other "$rc_focus_result"; eq A.uid_mismatch.reason parent_uid_mismatch "$rc_focus_reason"
printf 'WL_PARENT_ID=30\nWL_PARENT_ID=31\nASX_RUNTIME_OWNER_UID=20011206\n' > "$PROC/$PARENT/environ"; rc_focus_state
eq A.wid_ambiguous.reason parent_wid_ambiguous "$rc_focus_reason"
put_parent; PARENT_BAD=1; rc_focus_state; eq A.parent_identity.reason parent_identity "$rc_focus_reason"; PARENT_BAD=0
rc_verify_window_process() { return 1; }; rc_focus_state; eq A.host_process_unverified.other other "$rc_focus_result"
eq A.reason_not_stale host_process_unverified "$rc_focus_reason"
unset -f rc_verify_window_process

# ===== B1. recreated host, strict preconditions: exactly one epoch switch and one spawn =====
reset_all; retire; focus desktop "newhost 66"; loop
eq B1.rc rc=0 "$LRC"; eq B1.one_term 1 "$(cnt "$WORK/terms")"; eq B1.term_target "$PARENT" "$(cat "$WORK/terms")"
eq B1.one_start 1 "$(cnt "$WORK/starts")"; eq B1.one_spawn 1 "$(cnt "$WORK/spawns")"
eq B1.switched_event 1 "$(evc "parent_epoch_switched old=$PARENT:$PARENT_B new=6100:6200 wid=66")"
eq B1.spawn_ok 1 "$(evc reentry_spawn_ok)"; eq B1.epoch_record "phase=switched old=$PARENT:$PARENT_B parent=6100:6200 wid=66 mntns=mnt:[4026533100] sock=5151 sockfile=$(rc_file_id "$SOCK")" "$(cat "$F/parent-epoch")"
eq B1.parent_identity "6100 6200" "$(cat "$F/parent-identity")"; eq B1.loop_parent "6100 6200 0" "$(cat "$WORK/loopparent")"
eq B1.socket_recreated_by_new_parent yes "$(sockstate)"
eq B1.old_exited_and_socket_gone_before_runsh_rewrite 0 "$(cnt "$WORK/start_violations")"
eq B1.retire_event_kept 1 "$(evc 'child_retired key=')"
order=$(grep -o 'reason=[a-z_]*' "$F/events.log" | grep -E 'child_retired|parent_epoch_stop|parent_epoch_switched|child_retirement_cleared|reentry_spawn_ok' | tr '\n' ' ')
eq B1.tuple_kept_until_new_spawn "reason=child_retired reason=parent_epoch_stop reason=parent_epoch_switched reason=child_retirement_cleared reason=reentry_spawn_ok " "$order"

# ===== B2. refusals before any action: no signal, no socket removal, no new parent =====
refused() { # <name> <expected reason prefix>
	eq "$1.no_term" 0 "$(cnt "$WORK/terms")"; eq "$1.no_start" 0 "$(cnt "$WORK/starts")"; eq "$1.no_spawn" 0 "$(cnt "$WORK/spawns")"
	eq "$1.socket_kept" yes "$(sockstate)"
	if [ "$(evc "parent_epoch_refused reason=$2")" -ge 1 ]; then ok "$1.reason"; else no "$1.reason" "$(grep -o 'parent_epoch_refused[^ ]* [^ ]*' "$F/events.log" | head -1)"; fi
}
reset_all; put_child "$CHILD" "$CB"; focus desktop "newhost 66"; loop          # live (unretired) child
eq B2.live.no_term 0 "$(cnt "$WORK/terms")"; eq B2.live.no_start 0 "$(cnt "$WORK/starts")"; eq B2.live.consumed 1 "$(evc 'consume_live_or_window child=alive')"
reset_all; retire; put_child 9001 1; focus desktop "newhost 66"; loop; refused B2.other_child children_present
reset_all; retire; put_child 9002 1; chmod 000 "$PROC/9002/stat"
if cat "$PROC/9002/stat" >/dev/null 2>&1; then echo "SKIP B2.enum_unknown (root)"; else focus desktop "newhost 66"; loop; refused B2.enum_unknown children_unknown; fi
chmod -R u+rwx "$PROC/9002" 2>/dev/null
reset_all; retire; : > "$PROC/$PARENT/net/unix"; focus desktop "newhost 66"; loop; refused B2.socket_owner socket_owner_unknown
reset_all; retire; mkpid 9300 1 0; ln -s "socket:[4242]" "$PROC/9300/fd/4"; focus desktop "newhost 66"; loop; refused B2.socket_second_holder socket_owner_unknown
reset_all; retire; rm -f "${SOCK:?}"; focus desktop "newhost 66"; loop
eq B2.socket_file_missing.no_term 0 "$(cnt "$WORK/terms")"; eq B2.socket_file_missing.reason 1 "$(evc 'parent_epoch_refused reason=socket_owner_unknown')"
reset_all; retire; focus "newhost 66" "newhost 66"; loop                        # no desktop edge
eq B2.no_desktop.no_term 0 "$(cnt "$WORK/terms")"; eq B2.no_desktop.no_spawn 0 "$(cnt "$WORK/spawns")"
reset_all; retire; PARENT_BAD=1; focus desktop "newhost 66"; loop               # parent identity drift
eq B2.parent_drift.rc rc=2 "$LRC"; eq B2.parent_drift.no_term 0 "$(cnt "$WORK/terms")"; eq B2.parent_drift.gate 1 "$(evc 'OWNER_REFUSED gate=parent_identity_no_signal')"

# ===== B3. partial failures: sticky hold, never a second parent or spawn =====
partial() { # <name> <reason prefix> <terms> <starts>
	eq "$1.terms" "$3" "$(cnt "$WORK/terms")"; eq "$1.starts" "$4" "$(cnt "$WORK/starts")"; eq "$1.no_spawn" 0 "$(cnt "$WORK/spawns")"
	eq "$1.tuple_kept" 0 "$(evc child_retirement_cleared)"
	eq "$1.no_start_while_old_alive" 0 "$(cnt "$WORK/start_violations")"
	if [ "$(evc "parent_epoch_partial_hold reason=$2")" -ge 1 ]; then ok "$1.reason"; else no "$1.reason" "$(grep -o 'parent_epoch_partial_hold[^ ]* [^ ]*' "$F/events.log" | head -1)"; fi
	# Old parent still alive -> sticky hold consumes the next edge. Old parent already gone -> the
	# loop-top gate refuses (parent_identity), guardian exits rc=2 keeping the lock. Both: no restart.
	if parent_owned "$PARENT" "$PARENT_B"; then eq "$1.second_edge_held" 1 "$(evc reentry_hold_fail_closed)"
	else eq "$1.exit_keep_lock" "rc=2 1" "$LRC $(evc 'OWNER_REFUSED gate=parent_identity_no_signal')"; fi
}
reset_all; retire; TERM_MODE=stay; focus desktop "newhost 66" desktop "newhost 66"; loop; partial B3.not_exited old_parent_not_exited 1 0
eq B3.not_exited.record_stopping 1 "$(grep -c "^phase=stopping old=$PARENT:$PARENT_B wid=66 sock=4242" "$F/parent-epoch")"
reset_all; retire; TERM_MODE=fail; focus desktop "newhost 66" desktop "newhost 66"; loop; partial B3.signal_failed old_parent_signal_failed 1 0
reset_all; retire; TERM_MODE=holder; focus desktop "newhost 66" desktop "newhost 66"; loop; partial B3.replacement_listener socket_still_held 1 0
eq B3.replacement_listener.socket_kept yes "$(sockstate)"
reset_all; retire; TERM_MODE=replace; focus desktop "newhost 66" desktop "newhost 66"; loop; partial B3.socket_replaced socket_file_replaced 1 0
eq B3.socket_replaced.not_unlinked yes "$(sockstate)"
reset_all; retire; START_MODE=nonzero; focus desktop "newhost 66" desktop "newhost 66"; loop; partial B3.start_unknown new_parent_start_nonzero 1 1
reset_all; retire; START_MODE=garbage; focus desktop "newhost 66" desktop "newhost 66"; loop; partial B3.start_garbage new_parent_pid_invalid 1 1
reset_all; retire; START_MODE=dead; focus desktop "newhost 66" desktop "newhost 66"; loop; partial B3.start_dead new_parent_not_alive 1 1
eq B3.start_dead.old_identity_logged 1 "$(evc "parent_epoch_stop old=$PARENT:$PARENT_B wid=66 sock=4242")"
reset_all; retire; NEW_WID=72; focus desktop "newhost 66" desktop "newhost 66"; loop; partial B3.new_parent_other_wid new_parent_wid_wid_mismatch 1 1
eq B3.new_parent_other_wid.no_switched_record 0 "$(grep -c '^phase=switched' "$F/parent-epoch")"

# persistence failure: stopping record unwritable -> io_fail before any signal; switched record
# unwritable after a successful start -> io_fail (exit 5, lock kept, IO_FAILED), never a spawn.
reset_all; retire; chmod 444 "$F/parent-epoch"; focus desktop "newhost 66"; loop
eq B3.persist_before_signal.rc rc=5 "$LRC"; eq B3.persist_before_signal.no_term 0 "$(cnt "$WORK/terms")"; eq B3.persist_before_signal.no_start 0 "$(cnt "$WORK/starts")"
eq B3.persist_before_signal.socket_kept yes "$(sockstate)"
reset_all; retire; START_MODE=ok_epoch_unwritable; focus desktop "newhost 66" desktop "newhost 66"; loop
eq B3.persist_after_start.rc rc=5 "$LRC"; eq B3.persist_after_start.one_start 1 "$(cnt "$WORK/starts")"; eq B3.persist_after_start.no_spawn 0 "$(cnt "$WORK/spawns")"
eq B3.persist_after_start.state IO_FAILED "$(cat "$F/state")"; eq B3.persist_after_start.old_identity_logged 1 "$(evc "parent_epoch_stop old=$PARENT:$PARENT_B")"
eq B3.persist_after_start.new_identity_readback "6100 6200" "$(cat "$F/parent-identity")"; eq B3.persist_after_start.no_switched_event 0 "$(evc parent_epoch_switched)"

# T37 counterexamples, end to end in the real loop (r4b revision)
reset_all; retire; mkpid 9001 1 0; printf 'malformed\n' > "$PROC/9001/stat"; focus desktop "newhost 66"; loop; refused B2.malformed_stat children_unknown
reset_all; retire; mkpid 9001 1 0; rm -rf "${PROC:?}/9001/fd"; focus desktop "newhost 66"; loop; refused B2.missing_fd_dir socket_owner_unknown
reset_all; retire; mkpid 9001 1 0; ln -s "x" "$PROC/9001/fd/9"; readlink() { case "$1" in */9001/fd/9) return 1;; *) command readlink "$@";; esac; }
focus desktop "newhost 66"; loop; refused B2.failed_readlink socket_owner_unknown; unset -f readlink
reset_all; retire; printf 'Num RefCount Protocol Flags Type St Inode Path\n0000000000000000: 00000002 00000000 00000000 0001 03 4242 %s\n' "$SOCK" > "$PROC/$PARENT/net/unix"
focus desktop "newhost 66"; loop; refused B2.connected_not_listener socket_owner_unknown
reset_all; retire; : > "$PROC/$$/net/unix"; focus desktop "newhost 66"; loop; refused B2.guardian_net_view_differs socket_owner_unknown
reset_all; retire; rm -f "${F:?}/parent-epoch"; focus desktop "newhost 66"; loop; refused B2.epoch_record_missing epoch_record_missing
reset_all; retire; printf 'phase=bound parent=%s:1 mntns=mnt:[4026532999] sock=4242 sockfile=%s\n' "$PARENT" "$(rc_file_id "$SOCK")" > "$F/parent-epoch"; focus desktop "newhost 66"; loop; refused B2.epoch_other_parent epoch_parent_mismatch
reset_all; retire; rm -f "$PROC/$PARENT/ns/mnt"; ln -s "mnt:[1]" "$PROC/$PARENT/ns/mnt"; focus desktop "newhost 66"; loop; refused B2.epoch_namespace_changed epoch_binding_changed
reset_all; retire; printf 'phase=unbound parent=%s:%s\n' "$PARENT" "$PARENT_B" > "$F/parent-epoch"; focus desktop "newhost 66"; loop; refused B2.epoch_unbound epoch_not_bound
reset_all; retire; mkpid 9400 1 "$OWNER"; ln -s /data/local/tmp/asx/appspawn-x "$PROC/9400/exe"; focus desktop "newhost 66"; loop
eq B2.owned_unclassifiable.no_term 0 "$(cnt "$WORK/terms")"; eq B2.owned_unclassifiable.window_unknown 1 "$(evc 'consume_live_or_window child=gone win=unknown')"
# the switch's own owned check (window parser bypassed) refuses too
reset_all; retire; mkpid 9400 1 "$OWNER"; ln -s /data/local/tmp/asx/appspawn-x "$PROC/9400/exe"; rc_owned_window_present() { rc_owned_result=no; return 0; }
focus desktop "newhost 66"; loop; refused B2.owned_unclassifiable_in_switch owned_enumeration_unknown; eval "$(sed -n '/^rc_owned_window_present() {$/,/^}$/p' "$R4")"
reset_all; retire; mkpid 9400 1 "$OWNER"; ln -s /system/bin/appspawn "$PROC/9400/exe"; focus desktop "newhost 66"; loop
eq B2.same_uid_other_exe_not_owned.one_spawn 1 "$(cnt "$WORK/spawns")"
reset_all; retire; mkpid 9400 1 "$OWNER"; : > "$PROC/9400/route-b-owned"; focus desktop "newhost 66"; loop; eq B2.owned_present.no_term 0 "$(cnt "$WORK/terms")"; eq B2.owned_present.no_spawn 0 "$(cnt "$WORK/spawns")"
reset_all; retire; TERM_MODE=zombie; focus desktop "newhost 66" desktop "newhost 66"; loop; partial B3.exit_unknown_zombie old_parent_exit_unknown 1 0
reset_all; retire; TERM_MODE=reuse; focus desktop "newhost 66" desktop "newhost 66"; loop; partial B3.pid_reused old_parent_pid_reused 1 0
eq B3.pid_reused.socket_kept yes "$(sockstate)"
reset_all; retire; TERM_MODE=listener; focus desktop "newhost 66" desktop "newhost 66"; loop; partial B3.listener_after_exit socket_listener_after_exit:1 1 0
eq B3.listener_after_exit.socket_kept yes "$(sockstate)"
reset_all; retire; TERM_MODE=exit; rc_send_term() { echo "$1" >> "$WORK/terms"; rmproc "$1"; : > "$PROC/$$/net/unix"; rmproc "$$"; }
focus desktop "newhost 66" desktop "newhost 66"; loop; partial B3.exit_without_live_view old_parent_exit_unknown 1 0
eval "$(sed -n '/^rc_send_term() {$/,/^}$/p' "$0")"

# ===== B4. warm return / historical behaviour unchanged =====
reset_all; put_child "$CHILD" "$CB"; make_dump "$WMS_SRC" 30; focus desktop "host 30" desktop "host 30"; loop
eq B4.warm.no_term 0 "$(cnt "$WORK/terms")"; eq B4.warm.no_spawn 0 "$(cnt "$WORK/spawns")"; eq B4.warm.parent_kept "$PARENT $PARENT_B 0" "$(cat "$WORK/loopparent")"
reset_all; retire; make_dump "$WMS_SRC" 30
printf '#!/bin/sh\necho SPAWNED >> "%s/spawns"\nmkdir -p "%s/8001"\nprintf "%%s\\n" "%s" > "%s/8001/stat"\necho "HOST_SPAWN result=0 pid=8001"\n' \
	"$WORK" "$PROC" "$(stat_row 8001 S 9100 "$PARENT")" "$PROC" > "$F/spawn.sh"
focus desktop "host 30"; loop
eq B4.same_host_reentry.one_spawn 1 "$(cnt "$WORK/spawns")"; eq B4.same_host_reentry.no_term 0 "$(cnt "$WORK/terms")"; eq B4.same_host_reentry.no_start 0 "$(cnt "$WORK/starts")"
reset_all; retire; make_dump "$WMS_SRC" 30; mkpid 9400 1 "$OWNER"; ln -s /data/local/tmp/asx/appspawn-x "$PROC/9400/exe"; focus desktop "host 30"; loop
eq B4.same_host_owned_enum_unknown.no_spawn 0 "$(cnt "$WORK/spawns")"; eq B4.same_host_owned_enum_unknown.consumed 1 "$(evc 'consume_live_or_window child=gone win=unknown')"
reset_all; retire; focus desktop other "newhost 66"; loop                        # other cancels the arm
eq B4.other_cancels.no_term 0 "$(cnt "$WORK/terms")"

# ===== C. source structure =====
R3="$REPO/benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/src/watchdog-reentry-r3.sh"
sh256() { (sha256sum "$1" 2>/dev/null || shasum -a 256 "$1") | cut -d' ' -f1; }
eq C.r3_source_unchanged 8bf74a08b71474e39e90fcdb012eed5e420f7352fa131cef2aa63b9c5bd80ef9 "$(sh256 "$R3")"
eq C.r3_common_unchanged 43d7b073467708770c8c69724633666e410d45581f8c0099d5098c31215e78ab "$(sh256 "$R2P/reentry-common.sh")"
eq C.one_kill_site 1 "$(grep -c 'kill -15' "$R4")"
eq C.kill_only_in_seam 1 "$(grep -c '^rc_send_term() { kill -15 "\$1"; }$' "$R4")"
eq C.term_called_once 1 "$(grep -c 'rc_send_term "\$pe_old"' "$R4")"
eq C.no_rb_owned_pids_call 0 "$(grep -c 'rb_owned_pids' "$R4")"
eq C.wid_gate_kept 1 "$(grep -c '\[ "\${vpw_wid#WL_PARENT_ID=}" = "\$vpw_fg" \] || return 1' "$R4")"
printf '\n%s passed, %s failed\n' "$pass" "$fail"
[ "$fail" = 0 ]
