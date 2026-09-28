#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
export ROUTE_A_PROJECT_ROOT="$TASK_ROOT/bms/src"
PLUGIN="$ROUTE_A_PROJECT_ROOT/adapter/framework/appspawn-x/security_specialization/stock_child_plugin"
set -a
source "$PLUGIN/r45_adapter_identity.env"
set +a
export WESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=1
exec bash "$PLUGIN/build_route_a_generation_in_container.sh"
