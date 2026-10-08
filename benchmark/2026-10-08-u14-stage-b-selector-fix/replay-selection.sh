#!/bin/bash
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
WORKSPACES=${WORKSPACES:-$(dirname "$REPO")}
export WORKSPACES
ROOT="$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-03-u14-stage-a-plan"
mkdir -p "$HERE/.artifacts/cli"
python3 "$REPO/scripts/lab/stage_a_selftest.py" --root "$ROOT" --selector u14-candidate-union-v1 --out "$HERE/.artifacts/cli" > "$HERE/.artifacts/cli-stdout.txt" 2> "$HERE/.artifacts/cli-stderr.txt"
printf 'union_cli_exit=0\n'
cat "$HERE/.artifacts/cli-stdout.txt"
set +e
python3 "$REPO/scripts/lab/stage_a_selftest.py" --root "$ROOT" --pattern 'window*/u14-A*/*/runner/**/record.json' > "$HERE/.artifacts/legacy-stdout.txt" 2> "$HERE/.artifacts/legacy-stderr.txt"
legacy=$?
python3 "$REPO/scripts/lab/stage_a_selftest.py" --root "$ROOT" --pattern 'window*/u14-A*/*/*/runner/**/record.json' > "$HERE/.artifacts/control-stdout.txt" 2> "$HERE/.artifacts/control-stderr.txt"
control=$?
set -e
printf 'legacy_cli_exit=%s\ncontrol_cli_exit=%s\n' "$legacy" "$control"
cat "$HERE/.artifacts/legacy-stderr.txt" "$HERE/.artifacts/control-stderr.txt"
test "$legacy" -eq 1
test "$control" -eq 1
python3 - "$legacy" "$control" > "$HERE/.artifacts/exit-codes.json" <<'PY'
import json
import sys
print(json.dumps(dict(union_cli_exit=0, legacy_cli_exit=int(sys.argv[1]), mixed_control_cli_exit=int(sys.argv[2]))))
PY
python3 "$HERE/bind_entry.py"
