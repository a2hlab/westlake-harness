#!/usr/bin/env bash
set -euo pipefail
test -f /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/adapter/framework/native-compat/westlake-commonevent/common_event_registration.cpp
python3 /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/scripts/lab/check_frozen.py --source-root /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy
export BUILD_INNER_INVOKED=1
export LD_LIBRARY_PATH=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/tools/lib64
export ADAPTER_ROOT=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b87-native/adapter
export AOSP_ROOT=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/aosp-restoration OH_ROOT=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/oh
export AOSP_LIB_DIR=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b67-generation/runtime-link ADAPTER_OUT_DIR=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/n1-native/runtime-out
export ANDROID_RUNTIME_BUILD_DIR=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/n1-native/runtime-objects
export L03_A12_GENERATION_ID=b6-latest-art14-runtime L03_A12_STRICT_BUILD=1
export L03_A12_CXX=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/build/cxx-sdk15
export L03_A12_NM=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/bin/llvm-nm L03_A12_READELF=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/bin/llvm-readelf
export L03_A12_LIBCXX_INCLUDE=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/include/c++/v1
export L03_A12_AIDL=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/tools/aidl L03_A12_PYTHON=/usr/bin/python3
export L03_A12_CC=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/bin/clang-15
mkdir -p "$ADAPTER_OUT_DIR"
cp /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b91-common-event/runtime-out/libwestlake_thread_guard_registry.so "$ADAPTER_OUT_DIR/"
bash /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/benchmark/2026-09-30-n1-native/runtime-recipe.sh
