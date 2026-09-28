#!/bin/bash
# ============================================================================
# [VENDORED 2026-07-10] 本文件 arm64 (aarch64-linux-ohos) 目标版本此前只存在于
# 兄弟项目 /opt/1F.Application/02.Noice/adapter/build/inner_arm64_5583/（Noice app
# 的 adapter 变体，为 Noice 自己的设备 5583 新增了 arm32 armv7 twin script 之外的
# arm64 支持）。本仓库 02.unity.cardwords/adapter 此前只 vendor 了这份脚本的 armv7
# 版本（同目录 cross_compile_arm32.sh 等），arm64 版本一直是本仓库"0外链"审计
# （见根目录 PROVENANCE.md + memory route3-rssurface-stack-confirmed.md "0外链缺口
# 闭合"一节）钉死的两个硬性外链缺口之一。
#
# 溯源：两份脚本（本仓库 armv7 版 + Noice arm64 版）架构/注释/变量命名逐行同源，
# 均出自同一个 "HanBingChen" 作者的 WestLake adapter 工程谱系（本仓库自己就是
# 2026-07-09 从共享树 /opt/10.Project/16-WestLake/16.12-HanBing/adapter vendor
# 来的，见 PROVENANCE.md 开头），Noice 只是同一谱系下针对自己设备（5583）额外
# 扩展出的 arm64 目标，不是另一个 app 的私有业务逻辑——脚本内容是"如何用 OH
# clang 交叉编译纯 AOSP 源码"这件事本身的构建工具链代码，不读取/不依赖 Noice
# app 自己的任何源文件。已核实：本文件只通过 OH_ROOT/AOSP_ROOT/ADAPTER_ROOT
# 三个环境变量（有 $HOME 相对默认值或自推导 ADAPTER_ROOT，均可覆盖）访问外部
# 输入，零处硬编码指向 /opt/1F.Application 或 GZ05 的构建期依赖（两处遗留纯
#文档性注释——设备侧历史 diff 路径 + 一个可选 header-mirror 的来源说明——均
# 不参与实际编译/链接，已在本次改动过程中逐条核实，见 PROVENANCE.md）。
#
# 本次改动（对比 Noice 原始版本，只改了这些，逻辑不变）：
#   1. out/aosp_lib → out/aosp_lib64（避免和本仓库 armv7 流水线的产物目录
#      同名冲突；匹配本仓库已有的 compile_oh_android_runtime_arm64_stage2unity.sh
#      的 AOSP_LIB_DIR 默认期望路径）。
#   2. OH_ROOT/AOSP_ROOT 默认值 /home/HanBingChen/{oh,aosp} → $HOME/{oh,aosp}；
#      ADAPTER_ROOT 默认值 $HOME/adapter → 脚本自身位置自推导（跟本仓库
#      2026-07-09 对 armv7 twin 脚本做过的同款修复一致，见 PROVENANCE.md）。
# 未改动语义/编译参数/link 顺序。逐字节 diff 见 PROVENANCE.md 对应章节。
# ============================================================================
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
# Target: aarch64-linux-ohos (musl), for DAYU200 RK3568 (32-bit userspace)
# Usage: cross_compile_arm32.sh [--oh-root=PATH] [--aosp-root=PATH] [--verbose]
#
# ════════════════════════════════════════════════════════════════════════════
#  USE CASE / 使用场景（2026-05-18 added per audit）
# ════════════════════════════════════════════════════════════════════════════
#
#  ▶ 一句话定位：把 AOSP 自身的 native .so 从 AOSP 源码交叉编译到 ARM64
#    OH/musl 上，作为 adapter 的"原料库"供下游 .so 链接。
#
#  ▶ 产物：out/aosp_lib64/ 下 22+ 个 .so，含：
#    - ART 核心：libart / libartbase / libdexfile / libartpalette /
#      libartpalette-system / libsigchain / libnativeloader / libnativebridge /
#      libelffile / libprofile / libopenjdk
#    - ARM 汇编：libvixl
#    - 压缩/IO：liblz4 / libziparchive / libexpat
#    - AOSP 基础库：libbase / libutils / libcutils / libnativehelper / liblog
#    - 资源系统：libandroidfw（591KB，给 liboh_android_runtime.so 链）
#    - 图形：libft2 / libharfbuzz_ng / libminikin / libicu_jni / libicui18n /
#      libicuuc / libjavacore / libcrypto / libandroidio
#    - adapter 兼容层：libbionic_compat（bionic→musl 边界）；禁止 broad ART stub DSO
#    - 部分 hwui 子模块（libhwui 单独由 compile_libhwui.sh 编）
#
#  ▶ 工具链与编译参数：
#    - 编译器：OH Clang ($OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++)
#    - Sysroot：$OH/out/wukong100/obj/third_party/musl/usr（OH musl，非 bionic）
#    - C++ 标准：-std=gnu++17（兼容 bionic 老代码 + bionic_compat 兼容层）
#    - 强制 include：libcxx_compat.h（补 OH libcxx-ohos 缺的 nullptr_t /
#      __promote / math.h 宏冲突等）
#    - ART 特殊：-isystem libcxx_array_aosp 覆盖 OH libcxx-ohos 的 std::array
#      ABI bug（array<T,0>::data() 返 nullptr）
#    - 不开 RTTI（-fno-rtti）匹配 OH inner_api 约定（少数模块如 sigchain 例外）
#    - sigchain：generation-owned source copy rewrites libc_musl.so → libc.so;
#      the AOSP source tree remains read-only and the produced ELF is checked
#      fail-closed so a missing device-side compatibility symlink cannot recur.
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
#    - 编译产物落到 out/aosp_lib64/，被 deploy 推到设备 /system/android/lib/
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
#    - 不部署（脚本只产 .so 到 out/aosp_lib64/，推设备由 deploy/ 下脚本负责）
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
O="${AOSP_OUT_DIR:-$ADAPTER_ROOT/out/aosp_lib64}"
OBJ_ROOT="${AOSP_OBJ_DIR:-/tmp/cc100}"
ERRLOG="${AOSP_BUILD_ERROR_LOG:-$ADAPTER_ROOT/out/build_errors.log}"
STRICT_BUILD="${L03_A12_STRICT_BUILD:-0}"

