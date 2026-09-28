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

generate_operator_out() {
    local output=$1 local_path=$2
    shift 2
    local temporary=$output.tmp
    mkdir -p "$(dirname "$output")"
    if ! "$PYTHON" "$A/art/tools/generate_operator_out.py" \
            "$local_path" "$@" >"$temporary"; then
        rm -f "$temporary"
        echo "ERROR: generate_operator_out failed: $output" >&2
        return 1
    fi
    mv "$temporary" "$output"
    test -s "$output"
}

# 2026-04-16: changed to incremental — only mkdir, no clean (use --clean for full rebuild)
if [ "${1:-}" = "--clean" ]; then
    echo "--clean: wiping $OBJ_ROOT"
    rm -rf "$OBJ_ROOT"
fi
mkdir -p "$OBJ_ROOT/logs"
echo "=========================================="
echo "  ARM64 Cross-Compilation"
echo "  OH Clang: $(basename $(dirname $(dirname $CXX)))"
echo "  Target: aarch64-linux-ohos (musl)"
echo "  Output: $O"
echo "  Objects: $OBJ_ROOT"
echo "  Link policy: $([ "$STRICT_BUILD" = 1 ] && echo strict-z-defs || echo legacy)"
echo "=========================================="

GENERATED_DIR=$OBJ_ROOT/generated
ARTBASE_OPERATOR_SRC=$GENERATED_DIR/artbase_operator_out.cc
DEXFILE_OPERATOR_SRC=$GENERATED_DIR/dexfile_operator_out.cc
ART_OPERATOR_SRC=$GENERATED_DIR/art_operator_out.cc
generate_operator_out "$ARTBASE_OPERATOR_SRC" "$A/art/libartbase" \
    "$A/art/libartbase/arch/instruction_set.h" \
    "$A/art/libartbase/base/allocator.h" \
    "$A/art/libartbase/base/unix_file/fd_file.h" || exit 1
generate_operator_out "$DEXFILE_OPERATOR_SRC" "$A/art/libdexfile" \
    "$A/art/libdexfile/dex/dex_file.h" \
    "$A/art/libdexfile/dex/dex_file_layout.h" \
    "$A/art/libdexfile/dex/dex_instruction.h" \
    "$A/art/libdexfile/dex/dex_instruction_utils.h" \
    "$A/art/libdexfile/dex/invoke_type.h" || exit 1
generate_operator_out "$ART_OPERATOR_SRC" "$A/art/runtime" \
    "$A/art/runtime/base/callee_save_type.h" \
    "$A/art/runtime/base/locks.h" \
    "$A/art/runtime/class_status.h" \
    "$A/art/runtime/compilation_kind.h" \
    "$A/art/runtime/gc_root.h" \
    "$A/art/runtime/gc/allocator_type.h" \
    "$A/art/runtime/gc/allocator/rosalloc.h" \
    "$A/art/runtime/gc/collector_type.h" \
    "$A/art/runtime/gc/collector/gc_type.h" \
    "$A/art/runtime/gc/collector/mark_compact.h" \
    "$A/art/runtime/gc/space/region_space.h" \
    "$A/art/runtime/gc/space/space.h" \
    "$A/art/runtime/gc/weak_root_state.h" \
    "$A/art/runtime/image.h" \
    "$A/art/runtime/instrumentation.h" \
    "$A/art/runtime/indirect_reference_table.h" \
    "$A/art/runtime/jdwp_provider.h" \
    "$A/art/runtime/jni_id_type.h" \
    "$A/art/runtime/linear_alloc.h" \
    "$A/art/runtime/lock_word.h" \
    "$A/art/runtime/oat.h" \
    "$A/art/runtime/oat_file.h" \
    "$A/art/runtime/process_state.h" \
    "$A/art/runtime/reflective_value_visitor.h" \
    "$A/art/runtime/stack.h" \
    "$A/art/runtime/suspend_reason.h" \
    "$A/art/runtime/thread.h" \
    "$A/art/runtime/thread_state.h" \
    "$A/art/runtime/trace.h" \
    "$A/art/runtime/verifier/verifier_enums.h" || exit 1

