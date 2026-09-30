#!/bin/bash
# === GUARD: internal helper, do not invoke directly ===
if [ "${BUILD_INNER_INVOKED}" != "1" ]; then
    echo "[GUARD] $(basename "$0") is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc." >&2
    echo "[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 bash $(basename "$0")" >&2
    exit 2
fi
# === END GUARD ===
# [DEPRECATED Phase 1 — 2026-05-21] Use build_adapter.sh --target=liboh_android_runtime.so instead.
echo "[DEPRECATED] $(basename "$0") is wrapped by build_adapter.sh — Phase 4 will absorb this" >&2
# ============================================================================
# compile_oh_android_runtime_arm64_stage2unity.sh
#
# Cross-compile liboh_android_runtime.so — OH-Adapter's trimmed version of
# AOSP libandroid_runtime.so.  Strategy: take AOSP source files for
# register_X modules we want real implementations of (AssetManager,
# ApkAssets, Bitmap, Canvas, Typeface, ...) + use AOSP libandroidfw real
# C++ engine; keep our own stubs for OH-incompatible modules (Surface ↔
# OH RS, BlastBufferQueue, DisplayEventReceiver, etc).
#
# Build separates two source groups:
#   SRCS          — our own .cpp (gnu++17, -fno-rtti, OH ABI)
#   SRCS_AOSP     — pulled-in AOSP register_X .cpp (C++20, AOSP headers)
# Objects merged at link, linked against libandroidfw + libbase + libutils
# + libcutils + liblog + libnativehelper + libziparchive + libicuuc + libz.
# ============================================================================
#
# ════════════════════════════════════════════════════════════════════════════
#  USE CASE / 使用场景（2026-05-18 added per audit）
# ════════════════════════════════════════════════════════════════════════════
#
#  ▶ 一句话定位：编 adapter 自家的 liboh_android_runtime.so 的 **aarch64
#    （arm64，wukong100/5eab 生产目标）STAGE2-UNITY 完整配方**——armv7（32位）
#    目标见同目录下的 compile_oh_android_runtime.sh，两者是不同架构/不同
#    文件集合的姊妹脚本，不是彼此的新旧版本。
#    （替代 AOSP 原 libandroid_runtime.so 2.28MB → ≈170KB。）
#
#  ▶ 产物：out/adapter/liboh_android_runtime.so 单一 .so（aarch64 ELF）
#    - 43 个 .o（`SRCS` 27 个 adapter 自写 + `SRCS_AOSP` 16 个 AOSP-ported/raw
#      直引，2026-07-10 自包含性审计时以实际编译日志逐条核对过，非估计值；
#      其中 4 个 raw AOSP 文件已 vendor 进本仓库 `third_party/aosp_raw/`，
#      不再从外部 `$AOSP_ROOT` 读取文件本体）
#    - 链 -landroidfw -lbase -lutils -lcutils -lziparchive -lnative_window
#      -lEGL -lGLESv2 -lGLESv3 -l:libhilog.so 等 OH 端 + adapter cross-compiled .so
#    - 导出 _ZN7android14AndroidRuntime8startRegEP7_JNIEnv 等关键符号
#      与 AOSP 原版对齐，让 appspawn-x 的 dlsym 调用点零修改
#
#  ▶ 何时跑（trigger 条件）：
#    - framework/android-runtime/src/ 下任何 .cpp/.h 改动后
#    - third_party/aosp_raw/ 下 4 个 raw AOSP 文件同步升级后
#    - 升级 OH SDK / libandroidfw 等链接库后
#    - 不需要：改 AOSP native 源码本身（那是产出 out/aosp_lib64 的 arm64
#      cross-compile 步骤的范围——见下"已知缺口"，本仓库目前没有这个脚本）
#
#  ▶ 上下游关系：
#    - 上游依赖 ← out/aosp_lib64/（22+ 个 aarch64 AOSP native .so：
#      libandroidfw / libbase / libutils / libcutils / libziparchive 等）。
#      **KNOWN GAP（2026-07-10）**：本仓库没有产出这个目录的 arm64 构建脚本
#      （armv7 的对应物 cross_compile_arm32.sh 产出 out/aosp_lib/，这里不是
#      同一个目录）；必须外部提供，见 PROVENANCE.md"已知缺口"一节。
#    - 上游依赖 ← liboh_adapter_bridge.so（arm64 版，`-loh_adapter_bridge`）：
#      本仓库 compile_oh_adapter_bridge.sh 只产出 armv7 版本；arm64 版本的
#      构建脚本同样是已知缺口，须外部提供 .so 本体。
#    - 上游依赖 ← compile_libhwui.sh：产出 libhwui.so，本脚本不链接但
#      运行时 dlopen + dlsym 调它的 45 个 register_X
#    - 上游依赖 ← OH 系统编译：libhilog.so / libnative_window.so / libbegetutil
#      / libhitrace_ndk 等来自 $OH_ROOT/out/wukong100/
#    - 下游 → deploy 链路：产物推到设备 /system/lib64/ + /system/android/lib64/
#      （双路径，per reference_liboh_android_runtime_dual_path memory）
#
#  ▶ NOT 范围（避免误用）：
#    - 不编 AOSP libart / libhwui / libandroidfw 等 arm64 native 库本身
#      （产出 out/aosp_lib64 的步骤——本仓库目前缺失，见上"已知缺口"）
#    - 不编 OH 系统服务（abilityms / scene_session 等，→ OH BUILD.gn）
#    - 不编 Java 产物（framework.jar / oh-adapter-framework.jar，→ AOSP Soong）
#    - 不编 appspawn-x / liboh_adapter_bridge.so（→ 各自独立 compile_*.sh）
#
# ════════════════════════════════════════════════════════════════════════════
#
# ┌──────────────────────────────────────────────────────────────────────────┐
# │  ⚠️  铁律 — RegJNIRec / kHwuiRegFns 表禁止 SKIP 任何条目                  │
# │                                                                          │
# │  AndroidRuntime.cpp::startReg 的 RegJNIRec 表禁止 SKIP 任何条目；         │
# │  若某 register_X 在启动期 abort，必须解决该条目内部的根因，不能跳过；    │
# │  跳过 = 把启动期 abort 推迟到运行期 IsInstanceOf(NULL) 这种远离根因      │
# │  的爆点。                                                                │
# │                                                                          │
# │  历史血训（2026-05-06）：                                                │
# │    `register_android_graphics_Graphics` 在 kHwuiRegFns 被注释 SKIP，     │
# │    导致 gFontMetricsInt_class / gRect / gColorSpace / gBitmapConfig      │
# │    等十几个全局 jclass 缓存全 NULL。helloworld 跑过 onCreate / onResume  │
# │    / activityResumed rc=0 后，TextView.onMeasure → Layout.getDesired    │
# │    Width → Paint.getFontMetricsInt → GraphicsJNI::set_metrics_int →     │
# │    env->IsInstanceOf(metrics, NULL_jclass) → ART CheckJNI fatal abort   │
# │    "JNI DETECTED ERROR IN APPLICATION: IsInstanceOf received NULL       │
# │    jclass in call to IsInstanceOf from int Paint.nGetFontMetricsInt".   │
# │    根因 T0（startReg 的 SKIP）和爆点 T1（运行期主线程 SIGABRT）相隔几秒  │
# │    + 几个生命周期阶段；T0 不留任何痕迹，光看栈完全看不出"是漏了一个      │
# │    register_X"。该 SKIP 反复出现并浪费了数天定位时间。                   │
# │                                                                          │
# │  原理：register_X 的"双职能"——A=注册 native methods（显眼），           │
# │    B=同函数尾巴缓存全局 g*_class / g*_field / g*_method（隐蔽）。       │
# │    AOSP 设计假设 "register 必然会跑"，缓存读取处既无 lazy 兜底也无       │
# │    NULL 断言。SKIP 任一 register_X = 该文件域所有 g*_* 全 NULL，         │
# │    依赖这些缓存的 native impl 首次进入 hot path 时 NULL deref。          │
# │                                                                          │
# │  特别危险：register_android_graphics_Graphics 是"超级缓存中心"，         │
# │    被 Paint / Canvas / Bitmap / Region / RectF / Point / ColorSpace /    │
# │    Picture / VMRuntime / Typeface 等几十个 graphics native 文件共用。    │
# │                                                                          │
# │  Fix discipline：                                                        │
# │    1. 任何修改 RegJNIRec[] / kHwuiRegFns[] 之前先复诵此条规则            │
# │    2. 若加 register_X 进表后 startReg 内部 abort，那 abort 是真问题，    │
# │       OrDie 失败的具体类名/方法名/字段名是真因——查 hilog domain        │
# │       0xD002000、`adapter_child_<pid>.stderr`、parent_appspawnx.stderr  │
# │       三处后定位到具体哪一行 OrDie 失败                                  │
# │    3. 子问题分类处理：缺类→补 framework.jar+重建 boot image；缺 field/  │
# │       method→对齐 AOSP 14 Java 源；连锁 clinit→单独 isolate            │
# │    4. 绝不接受 "SKIP 这个 register，graphics 走 OH 自己的链路就行" —    │
# │       OH RS / graphic_2d 是另一层，不替代 AOSP graphics native 内部     │
# │       的 g*_class 缓存机制。Paint/Canvas/TextView 是纯 AOSP Java 类，   │
# │       它们的 native 实现是 AOSP 自己的 .cpp，依赖 AOSP 自己的全局缓存。 │
# │                                                                          │
# │  Memory: feedback_no_skip_regjnirec.md (项目铁律)                        │
# │  Related: feedback_art_abort_check_stderr_file.md（abort 诊断方法）     │
# │  Related: feedback_no_stub_compile.md（同源反模式：用 stub 隐藏失败）   │
# └──────────────────────────────────────────────────────────────────────────┘
set -o pipefail

