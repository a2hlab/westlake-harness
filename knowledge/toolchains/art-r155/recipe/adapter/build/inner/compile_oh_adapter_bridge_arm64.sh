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
# [DEPRECATED Phase 1 — 2026-05-21] Use build_adapter.sh --target=liboh_adapter_bridge.so instead.
echo "[DEPRECATED] $(basename "$0") is wrapped by build_adapter.sh — Phase 4 will absorb this" >&2
# ============================================================================
# 重复犯错警示 (liboh_adapter_bridge.so 编译，调改前必读)
# ============================================================================
#
# [BR-1] sources 列表必须与 framework/jni/BUILD.gn 对齐 — 不要 glob
#   现象：bridge.so 编出来运行时报某个莫名 symbol 重复 / 类型冲突；或者把
#         apk_bundle_parser.cpp 这种本属于其他 .so 的文件错编进 bridge.so。
#   根因：早期版本用 find/glob 收集 sources，把 framework/ 下任意新 .cpp
#         都吃进来。BUILD.gn 是权威清单，glob 会悄悄漂移。
#   措施：sources 列表硬编 + post-flight 跟 BUILD.gn 的 sources 段比对，发现
#         drift 立即 fail。改 sources 时两边一起改。
#         （memory: feedback_bridge_sources_vs_buildgn.md）
#
# [BR-2] relaxed link 会把 undefined symbol 推到 runtime
#   现象：编译"成功"了，部署上去 dlopen 也不报错，等到第一次调那个函数时
#         dynamic linker 才崩，崩点离根因隔好几层。
#   根因：脚本里有 fallback "如果 strict link 失败，去掉 -Wl,--no-undefined
#         再来一遍"。一旦走到这条路径，UND 不会暴露在编译期。
#   措施：每次编完看 mode 输出（strict / relaxed），strict 才算过；relaxed
#         模式必须 readelf -d / nm -u 把 UND 全列出来确认每个都能 runtime
#         找到。bridge 已经在 2026-04-22 升级 strict (51 UND → 0)，禁止
#         为图省事退回 relaxed。
#         （memory: feedback_link_relaxed_hides_bugs.md / project_bridge_strict_link.md）
#
# [BR-3] 优先 inner_api，禁用 NDK 变体
#   现象：bridge.so 链接 libhilog_ndk.z.so 编过了，runtime 调 OH_LOG_Print
#         发现 hilog 收不到 — OH 系统服务和 adapter 一个体系，必须走 innerAPI。
#   根因：OH 同一功能有 NDK 和 innerAPI 两套库；adapter 是系统侧组件，必须
#         链 innerAPI（如 libhilog.so / HiLogPrint），而不是 app 用的 NDK 变体。
#   措施：每加新依赖前看 OH BUILD.gn 上游怎么链；innerAPI 一律带 .so 不带
#         _ndk 后缀。本脚本顶部 LIBS 段已注释每个 .so 是 innerAPI 还是 NDK。
#         （memory: feedback_prefer_inner_api.md）
#
# [BR-4] CRITICAL_JNI_PARAMS_COMMA __ANDROID__ 宏陷阱
#   现象：bridge 调 graphics_jni_helpers 相关 @CriticalNative 方法时栈错位 SIGSEGV，
#         参数顺序看着对但 JNIEnv* 那一格变成了 jclass。
#   根因：graphics_jni_helpers.h 的 CRITICAL_JNI_PARAMS_COMMA 宏只在
#         #if defined(__ANDROID__) 时定义为 ""，否则定义成 "JNIEnv*, jclass,"。
#         OH 交叉编译没有 __ANDROID__，宏走错分支，函数签名跟 JVM ABI 不匹配。
#   措施：所有 graphics_jni_helpers 用法必须 patch 宏改成
#         #if defined(__ANDROID__) || defined(__OHOS__)。改 bridge 引入新
#         JNI helper 前确认这条 patch 还在。
#         （memory: feedback_critical_native_abi_macro.md）
#
# [BR-5] OH 内部类跨 .so dynamic_cast / typeid 失败
#   现象：bridge 拿到 OH 系统服务的对象 dynamic_cast<XxxImpl*> 总返 nullptr，
#         或 typeid 比较两边的 type_info 地址不同。
#   根因：两种 case 分流：(R) RTTI 不对齐（class 在 .so A 编译时 RTTI 走
#         emit-everywhere，.so B 走 fno-rtti），或 (H) class 真有 hidden
#         visibility，跨 .so 拿不到 type_info。
#   措施：用 build/inspect_rtti.py 分流后再 fix，治法天差地别 — Case R 改
#         编译参数对齐，Case H 加 -fvisibility 注解或绕开 dynamic_cast。
#         （memory: feedback_oh_internal_class_no_export.md /
#                   feedback_skia_rtti_pure_object_cast.md）
#
# [BR-6] 跨编译参数与 AOSP 原生对齐 (-fno-rtti / __OHOS__ 等)
#   现象：bridge 编过、运行时 SIGSEGV / 类型错乱，先怀疑 mature lib 内 bug，
#         结果是编译参数和 AOSP 不一致引入 ODR 违规。
#   根因：项目铁律：Android/OH 都成熟，遇运行问题第一嫌疑是 adapter 层的
#         编译参数 / stub / 链接顺序，不是 mature lib。
#   措施：bridge 任何 -D / -isystem / -fno-rtti / -fvisibility 调整必须先对照
#         AOSP/OH 原生 Android.bp / BUILD.gn 一致再加。
#         （memory: feedback_compile_align_aosp.md / feedback_blame_adapter_first.md）
#
# [BR-7] 不要去改 framework/jni/BUILD.gn 加 -I / external_deps（2026-05-08 G2.14w）
#   现象：以为 oh_adapter_bridge.so 通过 OH GN/ninja 编译，跑去改 BUILD.gn
#         加 -I 或 external_deps（如 "input:libmmi-client"），结果触发 ccache
#         全 miss + 暴露一连串 missing header 错误（jni.h / android/log.h /
#         window_*_stub.h / FrontBufferedStream.h / LOG_TAG redefine / Werror
#         unused-private-field / OccupiedAreaChangeInfo 等），陷入"补一个 -I
#         又出新错"的雪崩 loop，浪费数小时。
#   根因：oh_adapter_bridge.so 实际编译路径是**本脚本**（独立 cross-compile，
#         bypass GN），framework/jni/BUILD.gn 是历史遗留不参与实际构建。
#         之前编出的 .so 是本脚本的产物，不是 GN 的产物；"GN 路径下 ccache
#         偶尔命中"是项目历史 cflags 残留，跟当前 BUILD.gn 是否能干净编通
#         没关系。改 BUILD.gn 不影响本脚本编出的产物，但会让所有走 GN 路径
#         的诊断行为产生误导。
#   措施：添加新 OH inner_api 依赖时直接在本脚本内改：
#         · INCLUDES 段加 `-I$OH/foundation/<subsystem>/.../include`
#         · LIBS 段加 `-l<lib_name>`
#         · ldflags / -L 段加对应 lib 输出目录（如 -L$PSDK / -L$SYSLIB）
#         编完 ssh + scp 拉回本机 out/adapter/，BUILD.gn 完全不动。
#         首次接手项目时如不确定，先看 doc/build_and_deployment_design.html
#         §1.1 类别 ⑤（"Adapter C++ 编译 = 独立 clang++ 脚本"）确认入口
#         再动手。framework/jni/BUILD.gn 文件头有详细警示注释，看完再改。
#         （memory: feedback_real_bridge_first.md / feedback_understand_before_act.md）
#
# ============================================================================
# compile_oh_adapter_bridge.sh — standalone cross-compile liboh_adapter_bridge.so
#
# Bypasses OH GN/ninja build system. Uses OH clang + aarch64-linux-ohos musl
# target directly, mirroring build/cross_compile_arm32.sh pattern.
#
# Rationale (feedback.txt Path 2, 2026-04-17):
#   framework/jni/BUILD.gn triggers OH cross-component include isolation rule
#   (BUILDCONFIG.gn:1068) because its include_dirs reference //foundation/xxx/
#   headers directly. Cleaning that up requires exposing every dependency as
#   proper OH inner_api with header_base metadata — multi-day structural work.
#   Standalone cross-compile sidesteps this entirely: we control the include
#   paths, link flags, and NEEDED set without needing GN's cooperation.
#
# Output: $ADAPTER_ROOT/out/adapter/liboh_adapter_bridge.so
#   - DT_NEEDED: full list of OH innerAPI + AOSP libs used at runtime
#   - DT_RUNPATH: /system/android/lib (for libnativehelper.so etc.)
#
# Usage:
#   cd ~/adapter && bash build/compile_oh_adapter_bridge.sh
#   bash build/compile_oh_adapter_bridge.sh --clean    # wipe $TMP before build