case "$STRICT_BUILD" in
    0|1) ;;
    *) echo "ERROR: L03_A12_STRICT_BUILD must be 0 or 1" >&2; exit 2 ;;
esac

# A generation build must own every writable path. This prevents two builds
# from silently reusing /tmp/cc100 objects or a shared output directory.
if [ -n "${L03_A12_GENERATION_ID:-}" ]; then
    : "${AOSP_OUT_DIR:?generation build requires AOSP_OUT_DIR}"
    : "${AOSP_OBJ_DIR:?generation build requires AOSP_OBJ_DIR}"
    : "${AOSP_BUILD_ERROR_LOG:?generation build requires AOSP_BUILD_ERROR_LOG}"
    : "${L03_A12_CXX:?generation build requires L03_A12_CXX}"
    : "${L03_A12_CC:?generation build requires L03_A12_CC}"
    : "${L03_A12_AS:?generation build requires L03_A12_AS}"
    : "${L03_A12_READELF:?generation build requires L03_A12_READELF}"
    : "${L03_A12_BUILTINS:?generation build requires L03_A12_BUILTINS}"
    : "${L03_A12_LIBCXX_INCLUDE:?generation build requires L03_A12_LIBCXX_INCLUDE}"
    : "${L03_A12_LIBART_ZERO_ARRAY_HEADER_COHORT:?generation build requires L03_A12_LIBART_ZERO_ARRAY_HEADER_COHORT}"
    : "${L03_A12_PYTHON:?generation build requires L03_A12_PYTHON}"
    if [ "$OBJ_ROOT" = /tmp/cc100 ] || [ "$O" = "$ADAPTER_ROOT/out/aosp_lib64" ]; then
        echo "ERROR: generation build resolved to a shared output/object path" >&2
        exit 2
    fi
