#!/bin/bash
# === GUARD: internal helper, do not invoke directly ===
if [ "${BUILD_INNER_INVOKED}" != "1" ]; then
    echo "[GUARD] $(basename "$0") is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc." >&2
    echo "[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 bash $(basename "$0")" >&2
    exit 2
fi
# === END GUARD ===
# [DEPRECATED Phase 1 — 2026-05-21] Use build_aosp_lib.sh instead.
echo "[DEPRECATED] $(basename "$0") is wrapped by build_aosp_lib.sh — Phase 4 will absorb this" >&2
# Cross-compile AOSP native libraries for ARM32 using OH Clang
# Target: arm-linux-ohos (musl), for DAYU200 RK3568 (32-bit userspace)
# Usage: cross_compile_arm32.sh [--oh-root=PATH] [--aosp-root=PATH] [--verbose]
#
# ════════════════════════════════════════════════════════════════════════════
#  USE CASE / 使用场景（2026-05-18 added per audit）
# ════════════════════════════════════════════════════════════════════════════
#
#  ▶ 一句话定位：把 AOSP 自身的 native .so 从 AOSP 源码交叉编译到 ARM32
#    OH/musl 上，作为 adapter 的"原料库"供下游 .so 链接。
#
#  ▶ 产物：out/aosp_lib/ 下 22+ 个 .so，含：
#    - ART 核心：libart / libartbase / libdexfile / libartpalette /
#      libartpalette-system / libsigchain / libnativeloader / libnativebridge /
#      libelffile / libprofile / libopenjdk
#    - ARM 汇编：libvixl
#    - 压缩/IO：liblz4 / libziparchive / libexpat
#    - AOSP 基础库：libbase / libutils / libcutils / libnativehelper / liblog
#    - 资源系统：libandroidfw（591KB，给 liboh_android_runtime.so 链）
#    - 图形：libft2 / libharfbuzz_ng / libminikin / libicu_jni / libicui18n /
#      libicuuc / libjavacore / libcrypto / libandroidio
#    - adapter 兼容层：libbionic_compat（bionic→musl 桥）+ libart_runtime_stubs
#    - 部分 hwui 子模块（libhwui 单独由 compile_libhwui.sh 编）
#
#  ▶ 工具链与编译参数：
#    - 编译器：OH Clang ($OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++)
#    - Sysroot：$OH/out/rk3568/obj/third_party/musl/usr（OH musl，非 bionic）
#    - C++ 标准：-std=gnu++17（兼容 bionic 老代码 + bionic_compat 兼容层）
#    - 强制 include：libcxx_compat.h（补 OH libcxx-ohos 缺的 nullptr_t /
#      __promote / math.h 宏冲突等）
#    - ART 特殊：-isystem libcxx_array_aosp 覆盖 OH libcxx-ohos 的 std::array
#      ABI bug（array<T,0>::data() 返 nullptr）
#    - 不开 RTTI（-fno-rtti）匹配 OH inner_api 约定（少数模块如 sigchain 例外）
#    - 链接器 patch：libsigchain.so 后置 binary patch（libc_musl → libc）
#
#  ▶ 何时跑（trigger 条件）：
#    - AOSP 源码升级（如 AOSP 14 → 15 大版本，或 cherry-pick 单个补丁）
#    - bionic_compat 兼容层改动（framework/appspawn-x/bionic_compat/ 下）
#    - OH SDK 升级导致 sysroot 变化
#    - 不需要：改 adapter framework/ 自家代码（那是 compile_oh_android_runtime.sh
#      / compile_oh_adapter_bridge.sh 等下游脚本的范围）
#
#  ▶ 上下游关系：
#    - 本脚本是项目编译链的最上游——没有外部依赖（除 OH SDK + AOSP 源码）
#    - 下游：compile_oh_android_runtime.sh 链本脚本产物的 libandroidfw /
#      libbase / libutils / libcutils / libziparchive 等
#    - 下游：compile_libhwui.sh 编 libhwui.so 时链本脚本的 libft2 /
#      libharfbuzz_ng / libminikin / libicuuc 等
#    - 下游：compile_oh_adapter_bridge.sh / compile_appspawnx.sh /
#      compile_apk_installer.sh 等都依赖本脚本的产物
#    - 编译产物落到 out/aosp_lib/，被 deploy 推到设备 /system/android/lib/
#
#  ▶ NOT 范围（避免误用）：
#    - 不编 adapter 自家 native .so（→ compile_oh_android_runtime.sh /
#      compile_oh_adapter_bridge.sh / compile_appspawnx.sh / compile_libhwui.sh
#      / compile_apk_installer.sh 等）
#    - 不编 OH 系统服务 .so（abilityms / scene_session_manager / libappms /
#      libbms 等，→ OH BUILD.gn）
#    - 不编 Java 产物（framework.jar / core-oj.jar / oh-adapter-framework.jar，
#      → AOSP Soong，build/auto_build.sh 触发）
#    - 不编 host 工具（dex2oat64 等 → AOSP Soong host build）
#    - 不部署（脚本只产 .so 到 out/aosp_lib/，推设备由 deploy/ 下脚本负责）
#
#  ▶ 严格规则（STRICT mode 自 2026-04-14 起）：
#    - 任何 .cpp 编译失败立即标 .so NOT_PRODUCED，不允许 silent-partial
#      链接（曾发生 libziparchive 丢 OpenArchive 等关键导出符号导致设备
#      工作副本被部分覆盖的事故）
#    - 失败现场写 out/build_errors.log，需要修根因或 allow-list 后才能继续
#
# ════════════════════════════════════════════════════════════════════════════
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
ADAPTER_ROOT="${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
O="$ADAPTER_ROOT/out/aosp_lib"
ERRLOG="$ADAPTER_ROOT/out/build_errors.log"

CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++
CC=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang
AS=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang
READELF=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf

# OH output dir for DAYU200/RK3568
if [ -d "$OH/out/rk3568" ]; then
    OH_OUT="$OH/out/rk3568"
else
    echo "ERROR: $OH/out/rk3568 not found. Run OH build first (--product-name rk3568)."
    exit 1
fi

SR=$OH_OUT/obj/third_party/musl/usr
ML=$SR/lib/arm-linux-ohos
BC=$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include
BC_SRC=$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/src

# Shared warning/optimization flags (no libcxx_compat.h — added only for C++)
WARN_FLAGS="-Wno-unused-parameter -Wno-format -Wno-sign-compare -Wno-missing-field-initializers -Wno-c99-designator -Wno-gnu-designator -Wno-extern-c-compat -Wno-deprecated-declarations -Wno-c++11-narrowing -Wno-error"
COMMON_BASE="--target=arm-linux-ohos -march=armv7-a --sysroot=$SR -I$SR/include/arm-linux-ohos -fPIC -O2 -D__OHOS__ -D_GNU_SOURCE -D_POSIX_SOURCE $WARN_FLAGS"

# C++ files: force-include libcxx_compat.h for bionic→musl bridging
CXXF="$CXX $COMMON_BASE -include $BC/libcxx_compat.h -I$BC -std=gnu++17"
# C files: no libcxx_compat.h (avoids C++ type leakage: bool, struct in extern "C")
CF="$CC $COMMON_BASE -std=c11 -D__ANDROID_API__=34 -DPAGE_SIZE=4096"
ASF="$AS --target=arm-linux-ohos -march=armv7-a --sysroot=$SR -I$SR/include/arm-linux-ohos -fPIC -I$A/art/runtime -I$A/art/runtime/arch/arm -I$A/art/runtime/arch -I$A/art/runtime/interpreter -I$A/art/libartbase -I$BC/art -DART_TARGET -DNDEBUG -DANDROID_HOST_MUSL -DART_ENABLE_CODEGEN_arm -DART_DEFAULT_GC_TYPE_IS_CMS -DART_STACK_OVERFLOW_GAP_arm=8192 -DIMT_SIZE=43"
LNK="$CXX --target=arm-linux-ohos -B$ML -L$ML -L$O -shared -fPIC"
BUILTINS=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/arm-linux-ohos/libclang_rt.builtins.a
# OH system lib paths for cross-lib linking
OH_SYSLIB=$OH_OUT/packages/phone/system/lib
OH_PLATFORMSDK=$OH_SYSLIB/platformsdk
OH_SYSLIB_NDK=$OH_SYSLIB/ndk

ART_DEFS="-DART_ARM32_SUPPRESS_LOCKFREE_ASSERT -DNDEBUG -DANDROID_HOST_MUSL -DART_STACK_OVERFLOW_GAP_arm=8192 -DART_STACK_OVERFLOW_GAP_arm64=8192 -DART_STACK_OVERFLOW_GAP_riscv64=8192 -DART_STACK_OVERFLOW_GAP_x86=8192 -DART_STACK_OVERFLOW_GAP_x86_64=8192 -DART_TARGET -DART_TARGET_LINUX -DART_BASE_ADDRESS=0x70000000 -DART_ENABLE_CODEGEN_arm -DART_DEFAULT_GC_TYPE_IS_CMS -DART_FRAME_SIZE_LIMIT=1736 -DIMT_SIZE=43"
ART_INC="-isystem $BC/libcxx_array_aosp -I$A/art -I$A/art/libdexfile -I$A/art/libartbase -I$A/art/runtime -I$A/art/libartpalette/include -I$A/art/libdexfile/external/include -I$A/art/libprofile -I$A/libnativehelper/include_jni -I$A/libnativehelper/include -I$A/libnativehelper/include_platform_header_only -I$A/libnativehelper/header_only_include -I$A/libnativehelper/header_only_include -I$A/system/logging/liblog/include -I$A/system/libbase/include -I$A/system/core/include -I$A/system/core/libcutils/include -I$A/system/core/libutils/include -I$A/external/fmtlib/include -I$A/external/lz4/lib -I$A/external/zlib -I$A/system/libziparchive/include -I$A/external/vixl/src -I$A/frameworks/native/include -I$A/external/tinyxml2 -I$A/system/unwinding/libunwindstack/include -I$A/system/unwinding/libbacktrace/include -I$BC/art -I$A/external/dlmalloc -I$A/external/cpu_features/include -I$A/art/cmdline -I$A/art/libelffile -I$A/external/googletest/googletest/include -I$A/libnativehelper/include_platform_header_only -I$A/art/libnativeloader/include -I$A/art/libnativebridge/include -I$A/system/libziparchive/incfs_support/include -I$A/art/odrefresh/include"