set -o pipefail

ADAPTER_ROOT="${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
AOSP="${AOSP_ROOT:-$HOME/aosp}"
OH="${OH_ROOT:-$HOME/oh}"
OH_PRODUCT="${OH_PRODUCT_NAME:-wukong100}"
OH_OUT="$OH/out/$OH_PRODUCT"
PM_SOURCE_ROOT="${PACKAGE_MANAGER_SOURCE_ROOT:-$ADAPTER_ROOT/framework/package-manager}"
OH_APPKIT_APP_ROOT="$OH/foundation/ability/ability_runtime/interfaces/kits/native/appkit/app"
OH_ABILITY_STAGE_ROOT="$OH/foundation/ability/ability_runtime/interfaces/kits/native/appkit/ability_runtime/app"
OH_RUNTIME_ROOT="$OH/foundation/ability/ability_runtime/interfaces/inner_api/runtime/include"
OUT="${ADAPTER_OUT_DIR:-$ADAPTER_ROOT/out/adapter}"
TMP="${BRIDGE_OBJ_DIR:-/tmp/cc100/bridge_build}"
WLTG_REGISTRY="$OUT/libwestlake_thread_guard_registry.so"
STRICT_BUILD="${L03_A12_STRICT_BUILD:-0}"

case "$STRICT_BUILD" in
    0|1) ;;
    *) echo "ERROR: L03_A12_STRICT_BUILD must be 0 or 1" >&2; exit 2 ;;
esac
if [ -n "${L03_A12_GENERATION_ID:-}" ]; then
    : "${ADAPTER_OUT_DIR:?generation build requires ADAPTER_OUT_DIR}"
    : "${BRIDGE_OBJ_DIR:?generation build requires BRIDGE_OBJ_DIR}"
    : "${AOSP_LIB_DIR:?generation build requires AOSP_LIB_DIR}"
    : "${L03_A12_CXX:?generation build requires L03_A12_CXX}"
    : "${L03_A12_READELF:?generation build requires L03_A12_READELF}"
    : "${L03_A12_BUILTINS:?generation build requires L03_A12_BUILTINS}"
    : "${L03_A12_LIBCXX_INCLUDE:?generation build requires L03_A12_LIBCXX_INCLUDE}"
    if [ "$TMP" = /tmp/cc100/bridge_build ] \
        || [ "$OUT" = "$ADAPTER_ROOT/out/adapter" ]; then
        echo "ERROR: generation bridge build resolved to a shared path" >&2
        exit 2
    fi
    if [ ! -e "$OH_OUT/obj/third_party/musl/usr/include/aarch64-linux-ohos/bits/alltypes.h" ]; then
        echo "ERROR: generation bridge build requires the pinned OH product sysroot" >&2
        exit 2
    fi
fi

if [ "${1:-}" = "--clean" ]; then
    echo "--clean: wiping $TMP"
    rm -rf "$TMP"
fi
mkdir -p "$OUT" "$TMP"
[ -f "$WLTG_REGISTRY" ] || {
    echo "ERROR: current R45 registry artifact missing: $WLTG_REGISTRY" >&2
    exit 1
}

# ============================================================
# Toolchain (same as cross_compile_arm32.sh / compile_jni_chain.sh)
# ============================================================
SR="$OH_OUT/obj/third_party/musl/usr"
ML="$SR/lib/aarch64-linux-ohos"
CXX="$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++"
BUILTINS="$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a"

