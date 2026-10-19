#!/bin/sh
# REAL exit-race tests for the r2 fix (cx-seal + p3 criteria, 2026-10-19).
#
# Not mock classification returns: a fake /proc tree, the REAL rb_birth and the REAL
# rb_deny JSON encoder from the frozen route-b-owner.sh, and the REAL monitor_child /
# rc_child_state bodies extracted from src/watchdog-reentry.sh. The race is
# reproduced by MUTATING /proc/<pid>/stat in the middle of the ownership check (the
# window where the live 61b controlled-SIGTERM evidence failed).
#
# Pass criteria:
#   * first read with a different birth -> refuse; ownership guard NOT consulted;
#     never laundered into an exit by a later disappearance
#   * ownership failure -> manual wait ONLY for (complete stat, same pid, same birth, Z)
#     or absence proven by a SUCCESSFUL complete PID listing of the proc root
#   * a CONFIRMED value mismatch (uid/exe/..., or a different numeric birth between
#     reads) stays refused even if the process vanishes afterwards (p3 #3)
#   * missing / unlistable proc root, listing failure, or pid listed but stat
#     unreadable -> unknown -> refused (never "exited") (p3 #1, #2)
#   * the pre-existing first-read Z branch verifies the birth; rc_child_state agrees
#   * the parent is never signalled; no capture on exit
# No device, no awk, no python. Exits non-zero on any mismatch.
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

# ---- fake /proc + real helpers ----
PROCROOT="$WORK/proc"; PROC="$PROCROOT"; RB_PROC="$PROC"; F="$WORK/F"
mkdir -p "$PROC/sys/kernel/random" "$F"
BOOT=f59c05dd-85b1-40f9-8ad5-baec804d642f
printf '%s\n' "$BOOT" > "$PROC/sys/kernel/random/boot_id"
RB_RUNTIME="$WORK/rt"; RB_OWNER_UID=20011206
. "$OWNER"                      # real rb_birth (Z -> rc 1) and real rb_deny / rb_guard_json
. "$BASE/src/exit-verdict.sh"
sed -n '/^rc_verdict_to_state() {/,/^}/p; /^rc_child_state() {/,/^}/p; /^monitor_child() {/,/^}/p' "$SRC" > "$WORK/under-test.sh"
grep -q '^monitor_child() {' "$WORK/under-test.sh" || { echo "monitor_child not extracted" >&2; exit 2; }
grep -q '^rc_child_state() {' "$WORK/under-test.sh" || { echo "rc_child_state not extracted" >&2; exit 2; }
. "$WORK/under-test.sh"

# Real 61b stat row shape (child-stat-before.txt evidence), parameterised on state/birth.
PID=7233; PARENT=5430; BIRTH=16206; OWNUID="$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID"
stat_row() { # <state> <birth>
	printf '%s (id.article.news) %s %s 5402 0 0 -1 1077936448 920061 5333 8232 0 23249 10693 4 74 20 0 332 0 %s 246606372864 259552 18446744073709551615 367158579140 367158712560 548698470336 0 0 0 4612 4097 1073841402 0 0 0 17 5 0 0 0 0 0 367158723536 367158723552 367784644608 548698472817 548698472892 548698472892 548698476505 0\n' "$PID" "$1" "$PARENT" "$2"
}
reset_proc() { # <state> <birth>   (also provides init "1" so listings have numeric entries)
	PROC="$PROCROOT"; RB_PROC="$PROC"
	chmod -R u+rwx "$PROC" 2>/dev/null; rm -rf "$PROC/$PID" "$PROC/1"; mkdir -p "$PROC/$PID" "$PROC/1"
	printf '1 (init) S 0 1 1 0 -1 4194560 1 0 0 0 1 1 0 0 20 0 1 0 2 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 0\n' > "$PROC/1/stat"
	stat_row "$1" "$2" > "$PROC/$PID/stat"
	rm -f "$F/stop"; : > "$WORK/events"; OWNED_CALLS=0; MUTATION=none
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
# The REAL race: an ownership check that passes its first rb_birth read, then the
# process transitions mid-check (file mutation), emitting the REAL deny record.
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
	esac
	lb=$(rb_birth "$1") || { rb_deny birth_after '<read-error-or-exited>' "$2"; return 1; }
	[ "$lb" = "$ob" ] || { rb_deny birth_after "$lb" "$ob"; return 1; }
}
child=$PID; child_birth=$BIRTH; parent=$PARENT; parent_birth=14767
seq=1; polls=0; TT_MAX_POLLS=0; self_birth=1; keep_lock=0; owner_verified=1
ev() { grep -c "$1" "$WORK/events" 2>/dev/null || true; }
unreadable_supported() { reset_proc S "$BIRTH"; chmod 000 "$PROC/$PID/stat"; if cat "$PROC/$PID/stat" >/dev/null 2>&1; then return 1; fi; return 0; }
UNR=0; unreadable_supported && UNR=1
mon() { monitor_child 2>/dev/null; MRC=$?; }