# Generate the target-width assembly contract from the exact AOSP .def files.
# The historical source checkout may contain an untracked ARM32 asm_defines.h;
# consuming it in an ARM64 generation would silently bake wrong thread/frame
# offsets into ART assembly.  Never edit or trust that source-tree artifact.
# The generated overlay is first in both C++ and assembler include order.
ASM_DEFINES_SOURCE="$A/art/tools/cpp-define-generator/asm_defines.cc"
ASM_DEFINES_INCLUDE="$A/art/tools/cpp-define-generator"
ASM_DEFINES_ASM="$GENERATED_DIR/asm_defines.s"
ASM_DEFINES="$GENERATED_DIR/asm_defines.h"
ASM_DEFINES_TMP="$ASM_DEFINES.tmp"
if ! $CXXF $ART_DEFS $ART_INC -I"$ASM_DEFINES_INCLUDE" \
        -S "$ASM_DEFINES_SOURCE" -o "$ASM_DEFINES_ASM" \
        2>"$OBJ_ROOT/logs/asm_defines_generate.err"; then
    echo "ERROR: failed to compile exact ARM64 asm_defines contract" >&2
    exit 1
fi
if ! "$PYTHON" "$ASM_DEFINES_INCLUDE/make_header.py" "$ASM_DEFINES_ASM" \
        >"$ASM_DEFINES_TMP"; then
    echo "ERROR: failed to extract exact ARM64 asm_defines header" >&2
    exit 1
fi
mv "$ASM_DEFINES_TMP" "$ASM_DEFINES"

# ============================================================
# Layer 1: bionic_compat
# ============================================================
echo ""
echo "--- Layer 1: bionic_compat ---"
# ============================================================
# Pre-build validation: generated asm_defines.h must be ARM64.
# ============================================================
if ! grep -q '^#define POINTER_SIZE 0x8$' "$ASM_DEFINES" 2>/dev/null \
        || ! grep -q '^#define POINTER_SIZE_SHIFT 0x3$' "$ASM_DEFINES" 2>/dev/null; then
    if [ "$STRICT_BUILD" = 1 ]; then
        echo "ERROR: asm_defines.h missing exact POINTER_SIZE 0x8" >&2
        exit 1
    fi
    echo "  WARN: asm_defines.h missing/not 0x8 (ARM64) — libart .S may fail"
else
    echo "  asm_defines.h: POINTER_SIZE=0x8 (ARM64) OK"
fi

bld bionic_compat "-I$OH/base/startup/init/interfaces/innerkits/include/syspara -DPARAM_VALUE_LEN_MAX=96 -nostdinc++ -Wno-constant-conversion" \
    $BC_SRC/system_properties.cpp $BC_SRC/malloc_compat.cpp $BC_SRC/fdsan_stubs.cpp $BC_SRC/misc_compat.cpp $BC_SRC/abort_message_compat.cpp $BC_SRC/liblog_android_supplement.cpp $BC_SRC/sync_builtins.c

# ============================================================
# Layer 2: AOSP base libraries
# ============================================================
echo ""
echo "--- Layer 2: AOSP base libs ---"
bld log "-I$A/system/logging/liblog/include -I$A/system/libbase/include -I$A/system/core/libcutils/include -I$A/system/core/include -DLIBLOG_LOG_TAG=1006 -DSNET_EVENT_LOG_TAG=1397638484" \
    $A/system/logging/liblog/log_event_list.cpp $A/system/logging/liblog/log_event_write.cpp $A/system/logging/liblog/logger_name.cpp $A/system/logging/liblog/logger_read.cpp $A/system/logging/liblog/logger_write.cpp $A/system/logging/liblog/logprint.cpp $A/system/logging/liblog/properties.cpp $A/system/logging/liblog/event_tag_map.cpp $A/system/logging/liblog/log_time.cpp $ADAPTER_ROOT/framework/core/jni/android_log_hilog_bridge.cpp

bld base "-I$A/system/libbase/include -I$A/system/logging/liblog/include -I$A/system/core/include -I$A/system/core/libcutils/include -I$A/external/fmtlib/include -DANDROID_BASE_UNIQUE_FD_DISABLE_FDSAN -fno-exceptions -UNDEBUG" \
    $A/system/libbase/abi_compatibility.cpp $A/system/libbase/chrono_utils.cpp $A/system/libbase/cmsg.cpp $A/system/libbase/errors_unix.cpp $A/system/libbase/file.cpp $A/system/libbase/hex.cpp $A/system/libbase/logging.cpp $A/system/libbase/mapped_file.cpp $A/system/libbase/parsebool.cpp $A/system/libbase/parsenetaddress.cpp $A/system/libbase/posix_strerror_r.cpp $A/system/libbase/process.cpp $A/system/libbase/properties.cpp $A/system/libbase/stringprintf.cpp $A/system/libbase/strings.cpp $A/system/libbase/threads.cpp \
    $A/external/fmtlib/src/format.cc