# ============================================================
# [single-dir stub route — 2026-07-10, doc-versioning: additive, non-destructive]
# When a full OH platform tree ($OH_ROOT/out/wukong100) is NOT present, fall back
# to the OH SDK's aarch64 musl sysroot + toolchain, and resolve the OH platform
# inner_api .z libs from the vendored symbol stubs in third_party/oh_stubs/lib.
# The original $OH-based SR/ML/CXX above are preserved and still used verbatim
# whenever the OH tree IS present (full-OH builds are unaffected).
#
# SCOPE (round2, superseded below): this closes the SYSROOT + LINK dimensions of a
# single-directory build. The COMPILE step still needs OH inner_api / generated /
# skia HEADERS (the -I$OH/foundation/... and $OH/out/.../gen/... paths). Round2
# treated those headers as an unfinished "separate vendoring task."
#
# [round3 UPDATE — 2026-07-10, doc-versioning: additive; corrects round2's verdict]
# The COMPILE dimension is now CLOSED, and the user's binding constraint was
# relaxed to: "the final build must be self-contained in THIS adapter directory;
# no OTHER external code may enter a compile unit — EXCEPT OH source + AOSP source,
# which MAY be external." Under that rule the bridge fully builds:
#   - COMPILER: OH SDK aarch64 clang++ (external tool — allowed).
#   - COMPILE inputs: (a) IN-DIR adapter sources framework/*/jni/*.cpp; (b) IN-DIR
#     headers: framework/** , hwui-shim/skia_compat_headers, bionic_compat shim,
#     and build/oh_headers_631_overlay (4 device-6.1.0.31 interface headers, now
#     wired via INCS_OVERLAY_631 below); (c) EXTERNAL OH source tree headers
#     (foundation/base/third_party incl. skia m133 + built out/<board>/gen); (d)
#     EXTERNAL AOSP source tree headers. NOTHING from Noice / WestLake adapter
#     mirrors / GZ05 host enters a compile unit.
#   - LINK inputs: IN-DIR third_party/oh_stubs (OH platform ABI) + EXTERNAL AOSP
#     libs + SDK builtins → strict AArch64 ELF64, no relaxed fallback.
# RESULT (device-independent, host cross-compile on darwin): 39/39 .cpp -> .o,
# strict link -> 1.4M liboh_adapter_bridge.so (ELF64/AArch64, 32 DT_NEEDED, 465
# runtime-resolvable UND). "Single-directory compilable (+ OH/AOSP external
# source)" = ACHIEVED. See build/oh_headers_631_overlay/HEADERS_MANIFEST.md.
#
# CAVEAT (SDK-toolchain libcxx skew): the OH SDK's libcxx-ohos (6.1.0.105,
# _LIBCPP_VERSION 15004) already ships std::__promote, std::span (in C++17), and
# proper math/abs — but the IN-DIR force-include framework/appspawn-x/bionic_compat/
# include/libcxx_compat.h POLYFILLS all of those (it was calibrated for the OLDER
# OH-tree libcxx that lacked them), so under the SDK compiler those 4 blocks clash
# (ambiguous std::__promote, redefined isinf, etc.). Two clean resolutions, pick one:
#   (A) build with the EXTERNAL OH source tree's OWN clang (prebuilts/clang) — the
#       shim matches it as-is (this is the historical GZ05 build); OR
#   (B) recalibrate libcxx_compat.h to no-op those 4 blocks when the target libcxx
#       already provides the symbol (guard on _LIBCPP_VERSION / __has_include).
# libcxx_compat.h is OUTSIDE this script's change scope; not edited here.
# ============================================================
OH_SDK="${OH_SDK:-/opt/17-TestLab/17.03-D600/apps/d600-sdk-full/native}"
OH_STUBS="$ADAPTER_ROOT/third_party/oh_stubs/lib"
# [single-dir round3 — 2026-07-10, additive] FORCE_OH_SDK=1 forces the SDK
# sysroot+toolchain even when an OH tree IS present. Needed when cross-building on
# a host that cannot execute the OH tree's own clang (e.g. running on darwin/macOS
# against a tree whose prebuilts/clang is a linux-x86_64 ELF). Default off: full-OH
# Linux builds keep using the OH tree toolchain verbatim (unchanged).
if [ "${FORCE_OH_SDK:-0}" = "1" ] \
   && [ -e "$OH_SDK/sysroot/usr/include/aarch64-linux-ohos/bits/alltypes.h" ]; then
    echo "[single-dir] FORCE_OH_SDK=1 -> OH SDK sysroot+toolchain $OH_SDK (6.1.0.105/api23)"
    SR="$OH_SDK/sysroot/usr"
    ML="$SR/lib/aarch64-linux-ohos"
    CXX="$OH_SDK/llvm/bin/clang++"
    BUILTINS="$(ls "$OH_SDK"/llvm/lib/clang/*/lib/aarch64-linux-ohos/libclang_rt.builtins.a 2>/dev/null | head -1)"
fi
if [ ! -e "$SR/include/aarch64-linux-ohos/bits/alltypes.h" ] \
   && [ -e "$OH_SDK/sysroot/usr/include/aarch64-linux-ohos/bits/alltypes.h" ]; then
    echo "[single-dir] OH tree sysroot absent -> OH SDK sysroot $OH_SDK/sysroot (6.1.0.105/api23)"
    SR="$OH_SDK/sysroot/usr"
    ML="$SR/lib/aarch64-linux-ohos"
    CXX="$OH_SDK/llvm/bin/clang++"
    BUILTINS="$(ls "$OH_SDK"/llvm/lib/clang/*/lib/aarch64-linux-ohos/libclang_rt.builtins.a 2>/dev/null | head -1)"
fi

# The JNI lifecycle seam in core/oh_environment.cpp is implemented by the
# canonical Fn01 package-manager owner, not by a header-only or stub provider.
# OHOSApplication also includes ability_stage.h from a second official appkit
# interface root.  Fail before compilation when either real source closure is
# absent; do not let a copied header or a later relaxed link hide the drift.
for required_bridge_input in \
    "$PM_SOURCE_ROOT/application_info/include/application_info_runtime_owner_v1.h" \
    "$PM_SOURCE_ROOT/application_info/src/application_info_runtime_owner_v1.cpp" \
    "$PM_SOURCE_ROOT/component_resolver/include/component_resolver_runtime_v1.h" \
    "$PM_SOURCE_ROOT/component_resolver/src/component_resolver_runtime_v1.cpp" \
    "$OH_APPKIT_APP_ROOT/ohos_application.h" \
    "$OH_ABILITY_STAGE_ROOT/ability_stage.h" \
    "$OH_RUNTIME_ROOT/runtime.h"; do
    if [ ! -f "$required_bridge_input" ] || [ -L "$required_bridge_input" ]; then
        echo "ERROR: required real adapter bridge input is missing or symlinked: $required_bridge_input" >&2
        exit 2
    fi
done

# A Route-A generation must link against reviewed product providers, never the
# project-local ABI-only stub DSOs.  The explicit root is manifest-covered by
# the generation orchestrator and is deliberately required even when a full OH
# output tree happens to be present: an implicit fallback would make the same
# source revision produce a different DT_NEEDED/ABI closure on another host.
if [ -n "${L03_A12_GENERATION_ID:-}" ]; then
    : "${L03_A12_OH_LINK_ROOT:?generation bridge build requires L03_A12_OH_LINK_ROOT}"
    [ -d "$L03_A12_OH_LINK_ROOT" ] && [ ! -L "$L03_A12_OH_LINK_ROOT" ] || {
        echo "ERROR: generation OH link root is missing or a symlink: $L03_A12_OH_LINK_ROOT" >&2
        exit 2
    }
    stub_root=$(cd "$ADAPTER_ROOT/third_party/oh_stubs/lib" && pwd -P)
    product_root=$(cd "$L03_A12_OH_LINK_ROOT" && pwd -P)
    [ "$product_root" != "$stub_root" ] || {
        echo "ERROR: Route-A generation forbids third_party/oh_stubs as product providers" >&2
        exit 2
    }
    OH_STUBS=$product_root
