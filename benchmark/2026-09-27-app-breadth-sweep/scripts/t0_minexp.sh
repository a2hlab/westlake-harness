#!/usr/bin/env bash
# Run in a2hlab after taking board_note.sh lock as cx-t0.
set -euo pipefail
exec python3 "$(dirname "$0")/t0_collect.py" "$@"
