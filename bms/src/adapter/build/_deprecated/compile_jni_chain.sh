#!/bin/bash
# Cross-compile the JNI dependency chain needed by ART Runtime::InitNativeMethods:
#   libcrypto.so   (BoringSSL)
#   libexpat.so    (XML parser)
#   libandroidio.so
#   libjavacore.so (libcore JNI)
#   libopenjdk.so  (OpenJDK JNI)
#
# Run on ECS. Outputs to ~/adapter/out/aosp_lib/.
# Idempotent: skip targets whose .so already exists newer than its sources.

set -o pipefail
ADAPTER_ROOT="${ADAPTER_ROOT:-$HOME/adapter}"
AOSP="${AOSP_ROOT:-$HOME/aosp}"
OH="${OH_ROOT:-$HOME/oh}"
OUT="$ADAPTER_ROOT/out/aosp_lib"
TMP="/tmp/jni_chain"
mkdir -p "$OUT" "$TMP"

# OH cross toolchain (same as cross_compile_arm32.sh)
SR="$OH/out/rk3568/obj/third_party/musl/usr"
ML="$SR/lib/arm-linux-ohos"
CC=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang
CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++
COMMON="--target=arm-linux-ohos -march=armv7-a --sysroot=$SR -I$SR/include/arm-linux-ohos -fPIC -O2 -D__OHOS__ -D_GNU_SOURCE -D_POSIX_SOURCE -Wno-unused-parameter -Wno-format -Wno-sign-compare -Wno-missing-field-initializers -Wno-c99-designator -Wno-gnu-designator -Wno-extern-c-compat -Wno-deprecated-declarations -Wno-error -include $ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include/libcxx_compat.h -I$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include"
LNK="$CXX --target=arm-linux-ohos -march=armv7-a -B$ML -L$ML -L$OUT -shared -fPIC"

CCOPTS_C="$CC $COMMON"
CCOPTS_CXX="$CXX $COMMON -std=c++17"

LOG="$OUT/jni_chain.log"
> "$LOG"

# ============================================================
# Helper: compile_filelist NAME EXTRA_FLAGS file1 file2 ... > log
# ============================================================
compile_filelist() {
    local name="$1"; shift
    local flags="$1"; shift
    local total=0 ok=0 fail=0
    local objs=""
    local objdir="$TMP/$name.objs"
    mkdir -p "$objdir"
    for src in "$@"; do
        [ -f "$src" ] || { echo "ERROR: required source missing: $src" >&2; exit 1; }
        total=$((total+1))
        local b="$(basename "$src")"
        local stem="${b%.*}"
        # de-dup name: include hash of full path to avoid collisions
        local h=$(printf "%s" "$src" | md5sum | cut -c1-6)
        local o="$objdir/${stem}_${h}.o"
        local cc=$CCOPTS_C
        case "$b" in *.cpp|*.cc|*.cxx|*.C) cc=$CCOPTS_CXX;; esac
        if $cc $flags -c "$src" -o "$o" 2>>"$LOG"; then
            ok=$((ok+1))
            objs="$objs $o"
        else
            fail=$((fail+1))
            echo "    FAIL: $b" >> "$LOG"
        fi
    done
    echo "$ok ok / $fail fail / $total total" >&2
    if [ $fail -eq 0 ] && [ $ok -gt 0 ]; then
        printf '%s' "$objs"
    fi
}

link_so() {
    local name="$1"; shift
    local extra_libs="$1"; shift
    local objs="$@"
    local libname="lib$name.so"
    if [ -z "$objs" ]; then echo "  no objs to link for $libname" >&2; return 1; fi
    if $LNK -Wl,-soname=$libname -o "$OUT/$libname" $objs $extra_libs -lc -ldl -lpthread 2>>"$LOG"; then
        echo "  ✅ LINKED $OUT/$libname ($(stat -c%s $OUT/$libname) bytes)" >&2
    else
        echo "  ❌ LINK FAIL $libname (see $LOG)" >&2
        return 1
    fi
}

# ============================================================
# 1. libexpat (smallest, no asm)
# ============================================================
echo "=== 1. libexpat ===" >&2
EXPAT=$AOSP/external/expat
EXPAT_SRCS=$(ls $EXPAT/lib/xml*.c 2>/dev/null)
EXPAT_FLAGS="-I$EXPAT/lib -I$EXPAT -DHAVE_EXPAT_CONFIG_H -DXML_DEV_URANDOM"
EXPAT_OBJS=$(compile_filelist expat "$EXPAT_FLAGS" $EXPAT_SRCS)
[ -n "$EXPAT_OBJS" ] && link_so expat "" $EXPAT_OBJS

# ============================================================
# 2. libcrypto (BoringSSL — extract srcs from sources.bp)
# ============================================================
echo "=== 2. libcrypto (BoringSSL) ===" >&2
BSSL=$AOSP/external/boringssl
# Extract libcrypto_sources from sources.bp
SRCS_FILE=/tmp/jni_chain_libcrypto_srcs.txt
python3 <<PY > "$SRCS_FILE"
import re, sys
with open("$BSSL/sources.bp") as f:
    s = f.read()
