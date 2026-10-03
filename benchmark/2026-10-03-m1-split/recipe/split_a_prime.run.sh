#!/usr/bin/env bash
set -uo pipefail
FRESH=$WORKSPACES/westlake-harness-wiki/benchmark/2026-10-03-m1-split/build/gen
mkdir -p "$FRESH/out" "$FRESH/objs"
export BUILD_INNER_INVOKED=1
export LD_LIBRARY_PATH=$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/tools/lib64
export ADAPTER_ROOT=$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b87-native/adapter
export AOSP_ROOT=$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/aosp-restoration OH_ROOT=$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b6-latest/oh
export AOSP_LIB_DIR=$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b67-generation/runtime-link ADAPTER_OUT_DIR="$FRESH/out"
export ANDROID_RUNTIME_BUILD_DIR="$FRESH/objs"
export L03_A12_GENERATION_ID=b6-latest-art14-runtime L03_A12_STRICT_BUILD=1
export L03_A12_CXX=$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/build/cxx-sdk15
export L03_A12_NM=$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/bin/llvm-nm L03_A12_READELF=$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/bin/llvm-readelf
export L03_A12_LIBCXX_INCLUDE=$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/include/c++/v1
export L03_A12_AIDL=$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/tools/aidl L03_A12_PYTHON=/usr/bin/python3
export L03_A12_CC=$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/bin/clang-15
cp $WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b91-common-event/runtime-out/libwestlake_thread_guard_registry.so "$FRESH/out/"
bash $WORKSPACES/westlake-harness-wiki/benchmark/2026-10-03-m1-split/recipe/split_a_prime.inner.sh
