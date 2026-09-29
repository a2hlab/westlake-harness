#!/bin/bash
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
# Bypasses OH GN/ninja build system. Uses OH clang + arm-linux-ohos musl
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
source "$ADAPTER_ROOT/build/inner/bridge_manifest_inputs.sh"
OUT="$ADAPTER_ROOT/out/adapter"
TMP="/tmp/bridge_build"

if [ "${1:-}" = "--clean" ]; then
    echo "--clean: wiping $TMP"
    rm -rf "$TMP"
fi
mkdir -p "$OUT" "$TMP"

# ============================================================
# Toolchain (same as cross_compile_arm32.sh / compile_jni_chain.sh)
# ============================================================
SR="$OH/out/rk3568/obj/third_party/musl/usr"
ML="$SR/lib/arm-linux-ohos"
CXX="$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++"
BUILTINS="$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/arm-linux-ohos/libclang_rt.builtins.a"

# ============================================================
# OH system lib paths for linker -L
# ============================================================
PSDK="$OH/out/rk3568/packages/phone/system/lib/platformsdk"
SDKSP="$OH/out/rk3568/packages/phone/system/lib/chipset-sdk-sp"
SDK="$OH/out/rk3568/packages/phone/system/lib/chipset-sdk"
SYSLIB="$OH/out/rk3568/packages/phone/system/lib"
NDK="$OH/out/rk3568/packages/phone/system/lib/ndk"
AOSPLIB="$ADAPTER_ROOT/out/aosp_lib"

# ============================================================
# Compile flags (mirrors OH ohos_shared_library output + project defines)
# ============================================================
COMMON="--target=arm-linux-ohos -march=armv7-a --sysroot=$SR"
COMMON="$COMMON -I$SR/include/arm-linux-ohos"
COMMON="$COMMON -fPIC -O2 -std=c++17"
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
  -I$ADAPTER_ROOT/framework/core/include \
  -I$ADAPTER_ROOT/framework/core/jni \
  -I$ADAPTER_ROOT/framework/activity/jni \
  -I$ADAPTER_ROOT/framework/window/jni \
  -I$ADAPTER_ROOT/framework/surface/jni \
  -I$ADAPTER_ROOT/framework/broadcast/jni \
  -I$ADAPTER_ROOT/framework/contentprovider/jni \
  -I$ADAPTER_ROOT/framework/package-manager/jni"