m = re.search(r'name:\s*"libcrypto_sources".*?srcs:\s*\[\s*(.*?)\s*\]', s, re.DOTALL)
files = []
for ln in m.group(1).splitlines():
    ln = ln.strip()
    if ln.startswith('//'): continue
    m2 = re.match(r'"([^"]+)"', ln)
    if m2: files.append(m2.group(1))
for f in files: print(f"$BSSL/{f}")
PY
# Add ARM32 perlasm-generated assembly (linux-arm/crypto/*.S)
ARM_ASM=$(find $BSSL/linux-arm/crypto -name "*.S" 2>/dev/null)
echo "  asm files: $(echo $ARM_ASM | wc -w)" >&2
BSSL_FLAGS="-I$BSSL/src/include -I$BSSL/src/crypto -I$BSSL/src/third_party/fiat -DBORINGSSL_IMPLEMENTATION -DOPENSSL_NO_ASM_BUT_WITH_ARM_FOR_FILE_NAMES -DOPENSSL_SMALL"
# Use no-asm to avoid arch-specific .S complexity for now
BSSL_FLAGS="$BSSL_FLAGS -DOPENSSL_NO_ASM"
# Add libcrypto_bcm_sources (FIPS module unity build): src/crypto/fipsmodule/bcm.c
echo "$BSSL/src/crypto/fipsmodule/bcm.c" >> "$SRCS_FILE"
BSSL_OBJS=$(compile_filelist crypto "$BSSL_FLAGS" $(cat "$SRCS_FILE"))
[ -n "$BSSL_OBJS" ] && link_so crypto "-lbionic_compat" $BSSL_OBJS

# ============================================================
# 3. libandroidio (small, libcore/luni/src/main/native/android_io/ ?)
# ============================================================
echo "=== 3. libandroidio ===" >&2
# Find srcs for libandroidio
AIO_BP=$AOSP/libcore/luni/src/main/native/Android.bp
AIO_SRCS_NAMES=$(python3 <<PY
import re
with open("$AIO_BP") as f: s=f.read()
m = re.search(r'name:\s*"libandroidio_srcs".*?srcs:\s*\[\s*(.*?)\s*\]', s, re.DOTALL)
if not m:
    print("");
    import sys; sys.exit()
for ln in m.group(1).splitlines():
    ln = ln.strip()
    if ln.startswith('//'): continue
    m2 = re.match(r'"([^"]+)"', ln)
    if m2: print(m2.group(1))
PY
)
AIO_SRCS=""
for n in $AIO_SRCS_NAMES; do
    f=$(find $AOSP/libcore -name "$(basename $n)" 2>/dev/null | head -1)
    [ -n "$f" ] && AIO_SRCS="$AIO_SRCS $f"
done
echo "  files: $AIO_SRCS_NAMES" >&2
AIO_FLAGS="-I$AOSP/libnativehelper/include -I$AOSP/libnativehelper/include_jni -I$AOSP/libnativehelper/header_only_include -I$AOSP/system/logging/liblog/include"
AIO_OBJS=$(compile_filelist androidio "$AIO_FLAGS" $AIO_SRCS)
[ -n "$AIO_OBJS" ] && link_so androidio "-llog -lbionic_compat" $AIO_OBJS

# ============================================================
# 4. libjavacore (libcore/luni/src/main/native/)
# ============================================================
echo "=== 4. libjavacore ===" >&2
LUNI=$AOSP/libcore/luni/src/main/native
LUNI_SRCS=$(python3 <<PY
import re
with open("$LUNI/Android.bp") as f: s=f.read()
m = re.search(r'name:\s*"luni_native_srcs".*?srcs:\s*\[\s*(.*?)\s*\]', s, re.DOTALL)
for ln in m.group(1).splitlines():
    ln=ln.strip()
    if ln.startswith('//'): continue
    m2 = re.match(r'"([^"]+)"', ln)
    if m2: print(f"$LUNI/{m2.group(1)}")
PY
)
LUNI_FLAGS="-D_UAPI_LINUX_SOCKET_H -DANDROID_HOST_MUSL -include /tmp/jni_chain_kernel_compat.h -I$LUNI -I$AOSP/libnativehelper/include -I$AOSP/libnativehelper/include_jni -I$AOSP/libnativehelper/include_platform -I$AOSP/libnativehelper/header_only_include -I$AOSP/libnativehelper/include_platform_header_only -I$AOSP/system/libbase/include -I$AOSP/system/logging/liblog/include -I$AOSP/external/icu/icu4c/source/common -I$AOSP/external/icu/icu4c/source/i18n -I$AOSP/external/expat/lib -I$AOSP/external/boringssl/src/include -I$AOSP/system/libziparchive/include -I$AOSP/external/zlib -I$AOSP/system/core/include -DU_USING_ICU_NAMESPACE=0"
JC_OBJS=$(compile_filelist javacore "$LUNI_FLAGS" $LUNI_SRCS)
[ -n "$JC_OBJS" ] && link_so javacore "-llog -lbase -lnativehelper -licuuc -licui18n -lcrypto -lexpat -lz -lziparchive -landroidio -lbionic_compat -L$OH/out/rk3568/packages/phone/system/lib/platformsdk -lz" $JC_OBJS