# ================= owned_failure_kind against the REAL encoder =================
eq k.death_birth death "$(owned_failure_kind "$(rb_deny birth '<read-error-or-exited>' 1 2>&1)")"
eq k.death_birth_after death "$(owned_failure_kind "$(rb_deny birth_after '<read-error-or-exited>' 1 2>&1)")"
eq k.death_readerror death "$(owned_failure_kind "$(rb_deny uid '<read-error>' x 2>&1)")"
eq k.mismatch_uid mismatch "$(owned_failure_kind "$(rb_deny uid 20010000:20010000:20010000:20010000 "$OWNUID" 2>&1)")"
eq k.mismatch_exe mismatch "$(owned_failure_kind "$(rb_deny exe /system/bin/sh exact_route_b_alias 2>&1)")"
eq k.mismatch_numeric_birth mismatch "$(owned_failure_kind "$(rb_deny birth_after 99999 16206 2>&1)")"
eq k.no_record_failclosed mismatch "$(owned_failure_kind '')"

# ================= child_exit_verdict unit (single-read + listing contract) =================
reset_proc Z "$BIRTH";      eq v.zombie_same_birth exited "$(child_exit_verdict $PID $BIRTH)"
reset_proc Z 99999;         eq v.zombie_other_birth refuse:pid_reused_birth_99999 "$(child_exit_verdict $PID $BIRTH)"
reset_proc S "$BIRTH";      eq v.alive_same_birth refuse:alive_ownership_failed_state_S "$(child_exit_verdict $PID $BIRTH)"
reset_proc S 99999;         eq v.alive_other_birth refuse:pid_reused_birth_99999 "$(child_exit_verdict $PID $BIRTH)"
reset_proc S "$BIRTH"; rm -rf "$PROC/$PID"; eq v.absent_via_listing exited "$(child_exit_verdict $PID $BIRTH)"
reset_proc S "$BIRTH"; printf '%s (x) Z 5430\n' "$PID" > "$PROC/$PID/stat"; eq v.short_stat refuse:stat_short "$(child_exit_verdict $PID $BIRTH)"
reset_proc S "$BIRTH"; : > "$PROC/$PID/stat"; eq v.empty_stat refuse:stat_empty "$(child_exit_verdict $PID $BIRTH)"
reset_proc S "$BIRTH"; stat_row Z "$BIRTH" | sed "s/^$PID /4242 /" > "$PROC/$PID/stat"; eq v.pid_mismatch refuse:stat_pid_mismatch "$(child_exit_verdict $PID $BIRTH)"
reset_proc S "$BIRTH"; PROC="$WORK/no-such-proc"; eq v.root_missing unknown "$(child_exit_verdict $PID $BIRTH)"; PROC="$PROCROOT"
reset_proc S "$BIRTH"; rm -rf "$PROC/$PID" "$PROC/1"; eq v.root_without_numeric unknown "$(child_exit_verdict $PID $BIRTH)"
if [ "$UNR" = 1 ]; then
	reset_proc S "$BIRTH"; chmod 000 "$PROC/$PID/stat"; eq v.stat_unreadable_pid_listed unknown "$(child_exit_verdict $PID $BIRTH)"
	reset_proc S "$BIRTH"; rm -rf "$PROC/$PID"; chmod 000 "$PROC"; eq v.root_unlistable unknown "$(child_exit_verdict $PID $BIRTH)"; chmod u+rwx "$PROC"