# ============================================================
# [S24 cut9 2026-07-09 build-fix] 6.1.0.31 (real device) interface-header
# overlay — generation-skew shim, NOT a full OH source tree.
#
# Context: $OH (OH_ROOT) is the only locally-available *complete, buildable*
# OH source tree, but it is the older "api24" generation. Two adapter files
# (app_scheduler_adapter.h, session_stage_adapter.h) were deliberately
# updated on 2026-07-09 to match the REAL deployed device's ABI
# (HarmonyOS 6.1.0.31 / wukong100 generation) for two IPC interface methods
# whose parameter count changed across generations:
#   - OHOS::AppExecFwk::IAppScheduler::ScheduleMemoryLevel
#       api24:     ScheduleMemoryLevel(int32_t level, bool isShellCall = false)
#       6.1.0.31:  ScheduleMemoryLevel(int32_t level)                     [1-arg]
#   - OHOS::Rosen::ISessionStage::NotifyAppForceLandscapeConfigEnableUpdated
#       api24:     NotifyAppForceLandscapeConfigEnableUpdated(bool needUpdateViewport = false)
#       6.1.0.31:  NotifyAppForceLandscapeConfigEnableUpdated()           [0-arg]
# Compiling the adapter's now-6.1.0.31-shaped `override` declarations
# against api24's headers fails ("non-virtual member function marked
# 'override' hides virtual member function ... different number of
# parameters"), for exactly these two methods (confirmed via full
# directory diff — no other signature drift in these two interface files
# besides pure-*additions* in api24 that the adapter already handles by
# dropping `override`, see the "V7-only" comment block in
# session_stage_adapter.h).
#
# Fix: shadow ONLY the 4 declaration headers that carry the mismatch
# (app_scheduler_host.h + app_scheduler_interface.h;
#  session_stage_stub.h + session_stage_interface.h), sourced verbatim
# from a real-device 6.1.0.31/wukong100 header mirror
# (/opt/1F.Application/02.Noice/adapter/local_oh_headers/oh_mirror — a
# different, unrelated project's read-only header-only ABI mirror, NOT a
# full OH source tree; used here purely as a signature oracle). Everything
# else (types these headers themselves #include, e.g. fault_data.h,
# ws_common.h, window_session_property.h, etc.) still resolves from $OH
# (api24) as before — confirmed identical or non-participating in this
# specific skew by the same directory diff. Placed in
# build/oh_headers_631_overlay/ mirroring $OH's own relative layout, and
# given -I priority (below, ahead of $INCS_OH and the ninja-harvested list)
# so the quote-form #include chain (app_scheduler_adapter.h ->
# "app_scheduler_host.h" -> "app_scheduler_interface.h", and
# session_stage_adapter.h -> "session/container/include/zidl/
# session_stage_stub.h" -> "session_stage_interface.h") resolves entirely
# within the overlay for these 4 files, without touching sibling files
# (app_scheduler_proxy.h, ams_mgr_*.h, etc.) that also drift generationally
# but are NOT touched by any `override` in this adapter (out of scope here;
# see PROVENANCE.md for the residual-risk note).
# ============================================================
# NOTE: -I must point at the exact leaf directories that $INCS_OH/harvested
# ninja reference (bare-filename #include "app_scheduler_host.h" resolves
# against the "appmgr" leaf dir directly; #include
# "session/container/include/zidl/session_stage_stub.h" resolves against the
# "window_scene" leaf dir, one level up from "session/"). Pointing -I at the
# overlay tree's *root* (mirroring $OH's full relative path only for
# provenance/readability on disk) would NOT match either #include form.
INCS_OVERLAY_631="\
  -I$ADAPTER_ROOT/build/oh_headers_631_overlay/foundation/ability/ability_runtime/interfaces/inner_api/app_manager/include/appmgr \
  -I$ADAPTER_ROOT/build/oh_headers_631_overlay/foundation/window/window_manager/window_scene"

# OH inner_api headers (direct paths — OH GN would bring these via
# external_deps+header_base; we bypass GN so just include directly)
INCS_OH="\
  -I$ADAPTER_ROOT/sources/oh61-v7-b2133b5b/local_oh_headers/oh_mirror/foundation/ability/ability_runtime/interfaces/kits/native/appkit/app \
  -I$ADAPTER_ROOT/sources/oh61-v7-b2133b5b/local_oh_headers/oh_mirror/foundation/ability/ability_runtime/interfaces/kits/native/appkit/ability_runtime/app \
  -I$ADAPTER_ROOT/sources/oh61-v7-b2133b5b/local_oh_headers/oh_mirror/foundation/ability/ability_runtime/interfaces/kits/native/appkit/ability_runtime/context \
  -I$ADAPTER_ROOT/sources/oh61-v7-b2133b5b/local_oh_headers/oh_mirror/foundation/ability/ability_runtime/interfaces/kits/native/ability/native \
  -I$ADAPTER_ROOT/sources/oh61-v7-b2133b5b/local_oh_headers/oh_mirror/foundation/ability/ability_runtime/interfaces/inner_api/app_manager/include/appmgr \
  -I$ADAPTER_ROOT/sources/oh61-v7-b2133b5b/local_oh_headers/oh_mirror/foundation/ability/ability_runtime/interfaces/inner_api/runtime/include \
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
  -I$OH/out/rk3568/obj/third_party/openssl/build_all_generated/include \
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
  -I$OH/out/rk3568/gen/foundation/window/window_manager/wmserver \
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
  -I$OH/out/rk3568/gen/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_core \
  -I$OH/third_party/zlib/contrib/minizip \
  -I$OH/third_party/zlib \
  -I$OH/third_party/json/include \
  -I$OH/third_party/openssl/include \
  -I$OH/third_party/skia/m133/modules \
  -I$OH/out/rk3568/gen/third_party/jsoncpp/jsoncpp-1.9.6/include \
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