fi

# A generation never selects an SDK/tool fallback implicitly. The orchestrator
# passes the exact, manifest-covered compiler, readelf, and builtins archive.
CXX="${L03_A12_CXX:-$CXX}"
BUILTINS="${L03_A12_BUILTINS:-$BUILTINS}"
READELF="${L03_A12_READELF:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf}"

# ============================================================
# OH system lib paths for linker -L
# ============================================================
PSDK="$OH_OUT/packages/phone/system/lib64/platformsdk"
SDKSP="$OH_OUT/packages/phone/system/lib64/chipset-sdk-sp"
SDK="$OH_OUT/packages/phone/system/lib64/chipset-sdk"
SYSLIB="$OH_OUT/packages/phone/system/lib64"
NDK="$OH_OUT/packages/phone/system/lib64/ndk"
AOSPLIB="${AOSP_LIB_DIR:-$ADAPTER_ROOT/out/aosp_lib64}"

# ============================================================
# Compile flags (mirrors OH ohos_shared_library output + project defines)
# ============================================================
COMMON="--target=aarch64-linux-ohos --sysroot=$SR"
COMMON="$COMMON -I$SR/include/aarch64-linux-ohos"
COMMON="$COMMON -fPIC -O2 -std=c++17"
if [ -n "${L03_A12_GENERATION_ID:-}" ]; then
    COMMON="$COMMON -nostdinc++ -isystem $L03_A12_LIBCXX_INCLUDE -MMD -MP"
    COMMON="$COMMON -ffile-prefix-map=$ADAPTER_ROOT=. -fdebug-prefix-map=$ADAPTER_ROOT=."
fi
COMMON="$COMMON -D__OHOS__ -D__MUSL__ -D_LIBCPP_HAS_MUSL_LIBC -D_GNU_SOURCE"
COMMON="$COMMON -D_POSIX_SOURCE"
# LOG_TAG + OHOS_PLATFORM + SUPPORT_* come from ninja harvest; don't double-define here.
# libcxx-ohos nullptr_t / cstddef fix: force-include the libcxx compat shim
# used by cross_compile_arm32.sh for the same issue.
COMMON="$COMMON -include $ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include/libcxx_compat.h"
# Also force-include <sys/types.h> — OH headers relying on mode_t/pid_t may
# not pull it transitively under our -include shim.
COMMON="$COMMON -include sys/types.h"
COMMON="$COMMON -I$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include"
COMMON="$COMMON -Wno-unused-parameter -Wno-unused-variable -Wno-unused-function"
COMMON="$COMMON -Wno-format -Wno-sign-compare -Wno-missing-field-initializers"
COMMON="$COMMON -Wno-deprecated-declarations -Wno-c99-designator -Wno-gnu-designator"
COMMON="$COMMON -Wno-narrowing -Wno-c++11-narrowing"
COMMON="$COMMON -Wno-extern-c-compat -Wno-error"
# Align with OH default (-fno-rtti). OH inner polymorphic classes such as
# OHOS::AAFwk::AbilityConnectionStub emit vtable but NOT typeinfo (_ZTI),
# because their provider .so is compiled -fno-rtti. If bridge keeps default
# -frtti, Clang emits typeinfo for derived adapter class referencing parent
# typeinfo -> UND at runtime dlopen. See doc/compile_report.html §3.9.
COMMON="$COMMON -fno-rtti"

# Local adapter headers (same project, cross-referenced between jni dirs)
INCS_LOCAL="\
  -I$ADAPTER_ROOT \
  -I$ADAPTER_ROOT/framework/native-compat/jni-attach-admission/include \
  -I$ADAPTER_ROOT/framework/native-compat/thread-guard-registry/include \
  -I$ADAPTER_ROOT/framework/core/include \
  -I$ADAPTER_ROOT/framework/core/jni \
  -I$ADAPTER_ROOT/framework/activity/jni \
  -I$ADAPTER_ROOT/framework/window/jni \
  -I$ADAPTER_ROOT/framework/surface/jni \
  -I$ADAPTER_ROOT/framework/broadcast/jni \
  -I$ADAPTER_ROOT/framework/contentprovider/jni \
  -I$PM_SOURCE_ROOT/jni \
  -I$PM_SOURCE_ROOT/install_plan/include \
  -I$PM_SOURCE_ROOT/package_transaction/include \
  -I$PM_SOURCE_ROOT/package_query/include \
  -I$PM_SOURCE_ROOT/manifest_facts/include \
  -I$PM_SOURCE_ROOT/package_info/include \
  -I$PM_SOURCE_ROOT/application_info/include \
  -I$PM_SOURCE_ROOT/component_resolver/include \
  -I$PM_SOURCE_ROOT/package_layout/include \
  -I$PM_SOURCE_ROOT/resource_projection/include \
  -I$PM_SOURCE_ROOT/runtime_path_descriptor/include"