else skip=$((skip + 2)); echo "SKIP v.stat_unreadable_pid_listed v.root_unlistable (root: chmod 000 ineffective)"; fi
eq v.bad_args refuse:bad_pid_argument "$(child_exit_verdict abc $BIRTH)"

# ================= monitor_child: the live 61b race, reproduced =================
# M1 first read S/same birth, dies (Z, same birth) DURING ownership check -> manual wait.
reset_proc S "$BIRTH"; MUTATION=to_zombie; mon
eq m1.race_zombie.rc 0 "$MRC"; eq m1.exit_event 1 "$(ev 'EVENT process_exit during_ownership_check')"; eq m1.no_refuse 0 "$(ev 'STATE OWNER_REFUSED')"
# M2 vanishes entirely during the check (stat read fails, listing proves absence) -> manual wait.
reset_proc S "$BIRTH"; MUTATION=vanish; mon
eq m2.race_vanish.rc 0 "$MRC"; eq m2.exit_event 1 "$(ev 'EVENT process_exit during_ownership_check')"
# M3 PID reused by a live process during the check: the guard reads a different NUMERIC
# birth -> confirmed mismatch -> fixed refuse (verdict not consulted), never an exit.
reset_proc S "$BIRTH"; MUTATION=to_reuse_alive; mon
eq m3.reuse_alive.rc 2 "$MRC"; eq m3.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq m3.no_exit 0 "$(ev 'EVENT process_exit')"
# M4 PID reused and already a zombie with a different birth -> refuse.
reset_proc S "$BIRTH"; MUTATION=to_zombie_reuse; mon
eq m4.reuse_zombie.rc 2 "$MRC"; eq m4.no_exit 0 "$(ev 'EVENT process_exit')"
# M5 (p3 #3) CONFIRMED uid mismatch while alive -> fixed refuse, verdict not consulted.
reset_proc S "$BIRTH"; MUTATION=mismatch_alive; mon
eq m5.mismatch_alive.rc 2 "$MRC"; eq m5.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq m5.no_exit 0 "$(ev 'EVENT process_exit')"
# M6 (p3 #3) CONFIRMED exe mismatch, THEN the process vanishes -> still refused, never laundered.
reset_proc S "$BIRTH"; MUTATION=mismatch_then_vanish; mon
eq m6.mismatch_then_vanish.rc 2 "$MRC"; eq m6.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq m6.no_exit 0 "$(ev 'EVENT process_exit')"
# M7 (p3 #3) CONFIRMED uid mismatch, THEN becomes a same-birth zombie -> still refused.
reset_proc S "$BIRTH"; MUTATION=mismatch_then_zombie; mon
eq m7.mismatch_then_zombie.rc 2 "$MRC"; eq m7.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq m7.no_exit 0 "$(ev 'EVENT process_exit')"
# M8 different NUMERIC birth read between checks (reuse), then vanishes -> refused, not exit.
reset_proc S "$BIRTH"; MUTATION=reuse_between_reads; mon
eq m8.reuse_then_vanish.rc 2 "$MRC"; eq m8.fixed_refuse 1 "$(ev 'confirmed_mismatch_no_verdict')"; eq m8.no_exit 0 "$(ev 'EVENT process_exit')"
# M9 FIRST read already shows a different birth -> refuse outright; ownership NOT consulted.
reset_proc S 99999; MUTATION=vanish; mon
eq m9.first_read_other_birth.rc 2 "$MRC"; eq m9.owned_not_called 0 "$OWNED_CALLS"; eq m9.not_laundered 0 "$(ev 'EVENT process_exit')"; eq m9.refuse 1 "$(ev 'STATE OWNER_REFUSED child_identity_changed_no_signal')"
# M10 pre-existing zombie, same birth (first read fails) -> manual wait (old Z branch, birth-verified).
reset_proc Z "$BIRTH"; mon
eq m10.zombie_same_birth.rc 0 "$MRC"; eq m10.exit_event 1 "$(ev 'EVENT process_exit first_read_exited')"
# M11 pre-existing zombie with a DIFFERENT birth -> refuse (the gap cx-seal flagged).
reset_proc Z 99999; mon
eq m11.zombie_other_birth.rc 2 "$MRC"; eq m11.refuse 1 "$(ev 'verdict=refuse:pid_reused_birth_99999')"; eq m11.no_exit 0 "$(ev 'EVENT process_exit')"
# M12 (p3 #1) proc root MISSING: first read fails, nothing provable -> unknown -> refused, never exited.
reset_proc S "$BIRTH"; PROC="$WORK/no-such-proc"; RB_PROC="$PROC"; mon; PROC="$PROCROOT"; RB_PROC="$PROC"
eq m12.root_missing.rc 2 "$MRC"; eq m12.no_exit 0 "$(ev 'EVENT process_exit')"
# M13 (p3 #2) stat becomes unreadable during the check (pid still listed) -> unknown -> refused.
if [ "$UNR" = 1 ]; then
	reset_proc S "$BIRTH"; MUTATION=unreadable; mon
	eq m13.unreadable.rc 2 "$MRC"; eq m13.unknown_refused 1 "$(ev 'verdict=unknown')"; eq m13.no_exit 0 "$(ev 'EVENT process_exit')"
