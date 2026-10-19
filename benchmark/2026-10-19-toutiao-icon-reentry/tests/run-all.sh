#!/bin/sh
# Single offline entrypoint for the toutiao icon-reentry candidate, transcalled by
# tools/spec-checks/tests/toutiao_icon_reentry.rs. Runs the pure WMS parser tests,
# the reentry state-machine tests (final adapter seam contract), and a generator
# smoke test that regenerates the candidate and checks the SHA cascade linkage.
# No device, no network, no awk, no python. Exits non-zero on any failure.
set -u
HERE=$(CDPATH= cd -P "$(dirname "$0")" && pwd -P)
BASE=$(CDPATH= cd -P "$HERE/.." && pwd -P)
GEN="$BASE/generator/derive-candidate.sh"
LOG="$HERE/last-run.log"
: > "$LOG"
run() { printf '\n=== %s ===\n' "$1" | tee -a "$LOG"; shift; "$@" 2>&1 | tee -a "$LOG"; }

rc=0

printf '=== parser tests ===\n' | tee -a "$LOG"
sh "$HERE/run-parser-tests.sh" 2>&1 | tee -a "$LOG"
case "$(tail -1 "$LOG")" in *"0 failed"*) :;; *) rc=1;; esac

printf '\n=== reentry state-machine tests ===\n' | tee -a "$LOG"
sh "$HERE/run-reentry-tests.sh" 2>&1 | tee -a "$LOG"
case "$(tail -1 "$LOG")" in *"0 failed"*) :;; *) rc=1;; esac

printf '\n=== generator smoke + SHA cascade linkage ===\n' | tee -a "$LOG"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/rc-gen.XXXXXX") || { echo "mktemp failed" | tee -a "$LOG"; exit 2; }
trap 'rm -rf "$WORK"' EXIT
if sh "$GEN" --out "$WORK/cand" >> "$LOG" 2>&1; then
	sha_of() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
	mt=$(sha_of "$WORK/cand/payload/members.tsv")
	se=$(grep "STARTUP_MEMBERS_SHA=" "$WORK/cand/payload/startup.env" | sed "s/.*'\\(.*\\)'.*/\\1/")
	ee=$(cat "$WORK/cand/payload/startup.expected.sha256")
	ev=$(sha_of "$WORK/cand/payload/startup.env")
	wd=$(sha_of "$WORK/cand/payload/watchdog.sh")
	nfiles=$(grep -c '' "$WORK/cand/MANIFEST.sha256")
	linkfail=0
	[ "$mt" = "$se" ] || { echo "LINK FAIL members.tsv($mt) != STARTUP_MEMBERS_SHA($se)" | tee -a "$LOG"; linkfail=1; }
	[ "$ee" = "$ev" ] || { echo "LINK FAIL startup.expected($ee) != sha(startup.env)($ev)" | tee -a "$LOG"; linkfail=1; }
	grep -q "$wd" "$WORK/cand/payload/entry.sh" || { echo "LINK FAIL entry.sh missing candidate watchdog sha" | tee -a "$LOG"; linkfail=1; }
	[ "$nfiles" = 21 ] || { echo "LINK FAIL payload file count=$nfiles (want 21)" | tee -a "$LOG"; linkfail=1; }
	grep -q "STARTUP_ENABLED='0'" "$WORK/cand/payload/startup.env" || { echo "LINK FAIL default package is not disabled" | tee -a "$LOG"; linkfail=1; }
	if [ "$linkfail" = 0 ]; then echo "generator smoke: PASS (21 files, cascade linked, disabled by default)" | tee -a "$LOG"
	else rc=1; fi
else
	echo "generator smoke: FAIL (non-zero exit)" | tee -a "$LOG"; rc=1
fi

printf '\n=== run-all result: %s ===\n' "$([ "$rc" = 0 ] && echo PASS || echo FAIL)" | tee -a "$LOG"
exit "$rc"
