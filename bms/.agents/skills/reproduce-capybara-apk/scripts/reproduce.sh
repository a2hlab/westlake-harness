#!/usr/bin/env bash

set -Eeuo pipefail

SELF="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
DRIVER="$REPO_ROOT/src/tools/devices/capybara-apk-lightup.sh"

[ -x "$DRIVER" ] || {
    printf 'ERROR: missing executable driver: %s\n' "$DRIVER" >&2
    exit 1
}

exec "$DRIVER" "$@"