# AOSP incfs (map_ptr.h used by libandroidfw)
INCS_AOSP_EXTRA="-I$AOSP/system/incremental_delivery/incfs/util/include"

INCS="$INCS_LOCAL $INCS_OVERLAY_631 $INCS_OH $INCS_AOSP $INCS_AOSP_EXTRA $INCS_SKIA"

# ============================================================
# Harvest -I paths from OH's own ninja plan for oh_adapter_bridge.
# OH GN already computed the correct include_dirs set (225 entries for rk3568);
# we reuse them as-is rather than hand-maintain a duplicate.
# Paths in ninja are relative to $OH/out/rk3568/ — prepend to get absolute.
# ============================================================
NINJA_FILE="$OH/out/rk3568/obj/adapter/framework/jni/oh_adapter_bridge.ninja"
# --- OH 6.1.0.31 harvest fallback (2026-07-11) ---------------------------------
# When the OH tree lacks the integrated adapter GN target (adapter/framework/jni
# not vendored into OH source), OH GN never generates the live oh_adapter_bridge
# .ninja plan, so the harvest below silently degrades to the incomplete
# hand-maintained flag set (missing ~230 -I + defines incl. USE_M133_SKIA ->
# "clone_param.h / parameters.h / skcms.h / ... not found").  Fall back to the
# committed harvest snapshot oh_adapter_bridge.ninja.template (captured from a
# working OH build): it carries the SAME include_dirs + defines OH GN computed,
# run through the SAME sed transforms below.  No invented flags; restores the
# script's own intended harvested flag set.  Only engages when the live plan is
# absent -> machines with the integrated GN target are unaffected.
if [ ! -f "$NINJA_FILE" ]; then
    _bridge_tmpl="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/oh_adapter_bridge.ninja.template"
    if [ -f "$_bridge_tmpl" ]; then
        NINJA_FILE="$_bridge_tmpl"
        echo "Live OH ninja plan absent; harvesting from committed template snapshot: $NINJA_FILE"
    fi