# OH inner_api headers (direct paths — OH GN would bring these via
# external_deps+header_base; we bypass GN so just include directly).
# NOTE: these point at $OH (the local tree). The single device-version
# (6.1.0.31 / api23) header source is the oh_mirror SHADOW applied after the
# ninja harvest below ([BR-8]); do NOT add per-subsystem override -I here.
INCS_OH="\
  -I$OH_APPKIT_APP_ROOT \
  -I$OH_ABILITY_STAGE_ROOT \
  -I$OH_RUNTIME_ROOT \
  -I$OH/foundation/ability/ability_runtime/interfaces/inner_api/ability_manager/include \
  -I$OH/foundation/ability/ability_runtime/interfaces/inner_api/app_manager/include \
  -I$OH/foundation/ability/ability_runtime/interfaces/inner_api/app_manager/include/appmgr \
  -I$OH/foundation/ability/ability_runtime/interfaces/inner_api/connectionobs_manager/include \
  -I$OH/foundation/ability/ability_runtime/interfaces/inner_api/ability_manager \
  -I$OH/foundation/ability/ability_base/interfaces/kits/native/uri/include \
  -I$OH/foundation/ability/ability_base/interfaces/kits/native/session_info/include \
  -I$OH/third_party/bounds_checking_function/include \
  -I$OH/foundation/graphic/graphic_2d/rosen/modules/2d_graphics/src \
  -I$OH/foundation/distributeddatamgr/data_share/interfaces/inner_api/provider/include \
  -I$OH/foundation/window/window_manager/interfaces/innerkits/wm \
  -I$OH/foundation/window/window_manager/interfaces/innerkits/dm \
  -I$OH/foundation/window/window_manager/window_scene/session/host/include \
  -I$OH/foundation/window/window_manager/window_scene/session/host/include/zidl \
  -I$OH/foundation/window/window_manager/wm/include \
  -I$OH/foundation/window/window_manager/wm/include/zidl \
  -I$OH_OUT/obj/third_party/openssl/build_all_generated/include \
  -I$OH/foundation/ability/ability_runtime/services/abilitymgr/include \
  -I$OH/foundation/ability/ability_runtime/interfaces/inner_api/dataobs_manager/include \
  -I$OH/foundation/graphic/graphic_2d/rosen/modules/render_service_client/core \
  -I$OH/foundation/graphic/graphic_2d/rosen/modules/render_service_base/core \
  -I$OH/foundation/graphic/graphic_2d/rosen/modules/render_service_base/include \
  -I$OH/foundation/graphic/graphic_2d/rosen/modules/2d_graphics/drawing_ndk/include \
  -I$OH/foundation/graphic/graphic_2d/interfaces/inner_api/common \
  -I$OH/foundation/graphic/graphic_2d/interfaces/inner_api \
  -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/surface \
  -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/buffer_handle \
  -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api \
  -I$OH/foundation/graphic/graphic_surface/interfaces \
  -I$OH/foundation/window/window_manager/window_scene/session_manager/include/zidl \
  -I$OH/foundation/window/window_manager/window_scene/session_manager_service/include \
  -I$OH_OUT/gen/foundation/window/window_manager/wmserver \
  -I$OH/foundation/window/window_manager/wmserver/include/zidl \
  -I$OH/foundation/distributeddatamgr/relational_store/interfaces/inner_api/rdb/include \
  -I$OH/foundation/multimodalinput/input/util/common/include \
  -I$OH/foundation/multimodalinput/input/interfaces/native/innerkits/proxy/include \
  -I$OH/foundation/multimodalinput/input/interfaces/native/innerkits/event/include \
  -I$OH/foundation/graphic/graphic_2d/rosen/modules/animation/window_animation/include \
  -I$OH/third_party/skia/m133/include/effects \
  -I$OH/third_party/skia/m133/include/utils \
  -I$OH/third_party/skia/m133/include/codec \
  -I$OH/third_party/skia/m133/client_utils/android \
  -I$OH/foundation/communication/ipc/interfaces/innerkits/ipc_core/include \
  -I$OH/foundation/communication/ipc/interfaces/innerkits/ipc_single/include \
  -I$OH/foundation/distributeddatamgr/data_share/interfaces/inner_api/consumer/include \
  -I$OH/foundation/distributeddatamgr/data_share/interfaces/inner_api/common/include \
  -I$OH/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_base/include \
  -I$OH/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_core/include \
  -I$OH/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_core/include/bundlemgr \
  -I$OH/foundation/bundlemanager/bundle_framework/services/bundlemgr/include \
  -I$OH/foundation/bundlemanager/bundle_framework/services/bundlemgr/include/quick_fix \
  -I$OH_OUT/gen/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_core \
  -I$OH/third_party/zlib/contrib/minizip \
  -I$OH/third_party/zlib \
  -I$OH/third_party/json/include \
  -I$OH/third_party/openssl/include \
  -I$OH/third_party/skia/m133/modules \
  -I$OH_OUT/gen/third_party/jsoncpp/jsoncpp-1.9.6/include \
  -I$OH/foundation/graphic/graphic_2d/utils/color_manager/export \
  -I$OH/foundation/window/window_manager/window_scene/interfaces/include \
  -I$OH/foundation/graphic/graphic_2d/rosen/modules/2d_graphics/include \
  -I$OH/foundation/ability/ability_base/interfaces/kits/native/want/include \
  -I$OH/foundation/ability/ability_base/interfaces/kits/native/configuration/include \
  -I$OH/foundation/ability/ability_base/interfaces/inner_api/base/include \
  -I$OH/base/hiviewdfx/hilog/interfaces/native/innerkits/include \
  -I$OH/base/hiviewdfx/hitrace/interfaces/native/innerkits/include/hitrace_meter \
  -I$OH/commonlibrary/c_utils/base/include \
  -I$OH/base/security/access_token/interfaces/innerkits/accesstoken/include \
  -I$OH/base/notification/common_event_service/interfaces/inner_api \
  -I$OH/base/notification/common_event_service/frameworks/core/include \
  -I$OH/base/startup/init/interfaces/innerkits/include \
  -I$OH/base/startup/init/services/param/base/include \
  -I$OH/foundation/systemabilitymgr/samgr/interfaces/innerkits/samgr_proxy/include \
  -I$OH/foundation/systemabilitymgr/safwk/interfaces/innerkits/safwk"

# AOSP cross-compiled headers (JNI, log, utils, cutils)
INCS_AOSP="\
  -I$AOSP/libnativehelper/include_jni \
  -I$AOSP/libnativehelper/include \
  -I$AOSP/libnativehelper/header_only_include \
  -I$AOSP/libnativehelper/include_platform \
  -I$AOSP/system/core/include \
  -I$AOSP/system/core/libutils/include \
  -I$AOSP/system/core/libcutils/include \
  -I$AOSP/system/logging/liblog/include \
  -I$AOSP/system/libbase/include \
  -I$AOSP/external/fmtlib/include \
  -I$AOSP/frameworks/base/libs/androidfw/include \
  -I$AOSP/frameworks/base/libs/hwui \
  -I$AOSP/frameworks/base/core/jni \
  -I$AOSP/frameworks/native/include"

# Skia (M133) headers — needed by android_view_surface_stubs + rs_surface_node chain
INCS_SKIA="-I$OH/third_party/skia/m133 -I$OH/third_party/skia/m133/include -I$OH/third_party/skia/m133/include/core"
# [single-dir round3 — 2026-07-10, additive, doc-versioning] skia_codec_register.cpp
# and color_space.h need include/codec + include/effects + include/utils roots too.
INCS_SKIA="$INCS_SKIA -I$OH/third_party/skia/m133/include/codec -I$OH/third_party/skia/m133/include/effects -I$OH/third_party/skia/m133/include/utils"
# [single-dir round3] SKIA REAL-PATH FALLBACK. In some OH source-tree checkouts
# $OH/third_party/skia/m133 is a symlink to a Linux bind-mount form
# (/mnt/mac/opt/.../16.12-HanBing/oh/third_party/skia/m133) that DANGLES when the
# tree is read on a host that does not have that mount (e.g. building on the mac
# directly). If the canonical skia header is unreadable, resolve skia from an
# explicit external OH source tree (OH/AOSP external source is the sanctioned
# exception). Override with R3_SKIA_ROOT if your OH checkout keeps skia elsewhere.
if [ ! -r "$OH/third_party/skia/m133/include/core/SkColorSpace.h" ]; then
    if [ -n "${L03_A12_GENERATION_ID:-}" ]; then
        echo "ERROR: generation build forbids external R3_SKIA_ROOT fallback" >&2
        exit 2
    fi
    R3_SKIA_ROOT="${R3_SKIA_ROOT:-/opt/10.Project/16-WestLake/16.12-HanBing/oh/third_party/skia/m133}"
    if [ -r "$R3_SKIA_ROOT/include/core/SkColorSpace.h" ]; then
        echo "[single-dir] OH skia m133 unreadable (dangling mount symlink?) -> external OH skia $R3_SKIA_ROOT"
        INCS_SKIA="-I$R3_SKIA_ROOT -I$R3_SKIA_ROOT/include -I$R3_SKIA_ROOT/include/core -I$R3_SKIA_ROOT/include/codec -I$R3_SKIA_ROOT/include/effects -I$R3_SKIA_ROOT/include/utils -I$R3_SKIA_ROOT/modules -I$R3_SKIA_ROOT/client_utils/android"
    else
        echo "WARN: skia m133 headers unreadable at both \$OH and R3_SKIA_ROOT; skia-touching .cpp will fail"
    fi
