#!/bin/sh
# REAL exit-race tests for the r2 fix (cx-seal + p3 + cx-seal r2 review, 2026-10-19).
#
# Two lanes, both against the REAL bodies extracted from src/watchdog-reentry.sh and
# the REAL frozen route-b-owner.sh (rb_birth, rb_owned, rb_deny encoder):
#   Lane A (stub guard): child_owned is a wrapper that emits the REAL deny records and
#           mutates the fake /proc mid-check, to drive every verdict/classifier branch.
#   Lane B (real chain): the REAL child_owned + REAL rb_owned run unmodified; only the
#           command boundaries (sha256sum / stat / readlink) are shimmed, injecting the
#           race at named I/O sites — the method cx-seal used to reproduce the r2
#           blockers (t4 r2-4390a193/probe-real-paths.sh). Those six cases are ported.
# No device, no awk, no python, no temp files from the code under test.
set -u
HERE=$(CDPATH= cd -P "$(dirname "$0")" && pwd -P)
BASE=$(CDPATH= cd -P "$HERE/.." && pwd -P)
REPO=$(CDPATH= cd -P "$BASE/../.." && pwd -P)
SRC="$BASE/src/watchdog-reentry.sh"
OWNER="$REPO/benchmark/2026-10-12-v1-seal-assembly/restore-v6/package-composed-disabled/payload/route-b-owner.sh"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/rc-race.XXXXXX") || { echo "mktemp failed" >&2; exit 2; }
trap 'chmod -R u+rwx "$WORK" 2>/dev/null; rm -rf "$WORK"' EXIT

pass=0; fail=0; skip=0
ok() { pass=$((pass + 1)); printf 'PASS %s\n' "$1"; }
no() { fail=$((fail + 1)); printf 'FAIL %s : %s\n' "$1" "$2"; }
eq() { if [ "$2" = "$3" ]; then ok "$1"; else no "$1" "expected [$2] got [$3]"; fi; }

PROCROOT="$WORK/proc"; PROC="$PROCROOT"; RB_PROC="$PROC"; F="$WORK/F"
mkdir -p "$PROC/sys/kernel/random" "$F"
BOOT=f59c05dd-85b1-40f9-8ad5-baec804d642f
printf '%s\n' "$BOOT" > "$PROC/sys/kernel/random/boot_id"
RB_RUNTIME="$WORK/rt"; RB_OWNER_UID=20011206; mkdir -p "$RB_RUNTIME"
. "$OWNER"
. "$BASE/src/exit-verdict.sh"
sed -n '/^child_owned() {/,/^}/p; /^rc_verdict_to_state() {/,/^}/p; /^rc_child_state() {/,/^}/p; /^monitor_child() {/,/^}/p' "$SRC" > "$WORK/under-test.sh"
for fn in child_owned rc_child_state monitor_child; do grep -q "^$fn() {" "$WORK/under-test.sh" || { echo "$fn not extracted" >&2; exit 2; }; done
. "$WORK/under-test.sh"
REAL_CHILD_OWNED=$(sed -n '/^child_owned() {/,/^}/p' "$WORK/under-test.sh")

