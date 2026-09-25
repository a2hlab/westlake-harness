#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$here/apply_all_fixes.py" "$@"
