#!/bin/bash
# Cross-compile ALL layers to 100% using OH Clang
# Usage: cross_compile_100pct.sh [--oh-root=PATH] [--aosp-root=PATH] [--verbose]
#
# Override paths via env vars or arguments:
#   OH_ROOT=/path/to/oh AOSP_ROOT=/path/to/aosp ./cross_compile_100pct.sh
set -o pipefail

# Parse args
VERBOSE=0
for arg in "$@"; do
    case "$arg" in
        --oh-root=*) OH_ROOT="${arg#*=}";;
        --aosp-root=*) AOSP_ROOT="${arg#*=}";;
        --verbose) VERBOSE=1;;
    esac
done

OH="${OH_ROOT:-$HOME/oh}"
A="${AOSP_ROOT:-$HOME/aosp}"
ADAPTER_ROOT="${ADAPTER_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
# NOTE 2026-04-11: this script outputs to out/native (not out/aosp_lib/),
# which conflicts with feedback_aosp_lib_dir.md. Separate cleanup needed.
O="$ADAPTER_ROOT/out/native"
ERRLOG="$ADAPTER_ROOT/out/native/build_errors.log"

CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++
CC=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang
AS=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang
READELF=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf

# OH output dir — rk3568 (DAYU200, current target).
# If rebuilding for a different product, pass --oh-root or set
# OH_PRODUCT_NAME via env.
if [ -d "$OH/out/rk3568" ]; then
    OH_OUT="$OH/out/rk3568"
else
    echo "ERROR: $OH/out/rk3568 not found. Run OH build first (--product-name rk3568)."
    exit 1
fi

SR=$OH_OUT/obj/third_party/musl/usr
ML=$SR/lib/aarch64-linux-ohos
BC=$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include
BC_SRC=$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/src

# NOTE: Do NOT add -isystem for clang builtin include (causes cstdlib abs conflict).
# Instead, nullptr_t is defined in libcxx_compat.h which is force-included.
COMMON="--target=aarch64-linux-ohos --sysroot=$SR -I$SR/include/aarch64-linux-ohos -fPIC -O2 -D__OHOS__ -D_GNU_SOURCE -D_POSIX_SOURCE -Wno-unused-parameter -Wno-format -Wno-sign-compare -Wno-missing-field-initializers -Wno-c99-designator -Wno-gnu-designator -Wno-extern-c-compat -Wno-deprecated-declarations -include $BC/libcxx_compat.h -I$BC"
CXXF="$CXX $COMMON -std=c++17"
CF="$CC $COMMON -std=c11"
ASF="$AS --target=aarch64-linux-ohos -fPIC"
LNK="$CXX --target=aarch64-linux-ohos -B$ML -L$ML -L$O -shared -fPIC"

ART_DEFS="-DANDROID_HOST_MUSL -DART_STACK_OVERFLOW_GAP_arm=8192 -DART_STACK_OVERFLOW_GAP_arm64=8192 -DART_STACK_OVERFLOW_GAP_riscv64=8192 -DART_STACK_OVERFLOW_GAP_x86=8192 -DART_STACK_OVERFLOW_GAP_x86_64=8192 -DART_TARGET -DART_TARGET_LINUX -DART_BASE_ADDRESS=0x70000000 -DART_DEFAULT_GC_TYPE_IS_CMS -DIMT_SIZE=43"
ART_INC="-I$A/art -I$A/art/libdexfile -I$A/art/libartbase -I$A/art/runtime -I$A/art/libartpalette/include -I$A/art/libdexfile/external/include -I$A/art/libprofile -I$A/libnativehelper/include_jni -I$A/libnativehelper/include -I$A/libnativehelper/header_only_include -I$A/system/logging/liblog/include -I$A/system/libbase/include -I$A/system/core/include -I$A/system/core/libcutils/include -I$A/system/core/libutils/include -I$A/external/fmtlib/include -I$A/external/lz4/lib -I$A/external/zlib -I$A/system/libziparchive/include -I$A/external/vixl/src -I$A/frameworks/native/include -I$A/external/tinyxml2 -I$A/system/unwinding/libunwindstack/include -I$A/system/unwinding/libbacktrace/include -I$BC/art"

mkdir -p $O
REPORT=""
> "$ERRLOG"