PID=7233; PARENT=5430; BIRTH=16206; OWNUID="$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID"
stat_row() { # <state> <birth>
	printf '%s (id.article.news) %s %s 5402 0 0 -1 1077936448 920061 5333 8232 0 23249 10693 4 74 20 0 332 0 %s 246606372864 259552 18446744073709551615 367158579140 367158712560 548698470336 0 0 0 4612 4097 1073841402 0 0 0 17 5 0 0 0 0 0 367158723536 367158723552 367784644608 548698472817 548698472892 548698472892 548698476505 0\n' "$PID" "$1" "$PARENT" "$2"
}
reset_proc() { # <state> <birth>; a realistic child: stat/status/exe/ns, plus init ns
	PROC="$PROCROOT"; RB_PROC="$PROC"
	chmod -R u+rwx "$PROC" 2>/dev/null; rm -rf "$PROC/$PID" "$PROC/1"; mkdir -p "$PROC/$PID/ns" "$PROC/1/ns"
	printf '1 (init) S 0 1 1 0 -1 4194560 1 0 0 0 1 1 0 0 20 0 1 0 2 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 0\n' > "$PROC/1/stat"
	stat_row "$1" "$2" > "$PROC/$PID/stat"
	printf 'Uid:\t%s\t%s\t%s\t%s\n' "$RB_OWNER_UID" "$RB_OWNER_UID" "$RB_OWNER_UID" "$RB_OWNER_UID" > "$PROC/$PID/status"
	ln -s /data/local/tmp/asx/appspawn-x "$PROC/$PID/exe"
	ln -s 'mnt:[2]' "$PROC/$PID/ns/mnt"; ln -s 'mnt:[1]' "$PROC/1/ns/mnt"
	rm -f "$F/stop"; : > "$WORK/events"; OWNED_CALLS=0; MUTATION=none; MODE=normal
}
state() { printf 'STATE %s %s\n' "$1" "$2" >> "$WORK/events"; }
event() { printf 'EVENT %s\n' "$*" >> "$WORK/events"; }
verify_exact() { :; }
io_fail() { printf 'IOFAIL %s\n' "$*" >> "$WORK/events"; return 5; }
capture_frame() { printf 'CAPTURE_REACHED\n' >> "$WORK/events"; return 1; }
capture_context() { :; }
control_file() { :; }
sleep() { :; }
kill() { printf 'KILL %s\n' "$*" >> "$WORK/events"; }
child=$PID; child_birth=$BIRTH; parent=$PARENT; parent_birth=14767
seq=1; polls=0; TT_MAX_POLLS=1; self_birth=1; keep_lock=0; owner_verified=1
ev() { grep -c "$1" "$WORK/events" 2>/dev/null || true; }
unreadable_supported() { reset_proc S "$BIRTH"; chmod 000 "$PROC/$PID/stat"; if cat "$PROC/$PID/stat" >/dev/null 2>&1; then return 1; fi; return 0; }
UNR=0; unreadable_supported && UNR=1
mon() { monitor_child 2>/dev/null; MRC=$?; }
V() { child_exit_verdict "$PID" "$BIRTH" "$BOOT"; }

# ================= owned_failure_kind against the REAL encoder (field-aware) =================
eq k.death_birth death "$(owned_failure_kind "$(rb_deny birth '<read-error-or-exited>' 1 2>&1)")"
eq k.death_birth_after death "$(owned_failure_kind "$(rb_deny birth_after '<read-error-or-exited>' 1 2>&1)")"
eq k.death_uid_readerror death "$(owned_failure_kind "$(rb_deny uid '<read-error>' x 2>&1)")"
eq k.death_exe_readerror death "$(owned_failure_kind "$(rb_deny exe '<read-error>' exact_route_b_alias 2>&1)")"
eq k.death_namespace_readerror death "$(owned_failure_kind "$(rb_deny namespace '<read-error>' private 2>&1)")"
eq k.death_private_inode_readerror death "$(owned_failure_kind "$(rb_deny private_inode '<read-error>' 1:2 2>&1)")"
eq k.death_ppid_readerror death "$(owned_failure_kind "$(rb_deny ppid '<read-error>' 5430 2>&1)")"
eq k.death_exe_sha_empty death "$(owned_failure_kind "$(rb_deny exe_sha '' "$RB_SPAWNER_SHA" 2>&1)")"
eq k.mismatch_init_namespace_readerror mismatch "$(owned_failure_kind "$(rb_deny init_namespace '<read-error>' readable 2>&1)")"
eq k.mismatch_physical_inode_readerror mismatch "$(owned_failure_kind "$(rb_deny physical_inode '<read-error>' readable 2>&1)")"
eq k.mismatch_uid_value mismatch "$(owned_failure_kind "$(rb_deny uid 20010000:20010000:20010000:20010000 "$OWNUID" 2>&1)")"
eq k.mismatch_exe_value mismatch "$(owned_failure_kind "$(rb_deny exe /system/bin/sh exact_route_b_alias 2>&1)")"
eq k.mismatch_exe_sha_value mismatch "$(owned_failure_kind "$(rb_deny exe_sha deadbeef "$RB_SPAWNER_SHA" 2>&1)")"
eq k.mismatch_numeric_birth mismatch "$(owned_failure_kind "$(rb_deny birth_after 99999 16206 2>&1)")"
eq k.no_record_failclosed mismatch "$(owned_failure_kind '')"
eq k.decoder_roundtrip '<read-error>' "$(cev_decode "$(printf '%s' '<read-error>' | od -An -v -tx1 | sed 's/ *\([0-9a-f][0-9a-f]\)/\\u00\1/g' | tr -d ' \n')")"