bld cutils "-I$A/system/core/libcutils/include -I$A/system/logging/liblog/include -I$A/system/libbase/include -I$A/system/core/include -I$A/external/fmtlib/include" \
    $A/system/core/libcutils/config_utils.cpp $A/system/core/libcutils/hashmap.cpp $A/system/core/libcutils/iosched_policy.cpp $A/system/core/libcutils/load_file.cpp $A/system/core/libcutils/native_handle.cpp $A/system/core/libcutils/properties.cpp $A/system/core/libcutils/record_stream.cpp $A/system/core/libcutils/socket_inaddr_any_server_unix.cpp $A/system/core/libcutils/socket_local_client_unix.cpp $A/system/core/libcutils/socket_local_server_unix.cpp $A/system/core/libcutils/socket_network_client_unix.cpp $A/system/core/libcutils/sockets_unix.cpp $A/system/core/libcutils/sockets.cpp $A/system/core/libcutils/str_parms.cpp $A/system/core/libcutils/threads.cpp $A/system/core/libcutils/trace-dev.cpp

bld utils "-I$A/system/core/libutils/include -I$A/system/core/libcutils/include -I$A/system/logging/liblog/include -I$A/system/libbase/include -I$A/system/core/include -I$A/system/core/libprocessgroup/include -I$A/system/core/libvndksupport/include -I$A/external/fmtlib/include" \
    $A/system/core/libutils/Errors.cpp $A/system/core/libutils/FileMap.cpp $A/system/core/libutils/JenkinsHash.cpp $A/system/core/libutils/LightRefBase.cpp $A/system/core/libutils/Looper.cpp $A/system/core/libutils/NativeHandle.cpp $A/system/core/libutils/Printer.cpp $A/system/core/libutils/RefBase.cpp $A/system/core/libutils/SharedBuffer.cpp $A/system/core/libutils/StopWatch.cpp $A/system/core/libutils/String8.cpp $A/system/core/libutils/String16.cpp $A/system/core/libutils/StrongPointer.cpp $A/system/core/libutils/SystemClock.cpp $A/system/core/libutils/Threads.cpp $A/system/core/libutils/Timers.cpp $A/system/core/libutils/Tokenizer.cpp $A/system/core/libutils/Unicode.cpp $A/system/core/libutils/VectorImpl.cpp

bld nativehelper "-I$A/libnativehelper/include -I$A/libnativehelper/include_jni -I$A/libnativehelper/header_only_include -I$A/system/logging/liblog/include -I$A/system/libbase/include -I$A/system/core/include" \
    $A/libnativehelper/JNIHelp.c $A/libnativehelper/JniInvocation.c $A/libnativehelper/JniConstants.c $A/libnativehelper/JNIPlatformHelp.c $A/libnativehelper/DlHelp.c $A/libnativehelper/ExpandableString.c $A/libnativehelper/file_descriptor_jni.c

# ============================================================
# Layer 3: ART sub-libraries
# ============================================================
echo ""
echo "--- Layer 3: ART sub-libraries ---"
# D600 production images do not guarantee a /system/lib/libc_musl.so alias.
# A vanilla AOSP14 host-musl sigchain therefore aborts in its static
# constructor before ART can start. Keep the external AOSP tree read-only:
# copy the three sigchain sources into this generation and rewrite only the
# copied loader literal. This is a source-level build input, never a binary
# patch and never a device-side symlink dependency.
SIGCHAIN_GENERATED_DIR="$OBJ_ROOT/generated/sigchain"
SIGCHAIN_PATCH_SRC="$SIGCHAIN_GENERATED_DIR/sigchain.cc"
mkdir -p "$SIGCHAIN_GENERATED_DIR"
cp -f "$A/art/sigchainlib/sigchain.cc" "$SIGCHAIN_PATCH_SRC"
cp -f "$A/art/sigchainlib/sigchain.h" "$SIGCHAIN_GENERATED_DIR/sigchain.h"
cp -f "$A/art/sigchainlib/log.h" "$SIGCHAIN_GENERATED_DIR/log.h"

