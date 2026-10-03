#!/usr/bin/env bash
set -euo pipefail
if [ "${U15_PRODUCTION_REPLAY:-}" != outer-approved ]; then
  echo 'DISABLED: U15 production replay requires outer approval; no lock, apply or promotion'
  exit 78
fi
SURFACE=${1:?mac or vm}
BASE=${2:?explicit U14 per-board BASE}
BASE_SHA=${3:?full BASE bundle SHA}
PACKAGE=${4:?matching disabled U15 package}
OATDUMP=${5:?trusted oatdump binary or wrapper, outer-owned}
case "$SURFACE" in
  mac) [ "$(uname -s)" = Darwin ] || exit 3;;
  vm) [ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] || exit 3;;
  *) exit 2;;
esac
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
WS=${WORKSPACES:-$(dirname "$REPO")}
if [ "$SURFACE" = vm ]; then
  export PATH="$WS/westlake-harness/benchmark/2026-10-01-u7-executor/.vm-tools:$PATH"
  mkdir -p "$HERE/.artifacts/vm-tmp"
  export TMPDIR="$HERE/.artifacts/vm-tmp"
  MAC_HOME=${MAC_HOME:-$(mac sh -c 'printf %s "$HOME"')}
  [ -n "$MAC_HOME" ] || { echo 'REFUSE: Mac HOME discovery returned empty' >&2; exit 3; }
  export MAC_HOME
fi
python3 - "$BASE" "$BASE_SHA" "$PACKAGE" <<'PY'
import hashlib
import json
from pathlib import Path
import sys
base, expected, package = sys.argv[1:]
actual = hashlib.sha256((Path(base) / 'bundle.json').read_bytes()).hexdigest()
data = json.loads((Path(package) / 'bundle.json').read_text())
if actual != expected or data['static_checks']['baseline_bundle_sha256'] != expected:
    raise SystemExit('REFUSE: per-board U14 BASE binding mismatch')
if data.get('rollout_ready') or data.get('execution_enabled'):
    raise SystemExit('REFUSE: U15 package must remain disabled')
binding = data.get('transaction_binding', {})
if binding.get('base_sha256') != expected or binding.get('promotion_confirmed') is not False:
    raise SystemExit('REFUSE: explicit disabled U15 transaction binding required')
PY
OUT="$HERE/.artifacts/outer-$SURFACE-$(date +%Y%m%dT%H%M%S)"
mkdir -p "$OUT"
set +e
python3 "$WS/westlake-harness/scripts/lab/u7_executor.py" --dry-run --package "$PACKAGE" \
  --baseline-native "$BASE/native" --oatdump "$OATDUMP" --out "$OUT/executor.json" 2>&1 | tee "$OUT/production.log"
STATUS=("${PIPESTATUS[@]}")
set -e
printf '{"executor_exit_code":%s,"tee_exit_code":%s,"device_access":false}\n' "${STATUS[0]}" "${STATUS[1]}" > "$OUT/status.json"
[ "${STATUS[1]}" -eq 0 ] || exit 8
exit "${STATUS[0]}"
