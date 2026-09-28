#!/usr/bin/env bash
# Runs inside the locked Linux container.  Every path below is supplied by the
# project-local frozen closure mounted read-only at /inputs.

set -euo pipefail
IFS=$'\n\t'
umask 022

INPUTS=${WESTLAKE_PROVIDER_INPUTS_ROOT:-/inputs}
ADAPTER_ROOT=$INPUTS/adapter
AOSP_ROOT=$INPUTS/aosp
OH_ROOT=$INPUTS/oh
TOOLCHAIN=$OH_ROOT/toolchain
SYSROOT=$OH_ROOT/out/wukong100/obj/third_party/musl
ARTIFACTS=${WESTLAKE_PROVIDER_ARTIFACTS_ROOT:-/artifacts}
WORK_ROOT=${WESTLAKE_PROVIDER_WORK_ROOT:-/work}
PROVIDERS=$ARTIFACTS/providers
FIXTURES=$WORK_ROOT/app-native-loader-fixtures
OBJECTS=$WORK_ROOT/objects
ERROR_LOG=$WORK_ROOT/aosp-build-errors.log
LOADER=$INPUTS/providers/ld-musl-aarch64.so.1
ZERO_ARRAY_COHORT=$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include/libcxx_array_aosp

export TMPDIR=$WORK_ROOT/tmp
export XDG_CACHE_HOME=$WORK_ROOT/cache
export LD_LIBRARY_PATH="$TOOLCHAIN/runtime"
mkdir -p "$PROVIDERS" "$FIXTURES" "$OBJECTS" "$TMPDIR" "$XDG_CACHE_HOME"

env \
    BUILD_INNER_INVOKED=1 \
    ADAPTER_ROOT="$ADAPTER_ROOT" \
    ANL_OUT_DIR="$PROVIDERS" \
    ANL_FIXTURE_OUT_DIR="$FIXTURES" \
    OH_CC="$TOOLCHAIN/bin/clang-15" \
    OH_READELF="$TOOLCHAIN/bin/llvm-readelf" \
    OH_SYSROOT="$SYSROOT" \
    OH_DLNS_PROVIDER="$LOADER" \
    OH_DLNS_PROVIDER_SHA256=fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2 \
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
    L03_A12_LIBART_ZERO_ARRAY_HEADER_COHORT="$ZERO_ARRAY_COHORT" \
    L03_A12_PYTHON=/usr/bin/python3 \
    BUILD_NJOBS="${BUILD_NJOBS:-12}" \
    bash "$ADAPTER_ROOT/build/inner/cross_compile_arm64.sh" --clean

python3 "$ADAPTER_ROOT/build/provider_generation/libart_tuple_receipt.py" emit \
    --generation-id "${WESTLAKE_PROVIDER_GENERATION_ID:-provider-build-v1}" \
    --inputs "$INPUTS" \
    --artifacts "$ARTIFACTS" \
    --objects "$OBJECTS" \
    --readelf "$TOOLCHAIN/bin/llvm-readelf"

find "$PROVIDERS" -maxdepth 1 -type f -name '*.so' -print0 \
    | LC_ALL=C sort -z | xargs -0 sha256sum > "$ARTIFACTS/providers.sha256"
printf 'status=build_pass\ndevice_verified=false\nproduct_activation=false\n' \
    > "$ARTIFACTS/build-result.env"
(cd "$ARTIFACTS" && find . -type f ! -name artifacts.sha256 -print0 \
    | LC_ALL=C sort -z | xargs -0 sha256sum) > "$ARTIFACTS/artifacts.sha256"
