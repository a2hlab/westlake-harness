#!/usr/bin/env bash
# Runs inside the locked Linux container.  Every path below is supplied by the
# project-local frozen closure mounted read-only at /inputs.

set -euo pipefail
IFS=$'\n\t'
umask 022

INPUTS=/inputs
ADAPTER_ROOT=$INPUTS/adapter
AOSP_ROOT=$INPUTS/aosp
OH_ROOT=$INPUTS/oh
TOOLCHAIN=$OH_ROOT/toolchain
SYSROOT=$OH_ROOT/out/wukong100/obj/third_party/musl
PROVIDERS=/artifacts/providers
FIXTURES=/work/app-native-loader-fixtures
OBJECTS=/work/objects
ERROR_LOG=/work/aosp-build-errors.log
LOADER=$INPUTS/providers/ld-musl-aarch64.so.1

export TMPDIR=/work/tmp
export HOME=/work/home
export LD_LIBRARY_PATH="$TOOLCHAIN/runtime"
mkdir -p "$PROVIDERS" "$FIXTURES" "$OBJECTS" "$TMPDIR" "$HOME"

env \
    BUILD_INNER_INVOKED=1 \
    ADAPTER_ROOT="$ADAPTER_ROOT" \
    ANL_OUT_DIR="$PROVIDERS" \
    ANL_FIXTURE_OUT_DIR="$FIXTURES" \
    OH_CC="$TOOLCHAIN/bin/clang-15" \
    OH_READELF="$TOOLCHAIN/bin/llvm-readelf" \
    OH_SYSROOT="$SYSROOT" \
    OH_DLNS_PROVIDER="$LOADER" \
    OH_DLNS_PROVIDER_SHA256=316f70f2195b72aaf64e9f71e97d1d16cc25070f852f185994175893aeeeaa98 \
    bash "$ADAPTER_ROOT/build/compile_app_native_loader_arm64.sh"

env \
    BUILD_INNER_INVOKED=1 \
    ADAPTER_ROOT="$ADAPTER_ROOT" \
    OH_ROOT="$OH_ROOT" \
    AOSP_ROOT="$AOSP_ROOT" \
    AOSP_OUT_DIR="$PROVIDERS" \
    AOSP_OBJ_DIR="$OBJECTS" \
    AOSP_BUILD_ERROR_LOG="$ERROR_LOG" \
    L03_A12_GENERATION_ID=provider-build-v1 \
    L03_A12_STRICT_BUILD=1 \
    L03_A12_CC="$TOOLCHAIN/bin/clang-15" \
    L03_A12_CXX="$TOOLCHAIN/bin/clang++" \
    L03_A12_AS="$TOOLCHAIN/bin/clang-15" \
    L03_A12_READELF="$TOOLCHAIN/bin/llvm-readelf" \
    L03_A12_NM="$TOOLCHAIN/bin/llvm-nm" \
    L03_A12_BUILTINS="$TOOLCHAIN/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a" \
    L03_A12_LIBCXX_INCLUDE="$TOOLCHAIN/include/c++/v1" \
    L03_A12_PYTHON=/usr/bin/python3 \
    BUILD_NJOBS="${BUILD_NJOBS:-12}" \
    bash "$ADAPTER_ROOT/build/inner/cross_compile_arm64.sh" --clean

find "$PROVIDERS" -maxdepth 1 -type f -name '*.so' -print0 \
    | LC_ALL=C sort -z | xargs -0 sha256sum > /artifacts/providers.sha256
printf 'status=build_pass\ndevice_verified=false\nproduct_activation=false\n' \
    > /artifacts/build-result.env
