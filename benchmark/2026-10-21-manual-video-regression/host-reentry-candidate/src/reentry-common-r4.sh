#!/system/bin/sh
# Durable manual-icon reentry state machine (candidate for 61b).
#
# Control flow only. Every device interaction is a seam the caller MUST define
# before sourcing this file (production: reentry-seams.sh; tests: the fixture
# harness). See CHECKPOINT.md §4 and §9.
#
# Seams:
#   rc_stop_present        -> rc 0 if a stop marker exists (loop ends cleanly; stop NOT deleted)
#   rc_gates_ok            -> rc 0 if boot==expected AND lock is ours AND parent still owned AND
#                             no PID-reuse; sets rc_gate_reason on failure. NEVER signals parent.
#   rc_focus_state         -> sets rc_focus_result to exactly one token line:
#                               "desktop"      strict verified SceneBoard desktop focus
#                               "host <wid>"   strict verified imehost0 host focus (WinId=wid)
#                               "newhost <wid>" (r4) verified imehost0 host process whose WinId differs
#                                              from the parent's bound WL_PARENT_ID (recreated host)
#                               "other"        some other / unverifiable focused window
#                               "error"        WMS unreadable / ambiguous
#   rc_owned_window_present -> sets rc_owned_result to "yes" | "no" | "unknown": is any window owned by the bound
#                             old child PID or the owned-child set still present (incl. hidden)?
#                             The host's own window is NOT counted here.
#   rc_child_state         -> prints "alive" | "gone" | "unknown" (owned child liveness)
#   rc_do_spawn            -> ONE spawn+readiness (no monitor). Sets rc_spawn_result
#                             "ok <pid> <birth>" | "fail <reason>" | "unknown <reason>" and the
#                             rc MUST be 0 for a genuine ok. Anything else is treated as not-ok.
#   rc_after_spawn_ok <pid> <birth>
#                          -> production supervises the fresh child until it exits (reusing the
#                             original capture/readiness monitor). rc != 0 is a fatal identity/IO
#                             failure and is propagated UP (loop stops). Tests make it a no-op.
#   rc_event <tag> [msg]   -> append ONE audit line (only on real transitions/decisions)
#   rc_sleep               -> inter-poll wait seam (bounded in tests)
#
# Arming model (fixes blocker #1): a spawn fires only on a genuine desktop->host
# sequence. States: UNARMED -> DESKTOP_SEEN -> HOST_CONSUMED.
#   * loop entry and every confirmed child-gone re-arm to UNARMED, so a post-crash
#     host-foreground never auto-restarts;
#   * only a verified SceneBoard desktop focus moves UNARMED->DESKTOP_SEEN;
#   * only from DESKTOP_SEEN does a verified host focus fire ONE spawn, then HOST_CONSUMED;
#   * "other"/"unknown"/"error" never arm and never fire; "other" cancels a pending arm.
#
# Other invariants: no reentry counter cap (survives >=21 taps); quiet (no event on
# an unchanged poll); no fixed deadline. POSIX sh only; no awk, no python.
# Returns: 0 stop, 2 fatal gate/identity refusal.

