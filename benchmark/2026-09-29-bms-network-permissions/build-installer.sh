#!/usr/bin/env bash
set -euo pipefail
W=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b89-network-permissions
export BUILD_INNER_INVOKED=1
export OH_ROOT=/Users/zhaoyue/orca/workspaces/oh61-bms-kit
export ADAPTER_ROOT=$W/adapter
export APK_INSTALLER_BUILD_TMP=$W/installer-objects
export LD_LIBRARY_PATH=/home/zhaoyue/a2hlab/ws/toolchains/ohos-sdk/native/llvm/lib
bash "$ADAPTER_ROOT/build/inner/compile_apk_installer.sh"
if find "$APK_INSTALLER_BUILD_TMP" -name '*.err' -size +0c -exec grep -l 'error:' {} + | grep -q .; then exit 1; fi
/home/zhaoyue/a2hlab/ws/toolchains/ohos-sdk/native/llvm/bin/llvm-strip --strip-unneeded "$ADAPTER_ROOT/out/adapter/libapk_installer.so"
sha256sum "$ADAPTER_ROOT/out/adapter/libapk_installer.so"
