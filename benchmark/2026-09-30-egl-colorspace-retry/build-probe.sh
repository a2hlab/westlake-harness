#!/usr/bin/env bash
# Offline OH6.1 rebuild experiment; not a deployment-ready same-generation binary.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
W=$ROOT/bms/src/.work/b11-egl-retry
export BUILD_INNER_INVOKED=1
export OH_ROOT=$ROOT/bms/src/.work/b68-generation/oh
export AOSP_ROOT=$W/aosp14
export ADAPTER_ROOT=$W/oh61-rebuild-adapter
export LD_LIBRARY_PATH=$ROOT/bms/src/.work/product-tls-generation/frozen/toolchain/runtime
bash "$ROOT/benchmark/2026-09-30-egl-colorspace-retry/rebuild-recipe.sh" "$@"
