#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
export WORKSPACES="${WORKSPACES:-$(python3 "$root/scripts/lab/lab_paths.py")}"
export MAC_HOME="${MAC_HOME:-$HOME}"
export LAB_HOME="${LAB_HOME:?set hw248 lab root, see U7 executor README}"
package=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["bundle"])' "$root/benchmark/2026-10-01-u9-native/rollout/package.json")
orb -m a2hlab env "WORKSPACES=$WORKSPACES" "MAC_HOME=$MAC_HOME" "LAB_HOME=$LAB_HOME" bash \
 "$root/benchmark/2026-10-01-u7-executor/board61b/run-executor.sh" --dry-run \
 --package "$WORKSPACES/$package" --baseline-native "$WORKSPACES/westlake-generation-u8-j9-t7e/native" \
 --oatdump "$WORKSPACES/westlake-harness/scripts/lab/oatdump_remote.sh" \
 --out "$root/benchmark/2026-10-01-u9-native/rollout/production-j10g-dry-run.json"
