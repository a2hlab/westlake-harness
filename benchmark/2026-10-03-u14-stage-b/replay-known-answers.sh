#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
WS=${WORKSPACES:-$(cd "$HERE/../../.." && pwd)}
case "${1:?mac or vm; tests only, no devices}" in
  mac) [ "$(uname -s)" = Darwin ]; python3 "$HERE/test_promotion_u14.py";;
  vm) orb -m a2hlab env WORKSPACES="$WS" python3 "$HERE/test_promotion_u14.py";;
  *) exit 2;;
esac