SIGCHAIN_OLD_LITERAL_COUNT=$(grep -F -c '"libc_musl.so"' "$SIGCHAIN_PATCH_SRC" || true)
SIGCHAIN_FIXED_LITERAL_COUNT=$(grep -F -c '"libc.so"' "$SIGCHAIN_PATCH_SRC" || true)
# AOSP also has an independent __BIONIC__ "libc.so" branch. Accept either the
# vanilla host-musl literal (one old + one Bionic fixed) or an already-closed
# source (zero old + Bionic and host-musl fixed). Reject every other shape.
if ! { [ "$SIGCHAIN_OLD_LITERAL_COUNT" -eq 1 ] &&
        [ "$SIGCHAIN_FIXED_LITERAL_COUNT" -eq 1 ]; } &&
        ! { [ "$SIGCHAIN_OLD_LITERAL_COUNT" -eq 0 ] &&
            [ "$SIGCHAIN_FIXED_LITERAL_COUNT" -eq 2 ]; }; then
    echo "ERROR: unexpected AOSP14 sigchain libc literal counts: libc_musl.so=$SIGCHAIN_OLD_LITERAL_COUNT libc.so=$SIGCHAIN_FIXED_LITERAL_COUNT" >&2
    exit 1
fi
sed -i 's/"libc_musl\.so"/"libc.so"/g' "$SIGCHAIN_PATCH_SRC"
if grep -F -q '"libc_musl.so"' "$SIGCHAIN_PATCH_SRC" ||
        ! grep -F -q '"libc.so"' "$SIGCHAIN_PATCH_SRC"; then
    echo "ERROR: sigchain generation-owned source rewrite did not close" >&2
    exit 1
fi

bld sigchain "$ART_DEFS $ART_INC -fno-rtti -DHAVE_SIGCHAIN -I$SIGCHAIN_GENERATED_DIR" \
    "$SIGCHAIN_PATCH_SRC"

if strings "$O/libsigchain.so" | grep -F -q 'libc_musl.so' ||
        ! strings "$O/libsigchain.so" | grep -F -q 'libc.so'; then
    echo "ERROR: libsigchain.so retained libc_musl.so or lost libc.so" >&2
    exit 1
fi

bld artpalette "$ART_DEFS $ART_INC -fno-rtti" $A/art/libartpalette/apex/palette.cc

# OpenHarmony target provider: real Android managed-priority -> Linux nice
# semantics; remaining unsupported platform capabilities are explicit and
# never report functional success. Do not ship AOSP's host-only palette_fake.
bld artpalette-system "$ART_DEFS $ART_INC -fno-rtti" \
    $ADAPTER_ROOT/framework/art-palette-oh/src/palette_oh.c

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
        -not -name "*aarch32*" \
        | sort)
    # vixl_math_fix.h no longer needed: isnan/isinf/signbit fixes now in libcxx_compat.h
    bld vixl "-I$A/external/vixl/src -DVIXL_INCLUDE_TARGET_A64 -DVIXL_CODE_BUFFER_MALLOC -DVIXL_GENERATE_SIMULATOR_INSTRUCTIONS_VALUE=0" $VIXL_FILES
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

# AOSP libelffile consumes the SDK LZMA implementation as liblzma.  Build the
# exact non-Windows Android.bp source set before libelffile instead of relying
# on an unrelated platform library or leaving XZ symbols unresolved.
echo ""
echo "--- Layer 3: LZMA ---"
LZMA_DIR=$A/external/lzma/C
bld lzma "-DZ7_ST -I$LZMA_DIR -Wno-empty-body -Wno-enum-conversion -Wno-logical-op-parentheses -Wno-self-assign" \
    $LZMA_DIR/7zAlloc.c \
    $LZMA_DIR/7zArcIn.c \
    $LZMA_DIR/7zBuf2.c \
    $LZMA_DIR/7zBuf.c \
    $LZMA_DIR/7zCrc.c \
    $LZMA_DIR/7zCrcOpt.c \
    $LZMA_DIR/7zDec.c \
    $LZMA_DIR/7zFile.c \
    $LZMA_DIR/7zStream.c \
    $LZMA_DIR/Aes.c \
    $LZMA_DIR/AesOpt.c \
    $LZMA_DIR/Alloc.c \
    $LZMA_DIR/Bcj2.c \
    $LZMA_DIR/Bra86.c \
    $LZMA_DIR/Bra.c \
    $LZMA_DIR/BraIA64.c \
    $LZMA_DIR/CpuArch.c \
    $LZMA_DIR/Delta.c \
    $LZMA_DIR/LzFind.c \
    $LZMA_DIR/Lzma2Dec.c \
    $LZMA_DIR/Lzma2Enc.c \
    $LZMA_DIR/Lzma86Dec.c \
    $LZMA_DIR/Lzma86Enc.c \
    $LZMA_DIR/LzmaDec.c \
    $LZMA_DIR/LzmaEnc.c \
    $LZMA_DIR/LzmaLib.c \
    $LZMA_DIR/Ppmd7.c \
    $LZMA_DIR/Ppmd7Dec.c \
    $LZMA_DIR/Ppmd7Enc.c \
    $LZMA_DIR/Sha256.c \
    $LZMA_DIR/Sha256Opt.c \
    $LZMA_DIR/Sort.c \
    $LZMA_DIR/Xz.c \
    $LZMA_DIR/XzCrc64.c \
    $LZMA_DIR/XzCrc64Opt.c \
    $LZMA_DIR/XzDec.c \
    $LZMA_DIR/XzEnc.c \
    $LZMA_DIR/XzIn.c