fi

# AOSP incfs (map_ptr.h used by libandroidfw)
INCS_AOSP_EXTRA="-I$AOSP/system/incremental_delivery/incfs/util/include"

# OH product headers.  EventRunner must come from the public eventhandler
# inner_api that matches libeventhandler.z; graphic_2d's private platform shim
# has a different one-argument Create ABI and must not shadow it.
INCS_OH_PLATFORM="\
  -I$OH/base/notification/eventhandler/interfaces/inner_api \
  -I$OH/foundation/graphic/graphic_2d/rosen/modules/platform/image_native \
"

# [single-dir round3 — 2026-07-10, additive, doc-versioning] WIRE THE IN-DIR
# 6.1.0.31 interface overlay (build/oh_headers_631_overlay). PREVIOUSLY UNWIRED:
# the overlay existed on disk with a README claiming an "INCS_OVERLAY_631" segment,
# but no such segment was present in this script — so on an OH source tree that is
# an OLDER api generation than the device (e.g. the api24 HanBing OH tree vs the
# 6.1.0.31 device), the bridge failed to compile with 8 "non-virtual member
# function marked 'override' hides virtual member function" errors on
# app_scheduler_adapter.h (ScheduleMemoryLevel 2->1 params) and
# session_stage_adapter.h (NotifyAppForceLandscapeConfigEnableUpdated 1->0 params).
# The overlay's 4 device-exact interface headers fix exactly these. We PREPEND the
# overlay so its headers shadow the OH tree's same-named files. NOTE the include
# LEVELS: session_stage_adapter.h includes "session/container/include/zidl/..." so
# the -I must be the window_scene PARENT (not the zidl leaf) for that prefix to
# resolve; app_scheduler needs the appmgr leaf + its include parent. Verified: with
# this prepend, an external OH source tree + external AOSP tree + this in-dir
# overlay compiles all 39 .cpp and strict-links a 1.4M AArch64 ELF64 bridge, with
# ZERO non-OH/non-AOSP external code in any compile unit (single-directory route
# ACHIEVED under the "OH+AOSP source may be external" exception). See
# build/oh_headers_631_overlay/HEADERS_MANIFEST.md.
OVL="$ADAPTER_ROOT/build/oh_headers_631_overlay"
INCS_OVERLAY_631="\
  -I$OVL/foundation/ability/ability_runtime/interfaces/inner_api/app_manager/include/appmgr \
  -I$OVL/foundation/ability/ability_runtime/interfaces/inner_api/app_manager/include \
  -I$OVL/foundation/window/window_manager/window_scene \
  -I$OVL/foundation/window/window_manager/window_scene/session/container/include/zidl"

INCS="$INCS_OVERLAY_631 $INCS_LOCAL $INCS_OH $INCS_AOSP $INCS_AOSP_EXTRA $INCS_SKIA $INCS_OH_PLATFORM"

# ============================================================
# Harvest -I paths from OH's own ninja plan for oh_adapter_bridge.
# OH GN already computed the correct include_dirs set (225 entries for rk3568);
# we reuse them as-is rather than hand-maintain a duplicate.
# Paths in ninja are relative to $OH/out/wukong100/ — prepend to get absolute.
# ============================================================
NINJA_FILE="$ADAPTER_ROOT/build/inner/oh_adapter_bridge.ninja.template"
if [ -f "$NINJA_FILE" ]; then
    harvested=$(grep '^include_dirs' "$NINJA_FILE" | head -1 \
        | tr ' ' '\n' | grep -E '^-I' \
        | sed "s|^-I\.\.\/\.\.\/|-I$OH/|" \
        | sed "s|^-I\.\.\/|-I$OH_OUT/|" \
        | tr '\n' ' ')
    INCS="$INCS $harvested"
    nlines=$(printf '%s\n' "$harvested" | wc -w)
    echo "Harvested $nlines -I paths from OH ninja plan"

    # Also harvest defines (USE_M133_SKIA, SUPPORT_GRAPHICS, etc.) — these
    # gate #ifdef branches inside OH headers that pick between legacy and
    # current include layouts (e.g. color_space.h skcms.h). Without these
    # defines, compile hits "include/third_party/skcms/skcms.h not found"
    # because the #else branch is active.
    harvested_defs=$(grep '^defines' "$NINJA_FILE" | head -1 \
        | tr ' ' '\n' | grep -E '^-D' \
        | tr '\n' ' ')
    ndefs=$(printf '%s\n' "$harvested_defs" | wc -w)
    COMMON="$COMMON $harvested_defs"
    echo "Harvested $ndefs -D defines from OH ninja plan"
else
    echo "WARN: OH ninja file not found at $NINJA_FILE; using hand-maintained flags only"
fi

# ============================================================
# [BR-8 / bridge_localize 2026-06-28] Device-version (6.1.0.31) header SHADOW.
#   The local HanBing OH tree is api24 (sdk 26.0.0.18); the device is OH
#   6.1.0.31 (api23). MANY inner_api structs the bridge marshals across IPC
#   (ApplicationInfo, Want, AbilityInfo, Configuration, ...) gained fields in
#   api24 -> parcel offset skew -> getApplicationInfo truncation AND an
#   OH_BinderThread SIGSEGV while parsing the scheduleLaunchActivity (Want)
#   callback. Fix = compile the bridge against device-exact 6.1.0.31 headers,
#   bulk-copied verbatim from GZ05 /data/oh61-wukong100 into
#   adapter/local_oh_headers/oh_mirror (13k headers, full subsystem trees so
#   transitive includes are also device-correct). We PREPEND a mirror-rewritten
#   copy of every -I$OH/... path so the 6.1.0.31 header shadows the api24 one;
#   paths not present in the mirror (skia, musl sysroot, some generated obj
#   dirs) simply don't exist under $OHI and clang ignores them, falling through
#   to the original local -I. -L link libs and --sysroot are untouched.
OHI="$ADAPTER_ROOT/local_oh_headers/oh_mirror"
if [ -d "$OHI" ]; then
    MIRROR_INCS=$(printf '%s\n' $INCS | grep -E "^-I$OH/" | sed "s|^-I$OH/|-I$OHI/|" | tr '\n' ' ')
    INCS="$MIRROR_INCS $INCS"
    echo "Prepended $(printf '%s\n' $MIRROR_INCS | grep -c '^-I') device-version (6.1.0.31) mirror -I paths from $OHI"