rc_reentry_loop() {
	rc_arm=UNARMED
	rc_hold=0
	rc_gate_reason=
	while :; do
		# Stop always wins and is never deleted or signalled away.
		if rc_stop_present; then
			rc_event STOPPED existing_stop_no_delete
			return 0
		fi
		# Changed boot / lost lock / lost-or-reused parent is fatal: retain the lock
		# (caller EXIT trap), never signal the parent, never touch stop.
		if ! rc_gates_ok; then
			keep_lock=1
			rc_event OWNER_REFUSED "gate=${rc_gate_reason:-unknown}_no_signal_no_stop_delete"
			return 2
		fi

		rc_focus_result=error
        rc_focus_state
        rc_focus_status=$?
        [ "$rc_focus_status" = 0 ] || { keep_lock=1; return 2; }
        rc_focus=$rc_focus_result
		# shellcheck disable=SC2086
		set -- $rc_focus
		rc_fkind=${1:-error}
		rc_fwid=${2:-}

		case "$rc_fkind" in
		error)
				# A gap cannot prove a desktop-to-host transition. Require a new desktop.
				rc_arm=UNARMED
			rc_sleep
			continue
			;;
		other)
			# A non-desktop, non-host focused window cancels any pending qualification.
			# r4: an explicit reason from rc_focus_state is logged once per change (no silent other).
			if [ -n "${rc_focus_reason:-}" ] && [ "${rc_focus_reason:-}" != "${rc_last_other_reason:-}" ]; then
				rc_event focus_other "reason=$rc_focus_reason"
			fi
			rc_last_other_reason=${rc_focus_reason:-}
			rc_arm=UNARMED
			rc_sleep
			continue
			;;
		desktop)
			# Verified desktop focus arms the trigger. Quiet on repeats.
			[ "$rc_arm" = DESKTOP_SEEN ] || rc_arm=DESKTOP_SEEN
			rc_sleep
			continue
			;;
		host|newhost)
			rc_last_other_reason=
			if [ "$rc_arm" != DESKTOP_SEEN ]; then
				# Host foreground without a preceding desktop focus (host-at-start,
				# notification->host, or already consumed): consume silently, no spawn.
				rc_arm=HOST_CONSUMED
				rc_sleep
				continue
			fi
			# Genuine desktop->host transition: at most one spawn.
			rc_arm=HOST_CONSUMED

			if [ "$rc_hold" = 1 ]; then
				rc_event reentry_hold_fail_closed "wid=$rc_fwid"
				rc_sleep
				continue
			fi

				rc_child=$(rc_child_state 2>/dev/null) || rc_child=unknown
				if [ "$rc_child" = invalid ]; then
					keep_lock=1
					rc_event OWNER_REFUSED child_identity_no_spawn
					return 2
				fi
			rc_owned_result=unknown
                rc_owned_window_present
                rc_owned_status=$?
                [ "$rc_owned_status" = 0 ] || { keep_lock=1; return 2; }
                rc_win=$rc_owned_result
			if [ "$rc_child" != gone ] || [ "$rc_win" != no ]; then
				# Child alive, any owned (incl. hidden) window, or indeterminate:
				# consume, do NOT terminate, do NOT spawn.
				rc_event consume_live_or_window "child=$rc_child win=$rc_win wid=$rc_fwid"
				rc_sleep
				continue
			fi

			# Re-verify gates immediately before the single spawn.
			if ! rc_gates_ok; then
					keep_lock=1
					rc_event refuse_gate "gate=${rc_gate_reason:-unknown}_no_spawn_no_signal"
					return 2
			fi
			if [ "$rc_fkind" = newhost ]; then
				# r4: recreated host. Switch the parent epoch once (exact old parent, no child,
				# proven socket owner), then fall through to the unchanged single spawn.
				rc_parent_epoch_switch "$rc_fwid"
				rc_epoch_rc=$?
				case "$rc_epoch_rc" in
				0) : ;;
				1)
					rc_event parent_epoch_refused "reason=${rc_epoch_reason:-unknown} wid=$rc_fwid"
					rc_arm=UNARMED
					rc_sleep
					continue
					;;
				*)
					# Partial/unknown after an action: sticky hold, never a second parent or spawn.
					rc_hold=1
					rc_event parent_epoch_partial_hold "reason=${rc_epoch_reason:-unknown} wid=$rc_fwid"
					rc_arm=UNARMED
					rc_sleep
					continue
					;;
				esac
				if ! rc_gates_ok; then
					keep_lock=1
					rc_event refuse_gate "gate=${rc_gate_reason:-unknown}_after_epoch_no_spawn"
					return 2
				fi
			fi

				# Both calls run in this shell: child/birth/seq and fatal exits persist.
				rc_spawn_result=
				rc_do_spawn
				rc_spawn_rc=$?
				rc_spawn=$rc_spawn_result
				rc_classify_spawn "$rc_spawn_rc" "$rc_spawn"
			case "$rc_sres" in
			ok)
				rc_event reentry_spawn_ok "$rc_spawn"
				# Supervise the fresh child until it exits; a live child means later
				# host edges are consumed, so no second spawn while it lives.
				if ! rc_after_spawn_ok "$rc_spawn_pid" "$rc_spawn_birth"; then
					# Identity / IO failure during supervision is fatal; propagate up.
					keep_lock=1
					rc_event SUPERVISOR_FAILED child_identity_or_io_no_signal
					return 2
				fi
				# Child confirmed gone: require a fresh desktop->host for the next spawn.
				rc_arm=UNARMED
				;;
			fail)
				# Proven no child was created: wait for the NEXT desktop->host tap.
				rc_event reentry_spawn_fail "$rc_spawn"
				rc_arm=UNARMED
				;;
			*)
				# Unknown child status => fail closed: sticky hold, never spawn again.
				rc_hold=1
				rc_event reentry_spawn_unknown_hold "$rc_spawn"
				rc_arm=UNARMED
				;;
			esac
			rc_sleep
			continue
			;;
		*)
				# Unexpected tokens cancel any earlier qualification.
				rc_arm=UNARMED
			rc_sleep
			continue
			;;
		esac
	done
}

# Current-shell result classifier. Never use $(rc_classify_spawn ...).
# A result is accepted only with rc=0 and exactly three numeric identity fields.
rc_classify_spawn() {
 _rc_rc=$1
 _rc_line=$2
 rc_sres=unknown; rc_spawn_pid=; rc_spawn_birth=
 case "$_rc_line" in
 *"
"*) return 0;;
 esac
 # Disable pathname expansion for untrusted protocol text; restore caller flags.
 case $- in *f*) _rc_glob_off=1;; *) _rc_glob_off=0; set -f;; esac
 set -- $_rc_line
 [ "$_rc_glob_off" = 1 ] || set +f
 if [ "$_rc_rc" = 0 ] && [ "$#" = 3 ] && [ "$1" = ok ]; then
  case "$2" in ''|0|1|*[!0-9]*) return 0;; esac
  case "$3" in ''|*[!0-9]*) return 0;; esac
  rc_spawn_pid=$2; rc_spawn_birth=$3; rc_sres=ok
 elif [ "$_rc_rc" = 0 ] && [ "$#" = 2 ] && [ "$1" = fail ]; then
  rc_sres=fail
 fi
 return 0
}