else skip=$((skip + 3)); echo "SKIP m13.unreadable (root)"; fi
# M14 malformed/short stat during the check -> refuse.
reset_proc S "$BIRTH"; MUTATION=malformed; mon
eq m14.malformed.rc 2 "$MRC"; eq m14.refuse 1 "$(ev 'verdict=refuse:stat_short')"
# M15 the parent is never signalled; M16 no capture on any exit path.
eq m15.parent_never_signalled 0 "$(ev '^KILL')"
eq m16.no_capture_on_exit 0 "$(ev CAPTURE_REACHED)"

# ================= rc_child_state: same-family race must agree =================
reset_proc S "$BIRTH"; MUTATION=to_zombie;            eq c1.race_zombie gone "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; MUTATION=vanish;               eq c2.race_vanish gone "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; MUTATION=to_reuse_alive;       eq c3.race_reuse invalid "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; MUTATION=mismatch_alive;       eq c4.mismatch_alive invalid "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; MUTATION=mismatch_then_vanish; eq c5.mismatch_then_vanish invalid "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; MUTATION=none;                 eq c6.alive_owned alive "$(rc_child_state 2>/dev/null)"
reset_proc S 99999;    MUTATION=none;                 eq c7.first_read_other_birth invalid "$(rc_child_state 2>/dev/null)"
reset_proc Z "$BIRTH";                                eq c8.zombie_same_birth gone "$(rc_child_state 2>/dev/null)"
reset_proc Z 99999;                                   eq c9.zombie_other_birth invalid "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; rm -rf "$PROC/$PID";           eq c10.absent gone "$(rc_child_state 2>/dev/null)"
reset_proc S "$BIRTH"; PROC="$WORK/no-such-proc"; RB_PROC="$PROC"; eq c11.root_missing unknown "$(rc_child_state 2>/dev/null)"; PROC="$PROCROOT"; RB_PROC="$PROC"
if [ "$UNR" = 1 ]; then
	reset_proc S "$BIRTH"; MUTATION=unreadable; eq c12.unreadable unknown "$(rc_child_state 2>/dev/null)"
else skip=$((skip + 1)); echo "SKIP c12.unreadable (root)"; fi

printf '\nrace-tests: %d passed, %d failed, %d skipped\n' "$pass" "$fail" "$skip"
[ "$fail" = 0 ]
