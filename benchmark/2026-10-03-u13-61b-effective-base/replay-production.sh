#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
export WORKSPACES="${WORKSPACES:-$(cd "$HERE/../../.." && pwd)}"
case "${1:-}" in
  mac) python3 "$HERE/offline_gates.py" --surface mac ;;
  vm) orb -m a2hlab env "MAC_HOME=$HOME" "WORKSPACES=$WORKSPACES" python3 "$HERE/offline_gates.py" --surface vm ;;
  *) echo "usage: replay-production.sh mac|vm" >&2; exit 2 ;;
esac
