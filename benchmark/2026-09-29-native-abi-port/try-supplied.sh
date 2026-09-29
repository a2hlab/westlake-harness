#!/usr/bin/env bash
set -euo pipefail
export OHOS_SYSROOT=/home/dspfac/a2hlab/source-closure/verify/toolchains/ohos-sdk/native/sysroot
export CC=/home/dspfac/a2hlab/source-closure/verify/toolchains/ohos-sdk/native/llvm/bin/clang
export CXX_BIN=/home/dspfac/a2hlab/source-closure/verify/toolchains/ohos-sdk/native/llvm/bin/clang++
bash /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/adapter/framework/native-compat/westlake-bionic/build.sh /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b87-native/supplied-build