# ================= child_exit_verdict unit (stat-first, verified root, no temp files) =================
reset_proc Z "$BIRTH";      eq v.zombie_same_birth exited "$(V)"
reset_proc Z 99999;         eq v.zombie_other_birth refuse:pid_reused_birth_99999 "$(V)"
reset_proc S "$BIRTH";      eq v.alive_same_birth refuse:alive_ownership_failed_state_S "$(V)"
reset_proc S 99999;         eq v.alive_other_birth refuse:pid_reused_birth_99999 "$(V)"
reset_proc S "$BIRTH"; rm -rf "$PROC/$PID"; eq v.absent_via_listing exited "$(V)"
reset_proc S "$BIRTH"; rm -rf "$PROC/$PID"; eq v.absent_with_missing_tmpdir exited "$(TMPDIR="$WORK/no-such-tmp" V)"
reset_proc S "$BIRTH"; printf '%s (x) Z 5430\n' "$PID" > "$PROC/$PID/stat"; eq v.short_stat refuse:stat_short "$(V)"
reset_proc S "$BIRTH"; : > "$PROC/$PID/stat"; eq v.empty_stat refuse:stat_empty "$(V)"
reset_proc S "$BIRTH"; stat_row Z "$BIRTH" | sed "s/^$PID /4242 /" > "$PROC/$PID/stat"; eq v.pid_mismatch refuse:stat_pid_mismatch "$(V)"
reset_proc S "$BIRTH"; PROC="$WORK/no-such-proc"; eq v.root_missing unknown "$(V)"; PROC="$PROCROOT"
mkdir -p "$WORK/not-proc/1"; PROC="$WORK/not-proc"; eq v.numeric_dir_is_not_proc unknown "$(V)"; PROC="$PROCROOT"
reset_proc S "$BIRTH"; rm -rf "$PROC/$PID"; printf 'ffffffff-0000-0000-0000-000000000000\n' > "$PROC/sys/kernel/random/boot_id"
eq v.root_bootid_mismatch unknown "$(V)"; printf '%s\n' "$BOOT" > "$PROC/sys/kernel/random/boot_id"
if [ "$UNR" = 1 ]; then
	reset_proc S "$BIRTH"; chmod 000 "$PROC/$PID/stat"; eq v.stat_unreadable_pid_listed unknown "$(V)"
	reset_proc S "$BIRTH"; rm -rf "$PROC/$PID"; chmod 000 "$PROC"; eq v.root_unlistable unknown "$(V)"; chmod u+rwx "$PROC"
else skip=$((skip + 2)); echo "SKIP v.stat_unreadable_pid_listed v.root_unlistable (root: chmod 000 ineffective)"; fi
eq v.bad_args refuse:bad_pid_argument "$(child_exit_verdict abc $BIRTH "$BOOT")"

