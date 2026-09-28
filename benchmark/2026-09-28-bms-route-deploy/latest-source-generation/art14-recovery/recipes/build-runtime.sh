#!/usr/bin/env bash
set -euo pipefail
ROOT=${B6_REPO_ROOT:?Set B6_REPO_ROOT to the harness checkout}
export BUILD_INNER_INVOKED=1
export LD_LIBRARY_PATH=${ROOT}/bms/src/.work/b6-art14-recovery/tools/lib64
export ADAPTER_ROOT=${ROOT}/bms/src/.work/b6-latest/adapter
export AOSP_ROOT=${ROOT}/bms/src/.work/b6-art14-recovery/aosp-restoration OH_ROOT=${ROOT}/bms/src/.work/b6-latest/oh
export AOSP_LIB_DIR=${ROOT}/bms/src/.work/b6-art14-recovery/build/providers ADAPTER_OUT_DIR=${ROOT}/bms/src/.work/b6-latest/out
export ANDROID_RUNTIME_BUILD_DIR=${ROOT}/bms/src/.work/b6-art14-recovery/build/runtime-objects
export L03_A12_GENERATION_ID=b6-latest-art14-runtime L03_A12_STRICT_BUILD=1
export L03_A12_CXX=${ROOT}/bms/src/.work/b6-art14-recovery/build/cxx-sdk15
export L03_A12_NM=${ROOT}/bms/src/.work/product-tls-generation/frozen/toolchain/bin/llvm-nm L03_A12_READELF=${ROOT}/bms/src/.work/product-tls-generation/frozen/toolchain/bin/llvm-readelf
export L03_A12_LIBCXX_INCLUDE=${ROOT}/bms/src/.work/product-tls-generation/frozen/toolchain/include/c++/v1
export L03_A12_AIDL=${ROOT}/bms/src/.work/b6-art14-recovery/tools/aidl L03_A12_PYTHON=/usr/bin/python3
bash ${ROOT}/bms/src/.work/b6-art14-recovery/runtime-recipe.sh
