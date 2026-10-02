#!/usr/bin/env bash
set -uo pipefail
: "${U14_ROOT:?persistent U14 root required}"
: "${U14_RUN:?run number required}"
REAL="$HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64"
LOG="$U14_ROOT/logs/dex2oat-run$U14_RUN.log"
printf '[u14-dex2oat] argv'; printf ' %q' "$REAL" "$@"; printf '\n'
"$REAL" "$@" 2>&1 | tee "$LOG"
STATUS=("${PIPESTATUS[@]}")
printf '{"dex2oat_exit_code":%s,"tee_exit_code":%s}\n' "${STATUS[0]}" "${STATUS[1]}" > "$U14_ROOT/logs/dex2oat-run$U14_RUN.status.json"
printf '[u14-dex2oat] compiler_rc=%s tee_rc=%s\n' "${STATUS[0]}" "${STATUS[1]}" | tee -a "$LOG"
[ "${STATUS[0]}" -eq 0 ] && [ "${STATUS[1]}" -eq 0 ]