# ================= LANE A: monitor_child with the stub guard (real deny records) =================
child_owned() {
	OWNED_CALLS=$((OWNED_CALLS + 1))
	ob=$(rb_birth "$1") || { rb_deny birth '<read-error-or-exited>' "$2"; return 1; }
	case "$MUTATION" in
	none) :;;
	to_zombie)            stat_row Z "$BIRTH" > "$PROC/$PID/stat";;
	to_zombie_reuse)      stat_row Z 99999 > "$PROC/$PID/stat";;
	to_reuse_alive)       stat_row S 99999 > "$PROC/$PID/stat";;
	vanish)               rm -rf "$PROC/$PID";;
	unreadable)           chmod 000 "$PROC/$PID/stat";;
	malformed)            printf '%s (id.article.news) Z 5430\n' "$PID" > "$PROC/$PID/stat";;
	mismatch_alive)       rb_deny uid 20010000:20010000:20010000:20010000 "$OWNUID"; return 1;;
	mismatch_then_vanish) rb_deny exe /system/bin/sh exact_route_b_alias; rm -rf "$PROC/$PID"; return 1;;
	mismatch_then_zombie) rb_deny uid 20010000:20010000:20010000:20010000 "$OWNUID"; stat_row Z "$BIRTH" > "$PROC/$PID/stat"; return 1;;
	reuse_between_reads)  stat_row S 99999 > "$PROC/$PID/stat"; rb_deny birth_after 99999 "$2"; rm -rf "$PROC/$PID"; return 1;;
	init_ns_err_vanish)   rb_deny init_namespace '<read-error>' readable; rm -rf "$PROC/$PID"; return 1;;
	phys_inode_err_vanish) rb_deny physical_inode '<read-error>' readable; rm -rf "$PROC/$PID"; return 1;;
	esac
	lb=$(rb_birth "$1") || { rb_deny birth_after '<read-error-or-exited>' "$2"; return 1; }
	[ "$lb" = "$ob" ] || { rb_deny birth_after "$lb" "$ob"; return 1; }
}
reset_proc S "$BIRTH"; MUTATION=to_zombie; mon
eq a1.race_zombie.rc 0 "$MRC"; eq a1.exit_event 1 "$(ev 'EVENT process_exit during_ownership_check')"; eq a1.no_refuse 0 "$(ev 'STATE OWNER_REFUSED')"
reset_proc S "$BIRTH"; MUTATION=vanish; mon
eq a2.race_vanish.rc 0 "$MRC"; eq a2.exit_event 1 "$(ev 'EVENT process_exit during_ownership_check')"
reset_proc S "$BIRTH"; MUTATION=to_reuse_alive; mon
eq a3.reuse_alive.rc 2 "$MRC"; eq a3.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq a3.no_exit 0 "$(ev 'EVENT process_exit')"
reset_proc S "$BIRTH"; MUTATION=to_zombie_reuse; mon
eq a4.reuse_zombie.rc 2 "$MRC"; eq a4.no_exit 0 "$(ev 'EVENT process_exit')"
reset_proc S "$BIRTH"; MUTATION=mismatch_alive; mon
eq a5.mismatch_alive.rc 2 "$MRC"; eq a5.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq a5.no_exit 0 "$(ev 'EVENT process_exit')"
reset_proc S "$BIRTH"; MUTATION=mismatch_then_vanish; mon
eq a6.mismatch_then_vanish.rc 2 "$MRC"; eq a6.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq a6.no_exit 0 "$(ev 'EVENT process_exit')"
reset_proc S "$BIRTH"; MUTATION=mismatch_then_zombie; mon
eq a7.mismatch_then_zombie.rc 2 "$MRC"; eq a7.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq a7.no_exit 0 "$(ev 'EVENT process_exit')"
reset_proc S "$BIRTH"; MUTATION=reuse_between_reads; mon
eq a8.reuse_then_vanish.rc 2 "$MRC"; eq a8.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq a8.no_exit 0 "$(ev 'EVENT process_exit')"
reset_proc S 99999; MUTATION=vanish; mon
eq a9.first_read_other_birth.rc 2 "$MRC"; eq a9.owned_not_called 0 "$OWNED_CALLS"; eq a9.not_laundered 0 "$(ev 'EVENT process_exit')"; eq a9.refuse 1 "$(ev 'STATE OWNER_REFUSED child_identity_changed_no_signal')"
reset_proc Z "$BIRTH"; mon
eq a10.zombie_same_birth.rc 0 "$MRC"; eq a10.exit_event 1 "$(ev 'EVENT process_exit first_read_exited')"
reset_proc Z 99999; mon
eq a11.zombie_other_birth.rc 2 "$MRC"; eq a11.refuse 1 "$(ev 'verdict=refuse:pid_reused_birth_99999')"; eq a11.no_exit 0 "$(ev 'EVENT process_exit')"
reset_proc S "$BIRTH"; PROC="$WORK/no-such-proc"; RB_PROC="$PROC"; mon; PROC="$PROCROOT"; RB_PROC="$PROC"
eq a12.root_missing.rc 2 "$MRC"; eq a12.no_exit 0 "$(ev 'EVENT process_exit')"
if [ "$UNR" = 1 ]; then
	reset_proc S "$BIRTH"; MUTATION=unreadable; mon
	eq a13.unreadable.rc 2 "$MRC"; eq a13.unknown_refused 1 "$(ev 'verdict=unknown')"; eq a13.no_exit 0 "$(ev 'EVENT process_exit')"