fi

CXX=${L03_A12_CXX:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++}
CC=${L03_A12_CC:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang}
AS=${L03_A12_AS:-$CC}
READELF=${L03_A12_READELF:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf}
PYTHON=${L03_A12_PYTHON:-python3}
LIBCXX_INCLUDE=${L03_A12_LIBCXX_INCLUDE:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/include/c++/v1}
if [ ! -d "$LIBCXX_INCLUDE" ]; then
    echo "ERROR: exact libc++ include root is missing: $LIBCXX_INCLUDE" >&2
    exit 2
fi
# OH output dir for DAYU200/RK3568
if [ -d "$OH/out/wukong100" ]; then
    OH_OUT="$OH/out/wukong100"
else
    echo "ERROR: $OH/out/wukong100 not found. Run OH build first (--product-name rk3568)."
    exit 1
fi

SR=$OH_OUT/obj/third_party/musl/usr
ML=$SR/lib/aarch64-linux-ohos
BC=$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include
BC_SRC=$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/src
LIBART_ZERO_ARRAY_HEADER_COHORT=${L03_A12_LIBART_ZERO_ARRAY_HEADER_COHORT:-$BC/libcxx_array_aosp}
if [ ! -f "$LIBART_ZERO_ARRAY_HEADER_COHORT/array" ] || \
        [ -L "$LIBART_ZERO_ARRAY_HEADER_COHORT/array" ]; then
    echo "ERROR: exact libart zero-array header cohort is missing or symlinked: $LIBART_ZERO_ARRAY_HEADER_COHORT/array" >&2
    exit 2
fi

# Shared warning/optimization flags (no libcxx_compat.h — added only for C++)
WARN_FLAGS="-Wno-unused-parameter -Wno-format -Wno-sign-compare -Wno-missing-field-initializers -Wno-c99-designator -Wno-gnu-designator -Wno-extern-c-compat -Wno-deprecated-declarations -Wno-c++11-narrowing -Wno-error"
COMMON_BASE="--target=aarch64-linux-ohos --sysroot=$SR -I$SR/include/aarch64-linux-ohos -fPIC -O2 -D__OHOS__ -D_GNU_SOURCE -D_POSIX_SOURCE $WARN_FLAGS"

# C++ files: force-include libcxx_compat.h for bionic→musl bridging.  The
# generation-bound zero-array cohort must precede the general OH libc++ root;
# appending it through ART_INC silently selected the OH <array> first and
# produced the invalid nullptr/4 InvokeStatic transport in libart.
CXXF="$CXX $COMMON_BASE -nostdinc++ -I$LIBART_ZERO_ARRAY_HEADER_COHORT -isystem $LIBCXX_INCLUDE -include $BC/libcxx_compat.h -I$BC -std=gnu++17"
# C files: no libcxx_compat.h (avoids C++ type leakage: bool, struct in extern "C")
CF="$CC $COMMON_BASE -std=c11 -D__ANDROID_API__=34 -DPAGE_SIZE=4096"
ASF="$AS --target=aarch64-linux-ohos --sysroot=$SR -I$SR/include/aarch64-linux-ohos -fPIC -I$OBJ_ROOT/generated -I$A/art -I$A/art/runtime -I$A/art/runtime/arch/arm64 -I$A/art/runtime/arch -I$A/art/runtime/interpreter -I$A/art/libartbase -I$BC/art -DART_TARGET -DNDEBUG -DANDROID_HOST_MUSL -DART_ENABLE_CODEGEN_arm64 -DART_DEFAULT_GC_TYPE_IS_CMS -DART_STACK_OVERFLOW_GAP_arm=8192 -DIMT_SIZE=43"
LNK="$CXX --target=aarch64-linux-ohos -B$ML -L$ML -L$O -shared -fPIC"
STRICT_LINK_FLAGS=""
if [ "$STRICT_BUILD" = 1 ]; then
    STRICT_LINK_FLAGS="-Wl,-z,defs -Wl,--build-id=sha1"
