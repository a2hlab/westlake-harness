#!/usr/bin/env bash

set -Eeuo pipefail

SELF="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
DRIVER="$REPO_ROOT/src/tools/devices/boat-attack-apk-lightup.sh"
AUTOSTART_DRIVER="$REPO_ROOT/src/tools/devices/install-boat-attack-autostart.sh"

[ -x "$DRIVER" ] || {
    printf 'ERROR: missing executable driver: %s\n' "$DRIVER" >&2
    exit 1
}

case "${1:-check}" in
    autostart-status) autostart_mode=status ;;
    autostart-install) autostart_mode=install ;;
    autostart-activate) autostart_mode=activate ;;
    autostart-finalize) autostart_mode=finalize ;;
    autostart-reboot-test) autostart_mode=reboot-test ;;
    autostart-uninstall) autostart_mode=uninstall ;;
    *) exec "$DRIVER" "$@" ;;
esac

[ -x "$AUTOSTART_DRIVER" ] || {
    printf 'ERROR: missing executable autostart driver: %s\n' "$AUTOSTART_DRIVER" >&2
    exit 1
}

shift
exec "$AUTOSTART_DRIVER" "$autostart_mode" "$@"