else skip=$((skip + 3)); echo "SKIP a13.unreadable (root)"; fi
reset_proc S "$BIRTH"; MUTATION=malformed; mon
eq a14.malformed.rc 2 "$MRC"; eq a14.refuse 1 "$(ev 'verdict=refuse:stat_short')"
# (cx-seal r2) unrelated read errors (PID 1 ns / host runtime inode) + vanish -> refused, not exit.
reset_proc S "$BIRTH"; MUTATION=init_ns_err_vanish; mon
eq a15.init_ns_err_then_vanish.rc 2 "$MRC"; eq a15.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq a15.no_exit 0 "$(ev 'EVENT process_exit')"
reset_proc S "$BIRTH"; MUTATION=phys_inode_err_vanish; mon
eq a16.phys_inode_err_then_vanish.rc 2 "$MRC"; eq a16.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq a16.no_exit 0 "$(ev 'EVENT process_exit')"
eq a17.parent_never_signalled 0 "$(ev '^KILL')"
eq a18.no_capture_on_exit 0 "$(ev CAPTURE_REACHED)"

# rc_child_state with the stub guard
reset_proc S "$BIRTH"; MUTATION=to_zombie;            eq c1.race_zombie gone "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; MUTATION=vanish;               eq c2.race_vanish gone "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; MUTATION=to_reuse_alive;       eq c3.race_reuse invalid "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; MUTATION=mismatch_alive;       eq c4.mismatch_alive invalid "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; MUTATION=mismatch_then_vanish; eq c5.mismatch_then_vanish invalid "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; MUTATION=init_ns_err_vanish;   eq c6.init_ns_err_then_vanish invalid "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; MUTATION=none;                 eq c7.alive_owned alive "$(rc_child_state 2>/dev/null)"
reset_proc S 99999;    MUTATION=none;                 eq c8.first_read_other_birth invalid "$(rc_child_state 2>/dev/null)"
reset_proc Z "$BIRTH";                                eq c9.zombie_same_birth gone "$(rc_child_state 2>/dev/null)"
reset_proc Z 99999;                                   eq c10.zombie_other_birth invalid "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; rm -rf "$PROC/$PID";           eq c11.absent gone "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; PROC="$WORK/no-such-proc"; RB_PROC="$PROC"; eq c12.root_missing unknown "$(rc_child_state 2>/dev/null)"; PROC="$PROCROOT"; RB_PROC="$PROC"
if [ "$UNR" = 1 ]; then
	reset_proc S "$BIRTH"; MUTATION=unreadable; eq c13.unreadable unknown "$(rc_child_state 2>/dev/null)"
else skip=$((skip + 1)); echo "SKIP c13.unreadable (root)"; fi