# 2026-07-10 (adapter self-containment audit — see PROVENANCE.md
# "2026-07-10 追加" section): vendored into 02.unity.cardwords/adapter from
# GZ05 /data/adapter/build/inner/ (the actual recipe that built the
# currently-deployed liboh_android_runtime.so, md5
# 58d20467ed6e3ad7bb3d6860b75183e2). Defaults below realigned to this repo's
# *newer* build/inner/*.sh convention (self-locating ADAPTER_ROOT, $HOME/oh +
# $HOME/aosp fallbacks — matches compile_oh_android_runtime.sh,
# compile_oh_adapter_bridge.sh, cross_compile_arm32.sh) instead of the
# GZ05-specific /data/oh, /data/aosp, $HOME/adapter defaults. NOTE: this is
# not yet a repo-wide convention — compile_oh_adapter_runtime.sh,
# compile_oh_adapter_framework.sh and gen_boot_image.sh still default
# ADAPTER_ROOT to the literal $HOME/adapter; unifying those is a separate,
# not-yet-done cleanup (see PROVENANCE.md).
OH="${OH_ROOT:-$HOME/oh}"
A="${AOSP_ROOT:-$HOME/aosp}"
ADAPTER_ROOT="${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
SRC="$ADAPTER_ROOT/framework/android-runtime"
OUT="${ADAPTER_OUT_DIR:-$ADAPTER_ROOT/out/adapter}"
WLTG_REGISTRY="$OUT/libwestlake_thread_guard_registry.so"
# out/aosp_lib64 (22+ prebuilt AOSP native .so cross-compiled for aarch64-linux-
# ohos: libandroidfw/libbase/libutils/libcutils/libziparchive/libicuuc/...) is
# a KNOWN GAP: unlike ARM32 (whose producer cross_compile_arm32.sh lives in
# this same build/inner/), this repo does not yet contain an ARM64 equivalent.
# The arm64 cross-compile pipeline that produces this directory lives in a
# sibling, never-vendored-here adapter project:
#   /opt/1F.Application/02.Noice/adapter/build/inner_arm64_5583/
#     cross_compile_arm64.sh + cross_compile_extras_arm64.sh +
#     cross_compile_minikin_stack_arm64.sh
# Until that pipeline is vendored (out of scope for this pass — different app/
# subsystem, not touched this session), out/aosp_lib64 must be supplied
# externally (copy/symlink a prebuilt copy here, or point AOSP_LIB_DIR at one)
# before this script can link successfully — same category of external
# prerequisite as the OH/AOSP source trees themselves ($OH_ROOT/$AOSP_ROOT).
AOSP_LIB="${AOSP_LIB_DIR:-$ADAPTER_ROOT/out/aosp_lib64}"
BUILD="${ANDROID_RUNTIME_BUILD_DIR:-$ADAPTER_ROOT/out/android-runtime-build}"
BC="$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include"

