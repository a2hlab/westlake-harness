#!/usr/bin/env bash
set -uo pipefail
: "${U16_ROOT:?persistent U16 root required}"
: "${U16_RUN:?run number required}"
REAL="$HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64"
LOG="$U16_ROOT/logs/dex2oat-run$U16_RUN.log"
python3 - "$U16_ROOT/logs/dex2oat-run$U16_RUN.argv.json" "$REAL" "$@" <<'PY'
import json
from pathlib import Path
import sys

Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]) + "\n")
PY
if [ "$?" -ne 0 ]; then exit 9; fi
{
  printf '[u16-dex2oat] argv'; printf ' %q' "$REAL" "$@"; printf '\n'
  "$REAL" "$@"
} 2>&1 | tee "$LOG"
STATUS=("${PIPESTATUS[@]}")
printf '{"dex2oat_exit_code":%s,"tee_exit_code":%s}\n' "${STATUS[0]}" "${STATUS[1]}" > "$U16_ROOT/logs/dex2oat-run$U16_RUN.status.json"
printf '[u16-dex2oat] compiler_rc=%s tee_rc=%s\n' "${STATUS[0]}" "${STATUS[1]}"
[ "${STATUS[0]}" -eq 0 ] && [ "${STATUS[1]}" -eq 0 ]
