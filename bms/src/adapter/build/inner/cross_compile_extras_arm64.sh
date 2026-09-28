#!/usr/bin/env bash
# Build the ARM64 ART JNI companion chain in one generation-owned directory.
set -euo pipefail

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
CXX_COMMON="$COMMON -std=gnu++17 -include $BC/libcxx_compat.h -I$BC"
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

echo "=== libexpat.so ==="
EXPAT=$AOSP/external/expat
compile_group expat \
    "-DHAVE_EXPAT_CONFIG_H -DXML_DEV_URANDOM -I$EXPAT -I$EXPAT/lib" \
    "$EXPAT/lib/xmlparse.c" "$EXPAT/lib/xmlrole.c" "$EXPAT/lib/xmltok.c"
link_shared libexpat.so -lc -ldl

echo "=== libcrypto.so ==="
BORINGSSL=$AOSP/external/boringssl
CRYPTO_LIST=$OBJ/libcrypto.sources
"$PYTHON" - "$BORINGSSL/sources.bp" "$BORINGSSL" >"$CRYPTO_LIST" <<'PY'
import re
import sys

source_file, root = sys.argv[1:]
text = open(source_file, encoding="utf-8").read()
match = re.search(
    r'name:\s*"libcrypto_sources".*?srcs:\s*\[\s*(.*?)\s*\]',
    text,
    re.DOTALL,
)
if match is None:
    raise SystemExit("libcrypto_sources not found")
for raw in match.group(1).splitlines():
    raw = raw.strip()
    if raw.startswith("//"):
        continue
    item = re.match(r'"([^"]+)"', raw)
    if item:
        print(f"{root}/{item.group(1)}")
print(f"{root}/src/crypto/fipsmodule/bcm.c")
PY
mapfile -t CRYPTO_SOURCES <"$CRYPTO_LIST"
compile_group crypto \
    "-I$BORINGSSL/src/include -I$BORINGSSL/src/crypto -I$BORINGSSL/src/third_party/fiat -DBORINGSSL_IMPLEMENTATION -DOPENSSL_NO_ASM_BUT_WITH_ARM_FOR_FILE_NAMES -DOPENSSL_SMALL -DOPENSSL_NO_ASM" \
    "${CRYPTO_SOURCES[@]}"
link_shared libcrypto.so -L"$OUT" -lbionic_compat -lc -ldl -lpthread

echo "=== libandroidio.so ==="
compile_group androidio \
    "-include $SOCKET_FIX -I$AOSP/libnativehelper/include -I$AOSP/libnativehelper/include_platform -I$AOSP/libcore/luni/src/main/native -I$AOSP/system/logging/liblog/include -DANDROID_HOST_MUSL" \
    "$AOSP/libcore/luni/src/main/native/AsynchronousCloseMonitor.cpp"
link_shared libandroidio.so -L"$OUT" -llog -lc -ldl -lpthread

echo "=== libicu_jni.so ==="
mapfile -t ICU_JNI_SOURCES < <(find \
    "$AOSP/external/icu/android_icu4j/libcore_bridge/src/native" \
    -maxdepth 1 -type f -name '*.cpp' ! -name '*test*' | LC_ALL=C sort)
compile_group icu_jni \
    "-DU_USING_ICU_NAMESPACE=0 -DANDROID_LINK_SHARED_ICU4C -I$AOSP/external/icu/icu4c/source/common -I$AOSP/external/icu/icu4c/source/i18n -I$AOSP/libnativehelper/include_jni -I$AOSP/libnativehelper/include -I$AOSP/libnativehelper/include_platform_header_only -I$AOSP/libnativehelper/header_only_include -I$AOSP/system/libbase/include -I$AOSP/system/logging/liblog/include" \
    "${ICU_JNI_SOURCES[@]}"
link_shared libicu_jni.so -L"$OUT" -lnativehelper -licuuc -licui18n \
    -lbase -llog -lbionic_compat -lc -ldl -lpthread

