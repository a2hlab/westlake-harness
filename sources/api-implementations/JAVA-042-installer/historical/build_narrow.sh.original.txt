#!/usr/bin/env bash
set -euo pipefail
KIT=/Users/zhaoyue/orca/workspaces/oh61-bms-kit-b79
E=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/benchmark/2026-09-29-install-wall-validation
SDK=/home/dspfac/a2hlab/source-closure/verify/toolchains/ohos-sdk/native
export LD_LIBRARY_PATH="$SDK/llvm/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$KIT"
mkdir -p prebuilts/clang/ohos/linux-x86_64/llvm
BIN=prebuilts/clang/ohos/linux-x86_64/llvm/bin
if [ -L "$BIN" ]; then rm "$BIN"; fi
mkdir -p "$BIN"
for tool in clang-15 ld.lld llvm-strip llvm-ar llvm-nm llvm-readobj; do
  [ -f "$BIN/$tool" ] || cp -L "$SDK/llvm/bin/$tool" "$BIN/$tool"
done
ln -sfn clang-15 "$BIN/clang++"
ln -sfn clang-15 "$BIN/clang"
sha256sum "$SDK/llvm/bin/clang-15" > "$E/toolchain.sha256"
if [ ! -d candidate-source ]; then
mkdir -p baseline-source candidate-source
for rel in foundation/bundlemanager/bundle_framework/services/bundlemgr/src/base_bundle_installer.cpp foundation/bundlemanager/bundle_framework/services/bundlemgr/src/installd/installd_operator.cpp; do
 cp --parents "$rel" baseline-source/
done
patch --dry-run --fuzz=0 -p1 -i "$E/patches/0001-reuse-manifest-1mib.patch"
patch --fuzz=0 -p1 -i "$E/patches/0001-reuse-manifest-1mib.patch"
patch --dry-run --fuzz=0 -p1 -i "$E/patches/0002-native-exact-payloads.patch"
patch --fuzz=0 -p1 -i "$E/patches/0002-native-exact-payloads.patch"
for rel in foundation/bundlemanager/bundle_framework/services/bundlemgr/src/base_bundle_installer.cpp foundation/bundlemanager/bundle_framework/services/bundlemgr/src/installd/installd_operator.cpp; do
 cp --parents "$rel" candidate-source/
done
fi
cd out/wukong100
mkdir -p lib.unstripped/bundlemanager/bundle_framework bundlemanager/bundle_framework
"$KIT/tool-bin/ninja" -d keeprsp -v -j2 bundlemanager/bundle_framework/libbms.z.so bundlemanager/bundle_framework/libinstalls.z.so
sha256sum bundlemanager/bundle_framework/libbms.z.so bundlemanager/bundle_framework/libinstalls.z.so > "$E/candidate.sha256"