mkdir -p $O
REPORT=""
BUILD_HAD_FAIL=0
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
        # Incremental: skip if .o newer than source AND newer than header-deps file
        if [ -f "$D/$b.o" ] && [ "$D/$b.o" -nt "$s" ]; then
            ok=$((ok+1))
            continue
        fi
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
    # STRICT: any compile FAIL => skip link, flag build as broken.
    # Rationale (2026-04-14): previous warning-mode silently linked partial .so
    # with missing API exports (libziparchive lost OpenArchive/etc., wiping
    # working device copy). Fix root cause or allow-list, never silent-partial.
    if [ $fl -gt 0 ]; then
        echo "  ❌ lib$N: $ok/$total [COMPILE FAIL:$fails] — .so NOT produced"
        REPORT="$REPORT\n  ❌ lib$N: $ok/$total [COMPILE FAIL:$fails] — .so NOT produced"
        BUILD_HAD_FAIL=1
        rm -f $O/lib$N.so
        return 1
    fi
    local OB=$(ls $D/*.o 2>/dev/null | tr "\n" " ")
    if [ -z "$OB" ]; then
        echo "  ❌ lib$N: 0/$total (no objects)"
        REPORT="$REPORT\n  ❌ lib$N: 0/$total (no objects)"
        BUILD_HAD_FAIL=1
        return 1
    fi

    # Try strict link first, then fallback with unresolved symbols
    local link_mode="strict"
    local EXTRA_LIBS="-lbionic_compat"
    [ "$N" = "bionic_compat" ] && EXTRA_LIBS="-L$OH_PLATFORMSDK -lbegetutil.z"
    [ "$N" = "art_runtime_stubs" ] && EXTRA_LIBS=""
    [ "$N" = "log" ] && EXTRA_LIBS="-lbionic_compat -L$OH_PLATFORMSDK -lhilog"  # innerAPI hilog per memory feedback_prefer_inner_api.md (2026-04-17: NDK→innerAPI conversion)
    [ "$N" = "nativehelper" ] && EXTRA_LIBS="-lbionic_compat -llog"
    # libartbase directly consumes AOSP libziparchive (not a compat fallback).
    # --no-as-needed preserves the typed provider edge as an explicit runtime
    # contract even if a particular ART source revision stops importing it.
    [ "$N" = "artbase" ] && EXTRA_LIBS="-Wl,--no-as-needed -lziparchive -Wl,--as-needed -lbase -llog -lbionic_compat -L$OH_PLATFORMSDK -lz"
    # libartpalette-system (palette_fake.cc) uses base/logging.h LOG macros;
    # AOSP Android.bp shared_libs: libbase, liblog. Mirror here.
    [ "$N" = "artpalette-system" ] && EXTRA_LIBS="-lbase -llog -lbionic_compat"
    # Layer 3.5 aux libs (replace stub semantics with real implementations)
    [ "$N" = "tinyxml2" ]       && EXTRA_LIBS=""
    [ "$N" = "elffile" ]        && EXTRA_LIBS="-lbase -llog -lartbase -llz4"
    [ "$N" = "nativebridge" ]   && EXTRA_LIBS="-lbase -llog"
    [ "$N" = "nativeloader" ]   && EXTRA_LIBS="-lbase -llog -lnativebridge"
    [ "$N" = "icu_jni" ]        && EXTRA_LIBS="-lbase -llog -lnativehelper -licuuc -licui18n -lbionic_compat"
    # ziparchive / profile / others that call into OH zlib need -lz from platformsdk
    [ "$N" = "ziparchive" ]     && EXTRA_LIBS="-lbase -llog -lbionic_compat -L$OH_PLATFORMSDK -lz"
    [ "$N" = "profile" ]        && EXTRA_LIBS="-lbase -llog -lartbase -ldexfile -lziparchive -lart_runtime_stubs -L$OH_PLATFORMSDK -lz"
    # unwindstack: drop -llzma (would need AOSP xz-tools cross-compile; OH has
    # liblzma.z.so at platformsdk but name mismatch. libunwindstack only uses
    # lzma for some compressed ELF sections, not hot paths.)
    # Link -lart_runtime_stubs so excluded Demangle/ThreadUnwinder symbols
    # resolve via stubs at dlopen time (musl's loader only walks the
    # immediate NEEDED chain, not the full transitive closure).
    [ "$N" = "unwindstack" ]    && EXTRA_LIBS="-lbase -llog -ldexfile -lart_runtime_stubs"
    # libart: link against REAL aux libs (not stubs). libart_runtime_stubs still
    # kept for any residual symbols the 6 real libs don't cover (appended after).
    [ "$N" = "art-compiler" ] && EXTRA_LIBS="-Wl,-Bsymbolic -lbionic_compat -llog -lbase -lcutils -lutils -lnativehelper -lsigchain -ldexfile -lartbase -lartpalette -lvixl -llz4 -lziparchive -lelffile -lnativeloader -lprofile -lart"
    [ "$N" = "art" ] && EXTRA_LIBS="-Wl,-Bsymbolic -lbionic_compat -llog -lbase -lcutils -lutils -lnativehelper -lsigchain -ldexfile -lartbase -lartpalette -lvixl -llz4 -lziparchive -lelffile -lnativebridge -lnativeloader -lprofile -ltinyxml2 -lunwindstack"  # 2026-04-16: removed -lart_runtime_stubs, compile real AOSP srcs instead
    if ! $LNK -o $O/lib$N.so $OB -lc $EXTRA_LIBS -ldl -lpthread $BUILTINS 2>/tmp/cc100/${N}_link.err; then
        link_mode="relaxed"
        if ! $LNK -o $O/lib$N.so $OB -lc $EXTRA_LIBS -ldl -lpthread $BUILTINS \
            -Wl,--unresolved-symbols=ignore-all 2>/tmp/cc100/${N}_link2.err; then
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
    else
        echo "  ✅ lib$N: $ok/$total ($sz) [link: relaxed, undef: ~$undef_count]"
        REPORT="$REPORT\n  ✅ lib$N: $ok/$total ($sz) [link: relaxed, undef: ~$undef_count]"
    fi
}

# 2026-04-16: changed to incremental — only mkdir, no clean (use --clean for full rebuild)
if [ "${1:-}" = "--clean" ]; then echo "--clean: wiping /tmp/cc100"; rm -rf /tmp/cc100; fi
mkdir -p /tmp/cc100
echo "=========================================="
echo "  ARM32 Cross-Compilation"
echo "  OH Clang: $(basename $(dirname $(dirname $CXX)))"
echo "  Target: arm-linux-ohos (musl)"
echo "  Output: $O"
echo "=========================================="

# ============================================================
# Layer 1: bionic_compat
# ============================================================
echo ""
echo "--- Layer 1: bionic_compat ---"
# ============================================================
# Pre-build validation: asm_defines.h must be ARM32 (POINTER_SIZE=4)
# ============================================================
ASM_DEFINES="$A/art/asm_defines.h"
if ! grep -q "POINTER_SIZE 0x4" "$ASM_DEFINES" 2>/dev/null; then
    echo "FATAL: asm_defines.h has wrong POINTER_SIZE (expected 0x4 for ARM32)"
    echo "  File: $ASM_DEFINES"
    echo "  Fix: cp ~/aosp/art/runtime/asm_defines.h.generated $ASM_DEFINES"
    grep POINTER_SIZE "$ASM_DEFINES" 2>/dev/null || echo "  (POINTER_SIZE not found)"
    exit 1
fi
echo "  asm_defines.h: POINTER_SIZE=0x4 (ARM32) OK"

bld bionic_compat "-I$OH/base/startup/init/interfaces/innerkits/include/syspara -DPARAM_VALUE_LEN_MAX=96 -nostdinc++ -Wno-constant-conversion" \
    $BC_SRC/system_properties.cpp $BC_SRC/malloc_compat.cpp $BC_SRC/fdsan_stubs.cpp $BC_SRC/misc_compat.cpp $BC_SRC/abort_message_compat.cpp $BC_SRC/liblog_android_supplement.cpp $BC_SRC/sync_builtins.c

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
    $A/system/logging/liblog/log_event_list.cpp $A/system/logging/liblog/log_event_write.cpp $A/system/logging/liblog/logger_name.cpp $A/system/logging/liblog/logger_read.cpp $A/system/logging/liblog/logger_write.cpp $A/system/logging/liblog/logprint.cpp $A/system/logging/liblog/properties.cpp $A/system/logging/liblog/event_tag_map.cpp $A/system/logging/liblog/log_time.cpp $ADAPTER_ROOT/framework/core/jni/android_log_hilog_bridge.cpp

bld base "-I$A/system/libbase/include -I$A/system/logging/liblog/include -I$A/system/core/include -I$A/system/core/libcutils/include -I$A/external/fmtlib/include -DANDROID_BASE_UNIQUE_FD_DISABLE_FDSAN" \
    $A/system/libbase/abi_compatibility.cpp $A/system/libbase/chrono_utils.cpp $A/system/libbase/cmsg.cpp $A/system/libbase/errors_unix.cpp $A/system/libbase/file.cpp $A/system/libbase/hex.cpp $A/system/libbase/logging.cpp $A/system/libbase/mapped_file.cpp $A/system/libbase/parsebool.cpp $A/system/libbase/parsenetaddress.cpp $A/system/libbase/posix_strerror_r.cpp $A/system/libbase/process.cpp $A/system/libbase/properties.cpp $A/system/libbase/stringprintf.cpp $A/system/libbase/strings.cpp $A/system/libbase/threads.cpp

bld cutils "-I$A/system/core/libcutils/include -I$A/system/logging/liblog/include -I$A/system/libbase/include -I$A/system/core/include -I$A/external/fmtlib/include" \
    $A/system/core/libcutils/config_utils.cpp $A/system/core/libcutils/hashmap.cpp $A/system/core/libcutils/iosched_policy.cpp $A/system/core/libcutils/load_file.cpp $A/system/core/libcutils/native_handle.cpp $A/system/core/libcutils/properties.cpp $A/system/core/libcutils/record_stream.cpp $A/system/core/libcutils/socket_inaddr_any_server_unix.cpp $A/system/core/libcutils/socket_local_client_unix.cpp $A/system/core/libcutils/socket_local_server_unix.cpp $A/system/core/libcutils/socket_network_client_unix.cpp $A/system/core/libcutils/sockets_unix.cpp $A/system/core/libcutils/sockets.cpp $A/system/core/libcutils/str_parms.cpp $A/system/core/libcutils/threads.cpp

bld utils "-I$A/system/core/libutils/include -I$A/system/core/libcutils/include -I$A/system/logging/liblog/include -I$A/system/libbase/include -I$A/system/core/include -I$A/system/core/libprocessgroup/include -I$A/system/core/libvndksupport/include -I$A/external/fmtlib/include" \
    $A/system/core/libutils/Errors.cpp $A/system/core/libutils/FileMap.cpp $A/system/core/libutils/JenkinsHash.cpp $A/system/core/libutils/LightRefBase.cpp $A/system/core/libutils/Looper.cpp $A/system/core/libutils/NativeHandle.cpp $A/system/core/libutils/Printer.cpp $A/system/core/libutils/RefBase.cpp $A/system/core/libutils/SharedBuffer.cpp $A/system/core/libutils/StopWatch.cpp $A/system/core/libutils/String8.cpp $A/system/core/libutils/String16.cpp $A/system/core/libutils/StrongPointer.cpp $A/system/core/libutils/SystemClock.cpp $A/system/core/libutils/Threads.cpp $A/system/core/libutils/Timers.cpp $A/system/core/libutils/Tokenizer.cpp $A/system/core/libutils/Unicode.cpp $A/system/core/libutils/VectorImpl.cpp

bld nativehelper "-I$A/libnativehelper/include -I$A/libnativehelper/include_jni -I$A/libnativehelper/header_only_include -I$A/system/logging/liblog/include -I$A/system/libbase/include -I$A/system/core/include" \
    $A/libnativehelper/JNIHelp.c $A/libnativehelper/JniInvocation.c $A/libnativehelper/JniConstants.c $A/libnativehelper/JNIPlatformHelp.c $A/libnativehelper/DlHelp.c $A/libnativehelper/ExpandableString.c $A/libnativehelper/file_descriptor_jni.c

# ============================================================
# Layer 3: ART sub-libraries
# ============================================================
echo ""
echo "--- Layer 3: ART sub-libraries ---"
bld sigchain "$ART_DEFS $ART_INC -fno-rtti -DHAVE_SIGCHAIN" $A/art/sigchainlib/sigchain.cc

# libsigchain.so: NO binary patch needed (2026-05-21 dropped).
# Background: libsigchain.so static ctor dlopen()s "libc_musl.so" (string baked
# in by ANDROID_HOST_MUSL define). On OH the real libc is /lib/ld-musl-arm.so.1.
# Earlier (2026-04) we hex-edited "libc_musl.so" → "libc.so\0..." in the .so
# at build time. But deploy_stage.sh L519 ALREADY creates symlink
#   /system/lib/libc_musl.so → /lib/ld-musl-arm.so.1
# at deploy time, which resolves the dlopen via search-path. The binary patch
# became redundant. libsigchain.so now ships vanilla; runtime relies on the
# deploy-time symlink as single source of truth.

# Build the real ZIP provider before its ART consumers.  The deprecated
# bionic_compat/minizip.cpp is intentionally not in this source set.
echo ""
echo "--- Layer 3: ziparchive ---"
ZIPARCHIVE_DIR=$A/system/libziparchive
if [ -d "$ZIPARCHIVE_DIR" ]; then
    ZIPARCHIVE_SOURCES=$(find $ZIPARCHIVE_DIR \( -name "*.cc" -o -name "*.cpp" \) -not -name "*test*" -not -name "*fuzz*" -not -name "*benchmark*" -not -name "*tool*" | sort)
    if ! printf '%s\n' "$ZIPARCHIVE_SOURCES" | grep -Fxq "$ZIPARCHIVE_DIR/zip_error.cpp"; then
        echo "  ❌ libziparchive source closure missing canonical zip_error.cpp"
        BUILD_HAD_FAIL=1
    fi
    bld ziparchive "-DZLIB_CONST -I$ZIPARCHIVE_DIR/include -I$A/system/libbase/include -I$A/system/logging/liblog/include -I$A/system/core/include -I$A/external/zlib" \
        $ZIPARCHIVE_SOURCES
else
    echo "  SKIP: ziparchive not found at $ZIPARCHIVE_DIR"
fi

bld dexfile "$ART_DEFS $ART_INC -fno-rtti" $(ls $A/art/libdexfile/dex/*.cc | grep -v test)

bld artbase "$ART_DEFS $ART_INC -fno-rtti" $(ls $A/art/libartbase/base/*.cc $A/art/libartbase/base/unix_file/*.cc $A/art/libartbase/base/metrics/*.cc $A/art/libartbase/arch/*.cc 2>/dev/null | grep -v test | grep -v windows | grep -v fuchsia)

bld artpalette "$ART_DEFS $ART_INC -fno-rtti" $A/art/libartpalette/apex/palette.cc

# libartpalette-system.so = AOSP palette_fake.cc (runtime dlopen target of libartpalette.so).
# 111K "full" version per user preference (2026-04-14). 4K stub variant lives in
# framework/appspawn-x/bionic_compat/src/palette_system_stub.c but is no longer used.
bld artpalette-system "$ART_DEFS $ART_INC -fno-rtti" $A/art/libartpalette/system/palette_fake.cc

# ============================================================
# Layer 3: ART Runtime (largest component)
# ============================================================
echo ""
echo "--- Layer 3: VIXL (ARM assembler) ---"
VIXL_DIR=$A/external/vixl/src
if [ -d "$VIXL_DIR" ]; then
    # ARM32: exclude aarch64-specific files (cpu-aarch64, etc.)
    VIXL_FILES=$(find $VIXL_DIR -name "*.cc" \
        -not -name "*test*" -not -path "*/test/*" \
        -not -name "*example*" -not -name "*bench*" \
        -not -name "*aarch64*" \
        | sort)
    # vixl_math_fix.h no longer needed: isnan/isinf/signbit fixes now in libcxx_compat.h
    bld vixl "-I$A/external/vixl/src -DVIXL_INCLUDE_TARGET_A32 -DVIXL_CODE_BUFFER_MALLOC -DVIXL_GENERATE_SIMULATOR_INSTRUCTIONS_VALUE=0" $VIXL_FILES
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
# Layer 3.5: ART auxiliary libraries (real implementations)
# Replaces the stub-only approach previously in libart_runtime_stubs for:
# libtinyxml2 / libelffile / libnativebridge / libnativeloader / libprofile /
# libunwindstack. libart.so NEEDED previously pulled these in (see
# /data/local/tmp/libart_bak_20260414/libart.so on device — the authoritative
# libart-full version had them as DT_NEEDED). Restored 2026-04-14 after
# discovering aosp_lib's stub-only libart crashed early in Heap() construction
# because Unwinder/NativeLoader/Profile stubs returned garbage.
# ============================================================
echo ""
echo "--- Layer 3.5: ART auxiliary libraries ---"

bld tinyxml2 "-I$A/external/tinyxml2 -Wno-implicit-fallthrough" \
    $A/external/tinyxml2/tinyxml2.cpp

bld elffile "$ART_DEFS $ART_INC -fno-rtti -I$A/art/libelffile/include -I$A/external/lzma/C" \
    $A/art/libelffile/stream/file_output_stream.cc \
    $A/art/libelffile/stream/vector_output_stream.cc \
    $A/art/libelffile/stream/output_stream.cc \
    $A/art/libelffile/stream/buffered_output_stream.cc \
    $A/art/libelffile/elf/xz_utils.cc

bld nativebridge "$ART_DEFS $ART_INC -fno-rtti -I$A/art/libnativebridge/include" \
    $A/art/libnativebridge/native_bridge.cc

bld nativeloader "$ART_DEFS $ART_INC -fno-rtti -I$A/art/libnativeloader/include -I$A/art/libnativebridge/include" \
    $A/art/libnativeloader/library_namespaces.cpp \
    $A/art/libnativeloader/native_loader.cpp \
    $A/art/libnativeloader/native_loader_namespace.cpp \
    $A/art/libnativeloader/open_system_library.cpp \
    $A/art/libnativeloader/public_libraries.cpp

bld profile "$ART_DEFS $ART_INC -fno-rtti" \
    $A/art/libprofile/profile/profile_compilation_info.cc \
    $A/art/libprofile/profile/profile_boot_info.cc

# libicu_jni: ICU4C JNI bridge required by ART Runtime::InitNativeMethods (runtime.cc:2227).
# Without this, Runtime::Start aborts with LoadNativeLibrary FATAL.
bld icu_jni "-DU_USING_ICU_NAMESPACE=0 -DANDROID_LINK_SHARED_ICU4C -I$A/external/icu/icu4c/source/common -I$A/external/icu/icu4c/source/i18n -I$A/libnativehelper/include_jni -I$A/libnativehelper/include -I$A/libnativehelper/include_platform_header_only -I$A/libnativehelper/header_only_include -I$A/system/libbase/include -I$A/system/logging/liblog/include -Wno-error -Wno-unused-parameter"     $(ls $A/external/icu/android_icu4j/libcore_bridge/src/native/*.cpp 2>/dev/null | grep -v test)


# libunwindstack: 43 .cpp files total. Exclusions beyond tests:
#   Demangle.cpp       — needs librustc_demangle_static (Rust toolchain not set up)
#   ThreadUnwinder.cpp — uses tgkill() which musl doesn't expose via <signal.h>
#   LogStdout.cpp      — alternate Log impl for libunwindstack_stdout_log variant;
#                        duplicate symbols with LogAndroid.cpp
# These are not on the Heap()-construction hot path for our current goal
# (advancing past the libart-full Phase 2 crash point). If runtime callers hit
# missing symbols they fall back to libart_runtime_stubs which remains linked.
UNWIND_DIR=$A/system/unwinding/libunwindstack
UNWIND_FILES=$(find $UNWIND_DIR -maxdepth 1 -name "*.cpp" \
    -not -name "*Test*" -not -name "*_test*" -not -name "*Benchmark*" \
    -not -name "Demangle.cpp" -not -name "ThreadUnwinder.cpp" \
    -not -name "LogStdout.cpp" \
    2>/dev/null | sort)
bld unwindstack "-DDEXFILE_SUPPORT -I$UNWIND_DIR/include -I$A/system/libbase/include -I$A/system/logging/liblog/include -I$A/system/extras/libprocinfo/include -I$A/art/libdexfile/external/include -I$A/external/lzma/C -Wno-deprecated-declarations -Wno-unused-parameter -Wno-missing-field-initializers -fno-exceptions" \
    $UNWIND_FILES


# ============================================================
# Layer 3: ART Runtime (largest component)
# ============================================================
echo ""
echo "--- Layer 3: ART Runtime ---"

# Collect runtime .cc files (exclude tests, non-arm arch, android-specific, LP64-only)
RUNTIME_FILES=$(find $A/art/runtime -name "*.cc" \
    -not -name "*test*" -not -path "*/test/*" -not -name "*gtest*" \
    -not -name "*_android.cc" \
    -not -path "*/arch/arm64/*" -not -path "*/arch/x86/*" \
    -not -path "*/arch/x86_64/*" -not -path "*/arch/riscv64/*" \
    -not -name "monitor_pool.cc" \
    -not -name "statsd.cc" \
    | sort)

# Count source files
RUNTIME_COUNT=$(echo "$RUNTIME_FILES" | wc -l)
echo "  Runtime source files: $RUNTIME_COUNT .cc files"

# Generate nterp_arm.S (ARM nterp dispatch loop) via gen_mterp.py so the
# interpreter does not recurse into C++ ExecuteSwitchImplCpp per Java method
# call. Without nterp each invocation consumed ~8 bytes of native stack; a
# 128 MB worker pthread still ran out before ClassLinker finished boot init.
NTERP_ARM_S=/tmp/cc100/art/nterp_arm.S
mkdir -p /tmp/cc100/art
python3 $A/art/runtime/interpreter/mterp/gen_mterp.py $NTERP_ARM_S $A/art/runtime/interpreter/mterp/armng/*.S
ls -la $NTERP_ARM_S | awk '{print "  nterp_arm.S:", $5, "bytes"}'

# ARM assembly entrypoints: quick/jni/memcmp plus the freshly generated nterp.
# Earlier labelled as stubs because asm_support_gen.h was missing; bionic_compat
# ships an ARM32 asm_defines.h so the real entrypoints compile.
ASM_STUBS="$A/art/runtime/arch/arm/quick_entrypoints_arm.S $A/art/runtime/arch/arm/jni_entrypoints_arm.S $A/art/runtime/arch/arm/memcmp16_arm.S $NTERP_ARM_S"

# Include AOSP's arch/arm .cc files (C++ arch-specific code, NOT .S files)
ARM_CC=$(find $A/art/runtime/arch/arm -name "*.cc" -not -name "*test*" 2>/dev/null | sort)

# NOTE (2026-04-14): removed $BC_SRC/art_runtime_stubs.cpp from libart's own
# compilation. With -Wl,-Bsymbolic + the stub .cpp compiled inside libart,
# libart's internal references to OS::OpenFileForReading / FdFile::* bound to
# the stub copies (which use a different class layout than AOSP), causing
# ElfFile::Open to read garbage from FdFile objects. The stubs are still
# available externally via -lart_runtime_stubs for any symbols libartbase
# doesn't provide.
bld art "$ART_DEFS $ART_INC -fno-rtti -I$BC_SRC" \
    $RUNTIME_FILES $ARM_CC $ASM_STUBS

# Layer 4: libart-compiler.so (JIT compiler)
echo "" >&2; echo "--- Layer 4: libart-compiler ---" >&2
COMPILER_SRCS=$(cat /tmp/libart_compiler_srcs.txt 2>/dev/null)
if [ -n "$COMPILER_SRCS" ]; then
    bld art-compiler "$ART_DEFS $ART_INC -fno-rtti -fvisibility=protected -I$A/art/compiler -I$A/art/dex2oat -I$BC_SRC" $COMPILER_SRCS /tmp/cc100/art-compiler-gen/*.cc
fi


# ============================================================
# FINAL REPORT
# ============================================================
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

# ============================================================
# SMOKE TEST: verify critical exports are present in key .so.
# Catches "compile OK / link OK / exports missing" failure mode
# (e.g., libziparchive built but lost OpenArchive when -DZLIB_CONST
# flag was absent, silently producing an unusable library).
# ============================================================
smoke_check() {
    local lib="$O/lib$1.so"
    shift
    local missing=""
    if [ ! -f "$lib" ]; then
        echo "  ❌ smoke[$1]: $lib missing"
        BUILD_HAD_FAIL=1
        return 1
    fi
    # Write readelf output to temp file once; grep from file. Avoids bash var
    # issues with huge captures (libart dyn-syms has 10k+ lines, command sub
    # truncation / echo mangling observed when cached in a variable).
    local tmp=$(mktemp /tmp/smoke_$$_XXXXXX)
    $READELF --dyn-syms "$lib" > "$tmp" 2>/dev/null
    if [ ! -s "$tmp" ]; then
        echo "  ❌ smoke[$(basename $lib)]: readelf produced no output"
        rm -f "$tmp"
        BUILD_HAD_FAIL=1
        return 1
    fi
    for pat in "$@"; do
        if ! grep -q -- "$pat" "$tmp"; then
            missing="$missing $pat"
        fi
    done
    local base=$(basename $lib)
    local nlines=$(wc -l < "$tmp")
    rm -f "$tmp"
    if [ -n "$missing" ]; then
        echo "  ❌ smoke[$base]: missing exports:$missing (readelf $nlines lines)"
        BUILD_HAD_FAIL=1
        return 1
    fi
    echo "  ✅ smoke[$base]: all expected exports present ($nlines sym lines)"
}

# Enforce exact ABI ownership, not just substring presence.  This is the gate
# that prevents a future compat/stub source from competing with libziparchive.
smoke_exact_defined() {
    local lib="$O/lib$1.so" symbol="$2" expected="$3"
    local smoke_dir="$O/.westlake-smoke"
    local tmp="$smoke_dir/owner_$1_$$_${symbol}.txt"
    local count=0
    mkdir -p "$smoke_dir"
    if [ -f "$lib" ]; then
        $READELF --dyn-syms --wide "$lib" > "$tmp" 2>/dev/null || :
        count=$(awk -v wanted="$symbol" '
            $1 ~ /^[0-9]+:$/ && NF >= 8 {
                name=$8; sub(/@.*/, "", name)
                if (name == wanted && $5 == "GLOBAL" && $7 != "UND") count++
            }
            END { print count + 0 }
        ' "$tmp")
    fi
    rm -f "$tmp"
    if [ "$count" -ne "$expected" ]; then
        echo "  ❌ owner[$1:$symbol]: expected=$expected actual=$count"
        BUILD_HAD_FAIL=1
        return 1
    fi
    echo "  ✅ owner[$1:$symbol]: defined=$count"
}