if [ -n "${L03_A12_GENERATION_ID:-}" ]; then
    : "${ADAPTER_OUT_DIR:?generation build requires ADAPTER_OUT_DIR}"
    : "${ANDROID_RUNTIME_BUILD_DIR:?generation build requires ANDROID_RUNTIME_BUILD_DIR}"
    : "${AOSP_LIB_DIR:?generation build requires AOSP_LIB_DIR}"
    : "${L03_A12_CXX:?generation build requires L03_A12_CXX}"
    : "${L03_A12_READELF:?generation build requires L03_A12_READELF}"
    : "${L03_A12_NM:?generation build requires L03_A12_NM}"
    : "${L03_A12_AIDL:?generation build requires L03_A12_AIDL}"
    : "${L03_A12_PYTHON:?generation build requires L03_A12_PYTHON}"
    : "${L03_A12_LIBCXX_INCLUDE:?generation build requires L03_A12_LIBCXX_INCLUDE}"
fi
[ -f "$WLTG_REGISTRY" ] || {
    echo "ERROR: current R45 registry artifact missing: $WLTG_REGISTRY" >&2
    exit 1
}

mkdir -p "$BUILD" "$OUT"

OH_PRODUCT="${OH_PRODUCT_NAME:-wukong100}"
OH_OUT="$OH/out/$OH_PRODUCT"
SR="$OH_OUT/obj/third_party/musl/usr"
ML="$SR/lib/aarch64-linux-ohos"

CXX="${L03_A12_CXX:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++}"
READELF="${L03_A12_READELF:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf}"
NM="${L03_A12_NM:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-nm}"
PYTHON="${L03_A12_PYTHON:-python3}"

# Our own sources: same flags as before
COMMON="--target=aarch64-linux-ohos -march=armv8-a --sysroot=$SR -I$SR/include/aarch64-linux-ohos -fPIC -O2 -std=gnu++17 -fno-rtti"
if [ -n "${L03_A12_GENERATION_ID:-}" ]; then
    COMMON="$COMMON -nostdinc++ -isystem $L03_A12_LIBCXX_INCLUDE -MMD -MP"
    COMMON="$COMMON -ffile-prefix-map=$ADAPTER_ROOT=. -fdebug-prefix-map=$ADAPTER_ROOT=."
fi
INC="-I$ADAPTER_ROOT/framework/native-loader-oh/include -I$SRC/include -I$SRC/src -I$ADAPTER_ROOT/framework/surface/jni -I$ADAPTER_ROOT/framework/native-compat/jni-attach-admission/include -I$ADAPTER_ROOT/framework/native-compat/thread-guard-registry/include -I$BC -I$A/system/logging/liblog/include -I$A/libnativehelper/include_jni -I$A/libnativehelper/include -I$A/system/libbase/include -I$OH/base/hiviewdfx/hilog/interfaces/native/innerkits/include"
DEFS="-D__OHOS__ -D_GNU_SOURCE"

# AOSP-ported sources: C++20, AOSP includes, no -include libcxx_compat
# SR points to .../musl/usr, but --sysroot semantics expect the PARENT (so
# clang adds /usr/include). For AOSP-ported build use SR_PARENT to match the
# standalone-validated invocation.
SR_PARENT="$OH_OUT/obj/third_party/musl"
COMMON_AOSP="--target=aarch64-linux-ohos -march=armv8-a   --sysroot=$SR_PARENT -fPIC -O2 -std=c++20 -fno-exceptions -Wno-reorder-init-list"
if [ -n "${L03_A12_GENERATION_ID:-}" ]; then
    COMMON_AOSP="$COMMON_AOSP -nostdinc++ -isystem $L03_A12_LIBCXX_INCLUDE -MMD -MP"
    COMMON_AOSP="$COMMON_AOSP -ffile-prefix-map=$ADAPTER_ROOT=. -fdebug-prefix-map=$ADAPTER_ROOT=."
