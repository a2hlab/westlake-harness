#!/usr/bin/env bash
set -euo pipefail
R=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy
F=$R/bms/src/.work/b68-generation/.work/product-tls-generation/frozen
export LD_LIBRARY_PATH=$F/toolchain/runtime
"$F/toolchain/bin/clang-15" --target=aarch64-linux-ohos --sysroot="$F/sysroot" -B"$F/toolchain/bin" -O2 -g -Werror=implicit-function-declaration -Wl,-z,defs "$R/benchmark/2026-09-30-child-stack-default/stack_probe.c" -o "$R/bms/src/.work/b92-stack/stack_probe" -lpthread
sha256sum "$R/bms/src/.work/b92-stack/stack_probe"
