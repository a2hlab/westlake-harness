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
# compile_oh_android_runtime.sh
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
#  ▶ 一句话定位：编 adapter 自家的 liboh_android_runtime.so（替代 AOSP 原
#    libandroid_runtime.so 2.28MB → ≈170KB）。
#
#  ▶ 产物：out/adapter/liboh_android_runtime.so 单一 .so
#    - 36 个 .o（24 SRCS 自写 + 6 SRCS_AOSP 副本/直引 + 6 retired 已删）
#    - 链 -landroidfw -lbase -lutils -lcutils -lziparchive -lnative_window
#      -l:libhilog.so 等 OH 端 + adapter cross-compiled .so
#    - 导出 _ZN7android14AndroidRuntime8startRegEP7_JNIEnv 等关键符号
#      与 AOSP 原版对齐，让 appspawn-x 的 dlsym 调用点零修改
#
#  ▶ 何时跑（trigger 条件）：
#    - framework/android-runtime/src/ 下任何 .cpp/.h 改动后
#    - aosp_patches/ 修改后（涉及 SRCS_AOSP 那 5 个文件的同步）
#    - 升级 OH SDK / libandroidfw 等链接库后
#    - 不需要：改 AOSP native 源码（那是 cross_compile_arm32.sh 范围）
#
#  ▶ 上下游关系：
#    - 上游依赖 ← cross_compile_arm32.sh：必须先跑 cross_compile_arm32.sh
#      产出 22+ 个 AOSP native .so 到 out/aosp_lib/，本脚本链它们
#      （-landroidfw / -lbase / -lutils / -lcutils / -lziparchive 等）
#    - 上游依赖 ← compile_libhwui.sh：产出 libhwui.so，本脚本不链接但
#      运行时 dlopen + dlsym 调它的 45 个 register_X
#    - 上游依赖 ← OH 系统编译：libhilog.so / libnative_window.so / libbegetutil
#      / libhitrace_ndk 等来自 ~/oh/out/rk3568/
#    - 下游 → deploy 链路：产物推到设备 /system/lib/ + /system/android/lib/
#      （双路径，per reference_liboh_android_runtime_dual_path memory）
#
#  ▶ NOT 范围（避免误用）：
#    - 不编 AOSP libart / libhwui / libandroidfw 等（→ cross_compile_arm32.sh）
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

OH="${OH_ROOT:-$HOME/oh}"
A="${AOSP_ROOT:-$HOME/aosp}"
ADAPTER_ROOT="${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
SRC="$ADAPTER_ROOT/framework/android-runtime"
OUT="$ADAPTER_ROOT/out/adapter"
AOSP_LIB="$ADAPTER_ROOT/out/aosp_lib"
BUILD="$ADAPTER_ROOT/out/android-runtime-build"
BC="$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include"

mkdir -p "$BUILD" "$OUT"

OH_OUT="$OH/out/rk3568"
SR="$OH_OUT/obj/third_party/musl/usr"
ML="$SR/lib/arm-linux-ohos"

CXX="$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++"

# Our own sources: same flags as before
COMMON="--target=arm-linux-ohos -march=armv7-a --sysroot=$SR -I$SR/include/arm-linux-ohos -fPIC -O2 -std=gnu++17 -fno-rtti"
# 2026-07-09: android_graphics_compat_shim.cpp (one of $SRCS below) #includes
# "pixel_format_mapper.h", which lives in framework/surface/jni/, not in
# framework/android-runtime/{src,include}/. Missing -I here made standalone
# single-directory builds fail with a plain "file not found" (not a
# hardcoded-path bug — just a missing include dir); found + fixed while
# re-verifying this build target.
INC="-I$SRC/include -I$SRC/src -I$ADAPTER_ROOT/framework/surface/jni -I$BC -I$A/system/logging/liblog/include -I$A/libnativehelper/include_jni -I$A/libnativehelper/include -I$A/system/libbase/include -I$OH/base/hiviewdfx/hilog/interfaces/native/innerkits/include"
DEFS="-D__OHOS__ -D_GNU_SOURCE"