fi
# [STAGE2-GL 2026-06-28 parity] AOSP android_opengl_GLES31.cpp uses LONG_MIN/
# LONG_MAX without including <climits> directly (relies on a transitive
# include absent in this toolchain). Force-include <climits> for the whole
# AOSP group, matching compile_runtime_local.sh (OrbStack recipe that built
# the currently-loaded game1r_step1/liboh_android_runtime.so, md5 724009e2).
COMMON_AOSP="$COMMON_AOSP -include climits"
# 2026-07-10 (adapter self-containment audit): the GZ05 original pointed this
# at "$ADAPTER_ROOT/out/egl_inc" — a build-output directory that no step in
# this script (or anywhere else in this repo) ever generated; it only existed
# because someone had manually scp'd 4 Khronos EGL/KHR headers there once.
# Redirected to the vendored copy (byte-identical, md5-verified against both
# GZ05 /data/adapter/out/egl_inc and the AOSP frameworks/native/opengl/include
# originals) at third_party/aosp_raw/ so this step is reproducible from a
# clean checkout of this repo alone.
INC_AOSP="-I$ADAPTER_ROOT/third_party/aosp_raw/frameworks/native/opengl/include -I$SRC/src -I$SRC/include -I$ADAPTER_ROOT/framework/native-compat/jni-attach-admission/include -I$ADAPTER_ROOT/framework/native-compat/thread-guard-registry/include \
 -I$A/libnativehelper/include_jni \
 -I$A/libnativehelper/include \
 -I$A/libnativehelper/include_platform \
 -I$A/libnativehelper/header_only_include \
 -I$A/frameworks/base/libs/androidfw/include \
 -I$A/system/incremental_delivery/incfs/util/include \
 -I$A/system/core/include \
 -I$A/system/core/libcutils/include \
 -I$A/system/core/libutils/include \
 -I$A/system/libbase/include \
 -I$A/system/logging/liblog/include \
 -I$A/system/libziparchive/include \
 -I$A/external/icu/icu4c/source/common \
 -I$A/external/fmtlib/include \
 -I$A/frameworks/native/include \
 -I$A/external/zlib \
 -I$A/frameworks/base/core/jni \
 -I$OH/base/hiviewdfx/hilog/interfaces/native/innerkits/include \
 -I$A/frameworks/native/libs/input/include \
 -I$A/frameworks/native/libs/gui/include \
 -I$A/frameworks/native/libs/ui/include \
 -I$A/frameworks/native/libs/math/include \
 -I$A/frameworks/native/libs/arect/include \
 -I$A/frameworks/base/libs/hwui/apex/include \
 -I$A/frameworks/base/libs/hwui/jni \
 -I$A/frameworks/base/core/jni/include \
 -I$A/frameworks/native/opengl/include"
# [STAGE2-GL 2026-06-28 parity] opengl/include added for android_opengl_GLES*.cpp
# (<GLES2/gl2.h> <GLES3/gl3.h> <GLES3/gl31.h> <GLES2/gl2ext.h>). EGL/KHR
# resolve from egl_inc (listed first in INC_AOSP).
# 2026-05-18 (control experiment): OH Skia m133 include paths removed.
# Suspect Skia ABI drift between OH skia/m133 and AOSP-expected Skia is the
# source of ART mark_sweep "not contained by any spaces" abort.  If
# helloworld returns to G214bj working state after this rollback,
# direction is confirmed and a longer-term fix is needed (sz3 probe of
# Skia class sizeofs across both translation-unit contexts).

