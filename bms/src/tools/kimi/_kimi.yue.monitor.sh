#!/bin/bash
# _kimi.yue.monitor.sh
# Monitor lane: live health view of the yue lanes
#   1. design-verify  (validation report freshness, ERROR/WARN counts)
#   2. fn04-07-lifecycle (kimi agent process, log growth, last output)
# Read-only: never kills processes, never modifies lane state.
set -uo pipefail

MAIN_REPO="/opt/Bridge"
DV_DIR="${MAIN_REPO}/worker2/design-verify"
DV_REPORT="${DV_DIR}/reports/Fn01-design-validation.md"
LC_LOG="${MAIN_REPO}/evidence/runs/_kimi.yue.fn04-07-lifecycle.log"
INTERVAL="${1:-30}"

human_age() { # seconds -> "3m12s ago"
	local age="$1"
	if [ "${age}" -lt 60 ]; then echo "${age}s ago";
	elif [ "${age}" -lt 3600 ]; then echo "$((age/60))m$((age%60))s ago";
	else echo "$((age/3600))h$((age%3600/60))m ago"; fi
}

while true; do
	clear
	NOW=$(date +%s)
	echo "=== _kimi.yue monitor — $(date '+%Y-%m-%d %H:%M:%S') (refresh ${INTERVAL}s) ==="
	echo

	echo "--- lane 1: design-verify ---"
	if [ -f "${DV_REPORT}" ]; then
		MT=$(stat -f "%m" "${DV_REPORT}")
		echo "report: Fn01-design-validation.md  (updated $(human_age $((NOW-MT))))"
		grep -E "^- (ERROR|WARN):" "${DV_REPORT}" | sed 's/^/  /'
	else
		echo "report: MISSING (run ${DV_DIR}/run.sh)"
	fi
	echo

	echo "--- lane 2: fn04-07-lifecycle ---"
	PIDS=$(pgrep -f "_kimi.yue.fn04-07-lifecycle.sh" | tr '\n' ' ')
	if [ -n "${PIDS}" ]; then
		echo "lane script: ALIVE (pid ${PIDS})"
	else
		echo "lane script: NOT RUNNING"
	fi
	if [ -f "${LC_LOG}" ]; then
		MT=$(stat -f "%m" "${LC_LOG}")
		AGE=$((NOW-MT))
		SIZE=$(stat -f "%z" "${LC_LOG}")
		echo "log: $(basename "${LC_LOG}")  ${SIZE} bytes, last write $(human_age ${AGE})"
		if [ -z "${PIDS}" ]; then
			echo "status: EXITED — final output below"
		elif [ "${AGE}" -gt 600 ]; then
			echo "status: STALLED? (no log output for >10m, process alive)"
		else
			echo "status: RUNNING"
		fi
		echo "last output:"
		tail -c 1200 "${LC_LOG}" | tail -8 | sed 's/^/  /'
	else
		echo "log: MISSING"
	fi
	echo
	echo "(Ctrl-C to exit monitor; lanes are unaffected)"
	sleep "${INTERVAL}"
done
