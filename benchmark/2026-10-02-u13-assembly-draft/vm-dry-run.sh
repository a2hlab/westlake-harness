#!/usr/bin/env bash
set -euo pipefail
: "${WORKSPACES:?set WORKSPACES to the shared Mac workspace bind visible inside a2hlab}"
: "${MAC_HOME:?set MAC_HOME for the existing VM DEX/LLVM proxy tools}"
: "${LAB_HOME:?set LAB_HOME for the trusted remote oatdump}"
REPORT="$WORKSPACES/westlake-harness-bms/benchmark/2026-10-02-u13-assembly-draft"
export PATH="$WORKSPACES/westlake-harness/benchmark/2026-10-01-u7-executor/.vm-tools:$PATH"
python3 - "$REPORT" <<'PY'
import hashlib, json, pathlib, platform, sys
report = pathlib.Path(sys.argv[1])
composition = json.loads((report / 'composition.json').read_text())
package = report / '.artifacts/bundle'
assert platform.system() == 'Linux', 'VM command requires actual Linux execution'
assert hashlib.sha256((package / 'bundle.json').read_bytes()).hexdigest() == composition['bundle_sha256']
assert hashlib.sha256((package / 'native/package.json').read_bytes()).hexdigest() == composition['native_manifest_sha256']
assert composition['execution_enabled'] is False and composition['rollout_ready'] is False
PY
set +e
python3 "$REPORT/offline_gates.py" --surface vm 2>&1 | tee "$REPORT/.artifacts/vm-session.log"
status=${PIPESTATUS[0]}
set -e
exit "$status"
