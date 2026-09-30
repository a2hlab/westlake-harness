#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
python3 - "$HERE/fitness-gate.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));assert r['reviewed']==3 and r['t20_own_ui']>=2 and r['proceed_full_n1'] is True
PY
python3 "$HERE/jar_overlay.py" expose
"$REPO/scripts/lab/deploy_generation.sh" 61b0657200000000000000000324012c /Users/zhaoyue/orca/workspaces/westlake-generation-n1-aa57845c --upgrade --lane cx-t0
python3 "$HERE/jar_overlay.py" restore