fi
if [ -f "$NINJA_FILE" ]; then
    harvested=$(grep '^include_dirs' "$NINJA_FILE" | head -1 \
        | tr ' ' '\n' | grep -E '^-I' \
        | sed "s|^-I\.\.\/\.\.\/|-I$OH/|" \
        | sed "s|^-I\.\.\/|-I$OH/out/rk3568/|" \
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
# 2026-07-09: window/jni/ additionally carries
# oh_window_manager_client.cut9-untested-on-5eab.cpp — a historical variant
# kept for reference only (see PROVENANCE.md "版本锚定": cut8, commit
# 7d962e5, is the one actually pinned/built; cut9, commit 9640799, is
# "unadopted but locally retained", never tested on 5eab, and explicitly
# "不参与构建"). The naive *.cpp glob below does not know that and was
# silently sweeping it into SOURCES (BR-1's own "glob drift" trap, applied
# to itself) until this exclusion was added.
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
# package-manager/ selected explicitly — siblings belong to libapk_installer.so
# 2026-04-30 (P2-B): apk_manifest_jni.cpp + apk_manifest_parser.cpp + axml_parser.cpp
# added so PackageManagerAdapter.nativeParseApkManifestJson can lazy-parse APK
# manifests at runtime (className/theme/providers/largeHeap/...).
for src in \
    "$ADAPTER_ROOT/framework/package-manager/jni/oh_bundle_mgr_client.cpp" \
    "$ADAPTER_ROOT/framework/package-manager/jni/apk_manifest_jni.cpp" \
    "$ADAPTER_ROOT/framework/package-manager/jni/apk_manifest_parser.cpp" \
    "$ADAPTER_ROOT/framework/package-manager/jni/axml_parser.cpp" \
    "$ADAPTER_ROOT/framework/package-manager/jni/arsc_resolver.cpp" ; do
    [ -f "$src" ] || { echo "ERROR: required bridge source missing: $src" >&2; exit 1; }
    SOURCES="$SOURCES $src"
done

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
LINK="$CXX --target=arm-linux-ohos -march=armv7-a -B$ML -L$ML -shared -fPIC"
LIBS="\
  -L$PSDK -L$SDKSP -L$SDK -L$SYSLIB -L$NDK -L$AOSPLIB \
  -Wl,--enable-new-dtags \
  -Wl,-rpath,/system/android/lib \
  -lhilog -lutils.z -lipc_core.z -lsamgr_proxy.z \
  -lappkit_native \
  -lability_manager.z -lapp_manager.z -lability_connect_callback_stub.z \
  -lwm.z -ldm.z -lrender_service_client.z -lnative_drawing \
  -lmmi-client.z \
  -lsurface.z -lcesfwk_innerkits.z -ldatashare_consumer.z \
  -lappexecfwk_base.z -lappexecfwk_core.z \
  -lnativehelper \
  -lhwui \
  -lEGL \
  -ldl -lpthread   -llog     -lwant.z -lzuri.z -lconfiguration.z -lmission_info.z   -lrender_service_base.z -lscene_session.z -lwindow_scene_common.z   -lsync_fence.z   -lbegetutil.z"

# 2026-04-30 P2-B: minizip + zlib for apk_manifest_jni.cpp on-demand APK parse.
# minizip is built as separate .o files (not a library), so we explicitly add
# unzip.o + ioapi.o from OH's zlib/contrib/minizip build dir, plus libz.a static.
MINIZIP_DIR="${BRIDGE_MINIZIP_DIR:-$OH/out/rk3568/obj/third_party/zlib/contrib/minizip/shared_libz}"
LIBZ_A="${BRIDGE_LIBZ_A:-$OH/out/rk3568/obj/third_party/zlib/libz.a}"
if [ -f "$MINIZIP_DIR/unzip.o" ] && [ -f "$MINIZIP_DIR/ioapi.o" ] && [ -f "$LIBZ_A" ]; then
    LIBS="$LIBS $MINIZIP_DIR/unzip.o $MINIZIP_DIR/ioapi.o $LIBZ_A"
    echo "Added minizip+zlib for APK manifest parsing"
else
    for required in "$MINIZIP_DIR/unzip.o" "$MINIZIP_DIR/ioapi.o" "$LIBZ_A"; do
        [ -f "$required" ] || echo "ERROR: required bridge link input missing: $required" >&2
    done
    exit 1
fi
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
if $LINK -o "$OUT/liboh_adapter_bridge.so" $OBJS $LIBS $BUILTINS 2>"$link_err"; then
    link_mode="strict"
else
    # Fallback: allow unresolved refs, marks .so for RTLD_LAZY hope-for-best
    echo "  strict link failed; retrying with --unresolved-symbols=ignore-in-shared-libs"
    if ! $LINK -o "$OUT/liboh_adapter_bridge.so" $OBJS $LIBS $BUILTINS \
            -Wl,--unresolved-symbols=ignore-in-shared-libs 2>"$link_err"; then
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
/usr/bin/readelf -d "$OUT/liboh_adapter_bridge.so" 2>/dev/null | grep -E 'NEEDED|RUNPATH|SONAME'

if [ "$link_mode" = "relaxed" ]; then
    undef=$(/usr/bin/readelf --dyn-syms "$OUT/liboh_adapter_bridge.so" 2>/dev/null | grep 'UND' | grep -v 'WEAK' | wc -l)
    echo ""
    echo "Relaxed link: ~$undef undefined dynamic symbols remain (check $TMP/link.err)"
fi

echo ""
echo "Build complete."
