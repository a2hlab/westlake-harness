#!/usr/bin/env bash
set -euo pipefail
export B6_BRIDGE_OBJ_DIR=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/bridge-objects-final
export B6_BRIDGE_PROBE_SCRIPT=adapter/build/inner/compile_oh_adapter_bridge_arm64.sh
export B6_AOSP_ROOT=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/aosp-restoration B6_FORCE_OH_SDK=0
export AOSP_LIB_DIR=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/build/providers
export L03_A12_GENERATION_ID=b6-latest-art14
export L03_A12_CXX=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/build/cxx-sdk15 L03_A12_READELF=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/bin/llvm-readelf
export L03_A12_BUILTINS=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a
export L03_A12_LIBCXX_INCLUDE=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/product-tls-generation/frozen/toolchain/include/c++/v1
export L03_A12_OH_LINK_ROOT=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/platform-link
export OH61_LINK_INPUTS=$L03_A12_OH_LINK_ROOT
bash benchmark/2026-09-28-bms-route-deploy/latest-source-generation/run_bridge_probe.sh
