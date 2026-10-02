#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
if [ "${U14_PRODUCTION_REPLAY:-}" != outer-approved-after-window ]; then
  echo 'DISABLED: only outer may replay after the U13 window; no promotion or window authorization implied'
  exit 78
fi
SURFACE=${1:?mac or vm}
BASE=${2:?explicit actual or promoted per-board baseline bundle}
BASE_SHA=${3:?full baseline bundle SHA}
PACKAGE=${4:?matching disabled U14 metadata variant}
case "$SURFACE" in
  mac) [ "$(uname -s)" = Darwin ] || exit 3;;
  vm) [ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] || exit 3;;
  *) exit 2;;
esac
REPO=$(cd "$HERE/../.." && pwd)
WS=${WORKSPACES:-$(dirname "$REPO")}
python3 - "$BASE" "$BASE_SHA" "$PACKAGE" <<'PY'
import hashlib
import json
from pathlib import Path
import sys
base, expected, package = sys.argv[1:]
actual = hashlib.sha256((Path(base) / 'bundle.json').read_bytes()).hexdigest()
data = json.loads((Path(package) / 'bundle.json').read_text())
if actual != expected or data['static_checks']['baseline_bundle_sha256'] != expected:
    raise SystemExit('REFUSE: transaction base mismatch; choose or re-finalize the matching variant')
if data.get('rollout_ready'):
    raise SystemExit('REFUSE: replay requires a disabled offline bundle')
PY
OUT="$HERE/.artifacts/production-$SURFACE-$(date +%Y%m%dT%H%M%S)"
mkdir -p "$OUT"
set +e
python3 "$WS/westlake-harness/scripts/lab/u7_executor.py" --dry-run --package "$PACKAGE" --baseline-native "$BASE/native" --oatdump "$WS/westlake-harness/scripts/lab/oatdump_remote.sh" --out "$OUT/executor" 2>&1 | tee "$OUT/production.log"
STATUS=("${PIPESTATUS[@]}")
set -e
printf '{"executor_exit_code":%s,"tee_exit_code":%s,"device_access":false}\n' "${STATUS[0]}" "${STATUS[1]}" > "$OUT/status.json"
[ "${STATUS[1]}" -eq 0 ] || exit 8
exit "${STATUS[0]}"