smoke_needed() {
    local lib="$O/lib$1.so" needed="$2"
    local smoke_dir="$O/.westlake-smoke"
    local tmp="$smoke_dir/needed_$1_$$_${needed}.txt"
    local count=0
    mkdir -p "$smoke_dir"
    if [ -f "$lib" ]; then
        $READELF -d --wide "$lib" > "$tmp" 2>/dev/null || :
        count=$(grep -c "Shared library: \[$needed\]" "$tmp" || true)
    fi
    rm -f "$tmp"
    if [ "$count" -ne 1 ]; then
        echo "  ❌ edge[$1->$needed]: expected=1 actual=$count"
        BUILD_HAD_FAIL=1
        return 1
    fi
    echo "  ✅ edge[$1->$needed]: direct=1"
}

echo ""
echo "=========================================="
echo "  SMOKE TEST: Expected Exported Symbols"
echo "=========================================="
# libziparchive: 8 core APIs plus canonical AOSP error-string ABI.
smoke_check ziparchive OpenArchive CloseArchive FindEntry ExtractEntryToFile ExtractToMemory GetFileDescriptor OpenArchiveFd OpenArchiveFromMemory _Z15ErrorCodeStringi
smoke_exact_defined ziparchive _Z15ErrorCodeStringi 1
smoke_exact_defined bionic_compat _Z15ErrorCodeStringi 0
smoke_exact_defined bionic_compat ErrorCodeString 0
smoke_exact_defined art_runtime_stubs _Z15ErrorCodeStringi 0
smoke_exact_defined art_runtime_stubs ErrorCodeString 0
smoke_needed artbase libziparchive.so
# libdexfile: ArtDexFileLoader is exported here (not libartbase)
smoke_check dexfile ArtDexFileLoader
# libart: core Runtime entry (VM create) + VIXL-linked JIT allocator proof
smoke_check art JNI_CreateJavaVM
# libnativehelper: JNI invocation shim used by appspawn-x
smoke_check nativehelper JniInvocationCreate
# libvixl: code buffer malloc allocator present (catches VIXL_CODE_BUFFER_MALLOC regression)
smoke_check vixl CodeBuffer

echo "Build errors saved to: $ERRLOG"
echo "  Total error entries: $(grep -c "^=== FAIL:" "$ERRLOG" 2>/dev/null || echo 0)"

# Hard fail if any bld reported compile FAIL — prevents partial .so from
# silently overwriting a working device/local copy.
if [ $BUILD_HAD_FAIL -ne 0 ]; then
    echo ""
    echo "❌ BUILD FAILED: one or more targets had compile FAIL. See $ERRLOG"
    exit 1
fi
