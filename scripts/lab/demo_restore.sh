#!/bin/bash
set -euo pipefail
SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
exec python3 "$SELF_DIR/../../benchmark/2026-10-09-demo-baseline/t5/restore.py" "$@"
