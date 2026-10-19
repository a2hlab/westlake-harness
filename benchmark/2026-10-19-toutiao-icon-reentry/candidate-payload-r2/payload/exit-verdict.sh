#!/system/bin/sh
# Exit-vs-identity verdict for the monitored Route-B child (candidate r2 fix).
#
# Why: a child that is dying (SIGTERM, or the random crash) can pass the first
# rb_birth read and then fail the multi-read ownership guard (child_owned) a few
# milliseconds later because it became a zombie / vanished mid-check. The base
# monitor reported that as "child_identity_changed" and refused forever instead
# of entering the manual-icon wait.
#
# Contract (cx-seal + p3 + cx-seal r2 review, 2026-10-19). Output is ONE token:
#   exited    (a) a COMPLETE stat read shows field1==pid, starttime(field 22)==bound
#                 birth and state==Z; or
#             (b) the stat read failed AND a SUCCESSFUL complete PID listing of the
#                 IDENTITY-VERIFIED proc root (rc 0, empty stderr, non-empty) does NOT
#                 contain the pid. The root is verified by reading
#                 <root>/sys/kernel/random/boot_id and comparing it to the monitored
#                 boot: a numeric-looking directory is NOT a proc root.
#   refuse:*  a complete stat read that proves the pid is NOT our exited child:
#             different birth (PID reuse), malformed/short/empty stat, pid mismatch,
#             or same birth but not Z (still alive while ownership failed).
#   unknown   nothing could be proven: root identity unverifiable, listing
#             rc/stderr/empty failure, or the pid is listed but its stat cannot be
#             read (permission / IO). Callers MUST fail closed on unknown.
#
# No temp files are used (the device may have no /tmp). The caller MUST have
# already refused when its FIRST birth read differed from the bound birth, and MUST
# NOT consult this verdict after a CONFIRMED identity mismatch; see
# owned_failure_kind. Pure read-only; no signals; no awk/python.

# cev_decode <u00XX-encoded text> -> decoded text (frozen encoder writes every byte
# as backslash u 0 0 h h). Pure sh; printf octal escapes.
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

# owned_failure_kind <captured child_owned stderr> -> death | mismatch
# Decodes the LAST deny record of the frozen guard (route-b-owner.sh, verbatim).
# death only for a read failure OF THE CHILD ITSELF:
#   field birth|birth_after|uid|exe|namespace|private_inode|ppid with actual '<read-error…>'
#   field exe_sha with EMPTY actual (sha256sum of a vanished /proc/<pid>/exe prints nothing)
# Everything else is a confirmed mismatch and MUST stay refused, including read
# errors that are NOT about the child (init_namespace = PID 1, physical_inode = the
# host runtime), any value mismatch, and a different numeric birth between reads.
# No deny record at all => mismatch (fail closed).
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

# cev_root_verified <procroot> <expected_boot> -> 0 if <root>/sys/kernel/random/boot_id
# is readable and equals the monitored boot (empty expected_boot = must be non-empty).
cev_root_verified() {
	crv_b=$(cat "$1/sys/kernel/random/boot_id" 2>/dev/null) || return 1
	[ -n "$crv_b" ] || return 1
	case "$crv_b" in *[!0-9a-f-]*) return 1;; esac
	[ -z "$2" ] || [ "$crv_b" = "$2" ]
}

# cev_pid_listed <procroot> <pid> -> 0 listed | 1 proven absent | 2 listing unusable
# No temp files: stderr is checked by a separate capture. A usable listing = `ls -1`
# rc 0 with EMPTY stderr, and a non-empty stdout listing.
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

# child_exit_verdict <pid> <birth> [expected_boot] -> exited | refuse:* | unknown
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