SRCS=(
    "$ADAPTER_ROOT/framework/native-compat/jni-attach-admission/src/jni_attach_admission.cpp"
    "$SRC/src/AndroidRuntime.cpp"
    "$SRC/src/android_view_VelocityTracker.cpp"
    "/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/adapter/framework/native-compat/westlake-commonevent/common_event_registration.cpp"
    # Task 79 A3: board ICU72 C-ABI NativeConverter (13/16) and regex
    # Pattern/Matcher (15/15) late RegisterNatives bridge.
    "$SRC/src/android_util_Log.cpp"
    # G2.10 (2026-04-30): android.util.EventLog — UnsatisfiedLinkError on
    # Activity.performCreate → EventLogTags.writeWmOnCreateCalled previously
    # blocked HelloWorld onCreate.  Adapter routes writeEvent overloads to
    # OH HiLog (kEventLogTag="AndroidEventLog", domain=0xD002000) and returns
    # empty Collection from readEvents (no /dev/log event channel on OH).
    "$SRC/src/android_util_EventLog.cpp"
    # G2.10 (2026-04-30): android.app.Activity.getDlWarning() — bionic-linker
    # API not present on OH musl; return null = "no warnings".  Activity.
    # performStart at line 8645 calls this; without it onStart fails.
    "$SRC/src/android_app_Activity.cpp"
    # G2.11 (2026-04-30): android.view.SurfaceSession 2 native methods
    # (nativeCreate / nativeDestroy).  Activity.performStart → ViewRootImpl
    # ... → new SurfaceSession() previously UnsatisfiedLinkError'd.  Adapter
    # impl returns/frees a small magic-tagged OhSurfaceSession token; AOSP
    # caller paths only use the token as opaque data, never dereference it
    # as a real SurfaceComposerClient.
    "$SRC/src/android_view_SurfaceSession.cpp"
    # G2.11 (2026-04-30): android.view.DisplayEventReceiver 4 native methods.
    # Choreographer needs vsync ticks to drive doFrame on UI thread.  Adapter
    # uses a software 60Hz timer (std::thread sleeps 16ms then calls back into
    # Java DisplayEventReceiver.dispatchVsync via JNI).  Code adapted from the
    # deprecated framework/surface/jni/android_view_surface_stubs.cpp (P13).
    "$SRC/src/android_view_DisplayEventReceiver.cpp"
    # G2.12 (2026-04-30): android.view.InputChannel 8 native methods
    # NO_INPUT_EVENT_TRANSPORT baseline.  ViewRootImpl → addToDisplay path
    # creates an InputChannel pair; without these registered, every Activity
    # crashes during setView.  Adapter returns magic-tagged OhInputChannel
    # tokens; events never flow (touch/key disabled until OH MMI hookup).
    "$SRC/src/android_view_InputChannel.cpp"
    # G2.14e (2026-05-01): android.view.InputEventReceiver 6 native methods.
    # ViewRootImpl post-addToDisplay constructs WindowInputEventReceiver;
    # NO_INPUT_EVENT_TRANSPORT baseline (no real event delivery).
    "$SRC/src/android_view_InputEventReceiver.cpp"
    # libart LOG(FATAL)/CHECK + __android_set_abort_message → hilog bridge
    # (debug_bridge_design §4.7).  Must compile with -frtti because
    # android-base/logging.h uses std::function which needs typeinfo for
    # the bound LogFunction / AbortFunction.
    "$SRC/src/libart_log_bridge.cpp"
    # graphics JNI compat shim (graphics_jni_inventory §4.1) — last-wins
    # RegisterNatives for ImageDecoder/Surface/BLASTBufferQueue/DisplayEventReceiver.
    "$SRC/src/android_graphics_compat_shim.cpp"
    # G2.14k + 2026-05-02 audit: NAR null-guard kept (see file header for why
    # removal was attempted then reverted; main-thread initChild requires it).
    "$SRC/src/libcore_util_NativeAllocationRegistry_guard.cpp"
    # G2.14n (2026-05-01): PropertyValuesHolder JNI for android.animation
    "$SRC/src/android_animation_PropertyValuesHolder.cpp"
    "$SRC/src/android_os_SystemProperties.cpp"
    "$SRC/src/android_os_Trace.cpp"
    "$SRC/src/android_os_Process.cpp"
    "$SRC/src/android_os_SystemClock.cpp"
    "$SRC/src/android_os_Binder.cpp"
    "$SRC/src/android_view_SurfaceControl.cpp"
    # 2026-05-18: 6 retired stubs git rm'd (AssetManager / ApkAssets / Canvas /
    # HardwareRenderer / RenderNode / Paint). Replaced by SRCS_AOSP 真源
    # (AssetManager_aosp.cpp + ApkAssets_aosp.cpp) + libhwui dlopen 块 (kHwuiRegFns
    # in AndroidRuntime.cpp). See doc/report/android_runtime_analysis_report.html §6.
    "$SRC/src/android_os_MessageQueue.cpp"
    "$SRC/src/com_android_internal_os_ClassLoaderFactory.cpp"
    "$SRC/src/android_graphics_Typeface.cpp"
    "$SRC/src/android_os_GraphicsEnvironment.cpp"
    # AOSP atrace symbol stubs (atrace_get_enabled_tags / begin_body / end_body)
    # — referenced by AOSP-ported android_util_AssetManager.cpp via ATRACE_NAME.
    "$SRC/src/atrace_stubs.cpp"
    # [STAGE2-UNITY parity, 2026-07-10] the 5 files below were missing from
    # this GZ05 arm64 script (it predates them) but ARE present in
    # compile_runtime_local.sh (the OrbStack recipe that built the binary
    # currently loaded from game1r_step1/, md5 724009e2...) and ARE wired
    # into the just-synced AndroidRuntime.cpp's RegJNIRec table. Added here
    # so this rebuild is symbol-parity with what's actually running, not a
    # regression to a narrower historical GZ05 build.
    "$SRC/src/android_os_Debug.cpp"
    "$SRC/src/android_hardware_SensorManager.cpp"
    "$SRC/src/android_ndk_libandroid_shim.cpp"
    "$SRC/src/android_window_show_native.cpp"
    # 2026-07-10 (L12 视频探针，codex round2 定稿后范围订正): android.media.
    # MediaPlayer 的 49 个 native 方法桩实现（stub，不做真解码）。补的是
    # kRegJNI[] 里此前对 MediaPlayer 这一条 native 注册路径的 gap —— Java 类
    # 本身已在（一份 artifacts 备份 coherent_jars/framework.jar 里核实过的）
    # framework.jar 真源里，不需要 mainline-stubs 或任何新 Java 源；但这**不是**
    # "android.media.* 零覆盖"这个更大范围的 gap 已修复 —— MediaCodec/
    # MediaExtractor 等其它 android.media.* 类的 native 注册依然完全空白，不在
    # 本次改动范围内。见文件头注释完整证据链（dexdump 反汇编 coherent_jars 备份
    # framework.jar 的 classes2.dex 得到的 49 个 native 方法真实签名，未核实
    # 设备当前实际部署的 boot image 是否为同一份)。状态=build_pass+stub探针
    # 准备完成，非 device_verified，非真实解码/像素输出。
    "$SRC/src/android_media_MediaPlayer.cpp"
)

