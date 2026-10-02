#!/usr/bin/env bash
set -uo pipefail
: "${U15_ROOT:?persistent U15 root required}"
: "${U15_RUN:?run number required}"
REAL="$HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64"
LOG="$U15_ROOT/logs/dex2oat-run$U15_RUN.log"
python3 - "$U15_ROOT/logs/dex2oat-run$U15_RUN.argv.json" "$REAL" "$@" <<'PY'
import json
from pathlib import Path
import sys

Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]) + "\n")
PY
if [ "$?" -ne 0 ]; then exit 9; fi
{
  printf '[u15-dex2oat] argv'; printf ' %q' "$REAL" "$@"; printf '\n'
  "$REAL" "$@"
} 2>&1 | tee "$LOG"
STATUS=("${PIPESTATUS[@]}")
printf '{"dex2oat_exit_code":%s,"tee_exit_code":%s}\n' "${STATUS[0]}" "${STATUS[1]}" > "$U15_ROOT/logs/dex2oat-run$U15_RUN.status.json"
printf '[u15-dex2oat] compiler_rc=%s tee_rc=%s\n' "${STATUS[0]}" "${STATUS[1]}"
[ "${STATUS[0]}" -eq 0 ] && [ "${STATUS[1]}" -eq 0 ]
