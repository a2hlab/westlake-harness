#!/bin/sh
# Offline unit tests for the pure WMS parser (src/reentry-seams.sh), run under the
# host /bin/sh. No device, no awk, no python. Exercises the REAL locked 61b dump
# plus synthetic positives and the malformed-dump error paths the outer review
# hardened (missing header/footer, truncated rows, duplicate focus, Total<count,
# hidden-focus reject). Exits non-zero on any mismatch.
set -u
HERE=$(CDPATH= cd -P "$(dirname "$0")" && pwd -P)
BASE=$(CDPATH= cd -P "$HERE/.." && pwd -P)
. "$BASE/src/reentry-seams.sh"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/rc-parser.XXXXXX") || { echo "mktemp failed" >&2; exit 2; }
trap 'rm -rf "$WORK"' EXIT

pass=0; fail=0
check() { # <label> <expected> <actual>
	if [ "$2" = "$3" ]; then
		pass=$((pass + 1)); printf 'PASS %s\n' "$1"
	else
		fail=$((fail + 1)); printf 'FAIL %s : expected [%s] got [%s]\n' "$1" "$2" "$3"
	fi
}

# A complete, valid dump with the given Focus WinId and an extra desktop/host/child.
# Rows carry one geometry group (fields 10..15) which is all the validator inspects.
make_dump() { # <file> <focus_winid>
	{
		printf '6944c37e-31a6-4846-8f1f-48088a917153\n'
		printf '\n'
		printf -- '----------------------------------WindowManagerService----------------------------------\n'
		printf 'WindowName DisplayId Pid WinId Type Mode Flag ZOrd Orientation [ x y w h ]\n'
		printf 'SCBDesktop6 0 2408 11 2001 1 0 2 0 [ 0 0 1200 1920 ]\n'
		printf 'SCBScreenLock10 0 2408 15 2110 1 0 2000 0 [ 0 0 1200 1920 ]\n'
		printf 'imehost0 0 11318 33 1 1 0 7 0 [ 0 0 1200 1920 ]\n'
		printf 'com.ss.android.artic 0 13101 32 1001 1 0 -1 0 [ 0 0 1200 1920 ]\n'
		printf 'PopupWindow:4bc 0 13101 35 1001 1 0 -1 0 [ 0 0 1 1920 ]\n'
		printf 'Focus window: %s\n' "$2"
		printf 'All Focus window: \n'
		printf 'DisplayId: 0 WindowId: %s\n' "$2"
		printf 'Total window num: 38\n'
		printf 'Highlighted windows: %s\n' "$2"
		printf 'WMS_REMOTE_RC=0\n'
	} > "$1"
}

# --- Real captured dump (locked): focus 15 = SCBScreenLock10 (Z=2000), child 13101 hidden ---
REAL="$BASE/tests/outer-fixtures/actual-61b-locked.wms.txt"
check real.focus.row "SCBScreenLock10 2408 15 2000" "$(rc_parse_focus "$REAL")"
check real.focus.class.other other "$(rc_classify_focus "$(rc_parse_focus "$REAL")" SCBDesktop6 imehost0 33)"
check real.owned.child.yes yes "$(rc_parse_owned_window "$REAL" 13101)"
# The parser matches ANY windowed pid; excluding the host pid is the CALLER's job
# (production builds the owned set from the bound child + rb_owned_pids, never the
# host). So passing the host pid here legitimately yields yes.
check real.owned.hostpid.matches yes "$(rc_parse_owned_window "$REAL" 11318)"
check real.owned.absent.no no "$(rc_parse_owned_window "$REAL" 99999)"

# --- Synthetic positive: desktop focus (WinId 11) ---
make_dump "$WORK/desktop.txt" 11
check desktop.row "SCBDesktop6 2408 11 2" "$(rc_parse_focus "$WORK/desktop.txt")"
check desktop.class desktop "$(rc_classify_focus "$(rc_parse_focus "$WORK/desktop.txt")" SCBDesktop6 imehost0 33)"

# --- Synthetic positive: host focus (WinId 33, Z>=0) with matching host WID ---
make_dump "$WORK/host.txt" 33
check host.row "imehost0 11318 33 7" "$(rc_parse_focus "$WORK/host.txt")"
check host.class "host 33" "$(rc_classify_focus "$(rc_parse_focus "$WORK/host.txt")" SCBDesktop6 imehost0 33)"
check host.class.wrongwid other "$(rc_classify_focus "$(rc_parse_focus "$WORK/host.txt")" SCBDesktop6 imehost0 99)"

# --- Hidden-focus reject: focus points at a Z=-1 row (child 32) ---
make_dump "$WORK/hidden.txt" 32
check hidden.focus.error error "$(rc_parse_focus "$WORK/hidden.txt")"

# --- Owned yes/no on a synthetic dump ---
check syn.owned.yes yes "$(rc_parse_owned_window "$WORK/desktop.txt" 13101)"
check syn.owned.no no "$(rc_parse_owned_window "$WORK/desktop.txt" 44444)"

# --- Error: missing header ---
grep -v '^WindowName ' "$WORK/desktop.txt" > "$WORK/nohdr.txt"
check err.no_header error "$(rc_parse_focus "$WORK/nohdr.txt")"

# --- Error: missing footer (no Total line) ---
grep -v '^Total window num:' "$WORK/desktop.txt" > "$WORK/nofoot.txt"
check err.no_footer error "$(rc_parse_focus "$WORK/nofoot.txt")"

# --- Error: duplicate Focus line ---
sed 's/^Focus window: 11$/Focus window: 11\nFocus window: 15/' "$WORK/desktop.txt" > "$WORK/dupfocus.txt"
check err.dup_focus error "$(rc_parse_focus "$WORK/dupfocus.txt")"

# --- Error: a truncated 4-field data row must fail, not be silently skipped ---
sed 's#^imehost0 .*#imehost0 0 11318 33#' "$WORK/desktop.txt" > "$WORK/trunc.txt"
check err.truncated_row error "$(rc_parse_focus "$WORK/trunc.txt")"

# --- Error: Total window num smaller than the visible row count ---
sed 's/^Total window num: 38$/Total window num: 1/' "$WORK/desktop.txt" > "$WORK/badtotal.txt"
check err.total_lt_count error "$(rc_parse_focus "$WORK/badtotal.txt")"

# --- Error: "All Focus window:" heading must never be read as the focus line ---
# (A dump whose ONLY focus-like line is the All-heading has no real focus -> error.)
grep -v '^Focus window: ' "$WORK/desktop.txt" > "$WORK/allonly.txt"
check err.all_heading_only error "$(rc_parse_focus "$WORK/allonly.txt")"

# --- unknown: missing dump file ---
check err.missing_file.focus error "$(rc_parse_focus "$WORK/does-not-exist.txt")"
check err.missing_file.owned unknown "$(rc_parse_owned_window "$WORK/does-not-exist.txt" 13101)"

printf '\nparser-tests: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" = 0 ]