# Phase 1: AOSP-ported register_* sources.  Compiled with C++20 +
# libandroidfw headers; objects merged at link time.  Each file's
# register_android_content_AssetManager / register_android_content_res_ApkAssets
# function is referenced from kRegJNI[] in our AndroidRuntime.cpp.
SRCS_AOSP=(
    "$SRC/src/cutils_ashmem_shim.cpp"
    "$SRC/src/androidfw/CursorWindow.cpp"
    "$SRC/src/android_database_CursorWindow.cpp"
    "$SRC/src/android_database_SQLiteCommon.cpp"
    "$SRC/src/android_database_SQLiteConnection.cpp"
    "$SRC/src/android_database_SQLiteDebug.cpp"
    "$SRC/src/android_database_SQLiteGlobal.cpp"
    "$SRC/src/sqlite3_android_shim.cpp"
    # G2.14u r2 (2026-05-07): android_util_Binder_helpers_aosp.cpp removed.
    # Parcel.cpp now self-contained — no binder header dep, no helper file
    # abstraction; binder-touching native methods inline-stubbed inside Parcel.cpp.
    "$SRC/src/android_os_Parcel_aosp.cpp"
    "$ASSET_FD_SOURCE"
    "$SRC/src/android_content_res_ApkAssets_aosp.cpp"
    "$SRC/src/android_util_StringBlock_aosp.cpp"
    "$SRC/src/android_util_XmlBlock_aosp.cpp"
    "$SRC/src/com_android_internal_util_VirtualRefBasePtr_aosp.cpp"
    # G2.14w (2026-05-08): KeyCharacterMap 13 native methods register.
    # KCM.load fallback (PhoneWindow.preparePanel → KCM.obtainEmptyMap →
    # nativeObtainEmptyKeyCharacterMap) was UnsatisfiedLinkError'ing.
    # adapter-rewritten with <binder/Parcel.h>, <input/*.h> deps stripped;
    # mMap permanently nullptr in Phase 1 — falls into AOSP's own empty-map
    # early-return path bit-identical to AOSP behaviour for empty KCMs.
    # Source pattern: AOSP 14 frameworks/base/core/jni/
    # android_view_KeyCharacterMap.cpp (284 lines).
    "$SRC/src/android_view_KeyCharacterMap_aosp.cpp"
    # 2026-05-18 (L2 path, Input_Adapter_design §3.3.5 Phase 2 + memory
    # feedback_phase1_must_be_foundation): MotionEvent JNI via direct
    # reference to AOSP 14 source.  We pull in the actual AOSP source
    # tree files (no adapter rewrite) so the implementation is bit-exact
    # and inherit-able when future App scenarios need transform
    # composition / multi-touch / pointer remapping / display rotation
    # transforms etc.
    #
    # Dependency chain (all directly referenced from $A/...):
    #   android_view_MotionEvent.cpp  — JNI bindings (917 lines)
    #   input/Input.cpp               — android::MotionEvent/KeyEvent class (1224 lines)
    #   input/InputEventLabels.cpp    — label tables used by Input.cpp
    #   hwui/apex/android_matrix.cpp  — AMatrix_getContents impl (44 lines)
    #
    # Adapter stubs (in adapter source tree, not under aosp_patches/):
    #   none — all deps resolve via -I include path additions in INC_AOSP
    #   (HmacKeyManager.h / matrix.h are direct AOSP headers; INVALID_HMAC
    #    is constexpr inline so no link dependency; HmacKeyManager class
    #    methods aren't called by MotionEvent/Input — only the mHmac field
    #    is assigned/copied).
    # 2026-05-18 (Plan A — adapter-private *_aosp.cpp): direct AOSP source
    # compilation introduced ABI mismatch via deep transitive include chain
    # (attestation/, gui/, ui::Transform pulling layouts that disagreed with
    # OH device libraries — manifested as SIGBUS in
    # libicu_jni.so:ScopedCharArrayRO 943s after launch).  Following the
    # ApkAssets_aosp.cpp model: 3 adapter-private files under
    # framework/android-runtime/src/ + framework/android-runtime/include/input/
    # (shadow header replacing <input/Input.h>).  Class layouts are now
    # fully adapter-controlled.  See file-header comments for Phase 1 vs
    # Phase 2 boundary.
    "$SRC/src/android_input_InputEventLabels_aosp.cpp"
    "$SRC/src/android_input_Input_aosp.cpp"
    "$SRC/src/android_view_MotionEvent_aosp.cpp"
    "$SRC/src/android_view_KeyEvent_aosp.cpp"
    "$SRC/src/android_opengl_EGL14_adapter.cpp"
    # [STAGE2-GL parity 2026-07-10] Whole android.opengl.GLES* family, raw AOSP
    # generated sources — mirrors compile_runtime_local.sh exactly.
    # 2026-07-10 (adapter self-containment audit): these 3 files get compiled
    # directly into adapter's own deliverable (liboh_android_runtime.so), so
    # per this repo's existing "compiled into our own .so = vendor it" rule
    # (PROVENANCE.md, applied earlier to the framework/android-runtime/*_aosp.cpp
    # files) they're now vendored, byte-identical (md5-verified against both
    # GZ05 /data/aosp and a second independent AOSP mirror), at
    # third_party/aosp_raw/ instead of read from external $AOSP_ROOT.
    "$ADAPTER_ROOT/third_party/aosp_raw/frameworks/base/core/jni/android_opengl_GLES20.cpp"
    "$ADAPTER_ROOT/third_party/aosp_raw/frameworks/base/core/jni/android_opengl_GLES30.cpp"
    "$ADAPTER_ROOT/third_party/aosp_raw/frameworks/base/core/jni/android_opengl_GLES31.cpp"
    # [UNITY-NDK-ASSET parity 2026-07-10] real NDK AAssetManager backed by
    # AssetManager2 (android_util_AssetManager_aosp.cpp) — matches
    # compile_runtime_local.sh; gives AAssetManager_fromJava/AAsset_* symbols
    # some Unity/NDK code paths resolve directly (no JNI registration needed,
    # pure C API export). Vendored for the same reason as the 3 GLES files above.
    "$ADAPTER_ROOT/third_party/aosp_raw/frameworks/base/native/android/asset_manager.cpp"
    # android_matrix.cpp stays disabled — its only consumer was AOSP's
    # MotionEvent.cpp; the adapter MotionEvent_aosp.cpp declares the
    # AMatrix_getContents extern signature and links against the device
    # libhwui.so symbol provider (G2.14 already pulls libhwui via dlopen).
    # "$A/frameworks/base/libs/hwui/apex/android_matrix.cpp"
)