# ================= LANE B: REAL child_owned + REAL rb_owned, command-boundary shims =================
# Restore the REAL child_owned (extracted from the final watchdog). Only sha256sum / stat /
# readlink are shimmed: the ownership logic runs exactly as in production.
eval "$REAL_CHILD_OWNED"
sha256sum() {
	if [ "$1" = "$PROC/$PID/exe" ]; then
		if [ "$MODE" = exe_vanish ]; then rm -rf "$PROC/$PID"; return 1; fi
		if [ "$MODE" = exe_sha_wrong ]; then printf 'deadbeef  %s\n' "$1"; return 0; fi
		printf '%s  %s\n' "$RB_SPAWNER_SHA" "$1"; return 0
	fi
	command sha256sum "$@"
}
stat() {
	case "$*" in
	*"$RB_RUNTIME/run.sh"*) [ "$MODE" = phys_inode_err ] && { rm -rf "$PROC/$PID"; return 1; }; printf '1:2\n'; return 0;;
	*"/root/data/local/tmp/asx/run.sh"*) [ "$MODE" = private_inode_vanish ] && { rm -rf "$PROC/$PID"; return 1; }; printf '1:2\n'; return 0;;
	esac
	command stat "$@"
}
readlink() {
	if [ "$MODE" = init_read_error ] && [ "$1" = "$PROC/1/ns/mnt" ]; then rm -rf "$PROC/$PID"; return 1; fi
	if [ "$MODE" = child_ns_vanish ] && [ "$1" = "$PROC/$PID/ns/mnt" ]; then rm -rf "$PROC/$PID"; return 1; fi
	command readlink "$@"
}
reset_proc S "$BIRTH"; MODE=normal
eq b0.real_child_owned_alive 0 "$(child_owned "$child" "$child_birth" >/dev/null 2>&1; echo $?)"
# (cx-seal #5) real rb_owned: executable vanishes at the sha256sum site -> exe_sha "" -> death -> wait.
reset_proc S "$BIRTH"; MODE=exe_vanish; mon
eq b1.real_exe_vanish.rc 0 "$MRC"; eq b1.exit_event 1 "$(ev 'EVENT process_exit during_ownership_check')"; eq b1.no_refuse 0 "$(ev 'STATE OWNER_REFUSED')"
# (cx-seal #6) PID 1 namespace read error while the child vanishes -> unrelated -> refused.
reset_proc S "$BIRTH"; MODE=init_read_error; mon
eq b2.real_init_read_error.rc 2 "$MRC"; eq b2.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq b2.no_exit 0 "$(ev 'EVENT process_exit')"
# host runtime physical inode read error while the child vanishes -> unrelated -> refused.
reset_proc S "$BIRTH"; MODE=phys_inode_err; mon
eq b3.real_phys_inode_err.rc 2 "$MRC"; eq b3.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq b3.no_exit 0 "$(ev 'EVENT process_exit')"
# child's own private-root inode read fails because it vanished -> child death -> wait.
reset_proc S "$BIRTH"; MODE=private_inode_vanish; mon
eq b4.real_private_inode_vanish.rc 0 "$MRC"; eq b4.exit_event 1 "$(ev 'EVENT process_exit during_ownership_check')"
# child's own ns readlink fails because it vanished -> child death -> wait.
reset_proc S "$BIRTH"; MODE=child_ns_vanish; mon
eq b5.real_child_ns_vanish.rc 0 "$MRC"; eq b5.exit_event 1 "$(ev 'EVENT process_exit during_ownership_check')"
# real exe sha VALUE mismatch while alive -> confirmed mismatch -> refused (not death).
reset_proc S "$BIRTH"; MODE=exe_sha_wrong; mon
eq b6.real_exe_sha_wrong.rc 2 "$MRC"; eq b6.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq b6.no_exit 0 "$(ev 'EVENT process_exit')"
# real uid VALUE mismatch while alive -> refused.
reset_proc S "$BIRTH"; MODE=normal; printf 'Uid:\t20010000\t20010000\t20010000\t20010000\n' > "$PROC/$PID/status"; mon
eq b7.real_uid_wrong.rc 2 "$MRC"; eq b7.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq b7.no_exit 0 "$(ev 'EVENT process_exit')"
# real chain, child becomes a same-birth zombie before the guard's last birth read -> wait.
reset_proc S "$BIRTH"; MODE=normal; stat_row Z "$BIRTH" > "$PROC/$PID/stat"; mon
eq b8.real_pre_zombie.rc 0 "$MRC"; eq b8.exit_event 1 "$(ev 'EVENT process_exit first_read_exited')"
# real chain with the stub-free guard: rc_child_state agrees on exe-vanish.
reset_proc S "$BIRTH"; MODE=exe_vanish; eq b9.real_child_state_exe_vanish gone "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; MODE=init_read_error; eq b10.real_child_state_init_err invalid "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; MODE=normal; eq b11.real_child_state_alive alive "$(rc_child_state 2>/dev/null)"
eq b12.parent_never_signalled 0 "$(ev '^KILL')"

printf '\nrace-tests: %d passed, %d failed, %d skipped\n' "$pass" "$fail" "$skip"
[ "$fail" = 0 ]
