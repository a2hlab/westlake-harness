#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" == --help ]]; then
  echo 'ADAPTER_ROOT/AOSP_ROOT/OH_ROOT/AOSP_LIB_DIR=<restored pinned trees> BUILD_OUT=<new dir> ./build.sh'
  echo 'Original runtime recipe also consumes L03_A12_* compiler/header/tool variables; see recorded build.sh and BUILD.md.'
  exit 0
fi
: "${ADAPTER_ROOT:?restored runtime source required}" "${AOSP_ROOT:?required}" "${OH_ROOT:?required}" "${AOSP_LIB_DIR:?pinned link inputs required}" "${BUILD_OUT:?new absolute directory required}"
[[ "$BUILD_OUT" == /* && ! -e "$BUILD_OUT" ]] || { echo 'BUILD_OUT must be new and absolute' >&2; exit 2; }
mkdir -p "$BUILD_OUT"
export BUILD_INNER_INVOKED=1 ASSET_FD_SOURCE="$HERE/src/android_util_AssetManager_aosp.cpp"
export ANDROID_RUNTIME_BUILD_DIR="$BUILD_OUT/objects" ADAPTER_OUT_DIR="$BUILD_OUT/out"
bash "$HERE/build-evidence/runtime-recipe.sh.original.txt" 2>&1 | tee "$BUILD_OUT/build.log"