echo "=========================================="
echo "  liboh_android_runtime.so cross-compile"
echo "=========================================="

# 2026-05-18 (L2): AIDL pre-gen step for AOSP input subsystem.
# Input.h includes <android/os/IInputConstants.h>, an AIDL-generated header.
# We run AOSP's prebuilt aidl tool to produce it on-the-fly into a build-
# private include dir so we don't commit generated source.
AIDL_BIN="${L03_A12_AIDL:-$A/prebuilts/build-tools/linux-x86/bin/aidl}"
AIDL_GEN="$BUILD/aidl-gen"
mkdir -p "$AIDL_GEN"
if [ ! -f "$AIDL_GEN/headers/android/os/IInputConstants.h" ]; then
    echo "AIDL: generating IInputConstants.h ..."
    if [ ! -x "$AIDL_BIN" ]; then
        echo "FAIL: aidl tool not found at $AIDL_BIN"
        exit 1
    fi
    "$AIDL_BIN" --lang=cpp \
        -o "$AIDL_GEN/out" -h "$AIDL_GEN/headers" \
        -I "$A/frameworks/native/libs/input" \
        "$A/frameworks/native/libs/input/android/os/IInputConstants.aidl" \
        || { echo "FAIL: aidl gen IInputConstants"; exit 1; }
    echo "  OK: $AIDL_GEN/headers/android/os/IInputConstants.h"
fi
INC_AOSP="$INC_AOSP -I$AIDL_GEN/headers"

# 2026-05-18 (L2 / feedback_phase1_must_be_foundation):
# AOSP's InputEventLabels.cpp includes "input.h-labels.h" which is generated
# by system/core/toolbox/generate-input.h-labels.py from <linux/input.h>
# (bionic uapi).  We run the same generator here to keep label tables in
# sync with AOSP — running on the same kernel header AOSP sees.
LABELS_GEN="$BUILD/labels-gen"
LABELS_OUT="$LABELS_GEN/input.h-labels.h"
if [ ! -f "$LABELS_OUT" ]; then
    echo "LABELS: generating input.h-labels.h ..."
    mkdir -p "$LABELS_GEN"
    GEN_PY="$A/system/core/toolbox/generate-input.h-labels.py"
    KERNEL_INPUT_H="$A/bionic/libc/kernel/uapi/linux/input.h"
    if [ ! -f "$GEN_PY" ] || [ ! -f "$KERNEL_INPUT_H" ]; then
        echo "FAIL: missing $GEN_PY or $KERNEL_INPUT_H"
        exit 1
    fi
    "$PYTHON" "$GEN_PY" "$KERNEL_INPUT_H" > "$LABELS_OUT" \
        || { echo "FAIL: input.h-labels.h gen"; exit 1; }
    echo "  OK: $LABELS_OUT ($(stat -c%s "$LABELS_OUT") bytes)"
fi
INC_AOSP="$INC_AOSP -I$LABELS_GEN"

INC_AOSP="$INC_AOSP -I$SRC/src/sqlite -I$A/external/sqlite/android"
objs=()
if [ ! -f "$BUILD/sqlite3.o" ]; then
"$L03_A12_CC" --target=aarch64-linux-ohos --sysroot="$SR" -I"$SR/include/aarch64-linux-ohos" -fPIC -O2 -DSQLITE_ENABLE_COLUMN_METADATA -DSQLITE_ENABLE_FTS3 -DSQLITE_ENABLE_FTS3_PARENTHESIS -DSQLITE_ENABLE_FTS4 -DSQLITE_ENABLE_FTS5 -DSQLITE_ENABLE_RTREE -DSQLITE_ENABLE_JSON1 -DSQLITE_ENABLE_DBSTAT_VTAB -DSQLITE_THREADSAFE=2 -DSQLITE_TEMP_STORE=3 -c "$SRC/src/sqlite/sqlite3.c" -o "$BUILD/sqlite3.o" || exit $?
fi
objs+=("$BUILD/sqlite3.o")
for s in "${SRCS[@]}"; do
    bn=$(basename "$s" .cpp)
    obj="$BUILD/${bn}.o"
    if [ -f "$obj" ]; then objs+=("$obj"); continue; fi
    echo -n "  ${bn}.cpp ... "
    if $CXX $COMMON -include "$BC/libcxx_compat.h" $INC $DEFS \
        -c "$s" -o "$obj" 2>"$BUILD/${bn}.err"; then
        echo "OK ($(stat -c%s "$obj") bytes)"
        objs+=("$obj")
    else
        echo "FAIL"
        head -30 "$BUILD/${bn}.err"
        exit 1
    fi
