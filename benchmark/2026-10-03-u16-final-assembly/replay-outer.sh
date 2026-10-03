#!/usr/bin/env bash
set -euo pipefail
if [ "${U16_OUTER_REPLAY:-}" != outer-approved ]; then
  echo 'DISABLED: outer only; no remote or device operation'
  exit 78
fi
MODE=${1:?g2-mac or g2-vm}
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
WORKSPACES=${WORKSPACES:-$(dirname "$REPO")}
export WORKSPACES
: "${LAB_HOME:?explicit hw248 lab directory required}"
case "$MODE" in
  g2-mac) [ "$(uname -s)" = Darwin ] || exit 3;;
  g2-vm)
    [ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] || exit 3
    export PATH="$WORKSPACES/westlake-harness/benchmark/2026-10-01-u7-executor/.vm-tools:$PATH"
    mkdir -p "$HERE/.artifacts/vm-tmp"
    export TMPDIR="$HERE/.artifacts/vm-tmp"
    MAC_HOME=${MAC_HOME:-$(mac sh -c 'printf %s "$HOME"')}
    [ -n "$MAC_HOME" ] || exit 3
    export MAC_HOME;;
  *) exit 2;;
esac
OUT="$HERE/.artifacts/outer-$MODE-$(date +%Y%m%dT%H%M%S)"
mkdir -p "$OUT"
set +e
python3 "$HERE/run_gates.py" --image-only --oatdump "$WORKSPACES/westlake-harness/scripts/lab/oatdump_remote.sh" 2>&1 | tee "$OUT/g2.log"
STATUS=("${PIPESTATUS[@]}")
set -e
printf '{"gate_exit_code":%s,"tee_exit_code":%s,"device_access":false}\n' "${STATUS[0]}" "${STATUS[1]}" > "$OUT/status.json"
[ "${STATUS[1]}" -eq 0 ] || exit 8
exit "${STATUS[0]}"