echo "=== libjavacore.so ==="
mapfile -t JAVACORE_SOURCES < <(find "$AOSP/libcore/luni/src/main/native" \
    -maxdepth 1 -type f -name '*.cpp' | LC_ALL=C sort)
compile_group javacore \
    "-include $SOCKET_FIX -I$AOSP/libnativehelper/include -I$AOSP/libnativehelper/include_platform -I$AOSP/libnativehelper/include_jni -I$AOSP/libnativehelper/header_only_include -I$AOSP/libnativehelper/include_platform_header_only -I$AOSP/libcore/luni/src/main/native -I$AOSP/external/icu/icu4c/source/common -I$AOSP/external/icu/icu4c/source/i18n -I$AOSP/external/expat/lib -I$AOSP/external/zlib -I$BORINGSSL/src/include -I$AOSP/system/libbase/include -I$AOSP/system/logging/liblog/include -I$AOSP/system/core/include -DU_USING_ICU_NAMESPACE=0 -DHAVE_EXPAT_CONFIG_H -DANDROID_HOST_MUSL" \
    "${JAVACORE_SOURCES[@]}"
link_shared libjavacore.so -L"$OUT" -lnativehelper -landroidio \
    -licuuc -licui18n -lcrypto -lexpat -llog -lbase \
    -L"$OH_PSDK" -l:libz.so -lc -ldl -lpthread

echo "=== libopenjdkjvm.so ==="
compile_group openjdkjvm \
    "-include $SOCKET_FIX -DART_TARGET -DART_TARGET_LINUX -DNDEBUG -DANDROID_HOST_MUSL -DART_BASE_ADDRESS=0x70000000 -DART_DEFAULT_GC_TYPE_IS_CMS -DART_FRAME_SIZE_LIMIT=1736 -DIMT_SIZE=43 -DART_STACK_OVERFLOW_GAP_arm=8192 -DART_STACK_OVERFLOW_GAP_arm64=8192 -DART_STACK_OVERFLOW_GAP_riscv64=8192 -DART_STACK_OVERFLOW_GAP_x86=8192 -DART_STACK_OVERFLOW_GAP_x86_64=8192 -I$AOSP/art/libdexfile -I$AOSP/art/libartpalette/include -I$AOSP/art/libdexfile/external/include -I$AOSP/libnativehelper/include -I$AOSP/libnativehelper/include_jni -I$AOSP/libnativehelper/header_only_include -I$AOSP/libnativehelper/include_platform_header_only -I$AOSP/system/libbase/include -I$AOSP/system/logging/liblog/include -I$AOSP/art/runtime -I$AOSP/art/libartbase -I$AOSP/external/tinyxml2" \
    "$AOSP/art/openjdkjvm/OpenjdkJvm.cc"
link_shared libopenjdkjvm.so -L"$OUT" -lart -lartbase -llog -lbase -lc -ldl -lpthread

echo "=== libopenjdk.so ==="
FDLIBM=$AOSP/external/fdlibm
mapfile -t FDLIBM_SOURCES < <("$PYTHON" - "$FDLIBM/Android.bp" "$FDLIBM" <<'PY'
import re
import sys

blueprint, root = sys.argv[1:]
text = open(blueprint, encoding="utf-8").read()
module = re.search(r'cc_library_static\s*\{.*?name:\s*"libfdlibm"(.*?)\n\}', text, re.DOTALL)
if module is None:
    raise SystemExit("libfdlibm module not found")
srcs = re.search(r'srcs:\s*\[(.*?)\]', module.group(1), re.DOTALL)
if srcs is None:
    raise SystemExit("libfdlibm srcs not found")
for source in re.findall(r'"([^"]+\.c)"', srcs.group(1)):
    print(f"{root}/{source}")
PY
)
[ "${#FDLIBM_SOURCES[@]}" -eq 80 ] || {
    echo "libfdlibm source count mismatch: ${#FDLIBM_SOURCES[@]}" >&2
    exit 1
}
compile_group fdlibm \
    "-std=c99 -D_IEEE_LIBM -fno-strict-aliasing -Werror -Wno-sign-compare -Wno-dangling-else -Wno-unknown-pragmas -Wno-logical-op-parentheses -Wno-sometimes-uninitialized -I$FDLIBM" \
    "${FDLIBM_SOURCES[@]}"
