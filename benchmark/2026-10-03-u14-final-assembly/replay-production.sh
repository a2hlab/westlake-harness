#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
if [ "${U14_PRODUCTION_REPLAY:-}" != outer-approved-after-window ]; then
  echo 'DISABLED: U14 review draft; no VM during U13 windows; require outer authorization after window'
  exit 78
fi
SURFACE=${1:?surface mac or vm}
BASE=${2:?explicit signed per-board transaction baseline bundle}
BASE_SHA=${3:?explicit baseline bundle SHA}
PACKAGE=${4:?explicit disabled U14 bundle}
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
    raise SystemExit('REFUSE: transaction base mismatch; re-finalize metadata first')
if data.get('rollout_ready'):
    raise SystemExit('REFUSE: this replay is for the disabled review draft only')
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
