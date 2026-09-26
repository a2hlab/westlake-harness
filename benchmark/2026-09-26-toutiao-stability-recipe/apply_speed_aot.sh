#!/usr/bin/env bash
# Additive module for the CURRENT native stability baseline; does not replay v1.
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
exec bash "$here/../2026-09-26-toutiao-speed-aot/apply_speed_aot.sh" "$@"
