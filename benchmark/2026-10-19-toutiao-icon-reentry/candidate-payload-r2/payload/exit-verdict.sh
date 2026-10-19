#!/system/bin/sh
# Exit-vs-identity verdict for the monitored Route-B child (candidate r2 fix).
#
# Why: a child that is dying (SIGTERM, or the random crash) can pass the first
# rb_birth read and then fail the multi-read ownership guard (child_owned) a few
# milliseconds later because it became a zombie / vanished mid-check. The base
# monitor reported that as "child_identity_changed" and refused forever instead
# of entering the manual-icon wait.
#
# Contract (cx-seal + p3 pre-review, 2026-10-19). Output is ONE token:
#   exited    (a) a COMPLETE stat read shows field1==pid, starttime(field 22)==bound
#                 birth and state==Z; or
#             (b) the stat read failed AND a SUCCESSFUL complete PID listing of the
#                 verified proc root (rc 0, empty stderr, non-empty, numeric entries)
#                 does NOT contain the pid. Absence is never inferred from a failed
#                 `-d`/open: a missing or unreadable proc root is NOT "exited".
#   refuse:*  a complete stat read that proves the pid is NOT our exited child:
#             different birth (PID reuse), malformed/short/empty stat, pid mismatch,
#             or same birth but not Z (still alive while ownership failed).
#   unknown   nothing could be proven: proc root missing/unlistable, listing
#             rc/stderr/empty failure, or the pid is listed but its stat cannot be
#             read (permission / IO). Callers MUST fail closed on unknown.
#
# The caller MUST have already refused when its FIRST birth read differed from the
# bound birth, and MUST NOT consult this verdict after a CONFIRMED identity
# mismatch (uid/exe/inode/ns/ppid value mismatch while alive); only child-death
# related read failures are classified here. Never launders a changed birth or a
# confirmed mismatch into an exit. Pure read-only; no signals; no awk/python.

# cev_parse_stat <pid> <birth> <row> -> exited | refuse:* ; requires a complete row.
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

# cev_pid_listed <procroot> <pid> -> 0 listed | 1 proven absent | 2 listing unusable
# A usable listing = `ls -1` rc 0, EMPTY stderr, non-empty, and contains at least
# one numeric entry (sanity that this is a proc root, not an empty dir).
cev_pid_listed() {
	cpl_root=$1; cpl_pid=$2
	[ -d "$cpl_root" ] || return 2
	cpl_err="${TMPDIR:-/tmp}/.cev-ls-err.$$"
	cpl_list=$(ls -1 "$cpl_root" 2>"$cpl_err"); cpl_rc=$?
	cpl_errsz=$(wc -c < "$cpl_err" 2>/dev/null || echo 1); rm -f "$cpl_err"
	[ "$cpl_rc" = 0 ] || return 2
	# numeric compare: some wc implementations pad the count with spaces
	[ "$cpl_errsz" -eq 0 ] 2>/dev/null || return 2
	[ -n "$cpl_list" ] || return 2
	cpl_numeric=0; cpl_found=0
	for cpl_e in $cpl_list; do
		case "$cpl_e" in ''|*[!0-9]*) continue;; esac
		cpl_numeric=1
		[ "$cpl_e" = "$cpl_pid" ] && cpl_found=1
	done
	[ "$cpl_numeric" = 1 ] || return 2
	[ "$cpl_found" = 1 ] && return 0
	return 1
}

# owned_failure_kind <captured child_owned stderr> -> death | mismatch
# The frozen ownership guard (route-b-owner.sh, verbatim) emits one deny record per
# failure as \u00XX-encoded JSON on stderr. Only a read failure caused by the child
# dying ("actual" starts with '<', i.e. '<read-error...>' / '<read-error-or-exited>')
# may be classified by the exit verdict. Any VALUE mismatch (uid/exe/exe_sha/inode/
# namespace/ppid, or a different numeric birth read between checks) is a confirmed
# identity mismatch and MUST stay refused, even if the process vanishes afterwards.
# No deny record at all => mismatch (fail closed).
owned_failure_kind() {
	ofk_last=$(printf '%s\n' "$1" | grep '"field":' | tail -n 1)
	[ -n "$ofk_last" ] || { echo mismatch; return 0; }
	# The encoder writes '<' as backslash-u-0-0-3-c; match it via a single-char
	# wildcard for the backslash so no escape sequence is needed in this source.
	case "$ofk_last" in
	*'"actual":"'?u003c*) echo death;;
	*) echo mismatch;;
	esac
}

child_exit_verdict() {
	cev_pid=$1; cev_birth=$2
	case "$cev_pid" in ''|*[!0-9]*) echo refuse:bad_pid_argument; return 0;; esac
	case "$cev_birth" in ''|*[!0-9]*) echo refuse:bad_birth_argument; return 0;; esac
	cev_proc=${PROC:-/proc}
	# 1) Try ONE complete stat read first (no `-d` pre-test: a dir that exists at the
	#    test and is gone at the read is the race we must not misjudge).
	if cev_row=$(cat "$cev_proc/$cev_pid/stat" 2>/dev/null); then
		cev_parse_stat "$cev_pid" "$cev_birth" "$cev_row"; return 0
	fi
	# 2) Stat read failed: prove absence only via a SUCCESSFUL complete PID listing.
	cev_pid_listed "$cev_proc" "$cev_pid"; cev_l=$?
	case "$cev_l" in
	1) echo exited; return 0;;          # listed root, pid confirmed absent
	2) echo unknown; return 0;;         # root missing/unlistable/empty: prove nothing
	esac
	# 3) Pid is still listed: re-read; only same-birth Z is an exit, else unknown.
	if cev_row=$(cat "$cev_proc/$cev_pid/stat" 2>/dev/null); then
		cev_parse_stat "$cev_pid" "$cev_birth" "$cev_row"; return 0
	fi
	echo unknown
}
