#!/usr/bin/env bash
# Build the ARM64 ART JNI companion chain in one generation-owned directory.
set -euo pipefail
ROOT=${B6_REPO_ROOT:?Set B6_REPO_ROOT to the harness checkout}

if [ "${BUILD_INNER_INVOKED:-}" != 1 ]; then
    echo "[GUARD] invoke through the reviewed generation orchestrator" >&2
    exit 2
fi

ROOT=${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
OH=${OH_ROOT:?OH_ROOT is required}
AOSP=${AOSP_ROOT:?AOSP_ROOT is required}
OH_PRODUCT=${OH_PRODUCT_NAME:-wukong100}
OUT=${AOSP_OUT_DIR:-$ROOT/out/aosp_lib64}
OBJ=${EXTRAS_OBJ_DIR:-/tmp/cc100/extras-arm64}
LOG=${EXTRAS_BUILD_LOG:-$ROOT/out/extras-arm64.log}
STRICT_BUILD=${L03_A12_STRICT_BUILD:-0}

case "$STRICT_BUILD" in
    0|1) ;;
    *) echo "L03_A12_STRICT_BUILD must be 0 or 1" >&2; exit 2 ;;
esac
if [ -n "${L03_A12_GENERATION_ID:-}" ]; then
    : "${AOSP_OUT_DIR:?generation build requires AOSP_OUT_DIR}"
    : "${EXTRAS_OBJ_DIR:?generation build requires EXTRAS_OBJ_DIR}"
    : "${EXTRAS_BUILD_LOG:?generation build requires EXTRAS_BUILD_LOG}"
    : "${L03_A12_CC:?generation build requires L03_A12_CC}"
    : "${L03_A12_CXX:?generation build requires L03_A12_CXX}"
    : "${L03_A12_READELF:?generation build requires L03_A12_READELF}"
    : "${L03_A12_BUILTINS:?generation build requires L03_A12_BUILTINS}"
    : "${L03_A12_PYTHON:?generation build requires L03_A12_PYTHON}"
    if [ "$OUT" = "$ROOT/out/aosp_lib64" ] \
        || [ "$OBJ" = /tmp/cc100/extras-arm64 ]; then
        echo "generation extras build resolved to a shared path" >&2
        exit 2
    fi
fi

CC=${L03_A12_CC:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang}
CXX=${L03_A12_CXX:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++}
READELF=${L03_A12_READELF:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf}
BUILTINS=${L03_A12_BUILTINS:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a}
AR=${L03_A12_AR:-$(dirname "$CC")/llvm-ar}
NM=${L03_A12_NM:-$(dirname "$CC")/llvm-nm}
PYTHON=${L03_A12_PYTHON:-python3}
OH_OUT=$OH/out/$OH_PRODUCT
MUSL_USR=$OH_OUT/obj/third_party/musl/usr
MUSL_LIB=$MUSL_USR/lib/aarch64-linux-ohos
OH_PSDK=$OH_OUT/packages/phone/system/lib64/platformsdk
BC=$ROOT/framework/appspawn-x/bionic_compat/include
SOCKET_FIX=$ROOT/build/compat/musl_socket_fix.h

for executable in "$CC" "$CXX" "$READELF" "$AR" "$NM" "$PYTHON"; do
    test -x "$executable"
done
test -f "$BUILTINS"
test -f "$SOCKET_FIX"
test -d "$MUSL_USR/include/aarch64-linux-ohos"
test -d "$OH_PSDK"

if [ "${1:-}" = --clean ]; then
    rm -rf "$OBJ"
    shift
fi
if [ "$#" -ne 0 ]; then
    echo "unknown extras argument: $*" >&2
    exit 2
fi
mkdir -p "$OUT" "$OBJ" "$(dirname "$LOG")"
: >"$LOG"

