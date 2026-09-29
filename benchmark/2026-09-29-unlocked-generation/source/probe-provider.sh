#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
export ROUTE_A_PROJECT_ROOT=$ROOT
export WESTLAKE_GENERATION_ROOT=$ROOT/.work/product-tls-generation
export WESTLAKE_ROUTE_A_BASE_PROVIDER_ROOT=$ROOT/rebuilt-provider-base
export WESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=1
export LD_LIBRARY_PATH=$WESTLAKE_GENERATION_ROOT/frozen/toolchain/runtime
set -a
source "$ROOT/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/r45_adapter_identity.env"
set +a
exec bash "$ROOT/probe-provider-inner.sh"
