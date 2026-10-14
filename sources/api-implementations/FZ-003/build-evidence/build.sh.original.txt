#!/usr/bin/env bash
set -euo pipefail
test -f /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/adapter/framework/native-compat/westlake-commonevent/common_event_registration.cpp
export BUILD_INNER_INVOKED=1
export LD_LIBRARY_PATH=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/tools/lib64
export ADAPTER_ROOT=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b87-native/adapter
export AOSP_ROOT=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/aosp-restoration OH_ROOT=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/oh
export AOSP_LIB_DIR=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b67-generation/runtime-link ADAPTER_OUT_DIR=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/asset-fd/runtime-out
export ANDROID_RUNTIME_BUILD_DIR=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/asset-fd/runtime-objects
export L03_A12_GENERATION_ID=b6-latest-art14-runtime L03_A12_STRICT_BUILD=1
export L03_A12_CXX=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/build/cxx-sdk15
export L03_A12_NM=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/bin/llvm-nm L03_A12_READELF=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/bin/llvm-readelf
export L03_A12_LIBCXX_INCLUDE=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/include/c++/v1
export L03_A12_AIDL=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/tools/aidl L03_A12_PYTHON=/usr/bin/python3
export L03_A12_CC=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/bin/clang-15
mkdir -p "$ADAPTER_OUT_DIR"
cp /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b91-common-event/runtime-out/libwestlake_thread_guard_registry.so "$ADAPTER_OUT_DIR/"
export ASSET_FD_SOURCE=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/benchmark/2026-09-30-asset-fd-runtime/src/android_util_AssetManager_aosp.cpp
RECIPE=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/benchmark/2026-09-30-asset-fd-runtime/runtime-recipe.sh
python3 /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/benchmark/2026-09-30-asset-fd-runtime/restore_b91_cache.py
bash "$RECIPE"
test "$(sha256sum "$ADAPTER_OUT_DIR/liboh_android_runtime.so" | cut -d" " -f1)" = 9e14bf2005290c6e9e689fa779a1019bfcded7436c3a36d7a4973f462f46cd0f
cp "$ADAPTER_OUT_DIR/liboh_android_runtime.so" "$ADAPTER_OUT_DIR/baseline-9e14.so"
rm "$ANDROID_RUNTIME_BUILD_DIR/android_util_AssetManager_aosp.o"
bash "$RECIPE"
sha256sum "$ADAPTER_OUT_DIR/liboh_android_runtime.so"