fi
BUILTINS=${L03_A12_BUILTINS:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a}
# OH system lib paths for cross-lib linking
OH_SYSLIB=$OH_OUT/packages/phone/system/lib64
OH_PLATFORMSDK=$OH_SYSLIB/platformsdk
OH_SYSLIB_NDK=$OH_SYSLIB/ndk

ART_DEFS="-DART_ARM32_SUPPRESS_LOCKFREE_ASSERT -DNDEBUG -DANDROID_HOST_MUSL -DART_STACK_OVERFLOW_GAP_arm=8192 -DART_STACK_OVERFLOW_GAP_arm64=8192 -DART_STACK_OVERFLOW_GAP_riscv64=8192 -DART_STACK_OVERFLOW_GAP_x86=8192 -DART_STACK_OVERFLOW_GAP_x86_64=8192 -DART_TARGET -DART_TARGET_LINUX -DART_BASE_ADDRESS=0x70000000 -DART_ENABLE_CODEGEN_arm64 -DART_DEFAULT_GC_TYPE_IS_CMS -DART_FRAME_SIZE_LIMIT=1736 -DIMT_SIZE=43"
ART_INC="-I$ADAPTER_ROOT/framework/native-loader-oh/include -I$A/art/libnativeloader/include -I$A/art -I$A/art/libdexfile -I$A/art/libartbase -I$A/art/runtime -I$A/art/libartpalette/include -I$A/art/libdexfile/external/include -I$A/art/libprofile -I$A/libnativehelper/include_jni -I$A/libnativehelper/include -I$A/libnativehelper/include_platform_header_only -I$A/libnativehelper/header_only_include -I$A/libnativehelper/header_only_include -I$A/system/logging/liblog/include -I$A/system/libbase/include -I$A/system/core/include -I$A/system/core/libcutils/include -I$A/system/core/libutils/include -I$A/external/fmtlib/include -I$A/external/lz4/lib -I$A/external/zlib -I$A/system/libziparchive/include -I$A/external/vixl/src -I$A/frameworks/native/include -I$A/external/tinyxml2 -I$A/system/unwinding/libunwindstack/include -I$A/system/unwinding/libbacktrace/include -I$BC/art -I$A/external/dlmalloc -I$A/external/cpu_features/include -I$A/art/cmdline -I$A/art/libelffile -I$A/external/googletest/googletest/include -I$A/libnativehelper/include_platform_header_only -I$A/art/libnativebridge/include -I$A/system/libziparchive/incfs_support/include -I$A/art/odrefresh/include -I$A/external/cpu_features/src -DSTACK_LINE_READER_BUFFER_SIZE=1024 -DHAVE_DLFCN_H -DHAVE_STRONG_GETAUXVAL"
ART_INC="-I$OBJ_ROOT/generated $ART_INC"

mkdir -p "$O" "$OBJ_ROOT/logs" "$(dirname "$ERRLOG")"
REPORT=""
BUILD_HAD_FAIL=0
> "$ERRLOG"