done

# AOSP-ported sources (different flag set)
echo ""
echo "  AOSP-ported register_* sources (C++20)"
for s in "${SRCS_AOSP[@]}"; do
    bn=$(basename "$s" .cpp)
    obj="$BUILD/${bn}.o"
    if [ -f "$obj" ]; then objs+=("$obj"); continue; fi
    echo -n "  ${bn}.cpp ... "
    if $CXX $COMMON_AOSP $INC_AOSP -c "$s" -o "$obj" 2>"$BUILD/${bn}.err"; then
        echo "OK ($(stat -c%s "$obj") bytes)"
        objs+=("$obj")
    else
        echo "FAIL"
        head -30 "$BUILD/${bn}.err"
        exit 1
    fi
done

echo ""
echo "  linking liboh_android_runtime.so ..."
# Add libandroidfw and AOSP runtime deps so AssetManager2/ApkAssets/Theme
# real C++ classes resolve at runtime via DT_NEEDED.
LDFLAGS="-B$ML -L$ML -L$AOSP_LIB -L$OH_OUT/packages/phone/system/lib64/ndk -L$OH_OUT/packages/phone/system/lib64/platformsdk -L$OH_OUT/packages/phone/system/lib64/chipset-sdk-sp -L$OUT -shared -fPIC -Wl,-z,defs -Wl,--no-allow-shlib-undefined -Wl,--no-undefined -Wl,--build-id=sha1 -Wl,-soname,liboh_android_runtime.so"
if $CXX --target=aarch64-linux-ohos $LDFLAGS \
    -o "$OUT/liboh_android_runtime.so" -lEGL -lGLESv2 -lGLESv3 \
    "${objs[@]}" \
    -landroidfw -lbase -lutils -lcutils -lziparchive -licuuc \
    -llog -lbionic_compat -lhitrace_ndk.z -lbegetutil.z \
    "/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/platform-pool/system/lib64/chipset-sdk-sp/libnative_window.so" \
    -l:libhilog.so \
    -loh_adapter_bridge \
    -Wl,--no-as-needed -lnativehelper \
    -Wl,--no-as-needed "$WLTG_REGISTRY" -lnativeloader \
    "/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/libshared_libz.z.so" \
    2>"$BUILD/link.err"; then
    sz=$(stat -c%s "$OUT/liboh_android_runtime.so")
    echo "  OK ($sz bytes)"
    file "$OUT/liboh_android_runtime.so"
else
    echo "  FAIL"
    head -30 "$BUILD/link.err"
    exit 1
fi

runtime_dynamic="$BUILD/runtime.dynamic"
runtime_dynsym="$BUILD/runtime.dynsym"
runtime_header="$BUILD/runtime.header"
runtime_notes="$BUILD/runtime.notes"
"$READELF" -d --wide "$OUT/liboh_android_runtime.so" >"$runtime_dynamic"
"$READELF" --dyn-syms --wide "$OUT/liboh_android_runtime.so" >"$runtime_dynsym"
"$READELF" --file-header --wide "$OUT/liboh_android_runtime.so" >"$runtime_header"
"$READELF" --notes --wide "$OUT/liboh_android_runtime.so" >"$runtime_notes"
grep -q 'Class:.*ELF64' "$runtime_header" \
    && grep -q 'Machine:.*AArch64' "$runtime_header" || {
    echo "FAIL: runtime is not ELF64/AArch64"
    rm -f "$OUT/liboh_android_runtime.so"
    exit 1
}
runtime_soname_count=$(awk -F'[][]' \
    '/SONAME/ && $2 == "liboh_android_runtime.so" {count++} END {print count + 0}' \
    "$runtime_dynamic")
[ "$runtime_soname_count" -eq 1 ] || {
    echo "FAIL: runtime SONAME count=$runtime_soname_count"
    rm -f "$OUT/liboh_android_runtime.so"
    exit 1
}
if grep -Eq '\((RPATH|RUNPATH|TEXTREL)\)' "$runtime_dynamic"; then
    echo "FAIL: runtime contains RPATH/RUNPATH/TEXTREL"
    rm -f "$OUT/liboh_android_runtime.so"
    exit 1
fi
grep -q 'Build ID:' "$runtime_notes" || {
    echo "FAIL: runtime lacks a GNU Build-ID"
    rm -f "$OUT/liboh_android_runtime.so"
    exit 1
}
needed_count=$(awk -F'[][]' '/Shared library:/ && $2 == "libnativeloader.so" {count++} END {print count + 0}' "$runtime_dynamic")
create_und=$(awk '
    $1 ~ /^[0-9]+:$/ && NF >= 8 {
        name=$8; sub(/@.*/, "", name)
        if (name == "CreateClassLoaderNamespace" && $5 == "GLOBAL" && $7 == "UND") count++
    }
    END {print count + 0}
' "$runtime_dynsym")
if [ "$needed_count" -ne 1 ] || [ "$create_und" -ne 1 ]; then
    echo "FAIL: Profile B runtime edge needed=$needed_count create_und=$create_und"
    rm -f "$OUT/liboh_android_runtime.so"
    exit 1
fi
echo "  Profile B runtime edge: PASS"

echo ""
echo "=========================================="
echo "  Output: $OUT/liboh_android_runtime.so"
echo "  Export check:"
"$NM" \
    -D --defined-only --demangle "$OUT/liboh_android_runtime.so" 2>/dev/null \
    | grep -E "startReg|register_android_util_Log|register_android_content_AssetManager" | head -5
echo "=========================================="