else
    echo "WARN: 6.1.0.31 header mirror not found at $OHI — bridge may carry api24 parcel skew"
fi

# ============================================================
# Build inventory of .cpp sources
# ============================================================
# Note: sources must match framework/jni/BUILD.gn's oh_adapter_bridge sources.
# Previously this used `*.cpp` glob per sub-dir, which wrongly pulled in
# apk_bundle_parser.cpp etc. (those belong to libapk_installer.so, not
# liboh_adapter_bridge.so, and drag in unresolvable OH::InnerBundleInfo
# symbols that are hidden in libbms.z.so).
#
# Most sub-dirs still glob all *.cpp (no non-bridge files today), but
# package-manager/ only takes oh_bundle_mgr_client.cpp explicitly.
#
# [VENDORED 2026-07-10, codex round1 review catch] window/jni/ additionally
# carries oh_window_manager_client.cut9-untested-on-5eab.cpp — a historical
# variant kept for reference only (see PROVENANCE.md "版本锚定": cut8, commit
# 7d962e5, is the one actually pinned/built; cut9, commit 9640799, is
# "unadopted but locally retained", never tested on 5eab, explicitly "不参与
# 构建"). It defines the exact same OHWindowManagerClient:: symbols as
# oh_window_manager_client.cpp (getInstance/connect/disconnect/createSession/
# etc.) — the naive *.cpp glob below would silently sweep it into SOURCES
# alongside the real cut8 file, producing a duplicate-symbol link failure.
# This is BR-1's own "glob drift" trap (see file header) applied to itself;
# excluded explicitly rather than trusting the glob.
SOURCES=""
for srcdir in core activity window surface broadcast contentprovider; do
    for src in "$ADAPTER_ROOT/framework/$srcdir/jni"/*.cpp; do
        [ -f "$src" ] || continue
        case "$(basename "$src")" in
            *-untested-on-*.cpp) continue ;;  # reference-only variants, not build inputs
        esac
        SOURCES="$SOURCES $src"
    done
done
# Package-manager is selected explicitly.  The standalone recipe bypasses GN,
# so the lifecycle owners referenced by oh_environment.cpp and their static
# dependencies must be compiled here exactly as the historical strict target
# build did.  APK installer/verification sources remain excluded.
for src in \
    "$PM_SOURCE_ROOT/jni/oh_bundle_mgr_client.cpp" \
    "$PM_SOURCE_ROOT/jni/axml_parser.cpp" \
    "$PM_SOURCE_ROOT/jni/package_info_jni.cpp" \
    "$PM_SOURCE_ROOT/jni/application_info_jni.cpp" \
    "$PM_SOURCE_ROOT/jni/component_resolver_jni.cpp" \
    "$PM_SOURCE_ROOT/package_transaction/src/package_transaction_v1.cpp" \
    "$PM_SOURCE_ROOT/package_query/src/package_query_v1.cpp" \
    "$PM_SOURCE_ROOT/manifest_facts/src/manifest_facts_v1.cpp" \
    "$PM_SOURCE_ROOT/package_info/src/package_info_v1.cpp" \
    "$PM_SOURCE_ROOT/package_info/src/package_info_runtime_v1.cpp" \
    "$PM_SOURCE_ROOT/application_info/src/application_info_v1.cpp" \
    "$PM_SOURCE_ROOT/application_info/src/application_info_public_entry_v1.cpp" \
    "$PM_SOURCE_ROOT/application_info/src/application_info_runtime_v1.cpp" \
    "$PM_SOURCE_ROOT/application_info/src/application_info_runtime_owner_v1.cpp" \
    "$PM_SOURCE_ROOT/component_resolver/src/component_resolver_v1.cpp" \
    "$PM_SOURCE_ROOT/component_resolver/src/component_resolver_runtime_v1.cpp" \
    "$PM_SOURCE_ROOT/package_layout/src/package_layout_v1.cpp" \
    "$PM_SOURCE_ROOT/resource_projection/src/resource_projection_v1.cpp" \
    "$PM_SOURCE_ROOT/runtime_path_descriptor/src/runtime_path_descriptor_v1.cpp" \
    "$PM_SOURCE_ROOT/install_plan/src/sha256.c"; do
    if [ ! -f "$src" ] || [ -L "$src" ]; then
        echo "ERROR: required package-manager source is missing or symlinked: $src" >&2
        exit 2
    fi
    SOURCES="$SOURCES $src"
done
SOURCES="$SOURCES $ADAPTER_ROOT/framework/native-compat/jni-attach-admission/src/jni_attach_admission.cpp"

total=0
for _ in $SOURCES; do total=$((total + 1)); done

echo "=========================================="
echo "  liboh_adapter_bridge.so standalone build"
echo "  sources: $total .cpp files"
echo "  output:  $OUT/liboh_adapter_bridge.so"
echo "=========================================="

# ============================================================
# Compile each .cpp → .o
# ============================================================
OBJS=""
fails=0
ok=0
for src in $SOURCES; do
    # Avoid collisions: prefix object name with its parent jni dir.
    parent_dir="$(basename "$(dirname "$(dirname "$src")")")"  # core / activity / window / ...
    stem="$(basename "$src" .cpp)"
    obj="$TMP/${parent_dir}__${stem}.o"
    err="$TMP/${parent_dir}__${stem}.err"

    # Skip if already compiled and newer than source (incremental).
    if [ -f "$obj" ] && [ "$obj" -nt "$src" ]; then
        OBJS="$OBJS $obj"
        ok=$((ok + 1))
        continue
    fi

    eval "$CXX $COMMON $INCS -c \"$src\" -o \"$obj\"" 2>"$err"
    if [ -f "$obj" ]; then
        OBJS="$OBJS $obj"
        ok=$((ok + 1))
        printf "  ok  %s\n" "${parent_dir}/${stem}"
    else
        fails=$((fails + 1))
        printf "  FAIL %s\n" "${parent_dir}/${stem}"
        head -5 "$err" | sed 's/^/    /'
    fi
done

echo ""
echo "Compiled: $ok/$total (fails: $fails)"

if [ "$fails" -gt 0 ]; then
    echo ""
    echo "First 3 failing .cpp errors (full logs in $TMP/*.err):"
    ls -t "$TMP"/*.err 2>/dev/null | head -3 | while read f; do
        echo "--- $(basename "$f") ---"
        head -15 "$f"
    done
    exit 1
fi

# ============================================================
# Link → liboh_adapter_bridge.so
# ============================================================
LINK="$CXX --target=aarch64-linux-ohos -B$ML -L$ML -shared -fPIC"
LIBS="\
  -L$PSDK -L$SDKSP -L$SDK -L$SYSLIB -L$NDK -L$AOSPLIB -L$OH_STUBS \
  -Wl,--enable-new-dtags \
  -lhilog -lutils.z -lipc_single.z -lsamgr_proxy.z \
  -lability_manager.z -lapp_manager.z -lappkit_native.z -lability_connect_callback_stub.z \
  -lwm.z -ldm.z -lrender_service_client.z -lnative_drawing -lskia_canvaskit.z \
  -lmmi-client.z \
  -lsurface.z -lcesfwk_innerkits.z -ldatashare_consumer.z \
  -lappexecfwk_base.z -lappexecfwk_core.z \
  -lnativehelper \
  \
  -lEGL \
  -Wl,--no-as-needed $WLTG_REGISTRY -Wl,--as-needed \
  -ldl -lpthread -llog -lwant.z -lzuri.z -lconfiguration.z -lmission_info.z \
  -lrender_service_base.z -lscene_session.z -lwindow_scene_common.z \
  -lwmutil.z -lwmutil_base.z -leventhandler.z -lhitrace_ndk.z \
  -lsync_fence.z -lbegetutil.z"

# A.11: bridge link — added 2026-04-22
# static dlopen sim detected 51 residual UND after relaxed link. Added 10 lib:
#   liblog (AOSP __android_log_*), libskia_canvaskit.z (SkBitmap/SkImageInfo 8),
#   libwant.z (AAFwk::Want + ElementName 15), libzuri.z (Uri 4),
#   libconfiguration.z (Configuration::GetName), libmission_info.z (MissionInfo vtable),
#   librender_service_base.z (RSInterpolator/RSCommandFactory/LinearInterpolator 6),
#   libscene_session.z (SessionStageStub 1),
#   libwindow_scene_common.z (WindowSessionProperty 8),
#   libsync_fence.z (SyncFence 3)

echo ""
echo "Linking $OUT/liboh_adapter_bridge.so ..."
link_err="$TMP/link.err"
STRICT_IDENTITY_FLAGS="-Wl,-z,defs -Wl,--no-allow-shlib-undefined -Wl,--no-undefined -Wl,--build-id=sha1 -Wl,-soname,liboh_adapter_bridge.so"
if [ "$STRICT_BUILD" = 1 ]; then
    FIRST_LINK_FLAGS="$STRICT_IDENTITY_FLAGS"
else
    FIRST_LINK_FLAGS="-Wl,-soname,liboh_adapter_bridge.so -Wl,-rpath,/system/android/lib"
fi
if $LINK $FIRST_LINK_FLAGS -o "$OUT/liboh_adapter_bridge.so" \
        $OBJS $LIBS $BUILTINS 2>"$link_err"; then
    link_mode="strict"
else
    if [ "$STRICT_BUILD" = 1 ]; then
        echo "  strict generation link failed; relaxed fallback is forbidden"
        tail -30 "$link_err"
        rm -f "$OUT/liboh_adapter_bridge.so"
        exit 1
    fi
    # Legacy non-generation fallback retained until its callers are migrated.
    echo "  strict link failed; retrying with --unresolved-symbols=ignore-all"
    if ! $LINK -o "$OUT/liboh_adapter_bridge.so" $OBJS $LIBS $BUILTINS \
            -Wl,-soname,liboh_adapter_bridge.so \
            -Wl,-rpath,/system/android/lib \
            -Wl,--unresolved-symbols=ignore-all 2>"$link_err"; then
        echo "  LINK FAILED (both strict and relaxed):"
        tail -30 "$link_err"
        exit 1
    fi
    link_mode="relaxed"
fi

sz=$(ls -lh "$OUT/liboh_adapter_bridge.so" | awk '{print $5}')
echo "  linked: $sz [$link_mode]"

# ============================================================
# Verify NEEDED + RUNPATH
# ============================================================
echo ""
echo "=== NEEDED chain ==="
"$READELF" -d "$OUT/liboh_adapter_bridge.so" 2>/dev/null | grep -E 'NEEDED|RUNPATH|SONAME'

if [ "$link_mode" = "relaxed" ]; then
    undef=$("$READELF" --dyn-syms "$OUT/liboh_adapter_bridge.so" 2>/dev/null | grep 'UND' | grep -v 'WEAK' | wc -l)
    echo ""
    echo "Relaxed link: ~$undef undefined dynamic symbols remain (check $TMP/link.err)"
fi

if [ "$link_mode" = "strict" ]; then
    bridge_header="$TMP/liboh_adapter_bridge.header"
    bridge_dynamic="$TMP/liboh_adapter_bridge.dynamic"
    bridge_notes="$TMP/liboh_adapter_bridge.notes"
    "$READELF" --file-header --wide "$OUT/liboh_adapter_bridge.so" >"$bridge_header"
    "$READELF" --dynamic --wide "$OUT/liboh_adapter_bridge.so" >"$bridge_dynamic"
    "$READELF" --notes --wide "$OUT/liboh_adapter_bridge.so" >"$bridge_notes"
    grep -q 'Class:.*ELF64' "$bridge_header" \
        && grep -q 'Machine:.*AArch64' "$bridge_header" || {
        echo "ERROR: strict bridge is not ELF64/AArch64" >&2
        exit 1
    }
    soname_count=$(awk -F'[][]' \
        '/SONAME/ && $2 == "liboh_adapter_bridge.so" { count++ } END { print count + 0 }' \
        "$bridge_dynamic")
    [ "$soname_count" -eq 1 ] || {
        echo "ERROR: strict bridge SONAME count=$soname_count" >&2
        exit 1
    }
    if grep -Eq '\((RPATH|RUNPATH|TEXTREL)\)' "$bridge_dynamic"; then
        echo "ERROR: strict bridge contains RPATH/RUNPATH/TEXTREL" >&2
        exit 1
    fi
    grep -q 'Build ID:' "$bridge_notes" || {
        echo "ERROR: strict bridge lacks a GNU Build-ID" >&2
        exit 1
    }
fi

echo ""
echo "Build complete."