# ============================================================
# Build function: compile sources -> link shared library
# ============================================================
bld() {
    local N=$1 I=$2; shift 2
    local D=/tmp/cc100/$N; mkdir -p $D
    local ok=0 fl=0 fails=""
    for s in "$@"; do
        local b=$(basename $s); b=${b%.*}; local ext=${s##*.}
        local comp=$CXXF; [ "$ext" = "c" ] && comp=$CF; [ "$ext" = "S" ] && comp="$ASF"
        if $comp $I -c -o $D/$b.o $s 2>/tmp/cc100/${N}_${b}.err; then
            ok=$((ok+1))
        else
            fl=$((fl+1))
            fails="$fails $b"
            echo "=== FAIL: $N/$b ===" >> "$ERRLOG"
            grep -m3 'error:' /tmp/cc100/${N}_${b}.err >> "$ERRLOG" 2>/dev/null || head -8 /tmp/cc100/${N}_${b}.err >> "$ERRLOG"
            echo "" >> "$ERRLOG"
            if [ $VERBOSE -eq 1 ]; then
                echo "    FAIL: $b"
                head -3 /tmp/cc100/${N}_${b}.err | sed 's/^/      /'
            fi
        fi
    done
    local total=$((ok+fl))
    local OB=$(ls $D/*.o 2>/dev/null | tr "\n" " ")
    if [ -z "$OB" ]; then
        echo "  ❌ lib$N: 0/$total (no objects)"
        REPORT="$REPORT\n  ❌ lib$N: 0/$total (no objects)"
        return 1
    fi

    # Try strict link first, then fallback with unresolved symbols
    local link_mode="strict"
    if ! $LNK -o $O/lib$N.so $OB -lc -lbionic_compat -ldl -lpthread 2>/tmp/cc100/${N}_link.err; then
        link_mode="relaxed"
        if ! $LNK -o $O/lib$N.so $OB -lc -lbionic_compat -ldl -lpthread \
            -Wl,--unresolved-symbols=ignore-in-shared-libs 2>/tmp/cc100/${N}_link2.err; then
            echo "  ❌ lib$N: $ok/$total (link failed)"
            REPORT="$REPORT\n  ❌ lib$N: $ok/$total (link failed)"
            echo "=== LINK FAIL: $N ===" >> "$ERRLOG"
            cat /tmp/cc100/${N}_link2.err >> "$ERRLOG"
            return 1
        fi
    fi

    local sz=$(ls -lh $O/lib$N.so 2>/dev/null | awk '{print $5}')

    # Count unresolved symbols
    local undef_count=0
    if [ "$link_mode" = "relaxed" ]; then
        undef_count=$($READELF --dyn-syms $O/lib$N.so 2>/dev/null | grep "UND" | grep -v "WEAK\|GLOBAL.*UND.*\(GLIBC\|dl\)" | wc -l)
    fi

    if [ $fl -eq 0 ] && [ "$link_mode" = "strict" ]; then
        echo "  ✅ lib$N: $ok/$total ($sz)"
        REPORT="$REPORT\n  ✅ lib$N: $ok/$total ($sz)"
    elif [ $fl -eq 0 ]; then
        echo "  ✅ lib$N: $ok/$total ($sz) [link: relaxed, undef: ~$undef_count]"
        REPORT="$REPORT\n  ✅ lib$N: $ok/$total ($sz) [link: relaxed, undef: ~$undef_count]"
    else
        echo "  ⚠️  lib$N: $ok/$total ($sz) [FAIL:$fails] [link: $link_mode]"
        REPORT="$REPORT\n  ⚠️  lib$N: $ok/$total ($sz) [FAIL:$fails] [link: $link_mode]"
    fi
}

rm -rf /tmp/cc100 && mkdir -p /tmp/cc100
echo "=========================================="
echo "  Full Cross-Compilation (target: 100%)"
echo "  OH Clang: $(basename $(dirname $(dirname $CXX)))"
echo "  Target: aarch64-linux-ohos (musl)"
echo "  Output: $O"
echo "=========================================="

# ============================================================
# Layer 1: bionic_compat
# ============================================================
echo ""
echo "--- Layer 1: bionic_compat ---"
bld bionic_compat "-I$OH/base/startup/init/interfaces/innerkits/include/syspara -DPARAM_VALUE_LEN_MAX=96 -nostdinc++ -Wno-constant-conversion" \
    $BC_SRC/system_properties.cpp $BC_SRC/malloc_compat.cpp $BC_SRC/fdsan_stubs.cpp $BC_SRC/misc_compat.cpp

# ============================================================
# Layer 1.5: ART runtime stubs (nativeloader, nativebridge, etc.)
# ============================================================
echo ""
echo "--- Layer 1.5: ART runtime stubs ---"
bld art_runtime_stubs "" \
    $BC_SRC/art_runtime_stubs.cpp

# ============================================================
# Layer 2: AOSP base libraries
# ============================================================
echo ""
echo "--- Layer 2: AOSP base libs ---"
bld log "-I$A/system/logging/liblog/include -I$A/system/libbase/include -I$A/system/core/libcutils/include -I$A/system/core/include -DLIBLOG_LOG_TAG=1006 -DSNET_EVENT_LOG_TAG=1397638484" \
    $A/system/logging/liblog/log_event_list.cpp $A/system/logging/liblog/log_event_write.cpp $A/system/logging/liblog/logger_name.cpp $A/system/logging/liblog/logger_read.cpp $A/system/logging/liblog/logger_write.cpp $A/system/logging/liblog/logprint.cpp $A/system/logging/liblog/properties.cpp $A/system/logging/liblog/event_tag_map.cpp $A/system/logging/liblog/log_time.cpp

bld base "-I$A/system/libbase/include -I$A/system/logging/liblog/include -I$A/system/core/include -I$A/system/core/libcutils/include -I$A/external/fmtlib/include -DANDROID_BASE_UNIQUE_FD_DISABLE_FDSAN" \
    $A/system/libbase/abi_compatibility.cpp $A/system/libbase/chrono_utils.cpp $A/system/libbase/cmsg.cpp $A/system/libbase/errors_unix.cpp $A/system/libbase/file.cpp $A/system/libbase/hex.cpp $A/system/libbase/logging.cpp $A/system/libbase/mapped_file.cpp $A/system/libbase/parsebool.cpp $A/system/libbase/parsenetaddress.cpp $A/system/libbase/posix_strerror_r.cpp $A/system/libbase/process.cpp $A/system/libbase/properties.cpp $A/system/libbase/stringprintf.cpp $A/system/libbase/strings.cpp $A/system/libbase/threads.cpp

bld cutils "-I$A/system/core/libcutils/include -I$A/system/logging/liblog/include -I$A/system/libbase/include -I$A/system/core/include -I$A/external/fmtlib/include" \
    $A/system/core/libcutils/config_utils.cpp $A/system/core/libcutils/hashmap.cpp $A/system/core/libcutils/iosched_policy.cpp $A/system/core/libcutils/load_file.cpp $A/system/core/libcutils/native_handle.cpp $A/system/core/libcutils/properties.cpp $A/system/core/libcutils/record_stream.cpp $A/system/core/libcutils/socket_inaddr_any_server_unix.cpp $A/system/core/libcutils/socket_local_client_unix.cpp $A/system/core/libcutils/socket_local_server_unix.cpp $A/system/core/libcutils/socket_network_client_unix.cpp $A/system/core/libcutils/sockets_unix.cpp $A/system/core/libcutils/sockets.cpp $A/system/core/libcutils/str_parms.cpp $A/system/core/libcutils/threads.cpp

bld utils "-I$A/system/core/libutils/include -I$A/system/core/libcutils/include -I$A/system/logging/liblog/include -I$A/system/libbase/include -I$A/system/core/include -I$A/system/core/libprocessgroup/include -I$A/system/core/libvndksupport/include -I$A/external/fmtlib/include" \
    $A/system/core/libutils/Errors.cpp $A/system/core/libutils/FileMap.cpp $A/system/core/libutils/JenkinsHash.cpp $A/system/core/libutils/LightRefBase.cpp $A/system/core/libutils/Looper.cpp $A/system/core/libutils/NativeHandle.cpp $A/system/core/libutils/Printer.cpp $A/system/core/libutils/RefBase.cpp $A/system/core/libutils/SharedBuffer.cpp $A/system/core/libutils/StopWatch.cpp $A/system/core/libutils/String8.cpp $A/system/core/libutils/String16.cpp $A/system/core/libutils/StrongPointer.cpp $A/system/core/libutils/SystemClock.cpp $A/system/core/libutils/Threads.cpp $A/system/core/libutils/Timers.cpp $A/system/core/libutils/Tokenizer.cpp $A/system/core/libutils/Unicode.cpp $A/system/core/libutils/VectorImpl.cpp

bld nativehelper "-I$A/libnativehelper/include -I$A/libnativehelper/include_jni -I$A/libnativehelper/header_only_include -I$A/system/logging/liblog/include -I$A/system/libbase/include -I$A/system/core/include" \
    $A/libnativehelper/JNIHelp.c $A/libnativehelper/JniInvocation.c $A/libnativehelper/JniConstants.c $A/libnativehelper/JNIPlatformHelp.c

# ============================================================
# Layer 3: ART sub-libraries
# ============================================================
echo ""
echo "--- Layer 3: ART sub-libraries ---"
bld sigchain "$ART_DEFS $ART_INC -fno-rtti" $A/art/sigchainlib/sigchain.cc

bld dexfile "$ART_DEFS $ART_INC -fno-rtti" $(ls $A/art/libdexfile/dex/*.cc | grep -v test)

bld artbase "$ART_DEFS $ART_INC -fno-rtti" $(ls $A/art/libartbase/base/*.cc | grep -v test | grep -v windows | grep -v fuchsia)

bld artpalette "$ART_DEFS $ART_INC -fno-rtti" $A/art/libartpalette/apex/palette.cc

# ============================================================
# Layer 3: ART Runtime (largest component)
# ============================================================
echo ""
echo "--- Layer 3: ART Runtime ---"

# Collect runtime .cc files (exclude tests, non-arm64 arch, android-specific)
RUNTIME_FILES=$(find $A/art/runtime -name "*.cc" \
    -not -name "*test*" -not -path "*/test/*" -not -name "*gtest*" \
    -not -name "*_android.cc" \
    -not -path "*/arch/arm/*" -not -path "*/arch/x86/*" \
    -not -path "*/arch/x86_64/*" -not -path "*/arch/riscv64/*" \
    | sort)

# Count source files
RUNTIME_COUNT=$(echo "$RUNTIME_FILES" | wc -l)
echo "  Runtime source files: $RUNTIME_COUNT .cc files + ARM64 assembly stubs"

# Compile ARM64 assembly entrypoints from our stubs
ASM_STUBS="$BC_SRC/art_quick_entrypoints_arm64.S"

# Also include AOSP's arch/arm64 .cc files (C++ arch-specific code, NOT the .S files)
ARM64_CC=$(find $A/art/runtime/arch/arm64 -name "*.cc" -not -name "*test*" 2>/dev/null | sort)

bld art "$ART_DEFS $ART_INC -fno-rtti -I$BC_SRC" \
    $RUNTIME_FILES $ARM64_CC $ASM_STUBS $BC_SRC/art_runtime_stubs.cpp

# ============================================================
# Layer 3: VIXL (ARM assembler used by ART JIT)
# ============================================================
echo ""
echo "--- Layer 3: VIXL (ARM assembler) ---"
VIXL_DIR=$A/external/vixl/src
if [ -d "$VIXL_DIR" ]; then
    VIXL_FILES=$(find $VIXL_DIR -name "*.cc" \
        -not -name "*test*" -not -path "*/test/*" \
        -not -name "*example*" -not -name "*bench*" \
        | sort)
    bld vixl "-I$A/external/vixl/src" $VIXL_FILES
else
    echo "  SKIP: VIXL not found at $VIXL_DIR"
fi

# ============================================================
# Layer 3: LZ4 compression (used by ART for oat files)
# ============================================================
echo ""
echo "--- Layer 3: LZ4 ---"
LZ4_DIR=$A/external/lz4/lib
if [ -d "$LZ4_DIR" ]; then
    bld lz4 "-I$LZ4_DIR" $LZ4_DIR/lz4.c $LZ4_DIR/lz4hc.c $LZ4_DIR/lz4frame.c $LZ4_DIR/xxhash.c
else
    echo "  SKIP: LZ4 not found at $LZ4_DIR"
fi

# ============================================================
# Layer 3: ziparchive (used by ART for DEX/APK files)
# ============================================================
echo ""
echo "--- Layer 3: ziparchive ---"
ZIPARCHIVE_DIR=$A/system/libziparchive
if [ -d "$ZIPARCHIVE_DIR" ]; then
    bld ziparchive "-I$ZIPARCHIVE_DIR/include -I$A/system/libbase/include -I$A/system/logging/liblog/include -I$A/system/core/include -I$A/external/zlib" \
        $(find $ZIPARCHIVE_DIR -name "*.cc" -not -name "*test*" -not -name "*fuzz*" | sort)
else
    echo "  SKIP: ziparchive not found at $ZIPARCHIVE_DIR"
fi

# ============================================================
# FINAL REPORT
# ============================================================
echo ""
echo "=========================================="
echo "  FINAL REPORT"
echo "=========================================="
echo -e "$REPORT"
echo ""
echo "Output:"
ls -lh $O/lib*.so 2>/dev/null | awk '{print $5, $NF}'
echo ""
du -sh $O/
echo ""

# Check for unresolved symbols in libart.so
if [ -f "$O/libart.so" ]; then
    UNDEF=$($READELF --dyn-syms $O/libart.so 2>/dev/null | grep -c "UND" || true)
    NEEDED=$($READELF -d $O/libart.so 2>/dev/null | grep -c "NEEDED" || true)
    echo "libart.so analysis:"
    echo "  Dynamic deps (NEEDED): $NEEDED"
    echo "  Undefined symbols: $UNDEF"
    echo ""
    echo "  NEEDED libraries:"
    $READELF -d $O/libart.so 2>/dev/null | grep NEEDED | sed 's/^/    /'
fi

echo ""
echo "Build errors saved to: $ERRLOG"
echo "  Total error entries: $(grep -c "^=== FAIL:" "$ERRLOG" 2>/dev/null || echo 0)"
