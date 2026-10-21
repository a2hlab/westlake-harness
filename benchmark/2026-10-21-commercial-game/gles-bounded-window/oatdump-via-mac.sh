#!/usr/bin/env bash
# OrbStack transport adapter; the original Mac oatdump checker is unchanged.
set -euo pipefail
: "${LAB_HOME:?derive LAB_HOME from the original AOSP provenance}"
: "${WESTLAKE_HARNESS:?set the current main checkout shared with the Mac}"
: "${OATDUMP_TRACE_ROOT:?set a persistent shared directory for original probe output}"
checker="$WESTLAKE_HARNESS/scripts/lab/oatdump_remote.sh"
test -x "$checker"
trace=$(mktemp -d "$OATDUMP_TRACE_ROOT/probe.XXXXXX")
printf '%s\0' "$@" > "$trace/argv.nul"
# ORBENV preserves the remote prefix as an environment value. Passing it as an
# argv assignment makes mac translate /home/... into a local OrbStack path.
if ORBENV="${ORBENV:+$ORBENV:}LAB_HOME" mac "$checker" "$@" > "$trace/stdout.txt" 2> "$trace/stderr.txt"; then
  rc=0
else
  rc=$?
fi
printf '%s\n' "$rc" > "$trace/rc.txt"
cat "$trace/stdout.txt"
cat "$trace/stderr.txt" >&2
exit "$rc"