# ============================================================
# Layer 3: ziparchive (used by ART for DEX/APK files)
# ============================================================
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

# ART base/dex are placed after their strict direct providers.  Soong normally
# solves this graph; the standalone producer must make the same order explicit.
bld tinyxml2 "-I$A/external/tinyxml2 -Wno-implicit-fallthrough" \
    $A/external/tinyxml2/tinyxml2.cpp

bld artbase "$ART_DEFS $ART_INC -fno-rtti" \
    $(ls $A/art/libartbase/base/*.cc \
         $A/art/libartbase/base/unix_file/*.cc \
         $A/art/libartbase/base/metrics/*.cc \
         $A/art/libartbase/arch/*.cc 2>/dev/null \
      | grep -v test | grep -v windows | grep -v fuchsia) \
    "$ARTBASE_OPERATOR_SRC"

bld dexfile "$ART_DEFS $ART_INC -fno-rtti" \
    $(ls $A/art/libdexfile/dex/*.cc | grep -v test) \
    "$A/art/libdexfile/external/dex_file_ext.cc" \
    "$DEXFILE_OPERATOR_SRC"

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

bld elffile "$ART_DEFS $ART_INC -fno-rtti -I$A/art/libelffile/include -I$A/external/lzma/C" \
    $A/art/libelffile/stream/file_output_stream.cc \
    $A/art/libelffile/stream/vector_output_stream.cc \
    $A/art/libelffile/stream/output_stream.cc \
    $A/art/libelffile/stream/buffered_output_stream.cc \
    $A/art/libelffile/elf/xz_utils.cc

bld nativebridge "$ART_DEFS $ART_INC -fno-rtti -I$A/art/libnativebridge/include" \
    $A/art/libnativebridge/native_bridge.cc

# L03.A12 Profile B: the adapter owns libnativeloader at the OS/native-loader
# boundary. Never compile the executor's potentially dirty AOSP libnativeloader
# working tree into a product generation.
bld nativeloader "$ART_DEFS $ART_INC -fno-rtti -I$ADAPTER_ROOT/framework/native-loader-oh/src -I$ADAPTER_ROOT/framework/app-native-loader/include -I$ADAPTER_ROOT/framework/native-compat/bionic-pthread-bridge/include" \
    "$ADAPTER_ROOT/framework/native-loader-oh/src/native_loader.cpp" \
    "$ADAPTER_ROOT/framework/native-loader-oh/src/native_loader_registry.cpp" \
    "$ADAPTER_ROOT/framework/native-loader-oh/src/system_loader.cpp"

bld profile "$ART_DEFS $ART_INC -fno-rtti" \
    $A/art/libprofile/profile/profile_compilation_info.cc \
    $A/art/libprofile/profile/profile_boot_info.cc

# libunwindstack: complete common AOSP source set. Exclusion beyond tests:
#   LogStdout.cpp      — alternate Log impl for libunwindstack_stdout_log variant;
#                        duplicate symbols with LogAndroid.cpp
# AOSP's own rustc-demangle C stub is linked exactly as its Android.bp
# whole_static_libs contract; C++ demangling stays real through __cxa_demangle.
# libdexfile_support is compiled with STATIC_LIB so its function pointers bind
# directly to the real libdexfile external API without dlopen fallbacks.
UNWIND_DIR=$A/system/unwinding/libunwindstack
UNWIND_FILES=$(find $UNWIND_DIR -maxdepth 1 -name "*.cpp" \
    -not -name "*Test*" -not -name "*_test*" -not -name "*Benchmark*" \
    -not -name "LogStdout.cpp" \
    2>/dev/null | sort)
bld unwindstack "-include $ADAPTER_ROOT/build/compat/musl_tgkill_compat.h -DDEXFILE_SUPPORT -DSTATIC_LIB -I$UNWIND_DIR/include -I$A/system/libbase/include -I$A/system/logging/liblog/include -I$A/system/extras/libprocinfo/include -I$A/art/libdexfile/external/include -I$A/external/rust/crates/rustc-demangle-capi -I$A/external/lzma/C -Wno-deprecated-declarations -Wno-unused-parameter -Wno-missing-field-initializers -fno-exceptions" \
    $UNWIND_FILES \
    $A/art/libdexfile/external/dex_file_supp.cc \
    $A/external/rust/crates/rustc-demangle-capi/stub.c


# ============================================================
# Layer 3: ART Runtime (largest component)
# ============================================================
echo ""
echo "--- Layer 3: ART Runtime ---"

# Collect runtime .cc files (exclude tests, non-arm arch, android-specific, LP64-only)
RUNTIME_FILES=$(find $A/art/runtime -name "*.cc" \
    -not -name "*test*" -not -path "*/test/*" -not -name "*gtest*" \
    -not -name "*_android.cc" \
    -not -path "*/arch/arm/*" -not -path "*/arch/x86/*" \
    -not -path "*/arch/x86_64/*" -not -path "*/arch/riscv64/*" \
    -not -name "statsd.cc" \
    | sort)

# Count source files
RUNTIME_COUNT=$(echo "$RUNTIME_FILES" | wc -l)
echo "  Runtime source files: $RUNTIME_COUNT .cc files"

# Generate nterp_arm64.S (ARM nterp dispatch loop) via gen_mterp.py so the
# interpreter does not recurse into C++ ExecuteSwitchImplCpp per Java method
# call. Without nterp each invocation consumed ~8 bytes of native stack; a
# 128 MB worker pthread still ran out before ClassLinker finished boot init.
NTERP_ARM_S="$OBJ_ROOT/art/nterp_arm64.S"
mkdir -p "$OBJ_ROOT/art"
"$PYTHON" "$A/art/runtime/interpreter/mterp/gen_mterp.py" "$NTERP_ARM_S" "$A"/art/runtime/interpreter/mterp/arm64ng/*.S
ls -la $NTERP_ARM_S | awk '{print "  nterp_arm64.S:", $5, "bytes"}'

# ARM assembly entrypoints: quick/jni/memcmp plus the freshly generated nterp.
# Earlier labelled as stubs because asm_support_gen.h was missing; bionic_compat
# ships an ARM32 asm_defines.h so the real entrypoints compile.
ASM_STUBS="$A/art/runtime/arch/arm64/quick_entrypoints_arm64.S $A/art/runtime/arch/arm64/jni_entrypoints_arm64.S $A/art/runtime/arch/arm64/memcmp16_arm64.S $NTERP_ARM_S"

# Include AOSP's arch/arm .cc files (C++ arch-specific code, NOT .S files)
ARM_CC=$(find $A/art/runtime/arch/arm64 -name "*.cc" -not -name "*test*" 2>/dev/null | sort)
# [ARM64-XREF 2026-06-25] arm64 libart references ArmInstructionSetFeatures via
# InstructionSetFeatures::AsArmInstructionSetFeatures; the find above excludes
# arch/arm wholesale, so add just that one cross-referenced .cc back.
ARM_CC="$ARM_CC $A/art/runtime/arch/arm/instruction_set_features_arm.cc"
# AOSP libart always compiles the feature decoders for every ISA because the
# common InstructionSetFeatures factory can parse non-host variants at runtime.
# Only their feature files are cross-ISA; target entrypoints/register code stays
# ARM64-only.
ARM_CC="$ARM_CC $A/art/runtime/arch/riscv64/instruction_set_features_riscv64.cc"
ARM_CC="$ARM_CC $A/art/runtime/arch/x86/instruction_set_features_x86.cc"
# [CPUFEAT-ARM64 2026-06-25] arch/arm64/instruction_set_features_arm64.cc calls
# cpu_features::GetAarch64Info(); compile the arm64 cpu_features impl + its
# utils/hwcaps support .c into libart (AOSP links libcpu_features statically).
CPU_FEATURES_SRC="$A/external/cpu_features/src/impl_aarch64_linux_or_android.c $A/external/cpu_features/src/filesystem.c $A/external/cpu_features/src/stack_line_reader.c $A/external/cpu_features/src/string_view.c $A/external/cpu_features/src/hwcaps.c"
ARM_CC="$ARM_CC $CPU_FEATURES_SRC"

# NOTE (2026-04-14): removed $BC_SRC/art_runtime_stubs.cpp from libart's own
# compilation. With -Wl,-Bsymbolic + the stub .cpp compiled inside libart,
# libart's internal references to OS::OpenFileForReading / FdFile::* bound to
# the stub copies (which use a different class layout than AOSP), causing
# ElfFile::Open to read garbage from FdFile objects. The ARM64 product producer
# now requires real typed providers for every remaining edge and emits no
# libart_runtime_stubs.so.
bld art "$ART_DEFS $ART_INC -fno-rtti -I$BC_SRC" \
    $RUNTIME_FILES $ARM_CC $ASM_STUBS "$ART_OPERATOR_SRC" \
    "$ADAPTER_ROOT/framework/appspawn-x/src/art_abort_message_bridge.cpp"

# Layer 4: libart-compiler.so (JIT compiler)
echo "" >&2; echo "--- Layer 4: libart-compiler ---" >&2
COMPILER_SRCS_FILE="$OBJ_ROOT/libart_compiler_srcs.txt"
COMPILER_GEN_DIR="$OBJ_ROOT/art-compiler-gen"
mkdir -p "$COMPILER_GEN_DIR"
cat >"$COMPILER_SRCS_FILE" <<'EOF'
debug/elf_debug_writer.cc
dex/inline_method_analyser.cc
driver/compiler_options.cc
driver/dex_compilation_unit.cc
jit/jit_compiler.cc
jit/jit_logger.cc
jni/quick/calling_convention.cc
jni/quick/jni_compiler.cc
optimizing/block_builder.cc
optimizing/block_namer.cc
optimizing/bounds_check_elimination.cc
optimizing/builder.cc
optimizing/cha_guard_optimization.cc
optimizing/code_generator.cc
optimizing/code_generator_utils.cc
optimizing/code_sinking.cc
optimizing/constant_folding.cc
optimizing/constructor_fence_redundancy_elimination.cc
optimizing/data_type.cc
optimizing/dead_code_elimination.cc
optimizing/escape.cc
optimizing/execution_subgraph.cc
optimizing/graph_checker.cc
optimizing/graph_visualizer.cc
optimizing/gvn.cc
optimizing/induction_var_analysis.cc
optimizing/induction_var_range.cc
optimizing/inliner.cc
optimizing/instruction_builder.cc
optimizing/instruction_simplifier.cc
optimizing/intrinsic_objects.cc
optimizing/intrinsics.cc
optimizing/licm.cc
optimizing/linear_order.cc
optimizing/load_store_analysis.cc
optimizing/load_store_elimination.cc
optimizing/locations.cc
optimizing/loop_analysis.cc
optimizing/loop_optimization.cc
optimizing/nodes.cc
optimizing/optimization.cc
optimizing/optimizing_compiler.cc
optimizing/parallel_move_resolver.cc
optimizing/prepare_for_register_allocation.cc
optimizing/reference_type_propagation.cc
optimizing/register_allocation_resolver.cc
optimizing/register_allocator.cc
optimizing/register_allocator_graph_color.cc
optimizing/register_allocator_linear_scan.cc
optimizing/select_generator.cc
optimizing/scheduler.cc
optimizing/sharpening.cc
optimizing/side_effects_analysis.cc
optimizing/ssa_builder.cc
optimizing/ssa_liveness_analysis.cc
optimizing/ssa_phi_elimination.cc
optimizing/stack_map_stream.cc
optimizing/superblock_cloner.cc
optimizing/write_barrier_elimination.cc
trampolines/trampoline_compiler.cc
utils/assembler.cc
utils/jni_macro_assembler.cc
compiler.cc
jni/quick/arm64/calling_convention_arm64.cc
optimizing/code_generator_arm64.cc
optimizing/code_generator_vector_arm64_neon.cc
optimizing/code_generator_vector_arm64_sve.cc
optimizing/scheduler_arm64.cc
optimizing/instruction_simplifier_arm64.cc
optimizing/instruction_simplifier_shared.cc
optimizing/intrinsics_arm64.cc
optimizing/nodes_shared.cc
utils/arm64/assembler_arm64.cc
utils/arm64/jni_macro_assembler_arm64.cc
utils/arm64/managed_register_arm64.cc
EOF

COMPILER_SRCS=""
while IFS= read -r relative_source; do
    compiler_source="$A/art/compiler/$relative_source"
    [ -f "$compiler_source" ] || {
        echo "missing AOSP14 ART compiler source: $compiler_source" >&2
        exit 1
    }
    COMPILER_SRCS="$COMPILER_SRCS $compiler_source"
done <"$COMPILER_SRCS_FILE"

for operator_header in \
    linker/linker_patch.h \
    optimizing/locations.h \
    optimizing/nodes.h \
    optimizing/optimizing_compiler_stats.h \
    utils/arm/constants_arm.h
do
    operator_output="$COMPILER_GEN_DIR/${operator_header//\//_}.operator_out.cc"
    (
        cd "$A"
        "$PYTHON" art/tools/generate_operator_out.py \
            art/compiler "art/compiler/$operator_header"
    ) >"$operator_output"
done

bld art-compiler \
    "$ART_DEFS $ART_INC -fno-rtti -fvisibility=protected -I$A/art/compiler -I$A/art/dex2oat -I$BC_SRC" \
    $COMPILER_SRCS "$COMPILER_GEN_DIR"/*.cc


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
    local tmp=$(mktemp "$OBJ_ROOT/smoke_$$_XXXXXX")
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
smoke_needed artbase libziparchive.so
# libdexfile: ArtDexFileLoader is exported here (not libartbase)
smoke_check dexfile ArtDexFileLoader
# libart: core Runtime entry (VM create) + VIXL-linked JIT allocator proof
smoke_check art JNI_CreateJavaVM
# libnativehelper: JNI invocation shim used by appspawn-x
smoke_check nativehelper JniInvocationCreate
# libvixl: code buffer malloc allocator present (catches VIXL_CODE_BUFFER_MALLOC regression)
smoke_check vixl CodeBuffer

profile_b_check() {
    local loader="$O/libnativeloader.so"
    local art="$O/libart.so"
    local dynsym="$OBJ_ROOT/profile_b_nativeloader.dynsym"
    local dynamic="$OBJ_ROOT/profile_b_nativeloader.dynamic"
    local art_dynamic="$OBJ_ROOT/profile_b_art.dynamic"
    local symbol count
    if [ ! -f "$loader" ] || [ ! -f "$art" ]; then
        echo "  ❌ Profile B gate: libnativeloader.so or libart.so missing"
        BUILD_HAD_FAIL=1
        return 1
    fi
    "$READELF" --dyn-syms --wide "$loader" >"$dynsym" 2>/dev/null || :
    "$READELF" -d --wide "$loader" >"$dynamic" 2>/dev/null || :
    "$READELF" -d --wide "$art" >"$art_dynamic" 2>/dev/null || :
    for symbol in InitializeNativeLoader ResetNativeLoader \
                  CreateClassLoaderNamespace OpenNativeLibrary \
                  CloseNativeLibrary NativeLoaderFreeErrorMessage; do
        count=$(awk -v wanted="$symbol" '
            $1 ~ /^[0-9]+:$/ && NF >= 8 {
                name=$8; sub(/@.*/, "", name)
                if (name == wanted && $5 == "GLOBAL" && $6 == "DEFAULT" && $7 != "UND") count++
            }
            END {print count + 0}
        ' "$dynsym")
        if [ "$count" -ne 1 ]; then
            echo "  ❌ Profile B gate: $symbol provider count=$count"
            BUILD_HAD_FAIL=1
        fi
    done
    if grep -Eq '_ZN7android.*(NativeLoader|NativeLibrary|ClassLoaderNamespace)' "$dynsym"; then
        echo "  ❌ Profile B gate: C++-mangled NativeLoader export present"
        BUILD_HAD_FAIL=1
    fi
    if [ "$(awk -F'[][]' '/Shared library:/ && $2 == "libapp_native_loader.so" {count++} END {print count + 0}' "$dynamic")" -ne 1 ]; then
        echo "  ❌ Profile B gate: libnativeloader lacks one direct backend edge"
        BUILD_HAD_FAIL=1
    fi
    if [ "$(awk -F'[][]' '/Shared library:/ && $2 == "libnativeloader.so" {count++} END {print count + 0}' "$art_dynamic")" -ne 1 ]; then
        echo "  ❌ Profile B gate: libart lacks one direct libnativeloader edge"
        BUILD_HAD_FAIL=1
    fi
    if [ "$BUILD_HAD_FAIL" -eq 0 ]; then
        echo "  ✅ Profile B gate: raw-C provider + backend/art direct edges"
    fi
}

if [ "$STRICT_BUILD" = 1 ]; then
    profile_b_check
fi

echo "Build errors saved to: $ERRLOG"
echo "  Total error entries: $(grep -c "^=== FAIL:" "$ERRLOG" 2>/dev/null || echo 0)"

# Hard fail if any bld reported compile FAIL — prevents partial .so from
# silently overwriting a working device/local copy.
if [ $BUILD_HAD_FAIL -ne 0 ]; then
    echo ""
    echo "❌ BUILD FAILED: one or more targets had compile FAIL. See $ERRLOG"
    exit 1
fi
