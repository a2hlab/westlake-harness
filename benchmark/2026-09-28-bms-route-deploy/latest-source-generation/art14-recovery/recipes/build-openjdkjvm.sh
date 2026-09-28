#!/usr/bin/env bash
set -euo pipefail
ROOT=${B6_REPO_ROOT:?Set B6_REPO_ROOT to the harness checkout}
export BUILD_INNER_INVOKED=1
export ADAPTER_ROOT=${ROOT}/bms/src/adapter
export AOSP_ROOT=${ROOT}/bms/src/.work/b6-art14-recovery/aosp-restoration OH_ROOT=${ROOT}/bms/src/.work/b6-art14-recovery/oh
export AOSP_OUT_DIR=${ROOT}/bms/src/.work/b6-art14-recovery/build/providers
export MINIKIN_OBJ_DIR=${ROOT}/bms/src/.work/b6-art14-recovery/build/graphics-objects MINIKIN_BUILD_LOG=${ROOT}/bms/src/.work/b6-art14-recovery/build/graphics-errors.log
export L03_A12_GENERATION_ID=b6-art14-graphics L03_A12_STRICT_BUILD=1
export L03_A12_CXX=${ROOT}/bms/src/.work/b6-art14-recovery/build/cxx-sdk15 L03_A12_CC=${ROOT}/bms/src/.work/product-tls-generation/frozen/toolchain/bin/clang-15
export L03_A12_NM=${ROOT}/bms/src/.work/product-tls-generation/frozen/toolchain/bin/llvm-nm L03_A12_READELF=${ROOT}/bms/src/.work/product-tls-generation/frozen/toolchain/bin/llvm-readelf
export L03_A12_LIBCXX_INCLUDE=${ROOT}/bms/src/.work/product-tls-generation/frozen/toolchain/include/c++/v1

export EXTRAS_OBJ_DIR=${ROOT}/bms/src/.work/b6-art14-recovery/build/openjdkjvm-objects EXTRAS_BUILD_LOG=${ROOT}/bms/src/.work/b6-art14-recovery/openjdkjvm-errors.log
export L03_A12_BUILTINS=${ROOT}/bms/src/.work/product-tls-generation/frozen/toolchain/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a L03_A12_PYTHON=/usr/bin/python3
bash ${ROOT}/bms/src/.work/b6-art14-recovery/openjdkjvm-recipe.sh