# AOSP-ported sources: C++20, AOSP includes, no -include libcxx_compat
# SR points to .../musl/usr, but --sysroot semantics expect the PARENT (so
# clang adds /usr/include). For AOSP-ported build use SR_PARENT to match the
# standalone-validated invocation.
SR_PARENT="$OH_OUT/obj/third_party/musl"
COMMON_AOSP="--target=arm-linux-ohos -march=armv7-a -mfpu=neon-vfpv4 -mfloat-abi=soft --sysroot=$SR_PARENT -fPIC -O2 -std=c++20 -fno-exceptions -Wno-reorder-init-list"
INC_AOSP="-I$SRC/src -I$SRC/include \
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
 -I$A/frameworks/base/core/jni/include"
# 2026-05-18 (control experiment): OH Skia m133 include paths removed.
# Suspect Skia ABI drift between OH skia/m133 and AOSP-expected Skia is the
# source of ART mark_sweep "not contained by any spaces" abort.  If
# helloworld returns to G214bj working state after this rollback,
# direction is confirmed and a longer-term fix is needed (sz3 probe of
# Skia class sizeofs across both translation-unit contexts).

SRCS=(
    "$SRC/src/AndroidRuntime.cpp"
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
)

# Phase 1: AOSP-ported register_* sources.  Compiled with C++20 +
# libandroidfw headers; objects merged at link time.  Each file's
# register_android_content_AssetManager / register_android_content_res_ApkAssets
# function is referenced from kRegJNI[] in our AndroidRuntime.cpp.
SRCS_AOSP=(
    # G2.14u r2 (2026-05-07): android_util_Binder_helpers_aosp.cpp removed.
    # Parcel.cpp now self-contained — no binder header dep, no helper file
    # abstraction; binder-touching native methods inline-stubbed inside Parcel.cpp.
    "$SRC/src/android_os_Parcel_aosp.cpp"
    "$SRC/src/android_util_AssetManager_aosp.cpp"
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
AIDL_BIN="$A/prebuilts/build-tools/linux-x86/bin/aidl"
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
    python3 "$GEN_PY" "$KERNEL_INPUT_H" > "$LABELS_OUT" \
        || { echo "FAIL: input.h-labels.h gen"; exit 1; }
    echo "  OK: $LABELS_OUT ($(stat -c%s "$LABELS_OUT") bytes)"
fi
INC_AOSP="$INC_AOSP -I$LABELS_GEN"

objs=()
for s in "${SRCS[@]}"; do
    bn=$(basename "$s" .cpp)
    obj="$BUILD/${bn}.o"
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
LDFLAGS="-B$ML -L$ML -L$AOSP_LIB -L$OH_OUT/packages/phone/system/lib/ndk -L$OH_OUT/packages/phone/system/lib/platformsdk -L$OH_OUT/packages/phone/system/lib/chipset-sdk-sp -L$ADAPTER_ROOT/out/adapter -shared -fPIC -Wl,--allow-shlib-undefined"
if $CXX --target=arm-linux-ohos $LDFLAGS \
    -o "$OUT/liboh_android_runtime.so" \
    "${objs[@]}" \
    -landroidfw -lbase -lutils -lcutils -lziparchive -licuuc \
    -llog -lbionic_compat -lhitrace_ndk.z -lbegetutil.z \
    -lnative_window \
    -l:libhilog.so \
    -loh_adapter_bridge \
    -l:libz.so \
    2>"$BUILD/link.err"; then
    sz=$(stat -c%s "$OUT/liboh_android_runtime.so")
    echo "  OK ($sz bytes)"
    file "$OUT/liboh_android_runtime.so"
else
    echo "  FAIL"
    head -30 "$BUILD/link.err"
    exit 1
fi

echo ""
echo "=========================================="
echo "  Output: $OUT/liboh_android_runtime.so"
echo "  Export check:"
"$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-nm" \
    -D --defined-only --demangle "$OUT/liboh_android_runtime.so" 2>/dev/null \
    | grep -E "startReg|register_android_util_Log|register_android_content_AssetManager" | head -5
echo "=========================================="