COMMON="--target=aarch64-linux-ohos --sysroot=$MUSL_USR -I$MUSL_USR/include/aarch64-linux-ohos -fPIC -O2 -D__OHOS__ -D_GNU_SOURCE -D_POSIX_SOURCE -Wno-unused-parameter -Wno-format -Wno-sign-compare -Wno-missing-field-initializers -Wno-c99-designator -Wno-gnu-designator -Wno-extern-c-compat -Wno-deprecated-declarations -Wno-error"
C_COMMON="$COMMON"
CXX_COMMON="$COMMON -nostdinc++ -isystem $L03_A12_LIBCXX_INCLUDE -std=gnu++17 -include $BC/libcxx_compat.h -I$BC"
LNK="$CXX --target=aarch64-linux-ohos -B$MUSL_LIB -L$MUSL_LIB -L$OUT -shared -fPIC"
if [ "$STRICT_BUILD" = 1 ]; then
    LNK="$LNK -Wl,-z,defs -Wl,--build-id=sha1"
fi

COMPILED_OBJECTS=()
compile_group()
{
    local name=$1 flags=$2
    shift 2
    local directory=$OBJ/$name
    local source base stem key object compiler
    local failed=0
    mkdir -p "$directory"
    COMPILED_OBJECTS=()
    for source in "$@"; do
        if [ ! -f "$source" ]; then
            echo "missing source: $source" | tee -a "$LOG" >&2
            failed=$((failed + 1))
            continue
        fi
        base=$(basename "$source")
        stem=${base%.*}
        key=$(printf '%s' "$source" | sha256sum | cut -c1-10)
        object=$directory/${stem}_${key}.o
        compiler=$CC
        case "$base" in *.cpp|*.cc|*.cxx|*.C) compiler=$CXX ;; esac
        if "$compiler" $([ "$compiler" = "$CXX" ] && printf '%s' "$CXX_COMMON" || printf '%s' "$C_COMMON") \
            $flags -c "$source" -o "$object" 2>"$object.err"; then
            COMPILED_OBJECTS+=("$object")
        else
            echo "compile failed: $source" | tee -a "$LOG" >&2
            sed -n '1,20p' "$object.err" >>"$LOG"
            failed=$((failed + 1))
        fi
    done
    [ "$failed" -eq 0 ] && [ "${#COMPILED_OBJECTS[@]}" -gt 0 ]
}

link_shared()
{
    local soname=$1
    shift
    local output=$OUT/$soname
    $LNK -Wl,-soname,"$soname" -o "$output" \
        "${COMPILED_OBJECTS[@]}" "$@" "$BUILTINS" >>"$LOG" 2>&1
    echo "BUILT $soname bytes=$(stat -c%s "$output")"
}

echo "=== libopenjdkjvm.so ==="
compile_group openjdkjvm \
    "-include $SOCKET_FIX -DART_TARGET -DART_TARGET_LINUX -DNDEBUG -DANDROID_HOST_MUSL -DART_BASE_ADDRESS=0x70000000 -DART_DEFAULT_GC_TYPE_IS_CMS -DART_FRAME_SIZE_LIMIT=1736 -DIMT_SIZE=43 -DART_STACK_OVERFLOW_GAP_arm=8192 -DART_STACK_OVERFLOW_GAP_arm64=8192 -DART_STACK_OVERFLOW_GAP_riscv64=8192 -DART_STACK_OVERFLOW_GAP_x86=8192 -DART_STACK_OVERFLOW_GAP_x86_64=8192 -I$AOSP/art/libdexfile -I$AOSP/art/libartpalette/include -I$AOSP/art/libdexfile/external/include -I$AOSP/libnativehelper/include -I$AOSP/libnativehelper/include_jni -I$AOSP/libnativehelper/header_only_include -I$AOSP/libnativehelper/include_platform_header_only -I$AOSP/system/libbase/include -I$AOSP/system/logging/liblog/include -I$AOSP/art/runtime -I$AOSP/art/libartbase -I$AOSP/external/tinyxml2" \
    "$AOSP/art/openjdkjvm/OpenjdkJvm.cc"
link_shared libopenjdkjvm.so -L"$OUT" -lart -lartbase -llog -lbase -lc -ldl -lpthread