FDLIBM_OBJECTS=("${COMPILED_OBJECTS[@]}")
FDLIBM_ARCHIVE=$OUT/libfdlibm.a
rm -f "$FDLIBM_ARCHIVE"
"$AR" rcsD "$FDLIBM_ARCHIVE" "${FDLIBM_OBJECTS[@]}"
test "$("$AR" t "$FDLIBM_ARCHIVE" | wc -l | tr -d ' ')" -eq 80
"$NM" --defined-only "$FDLIBM_ARCHIVE" | grep -Eq '[[:space:]]ieee_cos$'
"$NM" --defined-only "$FDLIBM_ARCHIVE" | grep -Eq '[[:space:]]ieee_sin$'
"$NM" --defined-only "$FDLIBM_ARCHIVE" | grep -Eq '[[:space:]]ieee_tan$'
echo "BUILT libfdlibm.a objects=80 sha256=$(sha256sum "$FDLIBM_ARCHIVE" | awk '{print $1}')"

mapfile -t OPENJDK_C < <(find "$AOSP/libcore/ojluni/src/main/native" \
    -maxdepth 1 -type f -name '*.c' | LC_ALL=C sort)
mapfile -t OPENJDK_CXX < <(find "$AOSP/libcore/ojluni/src/main/native" \
    -maxdepth 1 -type f -name '*.cpp' | LC_ALL=C sort)
compile_group openjdk \
    "-include $SOCKET_FIX -I$AOSP/libcore/luni/src/main/native -I$AOSP/libcore/ojluni/src/main/native -I$AOSP/libnativehelper/include_platform_header_only -I$AOSP/libnativehelper/include_jni -I$AOSP/libnativehelper/include -I$AOSP/libnativehelper/include_platform -I$AOSP/libnativehelper/header_only_include -I$AOSP/system/libbase/include -I$AOSP/system/logging/liblog/include -I$AOSP/external/zlib -I$BORINGSSL/src/include -I$AOSP/external/icu/icu4c/source/common -I$AOSP/external/icu/icu4c/source/i18n -I$AOSP/system/core/include -DU_USING_ICU_NAMESPACE=0 -DANDROID_HOST_MUSL -Wno-unused-variable -Wno-parentheses-equality -Wno-constant-logical-operand -Wno-sometimes-uninitialized -Wno-implicit-function-declaration" \
    "${OPENJDK_C[@]}" "${OPENJDK_CXX[@]}"
link_shared libopenjdk.so "$FDLIBM_ARCHIVE" -L"$OUT" -ljavacore -lopenjdkjvm \
    -lnativehelper -lcrypto -licuuc -licui18n -llog -lbase \
    -L"$OH_PSDK" -l:libz.so -lm -lc -ldl -lpthread

required=(libexpat.so libcrypto.so libandroidio.so libicu_jni.so libjavacore.so libopenjdkjvm.so libopenjdk.so)
for library in "${required[@]}"; do
    file=$OUT/$library
    test -f "$file" && test ! -L "$file"
    if [ "$STRICT_BUILD" = 1 ]; then
        "$READELF" -n --wide "$file" | grep -q 'Build ID:'
        "$READELF" -d --wide "$file" | grep -q "Library soname: \[$library\]"
        ! "$READELF" -d --wide "$file" | grep -Eq '\((RPATH|RUNPATH|TEXTREL)\)'
    fi
done
echo "STRICT_EXTRAS_PASS outputs=${required[*]}"
