#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
export ROUTE_A_PROJECT_ROOT="$TASK_ROOT/bms/src"
export WLASC_P0_TYPED_REJECT_CAPABILITIES=1
exec bash "$ROUTE_A_PROJECT_ROOT/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/build_target_in_container.sh"