# ============================================================
# Build function: compile sources -> link shared library
# ============================================================
bld() {
    local N=$1 I=$2; shift 2
    local D="$OBJ_ROOT/$N"; mkdir -p "$D"
    local ok=0 fl=0 fails=""
    # [PARALLEL 2026-06-25] compile all sources concurrently via xargs -P.
    # Each source compiles independently into $D/$b.o; failures recorded as
    # $D/$b.FAILED. Incremental skip (.o newer than src) preserved.
    local NJOBS="${BUILD_NJOBS:-16}"
    export CXXF CF ASF D N I OBJ_ROOT
    printf '%s\0' "$@" | xargs -0 -P "$NJOBS" -I '{}' sh -c '
        s="{}"
        b=$(basename "$s"); b=${b%.*}; ext="${s##*.}"
        comp="$CXXF"; [ "$ext" = "c" ] && comp="$CF"; [ "$ext" = "S" ] && comp="$ASF"
        rm -f "$D/$b.FAILED"
        if [ -f "$D/$b.o" ] && [ "$D/$b.o" -nt "$s" ]; then exit 0; fi
        if $comp $I -c -o "$D/$b.o" "$s" 2>"$OBJ_ROOT/logs/${N}_${b}.err"; then
            :
        else
            : > "$D/$b.FAILED"
        fi
    '
    # Tally results sequentially (deterministic counts + error log).
    for s in "$@"; do
        local b=$(basename $s); b=${b%.*}
        if [ -f "$D/$b.FAILED" ]; then
            fl=$((fl+1)); fails="$fails $b"; rm -f "$D/$b.FAILED"
            echo "=== FAIL: $N/$b ===" >> "$ERRLOG"
            grep -m3 'error:' "$OBJ_ROOT/logs/${N}_${b}.err" >> "$ERRLOG" 2>/dev/null || head -8 "$OBJ_ROOT/logs/${N}_${b}.err" >> "$ERRLOG"
            echo "" >> "$ERRLOG"
            if [ $VERBOSE -eq 1 ]; then echo "    FAIL: $b"; head -3 "$OBJ_ROOT/logs/${N}_${b}.err" | sed 's/^/      /'; fi
        else
            ok=$((ok+1))
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

    # Generation builds are strict-only. Legacy non-generation invocations keep
    # the historical fallback until they are migrated independently.
    local link_mode="strict"
    local EXTRA_LIBS="-lbionic_compat"
    [ "$N" = "bionic_compat" ] && EXTRA_LIBS="-L$OH_PLATFORMSDK -lbegetutil.z"
    [ "$N" = "log" ] && EXTRA_LIBS="-lbionic_compat -L$OH_PLATFORMSDK -lhilog"  # innerAPI hilog per memory feedback_prefer_inner_api.md (2026-04-17: NDK→innerAPI conversion)
    # Mirror the direct AOSP shared_lib edges so strict -z defs does not rely
    # on process-global providers.  The order matches this script's Layer 2:
    # log -> base -> cutils -> utils.
    [ "$N" = "base" ] && EXTRA_LIBS="-llog -lbionic_compat"
    [ "$N" = "cutils" ] && EXTRA_LIBS="-llog -lbase -lbionic_compat"
    [ "$N" = "utils" ] && EXTRA_LIBS="-lcutils -llog -lbionic_compat"
    [ "$N" = "nativehelper" ] && EXTRA_LIBS="-lbionic_compat -llog"
    [ "$N" = "artpalette" ] && EXTRA_LIBS="-llog -lbionic_compat"
    # Real AOSP libziparchive is the typed ABI owner.  Preserve the direct
    # artbase provider edge independently of incidental undefined-symbol use.
    [ "$N" = "artbase" ] && EXTRA_LIBS="-Wl,--no-as-needed -lziparchive -Wl,--as-needed -lartpalette -ltinyxml2 -lbase -llog -lbionic_compat -L$OH_PLATFORMSDK -lz"
    [ "$N" = "dexfile" ] && EXTRA_LIBS="-lartbase -lartpalette -lziparchive -lbase -llog -lbionic_compat -L$OH_PLATFORMSDK -lz"
    # The OH Palette target boundary is a C ABI. It needs only real liblog for
    # crash diagnostics; priority operations resolve directly from Musl libc.
    [ "$N" = "artpalette-system" ] && EXTRA_LIBS="-llog"
    # Layer 3.5 aux libs (replace stub semantics with real implementations)
    [ "$N" = "tinyxml2" ]       && EXTRA_LIBS=""
    [ "$N" = "elffile" ]        && EXTRA_LIBS="-lartbase -lbase -llog -llzma"
    [ "$N" = "nativebridge" ]   && EXTRA_LIBS="-lbase -llog"
    [ "$N" = "nativeloader" ]   && EXTRA_LIBS="-Wl,--version-script=$ADAPTER_ROOT/framework/native-loader-oh/native_loader.map -Wl,--no-as-needed -lapp_native_loader"
    [ "$N" = "icu_jni" ]        && EXTRA_LIBS="-lbase -llog -lnativehelper -licuuc -licui18n -lbionic_compat"
    # ziparchive / profile / others that call into OH zlib need -lz from platformsdk
    [ "$N" = "ziparchive" ]     && EXTRA_LIBS="-lbase -llog -lbionic_compat -L$OH_PLATFORMSDK -lz"
    [ "$N" = "profile" ]        && EXTRA_LIBS="-lbase -llog -lartbase -lartpalette -ldexfile -lziparchive -L$OH_PLATFORMSDK -lz"
    # unwindstack: drop -llzma (would need AOSP xz-tools cross-compile; OH has
    # liblzma.z.so at platformsdk but name mismatch. libunwindstack only uses
    # lzma for some compressed ELF sections, not hot paths.)
    # libunwindstack owns real AOSP Demangle plus static libdexfile_support;
    # no broad runtime-stub DSO may enter the product closure.
    [ "$N" = "unwindstack" ]    && EXTRA_LIBS="-lbase -llog -ldexfile -llzma"
    # libart links only against real typed providers.
    [ "$N" = "art-compiler" ] && EXTRA_LIBS="-Wl,-Bsymbolic -lbionic_compat -llog -lbase -lcutils -lutils -lnativehelper -lsigchain -ldexfile -lartbase -lartpalette -lvixl -llz4 -lziparchive -lelffile -lnativeloader -lprofile -lart"
    [ "$N" = "art" ] && EXTRA_LIBS="-Wl,-Bsymbolic -lbionic_compat -llog -lbase -lcutils -lutils -lnativehelper -lsigchain -ldexfile -lartbase -lartpalette -lvixl -llz4 -lziparchive -lelffile -lnativebridge -lnativeloader -lprofile -ltinyxml2 -lunwindstack"  # 2026-04-16: removed -lart_runtime_stubs, compile real AOSP srcs instead
    local SONAME_FLAGS=""
    if [ "$STRICT_BUILD" = 1 ]; then
        SONAME_FLAGS="-Wl,-soname,lib$N.so"
    fi
    if ! $LNK $STRICT_LINK_FLAGS $SONAME_FLAGS -o "$O/lib$N.so" $OB -lc $EXTRA_LIBS -ldl -lpthread $BUILTINS 2>"$OBJ_ROOT/logs/${N}_link.err"; then
        if [ "$STRICT_BUILD" = 1 ]; then
            echo "  ❌ lib$N: $ok/$total (link failed)"
            REPORT="$REPORT\n  ❌ lib$N: $ok/$total (link failed)"
            echo "=== LINK FAIL: $N ===" >> "$ERRLOG"
            cat "$OBJ_ROOT/logs/${N}_link.err" >> "$ERRLOG"
            BUILD_HAD_FAIL=1
            rm -f "$O/lib$N.so"
            return 1
        fi
        link_mode="relaxed"
        if ! $LNK -o "$O/lib$N.so" $OB -lc $EXTRA_LIBS -ldl -lpthread $BUILTINS \
            -Wl,--unresolved-symbols=ignore-all 2>"$OBJ_ROOT/logs/${N}_link2.err"; then
            echo "  ❌ lib$N: $ok/$total (link failed)"
            REPORT="$REPORT\n  ❌ lib$N: $ok/$total (link failed)"
            echo "=== LINK FAIL: $N ===" >> "$ERRLOG"
            cat "$OBJ_ROOT/logs/${N}_link2.err" >> "$ERRLOG"
            BUILD_HAD_FAIL=1
            rm -f "$O/lib$N.so"
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


STRICT_LINK_FLAGS="$STRICT_LINK_FLAGS -Wl,--no-allow-shlib-undefined -Wl,--no-undefined"
bld art "$ART_DEFS $ART_INC -fno-rtti -I$BC_SRC" "$B6_ABORT_BRIDGE"
