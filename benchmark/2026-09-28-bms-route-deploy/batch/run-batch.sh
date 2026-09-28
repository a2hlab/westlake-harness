#!/bin/bash
# Run inside a2hlab (the Mac worktree is visible through /Users there).
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
REPO=$(cd -- "$HERE/../../.." && pwd)
TOOLS=${BMS_TOOLS:-$(dirname -- "$REPO")/westlake-inputs/tools}
for arg in "$@"; do
  if [ "$arg" = --execute ] && ! command -v mac >/dev/null 2>&1; then
    echo 'Run --execute inside a2hlab via orb; APK inputs and hdc_mac.sh live on that path.' >&2
    exit 2
  fi
done
exec python3 "$HERE/bms_batch.py" \
  --hdc-cmd "$TOOLS/hdc_mac.sh" \
  --lock-cmd "mac $TOOLS/board_note.sh" "$@"
