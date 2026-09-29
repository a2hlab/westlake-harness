#!/usr/bin/env bash
set -euo pipefail
export LD_LIBRARY_PATH=/home/dspfac/a2hlab/source-closure/verify/toolchains/ohos-sdk/native/llvm/lib
KIT=/Users/zhaoyue/orca/workspaces/oh61-bms-kit-b79
cd "$KIT/out/wukong100"
"$KIT/tool-bin/ninja" -d keeprsp -v -j2 bundlemanager/bundle_framework/libbms.z.so
sha256sum bundlemanager/bundle_framework/libbms.z.so