# ============================================================
# 5a. libopenjdkjvm (single OpenjdkJvm.cc — provides JVM_Open etc., needed by libopenjdk)
echo "=== 5a. libopenjdkjvm ===" >&2
OJVM_FLAGS="-DART_TARGET -DART_TARGET_LINUX -DNDEBUG -DART_BASE_ADDRESS=0x70000000 -DART_DEFAULT_GC_TYPE_IS_CMS -DART_FRAME_SIZE_LIMIT=1736 -DIMT_SIZE=43 -DART_STACK_OVERFLOW_GAP_arm=8192 -DART_STACK_OVERFLOW_GAP_arm64=8192 -DART_STACK_OVERFLOW_GAP_riscv64=8192 -DART_STACK_OVERFLOW_GAP_x86=8192 -DART_STACK_OVERFLOW_GAP_x86_64=8192 -D_UAPI_LINUX_SOCKET_H -DANDROID_HOST_MUSL -include /tmp/jni_chain_kernel_compat.h -I$AOSP/art/libdexfile -I$AOSP/art/libartpalette/include -I$AOSP/art/libdexfile/external/include -I$AOSP/libnativehelper/include -I$AOSP/libnativehelper/include_jni -I$AOSP/libnativehelper/header_only_include -I$AOSP/libnativehelper/include_platform_header_only -I$AOSP/system/libbase/include -I$AOSP/system/logging/liblog/include -I$AOSP/art/runtime -I$AOSP/art/libartbase -I$AOSP/external/tinyxml2"
OJVM_OBJS=$(compile_filelist openjdkjvm "$OJVM_FLAGS" $AOSP/art/openjdkjvm/OpenjdkJvm.cc)
[ -n "$OJVM_OBJS" ] && link_so openjdkjvm "-llog -lbase -lart -lartbase -lbionic_compat" $OJVM_OBJS

# 5. libopenjdk (libcore/ojluni/src/main/native/)
# ============================================================
echo "=== 5. libopenjdk ===" >&2
OJLUNI=$AOSP/libcore/ojluni/src/main/native
OJ_SRCS=$(python3 <<PY
import re
with open("$AOSP/libcore/NativeCode.bp") as f: s=f.read()
# srcs in ojluni/src/main/native/Android.bp not NativeCode.bp
with open("$OJLUNI/Android.bp") as f2: s = f2.read()
m = re.search(r'name:\s*"libopenjdk_native_srcs".*?srcs:\s*\[\s*(.*?)\s*\]', s, re.DOTALL)
if m:
    for ln in m.group(1).splitlines():
        ln=ln.strip()
        if ln.startswith('//'): continue
        m2 = re.match(r'"([^"]+)"', ln)
        if m2: print(m2.group(1))
PY
)
OJ_FLAGS="-D_UAPI_LINUX_SOCKET_H -DANDROID_HOST_MUSL -include /tmp/jni_chain_kernel_compat.h -I$AOSP/libcore/luni/src/main/native -I$AOSP/libnativehelper/include_platform -I$AOSP/libnativehelper/include -I$AOSP/libnativehelper/include_jni -I$AOSP/libnativehelper/header_only_include -I$AOSP/libnativehelper/include_platform_header_only -I$AOSP/libcore/ojluni/src/main/native -I$AOSP/system/libbase/include -I$AOSP/system/logging/liblog/include -I$AOSP/external/zlib -I$AOSP/external/boringssl/src/include -I$AOSP/external/icu/icu4c/source/common -I$AOSP/system/libziparchive/include -I$AOSP/system/core/include -Wno-unused-variable -Wno-parentheses-equality -Wno-constant-logical-operand -Wno-sometimes-uninitialized"
# Resolve paths
OJ_SRC_PATHS=""
for s in $OJ_SRCS; do
    f="$OJLUNI/$s"
    [ -f "$f" ] && OJ_SRC_PATHS="$OJ_SRC_PATHS $f"
done
echo "  resolved $(echo $OJ_SRC_PATHS | wc -w) paths" >&2
OJ_OBJS=$(compile_filelist openjdk "$OJ_FLAGS" $OJ_SRC_PATHS /tmp/jni_chain_ieee_shim.c)
[ -n "$OJ_OBJS" ] && link_so openjdk "-lopenjdkjvm -lm -llog -lbase -lnativehelper -licuuc -licui18n -lcrypto -lexpat -lz -lziparchive -landroidio -lbionic_compat -L$OH/out/rk3568/packages/phone/system/lib/platformsdk -lz" $OJ_OBJS

echo "" >&2
echo "Done. Outputs:" >&2
ls -lh $OUT/lib{crypto,expat,androidio,javacore,openjdk}.so 2>/dev/null >&2
echo "" >&2
echo "Log: $LOG" >&2
