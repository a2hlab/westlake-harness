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
# [DEPRECATED Phase 1 — 2026-05-21] Use build_aosp_lib.sh --target=libhwui.so instead.
echo "[DEPRECATED] $(basename "$0") is wrapped by build_aosp_lib.sh — kept as internal/ implementation; Phase 4 will move it" >&2
# ============================================================================
# 用途：libhwui.so 完整编译流水线 (G2.14bf 沉淀, 2026-05-12)。
#       合并历史 4 个 sh + restore_after_sync.sh A9-A9f 链:
#         compile_libhwui.sh + compile_hwui_stubs.sh + compile_hwui_shims.sh
#         + compile_skia_rtti_shim.sh + link_libhwui.sh
#       5 phase pipeline:
#         Phase 0 = apply hwui source patches (idempotent, pre-checked)
#         Phase 1 = compile hwui sources (88 hwui .cpp + 1 ColorSpace.cpp)
#         Phase 2 = compile adapter shim .o + 2 shim .so (oh_hwui_shim + skia_rtti_shim)
#         Phase 3 = link libhwui.so
#         Phase 4 = UND audit gate
# ============================================================================
# 重复犯错警示 (compile 类, 调改前必读)
# ============================================================================
# 以下是 hwui 编译链反复踩过的坑, 每一条都让 libhwui.so dlopen / 链接 / 装
# 设备启动死过. 修改本脚本前先把对应防护是否到位过一遍.
#
# [C-1] PHASE list 漂移 + stale .o 撑住增量编译
#   现象: rm -rf $OBJ/*.o 后重编 link 突然报 ReliableSurfaceD1Ev /
#         ColorSpace::sRGB 等 C++ class method UND not found; dlopen 失败.
#   根因: 历史 compile_libhwui_phase1.sh 把 renderthread/ReliableSurface.cpp
#         和 frameworks/native/libs/ui/ColorSpace.cpp 加进 PHASE; 后续 refactor
#         移除但留下的 .o 在 ~/adapter/out/hwui-build/obj/ 残留多个月撑住增量
#         编译; rm -rf 暴露漂移.
#   措施: 所有 hwui 源 .cpp 必须显式在 PHASE1_SRCS / PHASE2_SRCS /
#         PHASE_NATIVE_SRCS 之一中. 2026-05-27 改为默认增量 (保留 .o), --clean 才 rm $OBJ/*.o.
#         代价: 增删源文件 / 改 patch 结构后须手动 --clean, 否则 stale .o 可能漂移 (原默认 clean 就为防此).
#
# [C-2] ColorSpace.h shim 与真 header 之间的歧义
#   现象: utils_Color.cpp 引用 android::ColorSpace::sRGB() 报 UND.
#   根因: 历史 compile_libhwui_phase1.sh (Apr 10) 在
#         build/skia_compat_headers/ui/ColorSpace.h 写 inline shim:
#           static const ColorSpace& sRGB() { static ColorSpace s; return s; }
#         把定义内联进每个 .o, 无 UND. 后续 refactor 改用真
#         frameworks/native/libs/ui/include/ui/ColorSpace.h, 但没补 .cpp 编译,
#         留下 UND. (memory: 2026-05-12 G2.14bf 发现)
#   措施: PHASE_NATIVE_SRCS 显式加 frameworks/native/libs/ui/ColorSpace.cpp
#         (不在 hwui 树内, 需特殊 path 处理). 若拉入新 UND, 退而在
#         hwui_oh_abi_patch.cpp 加 sRGB stub.
#
# [C-3] ReliableSurface 上游版本拉入 18 个 AOSP NDK UND
#   现象: 编 ReliableSurface.cpp 上游版本后, libhwui.so dlopen 报
#         ANativeWindow_setCancelBufferInterceptor / cancelBuffer /
#         AHardwareBuffer_describe 等 18 个 C function symbol not found.
#   根因: ReliableSurface 是 AOSP reliability wrapper, init() 无条件调 5 个
#         ANativeWindow_set*Interceptor + hooks 调 13 个 ANativeWindow_* /
#         AHardwareBuffer_* AOSP NDK; OH 都无对应实现.
#   措施: aosp_patches/libs/hwui/renderthread/ReliableSurface.cpp 写 stub 版
#         (10 method 全 no-op + [G2.14bf stub] fprintf 标记 + 0 NDK 调用),
#         compile_libhwui.sh 的 HWUI_PATCH 优先级机制自动用 stub 替上游.
#   血训: 用户多次强调 "不能直接返 0, 至少需要增加调试 log, 最好能适配到 OH" —
#         stub 必须带 fprintf 调用记录, 不能哑实现.
#
# [C-4] -l:libskia_canvaskit.z.so link 缺失 (G2.14ay 引入)
#   现象: probe 加 surface->readPixels / recordingContext / gctx->oomed 后,
#         libhwui.so 报 3 个 SkSurface/GrDirectContext UND not found.
#   根因: 历史 link_libhwui.sh line 109 "no direct libskia_canvaskit dep here"
#         (2026-05-02 G2.14n+) 假设 liboh_hwui_shim.so 桥所有 Skia 引用; 但
#         shim 只桥了 GrAHB + Typeface init, 没桥 SkSurface 普通成员方法.
#   措施: phase 3 LIBS 加 -l:libskia_canvaskit.z.so (在 -loh_skia_rtti_shim 之后)
#         让 NEEDED 出现.
#
# [C-5] LDFLAGS --unresolved-symbols=ignore-all 隐藏致命 UND
#   现象: link 成功了, deploy 后 helloworld dlopen 才失败 (class_linker.cc:560
#         Error relocating /system/android/lib/libhwui.so: XXX symbol not found).
#   根因: lenient link 模式接受所有 UND; OH musl/ART 在 dlopen 时严格检查
#         C++ class method UND (PLT eager bind), 一个找不到就拒载整 .so.
#         C function UND (libc/libutils 类) 通过 NEEDED chain 可 lazy 解.
#   措施: phase 4 UND audit gate — 链接后立即 diff 当前 .so vs known-good
#         libhwui.so 的 UND set; 新增 C++ class method UND 即 FAIL (block 部署);
#         新增 C function UND 只 WARN.
#
# [C-6] 4 个编译脚本碎片化 (合并前的历史包袱, 本脚本即解药)
#   现象: 调用顺序错或漏调任一脚本 → 不完整 libhwui.so; 各 .o 来自不同脚本,
#         link 盲 glob $OBJ/*.o 不报错.
#   根因: 增量演化, 每 milestone 加一个 sh; restore_after_sync.sh 只 apply
#         patch 不验证完整 build.
#   措施: 本脚本 (G2.14bf, 2026-05-12) 合并 4 sh + A9 chain + 添 UND audit phase;
#         单一权威入口. legacy sh 改 5-line forwarding wrapper 保兼容.
#
# [C-7] -Bsymbolic-functions + dlsym 跨 .so namespace 隔离
#   现象: adapter 间 dlsym(RTLD_DEFAULT, sym) 失败, 静默返 NULL → startReg
#         不跑 → JNI register 全没 → 第一个 Log.i UnsatisfiedLinkError.
#   根因: OH dynamic linker namespace 隔离让 RTLD_DEFAULT 搜索范围不含 sibling .so.
#   措施: LDFLAGS 包含 -Wl,-Bsymbolic-functions 让 .so 内部调用直接 bind;
#         跨 .so 必须 dlopen(name, RTLD_NOLOAD) 显式拿 handle 再 dlsym.
#         (memory: feedback_rtldnow_dlopen_needed.md / project_g214ac_dlsym_cross_so_fix.md)
#
# [C-8] OH libskia_canvaskit ABI 宏对齐 (G2.14bf 启动)
#   现象: SkCanvas::clear(red) 写到 fbo 显红, 但 displayList->draw(canvas)
#         静默丢所有 op, View tree 不渲染.
#   根因: hwui 编译时未 define ENABLE_TEXT_ENHANCE / SKIA_OHOS_SINGLE_OWNER /
#         SK_GANESH (OH libskia_canvaskit.z.so 真编入这些 -D), 导致 SkTypeface
#         vtable (+2 槽) / SkFontArguments size (+12 字节) / SingleOwner class
#         (1 字节 vs 40+ 字节) ABI 在 hwui 与 OH lib 之间不匹配; byte-buffer
#         reinterpret_cast 共用 Skia type 时字段错位 → op silent NOOP.
#   措施: DEFS 加 -DENABLE_TEXT_ENHANCE -DSKIA_OHOS_SINGLE_OWNER -DSK_GANESH
#         (Stage 1); 后续根据 probe 信号扩展全 OH 私有宏集.
#
# [C-9] hwui 源码补丁现由 restore_after_sync.sh 应用，本脚本不再 patch (2026-05-21)
#   现象: 历史上 compile_libhwui.sh phase 0 直接 apply hwui_rk3568.patch + 7 个
#         per-file diff patch; 跟 restore_after_sync.sh A9/A9b 完全重复。
#   措施: 2026-05-21 重构后 compile_libhwui.sh 不再 apply 补丁，只做编译。
#         补丁应用归 restore_after_sync.sh 唯一入口，遍历
#         aosp_patches/libs/hwui/patches/*.patch (51 个 per-file pristine→final
#         patches，无 chain dependency)。本脚本前提是 source 已 patched 状态。
#
# [C-10] typeface_minimal_stub.cpp 已废弃 (G2.14r 2026-05-02 沉淀)
#   现象: libhwui.so link 报 multiple definition of
#         register_android_graphics_Typeface.
#   根因: 早期 P15 (2026-04-11) 创建 stub 替 AOSP jni/Typeface.cpp (#if 0 灭活);
#         G2.14q (2026-05-02) 恢复 AOSP 原版 + 编 jni/fonts/Font.cpp +
#         FontFamily.cpp 后, stub 与原版同时编入就 dup symbol.
#   措施: phase 2 编 stub 路径禁用 (DEPRECATED_TYPEFACE_STUB_BLOCK marker);
#         残留 typeface_minimal_stub.o 在 obj/ 主动 rm 防 link 撞名.
#
# [C-12] compile_libhwui_jni.sh 历史输出 dir 错配漂移
#   现象: 全 clean rebuild 后 libhwui.so 缺 16 个 register_android_graphics_* T
#         symbol; helloworld 启动立即闪退 (deploy 后 ~30ms 内 AMS 报
#         Ability on scheduler died, hwui JNI 注册链断裂导致).
#   根因: 历史上 compile_libhwui_jni.sh (8200 bytes) 与 compile_libhwui.sh
#         并列存在, 各管 disjoint 源集:
#           compile_libhwui.sh     -> $OUT_BUILD/obj/   (88 hwui core .o)
#           compile_libhwui_jni.sh -> $OUT/hwui/obj/    (66 JNI binding .o)
#         link_libhwui.sh 只读 $OUT_BUILD/obj/. 历史靠某次手工
#         "cp $OUT/hwui/obj/*.o $OUT_BUILD/obj/" 残留把 61 个 jni_*.o
#         留在 link 的 obj/ 里, 撑住后续每次 build (incremental). 谁也
#         没把 cp 步骤沉淀进脚本. rm -rf *.o 即暴露漂移.
#   措施: 本脚本 phase1 内嵌 compile_jni_files() — 递归 find jni/ + apex/
#         + jni/text/ + jni/fonts/ 全部 *.cpp (排 jni/pdf/, 0509-ok backup
#         实测未编), 输出 .o 直写 $OBJ (= hwui-build/obj/), 与 link
#         同 dir. compile_libhwui_jni.sh 改 5-line forwarding wrapper.
#         参考 0509-ok backup ~/bkup/adapter-0509-ok/ 的 153 .o baseline.
#
# [C-13] minikin / harfbuzz_ng 真 header 必须在 SKIA_COMPAT stub 之前
#   现象 (G2.14o, 2026-05-02): jni/Paint.cpp populateSkFont 路径 SIGILL —
#         SkRefCntBase::ref() refcount<=0 SK_ABORT trap. [POP_SKFONT] 探针
#         实证 vtable=_ZTVN7minikin11MinikinFontE (stub MinikinFont vtable).
#   根因: SKIA_COMPAT/ 历史含 stub minikin/Font.h 在前; INC 顺序若把
#         $SKIA_COMPAT 摆在 $AOSP/frameworks/minikin/include 之前, jni/Paint.cpp
#         编译时拿到 stub MinikinFont (typeface() inline fallback 创建 stub
#         MinikinFont 实例), 之后被 populateSkFont 当 MinikinFontSkia 强转
#         → 读 garbage refcount → SIGILL.
#   措施: INC 顺序固定为
#           AOSP minikin + harfbuzz_ng + freetype  (real headers)
#           ...
#           SKIA_COMPAT (stub headers, fills gaps only)
#         本脚本 INC 已按此序; refactor 时不可调换.
#         (memory: project_g214o_typeface_breakthrough.md)
#
# [C-14] jni/text/ 子目录历史被 compile_libhwui_jni.sh 主 glob 漏掉 (G2.14t fix)
#   现象 (G2.14t, 2026-05-07): HelloWorld TextView.onMeasure → StaticLayout.generate
#         → LineBreaker$Builder.build → LineBreaker.<clinit> 抛 UnsatisfiedLinkError
#         on nGetReleaseFunc → ART 抛异常 + AMS kill helloworld before first frame.
#   根因: 历史 compile_libhwui_jni.sh main 循环只 glob $HWUI_SRC/jni/*.cpp
#         (top-level), 不递归 text/. AOSP libhwui 有 4 个 text JNI 文件提供
#         apex/jni_runtime.cpp:149-152 引用的 register_android_graphics_text_*:
#           GraphemeBreak.cpp → register_android_graphics_text_GraphemeBreak
#           LineBreaker.cpp   → register_android_graphics_text_LineBreaker
#           MeasuredText.cpp  → register_android_graphics_text_MeasuredText
#           TextShaper.cpp    → register_android_graphics_text_TextShaper
#         缺这 4 个 .o 时 nGetReleaseFunc 找不到 → ULE.
#   措施: 本脚本 compile_jni_files() 用 find 递归收集 jni/ 下所有 *.cpp (排
#         pdf/), 自动跟踪 text/ + fonts/ + 任何新增子目录.
#
# [C-15] apex/jni_runtime.cpp 永远不编 — register_android_graphics_classes 已 DISABLED
#   现象 (G2.14bf, 2026-05-12 调查发现): 0509-ok backup obj/ 中 **没有**
#         apex_jni_runtime.o; compile_libhwui_jni.sh 尝试编但因
#         vkEnumerateInstanceVersion (Vulkan 函数指针 typedef vs 实际函数)
#         未声明编译失败. libhwui.so 一直没 export register_android_graphics_classes.
#   根因: aosp_patches/frameworks/base/core/jni/AndroidRuntime.cpp.patch line 72
#         显式 DISABLED REG_JNI(register_android_graphics_classes) — partial-sync
#         strategy 不需要 umbrella JNI registration. 直接列在 kHwuiRegFns 表里
#         的 register_X 函数才需要真定义 (jni/Bitmap.cpp / Canvas.cpp / 等).
#   措施: compile_jni_files() 主动 SKIP apex/jni_runtime.cpp; 编译失败是预期不是 bug.
#         未来若 partial-sync 策略改 full-sync, 要先取消 AndroidRuntime.cpp.patch
#         里 register_android_graphics_classes 的 DISABLED, 再补 apex/ 编译.
#
# [C-11] check_skia_rtti_coverage.sh 是 phase 3 link 硬依赖
#   现象: link_libhwui.sh 调 check_skia_rtti_coverage.sh 失败时直接 exit 1.
#   根因: libhwui.so 引用的 Sk* RTTI typeinfo (_ZTI*/_ZTS*) 由
#         liboh_skia_rtti_shim.so 提供; 若 hwui 引入新 Sk* 派生类 (e.g. new
#         SkCanvas 子类) 但 discover_skia_rtti_syms.sh 未 rerun, shim class
#         list 与 libhwui .o 真实需求漂移会让运行时 dynamic_cast 返 nullptr.
#   措施: phase 2c 内嵌 check; 失败立即 die. 任何新增 Sk* 派生必须 rerun
#         discover_skia_rtti_syms.sh 更新 class list.
#
# 修改本脚本任何 PHASE list / DEFS / LIBS / -l 前, 必须把对应警示项找出来,
# 看清是否还在防护之中. 增量演化路径上的每一个 milestone 都有可能引入新
# 警示项 (e.g. G2.14bd stencil fix, G2.14be DisplayList probe), 沉淀到这里.
# ============================================================================
#
# ============================================================================
# Annex A — Original compile_libhwui_jni.sh (185 lines) per-line audit trail
# ============================================================================
# Snapshot source : ~/bkup/adapter-0509-ok/build/compile_libhwui_jni.sh
#                   (last stable pre-G2.14bf version, 2026-05-09).
# Local backup    : D:\code\adapter\bkup\compile_libhwui_jni.original.sh
#
# Each original line below is transcribed verbatim, tagged with one of:
#   [R]   RETAINED  — line preserved verbatim in this unified script.
#   [M]   MODIFIED  — preserved but altered; note explains the diff.
#   [D]   DELETED   — not preserved; note explains why dropped.
#
# Format:
#   # L<NNN>  [TAG]  <verbatim original text>
#   #                └→ note: <destination line in this file / reason for drop>
#
# Grep `# L042` to jump to a specific original line.
# ----------------------------------------------------------------------------
#
# L001  [D]  #!/bin/bash
#            └→ note: superseded by this unified script's own shebang at line 1.
# L002  [M]  # Compile libhwui JNI files (Phase 3) using the same flags as compile_libhwui.sh.
#            └→ note: intent absorbed into compile_jni_files() docblock (Phase 1 section).
# L003  [R]  set -o pipefail
#            └→ note: line 211 (paired with new `set -e` on line 210 for strict mode).
# L004  [R]  (blank)
# L005  [M]  OH=$HOME/oh
#            └→ note: line 216 — now `OH="${OH_ROOT:-$HOME/oh}"` for env override.
# L006  [M]  AOSP=$HOME/aosp
#            └→ note: line 217 — `AOSP="${AOSP_ROOT:-$HOME/aosp}"`.
# L007  [M]  ADAPTER=/home/HanBingChen/adapter
#            └→ note: line 218 — `ADAPTER="${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"`.
# L008  [R]  OH_OUT=$OH/out/wukong100
#            └→ note: line 226.
# L009  [R]  SR=$OH_OUT/obj/third_party/musl/usr
#            └→ note: line 227.
# L010  [R]  BC=$ADAPTER/framework/appspawn-x/bionic_compat/include
#            └→ note: line 234.
# L011  [R]  (blank)
# L012  [R]  HWUI_SRC=$AOSP/frameworks/base/libs/hwui
#            └→ note: line 220.
# L013  [R]  HWUI_PATCH=$ADAPTER/aosp_patches/libs/hwui
#            └→ note: line 221.
# L014  [R]  SKIA_OH=$OH/third_party/skia/m133
#            └→ note: line 222.
# L015  [R]  SKIA_COMPAT=$ADAPTER/framework/hwui-shim/skia_compat_headers  # 2026-06-01: full 151-shim set (was build/skia_compat_headers, near-empty -> GrDirectContext/choreographer not found)
#            └→ note: line 223.
# L016  [R]  (blank)
# L017  [M]  OUT=$ADAPTER/out/hwui
#            └→ note: line 236 — RENAMED to `OUT_BUILD=$ADAPTER/out/hwui-build`. THIS IS [C-12]'s
#               root fix: old path `out/hwui` was disjoint from link's read dir, leaving 66
#               jni .o files stranded. Unified path now matches link.
# L018  [M]  OBJ=$OUT/obj
#            └→ note: line 237 — `OBJ=$OUT_BUILD/obj`. Same dir as link reads (closes [C-12]).
# L019  [R]  LOG=$OUT/log
#            └→ note: line 239 (under OUT_BUILD).
# L020  [R]  (blank)
# L021  [R]  CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++
#            └→ note: line 245.
# L022  [R]  (blank)
# L023  [M]  mkdir -p "$OBJ" "$LOG"
#            └→ note: line 294 — folded into one mkdir of all build dirs (OUT_BUILD/OBJ/SHIM_OBJ/
#               LOG/OUT_FINAL/OUT_ADAPTER/OUT_RTTI_SHIM/SKIA_COMPAT).
# L024  [R]  (blank)
# L025  [R]  WARN="-Wno-unused-parameter -Wno-missing-field-initializers -Wno-error"
#            └→ note: line 397 (inside phase1_setup_flags()).
# L026  [R]  WARN="$WARN -Wno-c++11-narrowing -Wno-deprecated-declarations -Wno-implicit-fallthrough"
#            └→ note: line 398.
# L027  [R]  WARN="$WARN -Wno-non-virtual-dtor -Wno-maybe-uninitialized -Wno-parentheses"
#            └→ note: line 399.
# L028  [R]  WARN="$WARN -Wno-thread-safety -Wno-free-nonheap-object -Wno-unused-variable"
#            └→ note: line 400.
# L029  [M]  WARN="$WARN -Wno-macro-redefined -Wno-unknown-warning-option"
#            └→ note: appended to WARN chain in phase1_setup_flags() right after line 400
#               (defensive flags retained — cost zero, prevents regression if a future patch
#               reintroduces macro redefinition / unknown-warning hits).
# L030  [R]  (blank)
# L031  [R]  DEFS="-DEGL_EGLEXT_PROTOTYPES -DGL_GLEXT_PROTOTYPES"
#            └→ note: line 402.
# L032  [M]  DEFS="$DEFS -DLOG_TAG=\"OpenGLRenderer\""
#            └→ note: line 403 — augmented with `-DATRACE_TAG=ATRACE_TAG_VIEW` for hwui core .cpp
#               (jni .cpp originally only needed LOG_TAG; merged list keeps both).
# L033  [R]  DEFS="$DEFS -D__OHOS__ -D_GNU_SOURCE -DANDROID"
#            └→ note: line 404.
# L034  [M]  DEFS="$DEFS -DHWUI_NO_VULKAN=1 -DHWUI_NO_STATS=1 -DHWUI_OH_SURFACE=1"
#            └→ note: split across lines 405/407/408 (one macro per `DEFS="$DEFS ..."` line for
#               cleaner diff). All three macros preserved.
# L035  [R]  DEFS="$DEFS -DSK_BUILD_FOR_ANDROID_FRAMEWORK=1"
#            └→ note: line 406.
#            (Plus G2.14bf ABI-alignment macros added at lines 411-413: ENABLE_TEXT_ENHANCE +
#             SKIA_OHOS_SINGLE_OWNER + SK_GANESH — see [C-8]. Not from original jni file.)
# L036  [R]  (blank)
# L037  [R]  CB="--target=aarch64-linux-ohos  --sysroot=$SR -I$SR/include/aarch64-linux-ohos"
#            └→ note: line 415.
# L038  [R]  CB="$CB -fPIC -O2 -std=c++17 $WARN $DEFS"
#            └→ note: line 416.
# L039  [R]  CB="$CB -include $BC/libcxx_compat.h -include $SKIA_COMPAT/hwui_force_include.h -I$BC"
#            └→ note: line 417.
# L040  [R]  (blank)
# L041  [M]  INC="-I$HWUI_SRC -I$HWUI_SRC/.. -I$AOSP/frameworks/base/libs/androidfw/include -I$AOSP/system/incremental_delivery/incfs/util/include -I$AOSP/external/fmtlib/include"
#            └→ note: lines 419-421 — split into 3 clusters of `INC="$INC ..."` for readability.
#               Path values identical.
# L042  [M]  # 2026-05-02 G2.14o: REAL minikin + harfbuzz_ng headers BEFORE $SKIA_COMPAT.
# L043  [M]  # Otherwise jni/Paint.cpp uses stub minikin/Font.h whose typeface() inline
# L044  [M]  # fallback creates `make_shared<MinikinFont>()` (instantiable stub class), and
# L045  [M]  # that stub MinikinFont gets passed to populateSkFont — which reinterprets it
# L046  [M]  # as MinikinFontSkia, reading garbage at offset+4 → SkRefCntBase::ref()
# L047  [M]  # refcount<=0 SK_ABORT trap → SIGILL.  Verified via [POP_SKFONT] diagnostic
# L048  [M]  # 2026-05-02: vtable=_ZTVN7minikin11MinikinFontE confirms stub instance.
#            └→ note (L042-L048): G2.14o root-cause block ESCALATED to top-level [C-13] in
#               this file's warning header (lines 137-151) — same content, broader scope
#               (applies to all hwui compile, not just jni). Order constraint encoded by
#               placing minikin/harfbuzz_ng before SKIA_COMPAT in INC (lines 422-424).
# L049  [R]  INC="$INC -I$AOSP/frameworks/minikin/include"
#            └→ note: line 422 (canonical order, before SKIA_COMPAT — [C-13]).
# L050  [R]  INC="$INC -I$AOSP/external/harfbuzz_ng/src"
#            └→ note: line 423.
# L051  [M]  INC="$INC -I$SKIA_COMPAT -I$SKIA_OH -I$SKIA_OH/include"
#            └→ note: lines 424-426 — split into three single-path -I lines.
# L052  [M]  INC="$INC -I$SKIA_OH/include/core -I$SKIA_OH/include/private"
#            └→ note: lines 427-428 — split.
# L053  [M]  INC="$INC -I$SKIA_OH/src/core -I$SKIA_OH/src/gpu -I$SKIA_OH/src/image -I$SKIA_OH/src/utils -I$SKIA_OH/src/shaders -I$SKIA_OH/src/codec"
#            └→ note: lines 429-434 — split into six single-path -I lines.
# L054  [M]  INC="$INC -I$AOSP/system/libbase/include -I$AOSP/system/core/include"
#            └→ note: lines 435-436 — split.
# L055  [M]  INC="$INC -I$AOSP/system/core/libcutils/include -I$AOSP/system/core/libutils/include"
#            └→ note: lines 437-438 — split.
# L056  [M]  INC="$INC -I$AOSP/system/core/libsystem/include -I$AOSP/system/logging/liblog/include"
#            └→ note: lines 439-440 — split.
# L057  [M]  INC="$INC -I$AOSP/frameworks/native/include -I$AOSP/frameworks/native/libs/nativewindow/include"
#            └→ note: lines 441-442 — split.
# L058  [M]  INC="$INC -I$AOSP/frameworks/native/libs/nativebase/include -I$AOSP/frameworks/native/libs/ui/include"
#            └→ note: lines 443-444 — split. Line 445 adds nativewindow/include_types
#               (new; required after Skia M133 header pull-in for AColorSpace_t).
# L059  [M]  INC="$INC -I$AOSP/frameworks/native/libs/arect/include -I$AOSP/frameworks/native/libs/math/include"
#            └→ note: lines 446-447 — split.
# L060  [M]  INC="$INC -I$AOSP/libnativehelper/include_jni -I$AOSP/libnativehelper/include"
#            └→ note: lines 448-449 — split.
# L061  [R]  INC="$INC -I$AOSP/libnativehelper/header_only_include"
#            └→ note: line 450.
# L062  [M]  INC="$INC -I$OH/third_party/EGL/api -I$OH/third_party/openGLES/api"
#            └→ note: lines 451-452 — split.
# L063  [R]  INC="$INC -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/surface"
#            └→ note: line 453.
# L064  [R]  INC="$INC -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/common"
#            └→ note: line 454.
# L065  [R]  INC="$INC -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/buffer_handle"
#            └→ note: line 455.
# L066  [R]  INC="$INC -I$OH/base/hiviewdfx/hilog/interfaces/native/innerkits/include"
#            └→ note: line 456.
# L067  [R]  INC="$INC -I$OH/commonlibrary/c_utils/base/include"
#            └→ note: line 457.
# L068  [R]  INC="$INC -I$AOSP/external/harfbuzz_ng/src -I$AOSP/frameworks/minikin/include"
#            └→ note: lines 458-459 — kept as duplicate of L049+L050 (matches original; defensive
#               in case a -include pulls a header that reorders search path).
# L069  [R]  INC="$INC -I$AOSP/external/freetype/include"
#            └→ note: line 460.
# L070  [M]  INC="$INC -I$AOSP/external/icu/icu4c/source/common"
#            └→ note: line 464 — relocated to last position (after jni/), value retained.
# L071  [R]  INC="$INC -I$ADAPTER/framework/surface/jni"
#            └→ note: line 461.
# L072  [R]  INC="$INC -I$HWUI_SRC/jni"
#            └→ note: line 463 (now guarded by a "[C-12] JNI sources need extra includes" comment).
# L073  [R]  (blank)
# L074  [D]  cd $HWUI_SRC/jni
#            └→ note: compile_jni_files() (line 638) uses absolute paths from `find`, so no cd.
# L075  [R]  (blank)
# L076  [M]  ok=0
# L077  [M]  fl=0
#            └→ note (L076-L077): line 641 — `local ok=0 fl=0` inside compile_jni_files().
# L078  [M]  total=$(ls *.cpp 2>/dev/null | wc -l)
#            └→ note: recovered as `local total=${#jni_srcs[@]}` immediately after the
#               find-based collection in compile_jni_files() — preserves the operator-visible
#               file count UX.
# L079  [M]  echo "Compiling $total JNI files..."
#            └→ note: recovered as `echo "  Compiling $total JNI files (recursive jni/* +
#               jni/text/* + jni/fonts/*)..."` in compile_jni_files().
# L080  [R]  (blank)
# L081  [M]  for src in *.cpp; do
#            └→ note: line 652 — replaced by `for full_path in "${jni_srcs[@]}"; do`, where
#               jni_srcs comes from `find "$HWUI_SRC/jni" -name '*.cpp' ! -path '*/pdf/*'`.
#               Recursion is the [C-14] fix.
# L082  [M]      name=$(basename "$src" .cpp)
#            └→ note: lines 656-657 — replaced by rel_path-based name (e.g.
#               `jni/text/LineBreaker.cpp -> jni_text_LineBreaker`).
# L083  [M]      out_o="$OBJ/jni_${name}.o"
#            └→ note: line 667 — output path now `$OBJ/$name.o` where $name already includes
#               the `jni_` prefix derived from rel_path.
# L084  [R]  (blank)
# L085  [D]      if [ -f "$out_o" ] && [ -z "$REBUILD" ]; then
# L086  [D]          # Skip if already compiled and not asked to rebuild
# L087  [D]          ((ok++))
# L088  [D]          continue
# L089  [D]      fi
#            └→ note (L085-L089): per-file incremental-skip removed by explicit user decision
#               (2026-05-12). Unified script defaults to clean rebuild (phase1
#               `rm -f $OBJ/*.o`); `--keep-obj` skips the rm but does NOT skip $CXX. The
#               original per-file skip is INTENTIONALLY NOT reinstated. If incremental
#               compile is wanted again, prefer a Make/ninja-driven build over an ad-hoc
#               REBUILD env var.
# L090  [R]  (blank)
# L091  [M]      if $CXX $CB $INC -c "$src" -o "$out_o" 2>"$LOG/jni_${name}.err"; then
#            └→ note: line 667 — uses `$full_path` (abs path) instead of bare `$src`; also
#               detects HWUI_PATCH override (lines 660-665) before compiling.
# L092  [M]          echo "  OK $src"
#            └→ note: line 669 — augmented to print size: `echo "OK ($bytes bytes)"`.
# L093  [R]          ((ok++))
#            └→ note: line 670 (`ok=$((ok+1))`).
# L094  [R]      else
# L095  [M]          echo "  FAIL $src"
#            └→ note: line 672 — `echo "FAILED"` + `head -5 "$LOG/$name.err"` for fast triage.
# L096  [R]          ((fl++))
#            └→ note: line 673.
# L097  [R]      fi
# L098  [R]  done
#            └→ note (L097-L098): lines 675-676.
# L099  [R]  (blank)
# L100  [D]  echo ""
#            └→ note: dropped — Phase JNI header echo already includes leading blank.
# L101  [M]  echo "Phase 3 JNI: $ok OK, $fl FAILED"
#            └→ note: line 677 — `echo "--- Phase JNI: $ok OK, $fl FAILED ---"`.
# L102  [R]  (blank)
# L103  [M]  # ============================================================================
# L104  [M]  # G2.14t fix (2026-05-07):
# L105  [M]  # Compile frameworks/base/libs/hwui/jni/text/*.cpp.
# L106  [M]  #
# L107  [M]  # The main loop above only globs jni/*.cpp (top level), missing jni/text/.
# L108  [M]  # AOSP libhwui has 4 text JNI files providing the register_X functions
# L109  [M]  # referenced by apex/jni_runtime.cpp:149-152:
# L110  [M]  #   - GraphemeBreak.cpp → register_android_graphics_text_GraphemeBreak
# L111  [M]  #   - LineBreaker.cpp   → register_android_graphics_text_LineBreaker
# L112  [M]  #   - MeasuredText.cpp  → register_android_graphics_text_MeasuredText
# L113  [M]  #   - TextShaper.cpp    → register_android_graphics_text_TextShaper
# L114  [M]  #
# L115  [M]  # Without these compiled in, HelloWorld's TextView.onMeasure → StaticLayout.generate
# L116  [M]  # → LineBreaker$Builder.build → LineBreaker.<clinit> hits UnsatisfiedLinkError on
# L117  [M]  # nGetReleaseFunc → ART throws and AMS kills the process before first frame.
# L118  [M]  #
# L119  [M]  # Object file naming convention: jni_text_<name>.o (matches existing
# L120  [M]  # jni_text_GraphemeBreak.o left from a prior manual build).
# L121  [M]  # ============================================================================
#            └→ note (L103-L121): G2.14t root-cause block ESCALATED to top-level [C-14] in
#               this file's warning header (lines 153-166) — same content. The fix itself
#               is now structural (recursive find under jni/), not a separate code block.
# L122  [D]  echo ""
# L123  [D]  echo "Compiling jni/text/*.cpp (G2.14t fix — main loop above misses subdir)..."
# L124  [D]  TEXT_DIR="$HWUI_SRC/jni/text"
# L125  [D]  text_ok=0
# L126  [D]  text_fl=0
# L127  [D]  if [ -d "$TEXT_DIR" ]; then
# L128  [D]      for src in "$TEXT_DIR"/*.cpp; do
# L129  [D]          [ -f "$src" ] || continue
# L130  [D]          name=$(basename "$src" .cpp)
# L131  [D]          out_o="$OBJ/jni_text_${name}.o"
# L132  [D]  (blank)
# L133  [D]          if [ -f "$out_o" ] && [ -z "$REBUILD" ]; then
# L134  [D]              ((text_ok++))
# L135  [D]              continue
# L136  [D]          fi
# L137  [D]  (blank)
# L138  [D]          if $CXX $CB $INC -I"$TEXT_DIR" -c "$src" -o "$out_o" \
# L139  [D]                  2>"$LOG/jni_text_${name}.err"; then
# L140  [D]              echo "  OK text/$name.cpp"
# L141  [D]              ((text_ok++))
# L142  [D]          else
# L143  [D]              echo "  FAIL text/$name.cpp — see $LOG/jni_text_${name}.err"
# L144  [D]              ((text_fl++))
# L145  [D]          fi
# L146  [D]      done
# L147  [D]      echo "  jni/text: $text_ok OK, $text_fl FAILED"
# L148  [D]  else
# L149  [D]      echo "  WARN: $TEXT_DIR not found"
# L150  [D]  fi
#            └→ note (L122-L150): entire jni/text/ second loop deleted. The unified
#               compile_jni_files() uses `find "$HWUI_SRC/jni" -name '*.cpp' ! -path '*/pdf/*'`
#               which naturally recurses into text/ + fonts/ + any future subdir. Same
#               outputs (jni_text_*.o) produced by the unified name-derivation logic.
# L151  [R]  (blank)
# L152  [M]  # ============================================================================
# L153  [M]  # GAP 0.4 fix (2026-04-11):
# L154  [M]  # Compile frameworks/base/libs/hwui/apex/jni_runtime.cpp.
# L155  [M]  #
# L156  [M]  # This file defines `register_android_graphics_classes(JNIEnv*)` — the umbrella
# L157  [M]  # function that libandroid_runtime.so::JNI_OnLoad invokes to register every
# L158  [M]  # android.graphics.* JNI class. Without this .o being linked into libhwui.so,
# L159  [M]  # libandroid_runtime.so resolves register_android_graphics_classes to nullptr
# L160  [M]  # and ART boot crashes with UnsatisfiedLinkError.
# L161  [M]  #
# L162  [M]  # It is in apex/, not jni/, which is why the loop above missed it.
# L163  [M]  # ============================================================================
#            └→ note (L152-L163): comment block RETAINED but CONCLUSION REVERSED in escalation
#               to top-level [C-15] (lines 168-179). G2.14bf investigation (2026-05-12) found
#               the 0509-ok stable backup obj/ NEVER contained apex_jni_runtime.o — it was
#               failing to compile silently (vkEnumerateInstanceVersion UND) and libhwui.so
#               worked anyway, because aosp_patches/.../AndroidRuntime.cpp.patch:72 explicitly
#               DISABLES REG_JNI(register_android_graphics_classes). Partial-sync strategy
#               doesn't need the umbrella registrar; the kHwuiRegFns table lists the actual
#               register_X functions directly. So the original premise ("Without this .o, ART
#               boot crashes") was wrong — [C-15] documents the corrected reality.
# L164  [D]  echo ""
# L165  [D]  echo "Compiling apex/jni_runtime.cpp (provides register_android_graphics_classes)..."
# L166  [D]  APEX_DIR="$HWUI_SRC/apex"
# L167  [D]  if [ -f "$APEX_DIR/jni_runtime.cpp" ]; then
# L168  [D]      out_o="$OBJ/apex_jni_runtime.o"
# L169  [D]      if [ ! -f "$out_o" ] || [ -n "$REBUILD" ]; then
# L170  [D]          # apex/ has slightly different include needs — same flags work for our build
# L171  [D]          if $CXX $CB $INC -I"$APEX_DIR" -c "$APEX_DIR/jni_runtime.cpp" \
# L172  [D]                  -o "$out_o" 2>"$LOG/apex_jni_runtime.err"; then
# L173  [D]              echo "  OK apex/jni_runtime.cpp -> $out_o"
# L174  [D]          else
# L175  [D]              echo "  FAIL apex/jni_runtime.cpp — see $LOG/apex_jni_runtime.err"
# L176  [D]              echo "  This is a HARD blocker — libandroid_runtime.so JNI_OnLoad needs"
# L177  [D]              echo "  register_android_graphics_classes. Without it ART boot will crash."
# L178  [D]          fi
# L179  [D]      else
# L180  [D]          echo "  SKIP apex/jni_runtime.cpp (already built; pass REBUILD=1 to force)"
# L181  [D]      fi
# L182  [D]  else
# L183  [D]      echo "  WARN: $APEX_DIR/jni_runtime.cpp not found"
# L184  [D]      echo "        Check that hwui_rk3568.patch was applied (restore_after_sync.sh A9)"
# L185  [D]  fi
#            └→ note (L164-L185): entire apex/jni_runtime.cpp compile block deleted per [C-15]
#               above. compile_jni_files() intentionally does NOT add apex/ to the find
#               search. If the partial-sync strategy ever flips to full-sync, the future
#               maintainer should: (a) undo AndroidRuntime.cpp.patch line 72 DISABLE; (b)
#               copy the 22 lines above back into a new compile_apex_jni_runtime() function;
#               (c) call it from phase1() after compile_jni_files(). User decision 2026-05-12:
#               NO dormant function in phase 1 code area — text-only retention in this
#               Annex A is sufficient provenance.
#
# Audit summary (185 original lines):
#   Retained (R)     :  54 lines (blanks + verbatim ports)
#   Modified (M)     :  72 lines (preserved with documented diff; incl. L029/L078/L079
#                                 recovered into real code per 2026-05-12 user review)
#   Deleted  (D)     :  59 lines (L001 / L074 / L085-L089 / L100 / L122-L150 / L164-L185)
# ============================================================================
#
# Usage:
#   compile_libhwui.sh                       # default: incremental (phases 0-4, keep .o)
#   compile_libhwui.sh --clean               # wipe $OBJ/*.o then rebuild
#   compile_libhwui.sh --phase=N1,N2,...     # run specific phases
#   compile_libhwui.sh --keep-obj            # back-compat no-op (incremental is now default)
#   compile_libhwui.sh --strict-audit        # phase 4 + strict link diagnostic
#   compile_libhwui.sh --no-und-gate         # skip phase 4 fail-on-new-UND
#   compile_libhwui.sh --help
#
# Legacy wrappers (5-line forward):
#   compile_hwui_stubs.sh        ->  --phase=2a
#   compile_hwui_shims.sh        ->  --phase=2b
#   compile_skia_rtti_shim.sh    ->  --phase=2c
#   link_libhwui.sh              ->  --phase=3,4
# ============================================================================

set -e
set -o pipefail

# ============================================================================
# Paths (single source of truth)
# ============================================================================
OH="${OH_ROOT:-$HOME/oh}"
AOSP="${AOSP_ROOT:-$HOME/aosp}"
ADAPTER="${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

HWUI_SRC=$AOSP/frameworks/base/libs/hwui
HWUI_PATCH=$ADAPTER/aosp_patches/libs/hwui
SKIA_OH=$OH/third_party/skia/m133
SKIA_COMPAT=$ADAPTER/framework/hwui-shim/skia_compat_headers  # 2026-06-01: full 151-shim set (was build/skia_compat_headers, near-empty -> GrDirectContext/choreographer not found)
SKIA_SO=$OH/out/wukong100/thirdparty/skia/libskia_canvaskit.z.so

OH_OUT=$OH/out/wukong100
SR=$OH_OUT/obj/third_party/musl/usr
SYS_LIB=$OH_OUT/packages/phone/system/lib64
SYS_LIB_NDK=$OH_OUT/packages/phone/system/lib64/ndk
SYS_LIB_PSDK=$OH_OUT/packages/phone/system/lib64/platformsdk
SYS_LIB_CSDK=$OH_OUT/packages/phone/system/lib64/chipset-sdk-sp
OH_SYSLIB=$SR/lib/aarch64-linux-ohos

BC=$ADAPTER/framework/appspawn-x/bionic_compat/include

OUT_BUILD=$ADAPTER/out/hwui-build
OBJ=$OUT_BUILD/obj
SHIM_OBJ=$OUT_BUILD/shim
LOG=$OUT_BUILD/log
OUT_FINAL=$ADAPTER/out/aosp_lib64
OUT_ADAPTER=$ADAPTER/out/adapter
OUT_RTTI_SHIM=$ADAPTER/out/skia-rtti-shim

# Toolchain
CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++
CC=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang
NM=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-nm

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ============================================================================
# Args parsing
# ============================================================================
PHASES="1,2,3,4"
KEEP_OBJ=1   # 2026-05-27: default incremental (keep .o). --clean wipes $OBJ. (was 0 = clean-by-default)
STRICT_AUDIT=0
NO_UND_GATE=0

for arg in "$@"; do
    case "$arg" in
        --phase=*)        PHASES="${arg#*=}" ;;
        --clean)          KEEP_OBJ=0 ;;   # 2026-05-27: explicit clean — wipe $OBJ/*.o before phase 1
        --keep-obj)       KEEP_OBJ=1 ;;   # back-compat: incremental is now the default
        --strict-audit)   STRICT_AUDIT=1 ;;
        --no-und-gate)    NO_UND_GATE=1 ;;
        --help|-h)
            sed -n '/^# Usage:/,/^# ====/p' "${BASH_SOURCE[0]}" | head -30 | sed 's/^# \?//'
            exit 0
            ;;
        *) echo "Unknown arg: $arg"; exit 2 ;;
    esac
done

# Validate PHASES — every comma-separated key must be one of the known phases.
# Fail-fast instead of silently no-op'ing through main dispatch (dry-run 2026-05-12).
IFS=',' read -ra _phase_keys <<< "$PHASES"
for _p in "${_phase_keys[@]}"; do
    case "$_p" in
        0|1|2|2a|2b|2c|3|4) ;;
        '') echo "Empty phase key in --phase=$PHASES"; exit 2 ;;
        *)  echo "Unknown phase: '$_p' (valid: 1, 2, 2a, 2b, 2c, 3, 4 — phase 0 removed 2026-05-21, patches now in restore_after_sync.sh)"; exit 2 ;;
    esac
done
unset _phase_keys _p

# ============================================================================
# Helpers
# ============================================================================
log_info()  { echo "[$(date +%H:%M:%S)] $*"; }
log_ok()    { echo "  ✓ $*"; }
log_warn()  { echo "  ⚠ $*" >&2; }
log_fail()  { echo "  ✗ $*" >&2; }
die()       { echo "ABORT: $*" >&2; exit 1; }

have_phase() {
    # have_phase 2   or   have_phase 2a (substring match)
    local needle="$1"
    case ",$PHASES," in
        *",${needle},"*) return 0 ;;
        *",${needle%a},"*|*",${needle%b},"*|*",${needle%c},"*)
            # phase 2a/2b/2c gated by phase=2 parent
            return 0 ;;
    esac
    return 1
}

mkdir -p $OUT_BUILD $OBJ $SHIM_OBJ $LOG $OUT_FINAL $OUT_ADAPTER $OUT_RTTI_SHIM $SKIA_COMPAT

echo "=========================================="
echo "  libhwui.so unified build pipeline"
echo "  Phases: $PHASES"
echo "  Keep obj: $KEEP_OBJ | Strict audit: $STRICT_AUDIT | No UND gate: $NO_UND_GATE"
echo "  AOSP:    $AOSP"
echo "  OH:      $OH"
echo "  ADAPTER: $ADAPTER"
echo "=========================================="

# ============================================================================
# Phase 0 — REMOVED 2026-05-21
# ----------------------------------------------------------------------------
# Patch application (formerly phase 0) moved to restore_after_sync.sh A9, which
# is the single authoritative source-tree restoration entry. compile_libhwui.sh
# is now pure compile + shim + link + audit.
#
# Prerequisite: caller must ensure ~/aosp/frameworks/base/libs/hwui/ has all
# patches from aosp_patches/libs/hwui/patches/*.patch applied. Normal workflow:
#   bash restore_after_sync.sh        # applies all patches including hwui
#   bash build_aosp_lib.sh --target=libhwui.so  # then build
# ============================================================================

# ============================================================================
# Phase 1 — compile hwui sources (88 hwui + 1 native ColorSpace.cpp)
# ============================================================================

# Compile flags shared across hwui sources
phase1_setup_flags() {
    WARN="-Wno-unused-parameter -Wno-missing-field-initializers -Wno-error"
    WARN="$WARN -Wno-c++11-narrowing -Wno-deprecated-declarations -Wno-implicit-fallthrough"
    WARN="$WARN -Wno-non-virtual-dtor -Wno-maybe-uninitialized -Wno-parentheses"
    WARN="$WARN -Wno-thread-safety -Wno-free-nonheap-object -Wno-unused-variable"
    # Annex A L029 recovery — defensive flags retained for regression safety; harmless
    # when current sources don't trigger them, prevents -Werror surprise if a future
    # patch reintroduces macro redefinition or unknown-warning hits.
    WARN="$WARN -Wno-macro-redefined -Wno-unknown-warning-option"

    DEFS="-DEGL_EGLEXT_PROTOTYPES -DGL_GLEXT_PROTOTYPES"
    DEFS="$DEFS -DATRACE_TAG=ATRACE_TAG_VIEW -DLOG_TAG=\"OpenGLRenderer\""
    DEFS="$DEFS -D__OHOS__ -D_GNU_SOURCE -DANDROID"
    DEFS="$DEFS -DHWUI_NO_VULKAN=1"
    DEFS="$DEFS -DSK_BUILD_FOR_ANDROID_FRAMEWORK=1"
    DEFS="$DEFS -DHWUI_NO_STATS=1"
    DEFS="$DEFS -DHWUI_OH_SURFACE=1"
    # G2.14bf (2026-05-12) — align hwui with OH libskia_canvaskit ABI view.
    # See [C-8] in header for root cause and staged plan.
    # ---- Stage 1: critical class-layout / vtable macros (3) ----
    DEFS="$DEFS -DENABLE_TEXT_ENHANCE"
    DEFS="$DEFS -DSKIA_OHOS_SINGLE_OWNER"
    DEFS="$DEFS -DSK_GANESH"
    # ---- Stage 2 (2026-05-12, post Stage 1 still-red verify): full -D set
    # confirmed present in OH skia_canvaskit_static.ninja. Each macro is one
    # of: visibility/dll (SKIA_DLL), class extensions (SKIA_OHOS*,
    # SK_OHOS_EXTENSION), feature flag (SK_GL, SK_GAMMA_APPLY_TO_A8),
    # debug-strip (NDEBUG). SK_R32_SHIFT=16 (blocker.txt guess) is NOT in
    # OH ninja and thus skipped. ----
    #
    # ---- [BISECT R1] 2026-05-12 RESULT: SKIA_DLL+NDEBUG alone do NOT cause
    # the appspawn-x SIGSEGV (R1 build = pure red + FOREGROUND + 0 crash,
    # equivalent to Stage 1). Culprit ⊂ the 6 low-suspicion macros.
    # ---- [BISECT R2] 2026-05-12 RESULT: R2 (Stage1+R1base + SK_GL/SKIA_OHOS/
    # SK_OHOS_EXTENSION on, Half B off) produced md5 IDENTICAL to full Stage 2.
    # → Half B (SKIA_OHOS_SHADER_REDUCE/SKIA_DFX_FOR_OHOS/SK_GAMMA_APPLY_TO_A8)
    # are no-ops on hwui compile (Skia headers don't read them when included
    # by hwui). Culprit ⊂ Half A: {SK_GL, SKIA_OHOS, SK_OHOS_EXTENSION}.
    # ---- [BISECT R3a] 2026-05-12 RESULT: SK_GL alone produces md5
    # IDENTICAL to R1 (no-op on hwui compile). Empirical reboot+deploy test
    # confirmed: red screen + master daemon alive + 0 find_sym2 crash.
    # Culprit ⊂ {SKIA_OHOS, SK_OHOS_EXTENSION}.
    # ---- [BISECT R3b] 2026-05-12: isolate SKIA_OHOS alone (in addition to
    # R3a base). If R3b crashes → SKIA_OHOS is culprit; else SK_OHOS_EXTENSION.
    # ----
    DEFS="$DEFS -DSKIA_OHOS"
    # [BISECT R2 OFF]  DEFS="$DEFS -DSKIA_OHOS_SHADER_REDUCE"
    # [BISECT R2 OFF]  DEFS="$DEFS -DSKIA_DFX_FOR_OHOS"
    # [BISECT R3b OFF] DEFS="$DEFS -DSK_OHOS_EXTENSION"
    DEFS="$DEFS -DSK_GL"
    DEFS="$DEFS -DSKIA_DLL"
    # [BISECT R2 OFF]  DEFS="$DEFS -DSK_GAMMA_APPLY_TO_A8"
    DEFS="$DEFS -DNDEBUG"

    # G2.14bg (2026-05-13) — fixes silent OpsTask drop / pure-red screen.
    # GrContextOptions.h gates fFailFlushTimeCallbacks (and 8 other test-util
    # bool fields) behind `#if defined(GPU_TEST_UTILS)`.  OH builds Skia with
    # -DGPU_TEST_UTILS=1 in production (confirmed in gpu.ninja defines), so
    # libskia_canvaskit's GrContextOptions includes those fields.  Without
    # this macro on the hwui side, hwui's default-constructed GrContextOptions
    # is a smaller struct; libskia reads fFailFlushTimeCallbacks at an offset
    # past hwui's struct end -> uninitialised stack byte interpreted as bool
    # -> failFlushTimeCallbacks() returns true -> GrAtlasManager::preFlush
    # short-circuits to `return false` -> preFlushSuccessful=false in
    # GrDrawingManager::flush -> the entire `if (preFlushSuccessful)` block
    # is skipped -> resourceAllocator + executeRenderTasks never runs ->
    # every OpsTask is drained via removeRenderTasks/endFlush with onExecute
    # count = 0 -> no GL draws -> screen stays whatever the clear loadop set.
    # Empirically confirmed by v4b probe (apply_oh_sk_gate_probe_v4b.py):
    # preFlushSuccessful=0 100%, fOnFlushCBObjects.size=1.
    # Aligning this macro is purely ABI alignment; hwui code does not reference
    # any field added by GPU_TEST_UTILS, so default-false initialisation of
    # those fields is exactly what libskia needs.
    DEFS="$DEFS -DGPU_TEST_UTILS=1"

    CB="--target=aarch64-linux-ohos  --sysroot=$SR -I$SR/include/aarch64-linux-ohos"
    CB="$CB -fPIC -O2 -std=c++17 $WARN $DEFS"
    CB="$CB -include $BC/libcxx_compat.h -include $SKIA_COMPAT/hwui_force_include.h -I$BC"

    INC="-I$HWUI_SRC"
    INC="$INC -I$HWUI_SRC/.."
    INC="$INC -I$AOSP/frameworks/base/libs/androidfw/include -I$AOSP/system/incremental_delivery/incfs/util/include -I$AOSP/external/fmtlib/include"
    INC="$INC -I$AOSP/frameworks/minikin/include"
    INC="$INC -I$AOSP/external/harfbuzz_ng/src"
    INC="$INC -I$SKIA_COMPAT"
    INC="$INC -I$SKIA_OH"
    INC="$INC -I$SKIA_OH/include"
    INC="$INC -I$SKIA_OH/include/core"
    INC="$INC -I$SKIA_OH/include/private"
    INC="$INC -I$SKIA_OH/src/core"
    INC="$INC -I$SKIA_OH/src/gpu"
    INC="$INC -I$SKIA_OH/src/image"
    INC="$INC -I$SKIA_OH/src/utils"
    INC="$INC -I$SKIA_OH/src/shaders"
    INC="$INC -I$SKIA_OH/src/codec"
    INC="$INC -I$AOSP/system/libbase/include"
    INC="$INC -I$AOSP/system/core/include"
    INC="$INC -I$AOSP/system/core/libcutils/include"
    INC="$INC -I$AOSP/system/core/libutils/include"
    INC="$INC -I$AOSP/system/core/libsystem/include"
    INC="$INC -I$AOSP/system/logging/liblog/include"
    INC="$INC -I$AOSP/frameworks/native/include"
    INC="$INC -I$AOSP/frameworks/native/libs/nativewindow/include"
    INC="$INC -I$AOSP/frameworks/native/libs/nativebase/include"
    INC="$INC -I$AOSP/frameworks/native/libs/ui/include"
    INC="$INC -I$AOSP/frameworks/native/libs/ui/include_types"
    INC="$INC -I$AOSP/frameworks/native/libs/arect/include"
    INC="$INC -I$AOSP/frameworks/native/libs/math/include"
    INC="$INC -I$AOSP/libnativehelper/include_jni"
    INC="$INC -I$AOSP/libnativehelper/include"
    INC="$INC -I$AOSP/libnativehelper/header_only_include"
    # JNIPlatformHelp.h in the compat overlay delegates to this real AOSP
    # platform header with #include_next; keep it after $SKIA_COMPAT.
    INC="$INC -I$AOSP/libnativehelper/include_platform"
    INC="$INC -I$OH/third_party/EGL/api"
    INC="$INC -I$OH/third_party/openGLES/api"
    INC="$INC -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/surface"
    INC="$INC -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/common"
    INC="$INC -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/buffer_handle"
    INC="$INC -I$OH/base/hiviewdfx/hilog/interfaces/native/innerkits/include"
    INC="$INC -I$OH/commonlibrary/c_utils/base/include"
    INC="$INC -I$AOSP/external/harfbuzz_ng/src"
    INC="$INC -I$AOSP/frameworks/minikin/include"
    INC="$INC -I$AOSP/external/freetype/include"
    INC="$INC -I$ADAPTER/framework/surface/jni"
    # [C-12] JNI sources need extra includes vs core hwui
    INC="$INC -I$HWUI_SRC/jni"
    INC="$INC -I$AOSP/external/icu/icu4c/source/common"
}

# 38 PHASE1 source files (relative to $HWUI_SRC unless absolute)
PHASE1_SRCS="
renderthread/RenderThread.cpp
renderthread/RenderProxy.cpp
renderthread/CanvasContext.cpp
renderthread/DrawFrameTask.cpp
renderthread/EglManager.cpp
renderthread/Frame.cpp
renderthread/RenderTask.cpp
renderthread/TimeLord.cpp
renderthread/CacheManager.cpp
renderthread/RenderEffectCapabilityQuery.cpp
renderthread/HintSessionWrapper.cpp
renderthread/ReliableSurface.cpp
renderstate/RenderState.cpp
thread/CommonPool.cpp
utils/GLUtils.cpp
utils/Color.cpp
utils/Blur.cpp
utils/LinearAllocator.cpp
utils/StringUtils.cpp
DamageAccumulator.cpp
Properties.cpp
MemoryPolicy.cpp
LightingInfo.cpp
DeviceInfo.cpp
FrameInfo.cpp
FrameInfoVisualizer.cpp
TreeInfo.cpp
JankTracker.cpp
ProfileData.cpp
ProfileDataContainer.cpp
FrameMetricsReporter.cpp
Matrix.cpp
Interpolator.cpp
AnimationContext.cpp
Animator.cpp
AnimatorManager.cpp
PropertyValuesAnimatorSet.cpp
PropertyValuesHolder.cpp
SkiaInterpolator.cpp
"

# 50 PHASE2 source files (relative to $HWUI_SRC)
PHASE2_SRCS="
pipeline/skia/SkiaPipeline.cpp
pipeline/skia/SkiaOpenGLPipeline.cpp
pipeline/skia/SkiaDisplayList.cpp
pipeline/skia/SkiaRecordingCanvas.cpp
pipeline/skia/SkiaProfileRenderer.cpp
pipeline/skia/RenderNodeDrawable.cpp
pipeline/skia/ReorderBarrierDrawables.cpp
pipeline/skia/LayerDrawable.cpp
pipeline/skia/ShaderCache.cpp
pipeline/skia/SkiaMemoryTracer.cpp
pipeline/skia/ATraceMemoryDump.cpp
pipeline/skia/HolePunch.cpp
pipeline/skia/StretchMask.cpp
pipeline/skia/TransformCanvas.cpp
pipeline/skia/GLFunctorDrawable.cpp
canvas/CanvasFrontend.cpp
canvas/CanvasOpBuffer.cpp
canvas/CanvasOpRasterizer.cpp
RenderNode.cpp
RenderProperties.cpp
RootRenderNode.cpp
RecordingCanvas.cpp
SkiaCanvas.cpp
CanvasTransform.cpp
DeferredLayerUpdater.cpp
Layer.cpp
LayerUpdateQueue.cpp
AutoBackendTextureRelease.cpp
HardwareBitmapUploader.cpp
Readback.cpp
effects/StretchEffect.cpp
effects/GainmapRenderer.cpp
Gainmap.cpp
Tonemapper.cpp
Mesh.cpp
VectorDrawable.cpp
hwui/Bitmap.cpp
hwui/Canvas.cpp
hwui/PaintImpl.cpp
hwui/MinikinSkia.cpp
hwui/MinikinUtils.cpp
hwui/Typeface.cpp
hwui/BlurDrawLooper.cpp
hwui/AnimatedImageDrawable.cpp
hwui/AnimatedImageThread.cpp
hwui/ImageDecoder.cpp
PathParser.cpp
utils/VectorDrawableUtils.cpp
utils/NdkUtils.cpp
WebViewFunctorManager.cpp
"

# Native (non-hwui) sources required for symbol completeness ([C-2])
# Listed as "src_path|output_name" so we can compile out-of-tree .cpp.
PHASE_NATIVE_SRCS="
$AOSP/frameworks/native/libs/ui/ColorSpace.cpp|ColorSpace.o
"

compile_files() {
    local phase_name="$1"; shift
    local srcs="$@"
    echo ""
    echo "--- $phase_name ---"
    local ok=0 fl=0
    for src in $srcs; do
        [ -z "$src" ] && continue
        [[ "$src" == *.sysprop ]] && { echo "  SKIP $src (sysprop)"; continue; }

        local name=$(echo "$src" | tr '/' '_' | sed 's/\.cpp$//')
        local full_path="$HWUI_SRC/$src"

        # HWUI_PATCH override check (e.g., aosp_patches/libs/hwui/renderthread/ReliableSurface.cpp stub)
        if [ -f "$HWUI_PATCH/$src" ]; then
            full_path="$HWUI_PATCH/$src"
            echo -n "  [PATCHED] $src ... "
        else
            echo -n "  $src ... "
        fi

        if [ ! -f "$full_path" ]; then
            echo "NOT FOUND"; fl=$((fl+1)); continue
        fi

        # A full-file adapter override lives outside the AOSP source
        # directory, so quoted sibling headers (for example
        # RenderNodeDrawable.h) are otherwise no longer found relative to the
        # source file.  Preserve the original source directory as a quote-only
        # include root; angle-bracket include ordering remains unchanged.
        local source_quote_dir
        source_quote_dir=$(dirname "$HWUI_SRC/$src")
        if $CXX $CB $INC -iquote "$source_quote_dir" -c "$full_path" -o "$OBJ/$name.o" 2>"$LOG/$name.err"; then
            echo "OK ($(stat -c%s "$OBJ/$name.o" 2>/dev/null || echo '?') bytes)"
            ok=$((ok+1))
        else
            echo "FAILED"
            fl=$((fl+1))
            head -5 "$LOG/$name.err"
        fi
    done
    echo "--- $phase_name: $ok OK, $fl FAILED ---"
    return $fl
}

compile_native_files() {
    echo ""
    echo "--- Phase Native: out-of-tree sources (ColorSpace.cpp etc.) ---"
    local ok=0 fl=0
    while IFS='|' read -r src outname; do
        src=$(echo "$src" | xargs)  # trim
        outname=$(echo "$outname" | xargs)
        [ -z "$src" ] && continue
        [ ! -f "$src" ] && { echo "  $src ... NOT FOUND"; fl=$((fl+1)); continue; }
        echo -n "  $(basename $src) ... "
        $CXX $CB $INC -c "$src" -o "$OBJ/$outname" 2>"$LOG/$outname.err"
        if [ $? -eq 0 ]; then
            echo "OK ($(stat -c%s "$OBJ/$outname" 2>/dev/null || echo '?') bytes)"
            ok=$((ok+1))
        else
            echo "FAILED"; fl=$((fl+1))
            head -10 "$LOG/$outname.err"
        fi
    done <<EOF
$PHASE_NATIVE_SRCS
EOF
    echo "--- Phase Native: $ok OK, $fl FAILED ---"
    return $fl
}

# [C-12] compile JNI sources (jni/* + jni/text/* + jni/fonts/* + apex/jni_runtime.cpp)
# Recursive find under $HWUI_SRC/jni, plus apex/jni_runtime.cpp. Excludes
# jni/pdf/* (per 0509-ok backup obj/, pdf not compiled historically).
# Output naming: jni_<flat-path>.o (e.g. jni/text/LineBreaker.cpp -> jni_text_LineBreaker.o)
compile_jni_files() {
    echo ""
    echo "--- Phase JNI: jni/* + jni/text/* + jni/fonts/* + apex/jni_runtime.cpp ---"
    local ok=0 fl=0

    # collect jni sources via find (recursive, exclude pdf/)
    local jni_srcs=()
    while IFS= read -r f; do
        jni_srcs+=("$f")
    done < <(find "$HWUI_SRC/jni" -name '*.cpp' ! -path '*/pdf/*' 2>/dev/null | sort)
    # Annex A L078/L079 recovery — operator-visible total file count for the JNI phase.
    local total=${#jni_srcs[@]}
    echo "  Compiling $total JNI files (recursive jni/* + jni/text/* + jni/fonts/*)..."
    # [C-15] apex/jni_runtime.cpp INTENTIONALLY SKIPPED — register_android_graphics_classes
    # is DISABLED in aosp_patches/.../AndroidRuntime.cpp.patch (partial-sync). 0509-ok
    # backup obj/ confirms apex_jni_runtime.o never existed in working libhwui.so.

    for full_path in "${jni_srcs[@]}"; do
        # Derive output name from path under $HWUI_SRC: e.g.
        #   jni/text/LineBreaker.cpp -> jni_text_LineBreaker.o
        #   apex/jni_runtime.cpp     -> apex_jni_runtime.o
        local rel_path="${full_path#$HWUI_SRC/}"
        local name=$(echo "$rel_path" | tr '/' '_' | sed 's/\.cpp$//')

        # HWUI_PATCH override check (e.g., aosp_patches/.../jni/Bitmap.cpp stub)
        if [ -f "$HWUI_PATCH/$rel_path" ]; then
            full_path="$HWUI_PATCH/$rel_path"
            echo -n "  [PATCHED] $rel_path ... "
        else
            echo -n "  $rel_path ... "
        fi

        if $CXX $CB $INC -c "$full_path" -o "$OBJ/$name.o" 2>"$LOG/$name.err"; then
            echo "OK ($(stat -c%s "$OBJ/$name.o" 2>/dev/null || echo '?') bytes)"
            ok=$((ok+1))
        else
            echo "FAILED"
            fl=$((fl+1))
            head -5 "$LOG/$name.err"
        fi
    done
    echo "--- Phase JNI: $ok OK, $fl FAILED ---"
    return $fl
}

phase1() {
    log_info "Phase 1/4 — Compile hwui sources"

    if [ "$KEEP_OBJ" = "0" ]; then
        log_info "  --clean: wiping \$OBJ/*.o \$LOG/*.err (default is incremental — pass --clean to force)"
        rm -f $OBJ/*.o $LOG/*.err
    fi

    phase1_setup_flags

    # [BR-8 / BUILD_LOCAL 2026-06-28] Device-version (6.1.0.31) OH-header SHADOW —
    # same mechanism as the bridge (compile_oh_adapter_bridge_arm64.sh). PREPEND a
    # mirror-rewritten copy of every -I$OH/... path so 6.1.0.31 headers from
    # adapter/local_oh_headers/oh_mirror shadow the local api24 tree. hwui's OH
    # surface = graphic_surface inner_api (surface/buffer_handle/common) + hilog +
    # c_utils; shadowing makes those device-exact. Paths absent in the mirror fall
    # through (clang ignores absent -I). Purely additive — original -I retained.
    OHI="${ADAPTER_ROOT:-$OH/adapter}/local_oh_headers/oh_mirror"
    if [ -d "$OHI" ]; then
        MIRROR_INC=$(printf '%s\n' $INC | grep -E "^-I$OH/" | sed "s|^-I$OH/|-I$OHI/|" | tr '\n' ' ')
        INC="$MIRROR_INC $INC"
        echo "[BR-8] hwui: prepended $(printf '%s\n' $MIRROR_INC | grep -c '^-I') 6.1.0.31 mirror -I from $OHI"
    fi

    P1_ARR=($PHASE1_SRCS)
    P2_ARR=($PHASE2_SRCS)

    # AlexBridge incremental diagnostic path.  A one-file probe change must
    # not force the whole ~200-source HWUI closure through a serial rebuild.
    # The caller must start from a previously complete object cache; phase 3
    # and phase 4 still relink and audit the complete library.
    if [ -n "${HWUI_ONLY_SOURCE:-}" ]; then
        case "$HWUI_ONLY_SOURCE" in
            /*|*..*)
                echo "HWUI_ONLY_SOURCE must be a relative path below libs/hwui" >&2
                return 2
                ;;
            *.cpp)
                ;;
            *)
                echo "HWUI_ONLY_SOURCE must name one .cpp file" >&2
                return 2
                ;;
        esac
        log_info "  targeted incremental compile: $HWUI_ONLY_SOURCE"
        compile_files "Phase 1 targeted diagnostic" "$HWUI_ONLY_SOURCE"
        return
    fi

    compile_files "Phase 1: Core Rendering Pipeline" "${P1_ARR[@]}"
    compile_files "Phase 2: DisplayList + Skia Pipeline" "${P2_ARR[@]}"
    compile_native_files
    compile_jni_files

    echo ""
    echo "  hwui Object files compiled: $(ls -1 $OBJ/*.o 2>/dev/null | wc -l)"
    log_info "Phase 1 DONE"
}

# ============================================================================
# Phase 2a — compile adapter shim .o (linked into libhwui.so)
# ============================================================================
phase2a() {
    log_info "Phase 2a — Compile adapter shim .o (hwui_oh_abi_patch + hwui_register_stubs)"

    local CFLAGS_STUB="--target=aarch64-linux-ohos    \
        --sysroot=$SR -I$SR/include/aarch64-linux-ohos \
        -fPIC -O2 -std=c++17 \
        -Wno-unused-parameter -Wno-unused-private-field \
        -I$BC \
        -I$AOSP/libnativehelper/include_jni \
        -I$AOSP/libnativehelper/include \
        -include $BC/libcxx_compat.h"

    echo -n "  hwui_oh_abi_patch.cpp ... "
    $CXX $CFLAGS_STUB \
        -c $HWUI_PATCH/hwui_oh_abi_patch.cpp \
        -o $OBJ/hwui_oh_abi_patch.o 2>$LOG/hwui_oh_abi_patch.err
    [ -f $OBJ/hwui_oh_abi_patch.o ] && echo "OK ($(stat -c%s $OBJ/hwui_oh_abi_patch.o) bytes)" || { echo "FAIL"; head -10 $LOG/hwui_oh_abi_patch.err; die "phase 2a failed"; }

    echo -n "  hwui_register_stubs.cpp ... "
    $CXX $CFLAGS_STUB \
        -c $HWUI_PATCH/hwui_register_stubs.cpp \
        -o $OBJ/hwui_register_stubs.o 2>$LOG/hwui_register_stubs.err
    [ -f $OBJ/hwui_register_stubs.o ] && echo "OK ($(stat -c%s $OBJ/hwui_register_stubs.o) bytes)" || { echo "FAIL"; head -10 $LOG/hwui_register_stubs.err; die "phase 2a failed"; }

    # [C-10] typeface_minimal_stub.o deprecated — remove stale .o to prevent dup symbol
    echo "  SKIP: typeface_minimal_stub.o (G2.14r deprecated — see [C-10])"
    if [ -f "$OBJ/typeface_minimal_stub.o" ]; then
        rm -v "$OBJ/typeface_minimal_stub.o"
        echo "  removed stale typeface_minimal_stub.o (would cause dup symbol)"
    fi
}

# ============================================================================
# Phase 2b — compile liboh_hwui_shim.so (NDK compat + Skia AOSP-only shims)
# ============================================================================
phase2b() {
    log_info "Phase 2b — Compile liboh_hwui_shim.so"

    local SHIM_SRC=$ADAPTER/framework/hwui-shim/jni

    local SHIM_CB="--target=aarch64-linux-ohos --sysroot=$SR -I$SR/include/aarch64-linux-ohos -fPIC -O2"
    SHIM_CB="$SHIM_CB -Wno-unused-parameter -Wno-unused-variable -Wno-error -Wno-deprecated-declarations"

    local SHIM_INC="-I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/surface"
    SHIM_INC="$SHIM_INC -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/common"
    SHIM_INC="$SHIM_INC -I$OH/foundation/graphic/graphic_2d/interfaces/inner_api/composer"
    SHIM_INC="$SHIM_INC -I$OH/foundation/graphic/graphic_2d/rosen/modules/2d_graphics/drawing_ndk/include"
    SHIM_INC="$SHIM_INC -I$OH/interface/sdk_c/graphic/graphic_2d/native_buffer"
    SHIM_INC="$SHIM_INC -I$AOSP/libnativehelper/include_jni"

    local SHIM_LDFLAGS="-B$OH_SYSLIB -L$OH_SYSLIB -L$SYS_LIB_NDK -L$SYS_LIB_PSDK -L$SYS_LIB_CSDK -L$SYS_LIB"

    # 1-4: C-based shims
    compile_shim_c() {
        local src=$1 outname=$2 errfile=$3
        echo -n "  $(basename $src) ... "
        $CC $SHIM_CB $SHIM_INC -c "$src" -o "$SHIM_OBJ/$outname" 2>"$SHIM_OBJ/$errfile"
        if [ $? -eq 0 ]; then
            echo "OK ($(stat -c%s "$SHIM_OBJ/$outname") bytes)"
        else
            echo "FAIL"; head -10 "$SHIM_OBJ/$errfile"; die "shim compile failed: $src"
        fi
    }
    compile_shim_c "$SHIM_SRC/oh_native_window_shim.c"  "oh_native_window_shim.o"  "nw.err"
    compile_shim_c "$SHIM_SRC/oh_choreographer_shim.c"  "oh_choreographer_shim.o"  "ch.err"
    compile_shim_c "$SHIM_SRC/oh_hardwarebuffer_shim.c" "oh_hardwarebuffer_shim.o" "hb.err"

    # 4: minikin shim (C++)
    echo -n "  oh_minikin_shim.cpp ... "
    $CXX $SHIM_CB -std=c++17 -include $BC/libcxx_compat.h -I$BC $SHIM_INC \
        -c $SHIM_SRC/oh_minikin_shim.cpp -o $SHIM_OBJ/oh_minikin_shim.o 2>$SHIM_OBJ/mk.err
    [ -f $SHIM_OBJ/oh_minikin_shim.o ] && echo "OK ($(stat -c%s $SHIM_OBJ/oh_minikin_shim.o) bytes)" || { echo "FAIL"; head -10 $SHIM_OBJ/mk.err; die "shim minikin failed"; }

    # 5-7: compat shims
    compile_shim_c "$SHIM_SRC/atrace_compat.c"      "atrace_compat.o"      "atrace.err"
    compile_shim_c "$SHIM_SRC/sync_wait_compat.c"   "sync_wait_compat.o"   "sync.err"
    compile_shim_c "$SHIM_SRC/ashmem_compat.c"      "ashmem_compat.o"      "ashmem.err"

    # 8: Skia AHardwareBuffer shim
    echo -n "  oh_skia_ahb_shim.cpp ... "
    local SKIA_INC="-I$SKIA_OH -I$SKIA_OH/include"
    local AHB_INC="-I$OH/third_party/mesa3d/include/android_stub"
    local GL_INC="-I$OH/third_party/EGL/api -I$OH/third_party/openGLES/api -I$OH/third_party/mesa3d/include"
    $CXX $SHIM_CB -std=c++17 -include $BC/libcxx_compat.h -I$BC $SKIA_INC $AHB_INC $GL_INC \
        -DSK_BUILD_FOR_ANDROID -D__ANDROID_API__=33 \
        -c $SHIM_SRC/oh_skia_ahb_shim.cpp -o $SHIM_OBJ/oh_skia_ahb_shim.o 2>$SHIM_OBJ/ahb.err
    [ -f $SHIM_OBJ/oh_skia_ahb_shim.o ] && echo "OK ($(stat -c%s $SHIM_OBJ/oh_skia_ahb_shim.o) bytes)" || { echo "FAIL"; head -30 $SHIM_OBJ/ahb.err; die "shim ahb failed"; }

    # 8b: Typeface init shim
    echo -n "  oh_typeface_init.cpp ... "
    local TYPEFACE_INC="-I$SKIA_OH -I$SKIA_OH/include -I$SKIA_OH/include/core -I$SKIA_OH/include/private/base"
    $CXX $SHIM_CB -std=c++17 -include $BC/libcxx_compat.h -I$BC $TYPEFACE_INC $AHB_INC \
        -DSK_BUILD_FOR_ANDROID -D__ANDROID_API__=33 -DENABLE_TEXT_ENHANCE \
        -c $SHIM_SRC/oh_typeface_init.cpp -o $SHIM_OBJ/oh_typeface_init.o 2>$SHIM_OBJ/tfi.err
    [ -f $SHIM_OBJ/oh_typeface_init.o ] && echo "OK ($(stat -c%s $SHIM_OBJ/oh_typeface_init.o) bytes)" || { echo "FAIL"; head -30 $SHIM_OBJ/tfi.err; die "shim typeface_init failed"; }

    # 9a: ADisplay NDK stub
    compile_shim_c "$SHIM_SRC/oh_display_shim.c"    "oh_display_shim.o"    "disp.err"

    # 9b: GraphicsStatsService stub (C++)
    echo -n "  oh_graphicsstats_shim.cpp ... "
    $CXX $SHIM_CB -std=c++17 -include $BC/libcxx_compat.h -I$BC \
        -c $SHIM_SRC/oh_graphicsstats_shim.cpp -o $SHIM_OBJ/oh_graphicsstats_shim.o 2>$SHIM_OBJ/gstats.err
    [ -f $SHIM_OBJ/oh_graphicsstats_shim.o ] && echo "OK ($(stat -c%s $SHIM_OBJ/oh_graphicsstats_shim.o) bytes)" || { echo "FAIL"; head -30 $SHIM_OBJ/gstats.err; die "shim graphicsstats failed"; }

    # 9c: __sync_* builtin shim (ARMv7 atomics)
    echo "  oh_sync_builtins.S ... SKIP (arm64: __sync_* are native compiler builtins)"

    # 9d: 6 AOSP Skia android-framework sources compiled with SK_BUILD_FOR_ANDROID
    local SKIA_INC_FULL="-I$SKIA_OH -I$SKIA_OH/include -I$SKIA_OH/src -I$SKIA_OH/modules/skcms/src"
    SKIA_INC_FULL="$SKIA_INC_FULL -I$OH/third_party/mesa3d/include/android_stub"
    local SKIA_DEFS="-DSK_BUILD_FOR_ANDROID -DSK_BUILD_FOR_ANDROID_FRAMEWORK -D__ANDROID_API__=33 -DSK_GANESH"
    local SKIA_CFLAGS_RTTI="-fno-rtti"
    for src_rel in src/android/SkAndroidFrameworkUtils.cpp src/codec/SkAndroidCodec.cpp src/android/SkAnimatedImage.cpp src/codec/SkSampledCodec.cpp src/codec/SkAndroidCodecAdapter.cpp src/codec/SkCodec.cpp; do
        local fname=$(basename $src_rel .cpp)
        echo -n "  $fname.cpp (AOSP from OH Skia m133) ... "
        $CXX $SHIM_CB $SKIA_CFLAGS_RTTI -std=c++17 -include $BC/libcxx_compat.h -I$BC $SKIA_DEFS $SKIA_INC_FULL \
            -c $SKIA_OH/$src_rel -o $SHIM_OBJ/$fname.o 2>$SHIM_OBJ/$fname.err
        [ -f $SHIM_OBJ/$fname.o ] && echo "OK ($(stat -c%s $SHIM_OBJ/$fname.o) bytes)" || { echo "FAIL"; head -30 $SHIM_OBJ/$fname.err; die "shim AOSP-skia $fname failed"; }
    done

    # 10: Link all into liboh_hwui_shim.so
    echo ""
    echo "  linking liboh_hwui_shim.so ..."
    $CXX --target=aarch64-linux-ohos $SHIM_LDFLAGS \
        -shared -fPIC \
        -o $OUT_ADAPTER/liboh_hwui_shim.so \
        $SHIM_OBJ/oh_native_window_shim.o \
        $SHIM_OBJ/oh_choreographer_shim.o \
        $SHIM_OBJ/oh_hardwarebuffer_shim.o \
        $SHIM_OBJ/oh_minikin_shim.o \
        $SHIM_OBJ/atrace_compat.o \
        $SHIM_OBJ/sync_wait_compat.o \
        $SHIM_OBJ/ashmem_compat.o \
        $SHIM_OBJ/oh_skia_ahb_shim.o \
        $SHIM_OBJ/oh_typeface_init.o \
        $SHIM_OBJ/SkAndroidFrameworkUtils.o \
        $SHIM_OBJ/SkAndroidCodec.o \
        $SHIM_OBJ/SkAnimatedImage.o \
        $SHIM_OBJ/SkSampledCodec.o \
        $SHIM_OBJ/SkAndroidCodecAdapter.o \
        $SHIM_OBJ/SkCodec.o \
        $SHIM_OBJ/oh_display_shim.o \
        $SHIM_OBJ/oh_graphicsstats_shim.o \
        -lnative_window -lnative_vsync -lnative_buffer -lnative_drawing \
        -L$SYS_LIB_NDK -lhitrace_ndk.z \
        -L$SYS_LIB_PSDK -lskia_canvaskit.z -lEGL -lGLESv3 \
        -L$ADAPTER/out/aosp_lib64 -llog \
        -L$ADAPTER/out/adapter -loh_adapter_bridge \
        -Wl,--no-allow-shlib-undefined \
        -Wl,--no-undefined \
        2>$SHIM_OBJ/link.err
    [ -f $OUT_ADAPTER/liboh_hwui_shim.so ] && echo "  OK ($(stat -c%s $OUT_ADAPTER/liboh_hwui_shim.so) bytes)" || { echo "  FAIL"; head -20 $SHIM_OBJ/link.err; die "liboh_hwui_shim.so link failed"; }
}

# ============================================================================
# Phase 2c — compile liboh_skia_rtti_shim.so (Itanium _ZTI*/_ZTS* for Skia classes)
# ============================================================================
phase2c() {
    log_info "Phase 2c — Compile liboh_skia_rtti_shim.so + verify coverage"

    local SRC_DIR=$ADAPTER/framework/surface/jni/skia_rtti_shim
    local RTTI_LOG=$OUT_RTTI_SHIM/log
    mkdir -p $RTTI_LOG

    local RTTI_CFLAGS="--target=aarch64-linux-ohos --sysroot=$SR -I$SR/include/aarch64-linux-ohos"
    RTTI_CFLAGS="$RTTI_CFLAGS   -fPIC -Os -std=c++17"
    RTTI_CFLAGS="$RTTI_CFLAGS -frtti -fvisibility=hidden -fno-exceptions"
    RTTI_CFLAGS="$RTTI_CFLAGS -Wall -Wno-unused-function"

    local RTTI_LDFLAGS="--target=aarch64-linux-ohos  "
    RTTI_LDFLAGS="$RTTI_LDFLAGS -fuse-ld=lld -fPIC -shared"
    RTTI_LDFLAGS="$RTTI_LDFLAGS --sysroot=$SR -L$SR/lib/aarch64-linux-ohos"
    RTTI_LDFLAGS="$RTTI_LDFLAGS -B$SR/lib/aarch64-linux-ohos"
    RTTI_LDFLAGS="$RTTI_LDFLAGS -L$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos"
    RTTI_LDFLAGS="$RTTI_LDFLAGS -Wl,--version-script=$SRC_DIR/skia_rtti_shim.ver"
    RTTI_LDFLAGS="$RTTI_LDFLAGS -Wl,--no-undefined"
    RTTI_LDFLAGS="$RTTI_LDFLAGS -Wl,-soname=liboh_skia_rtti_shim.so"

    echo -n "  skia_rtti_shim.cpp ... "
    $CXX $RTTI_CFLAGS -c $SRC_DIR/skia_rtti_shim.cpp -o $OUT_RTTI_SHIM/skia_rtti_shim.o 2>$RTTI_LOG/compile.err
    [ -f $OUT_RTTI_SHIM/skia_rtti_shim.o ] && echo "OK ($(stat -c%s $OUT_RTTI_SHIM/skia_rtti_shim.o) bytes)" || { echo "FAIL"; cat $RTTI_LOG/compile.err; die "phase 2c compile failed"; }

    echo -n "  liboh_skia_rtti_shim.so ... "
    $CXX $RTTI_LDFLAGS -o $OUT_RTTI_SHIM/liboh_skia_rtti_shim.so $OUT_RTTI_SHIM/skia_rtti_shim.o -lc++ -lc 2>$RTTI_LOG/link.err
    [ -f $OUT_RTTI_SHIM/liboh_skia_rtti_shim.so ] && echo "OK ($(stat -c%s $OUT_RTTI_SHIM/liboh_skia_rtti_shim.so) bytes)" || { echo "FAIL"; cat $RTTI_LOG/link.err; die "phase 2c link failed"; }

    # Publish to $OUT_ADAPTER/ so deploy_to_dayu200.sh:521 can find it (phase 2b
    # already publishes liboh_hwui_shim.so to the same dir; this closes the gap).
    cp -f $OUT_RTTI_SHIM/liboh_skia_rtti_shim.so $OUT_ADAPTER/liboh_skia_rtti_shim.so

    # [C-11] check_skia_rtti_coverage.sh is hard dependency
    if [ -f "$SCRIPT_DIR/check_skia_rtti_coverage.sh" ]; then
        echo "  verify shim coverage against libhwui .o UND set ..."
        bash "$SCRIPT_DIR/check_skia_rtti_coverage.sh" || die "phase 2c coverage check failed — Sk* class list drift, rerun discover_skia_rtti_syms.sh"
    else
        log_warn "  check_skia_rtti_coverage.sh missing — skipping coverage check"
    fi
}

phase2() {
    log_info "Phase 2/4 — Compile adapter shims + shim .so's"
    phase2a
    phase2b
    phase2c
    log_info "Phase 2 DONE"
}

# ============================================================================
# Phase 3 — link libhwui.so
# ============================================================================
phase3() {
    log_info "Phase 3/4 — Link libhwui.so"

    local LDFLAGS="--target=aarch64-linux-ohos  "
    LDFLAGS="$LDFLAGS -fuse-ld=lld -fPIC -shared"
    LDFLAGS="$LDFLAGS --sysroot=$SR -L$SR/lib/aarch64-linux-ohos"
    LDFLAGS="$LDFLAGS -B$SR/lib/aarch64-linux-ohos"
    LDFLAGS="$LDFLAGS -L$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos"
    LDFLAGS="$LDFLAGS -Wl,--gc-sections -Wl,--as-needed -Wl,-Bsymbolic-functions"
    if [ "$STRICT_AUDIT" = "1" ]; then
        LDFLAGS="$LDFLAGS -Wl,--allow-shlib-undefined"
        LDFLAGS="$LDFLAGS -Wl,--unresolved-symbols=ignore-in-shared-libs"
        LDFLAGS="$LDFLAGS -Wl,--error-limit=0"
    else
        LDFLAGS="$LDFLAGS -Wl,--allow-shlib-undefined"
        LDFLAGS="$LDFLAGS -Wl,-z,lazy"
        LDFLAGS="$LDFLAGS -Wl,--unresolved-symbols=ignore-all"
    fi

    local LIBS="-loh_hwui_shim"
    LIBS="$LIBS -L$ADAPTER/out/adapter"
    LIBS="$LIBS -L$ADAPTER/out/aosp_lib64"
    LIBS="$LIBS -L$OUT_RTTI_SHIM"
    LIBS="$LIBS -L$OH/out/wukong100/thirdparty/skia"
    LIBS="$LIBS -L$SYS_LIB_PSDK"
    LIBS="$LIBS -L$SYS_LIB_NDK"
    LIBS="$LIBS -L$OH/out/wukong100/innerkits/ohos-arm64/graphic_2d/EGL"
    LIBS="$LIBS -L$OH/out/wukong100/innerkits/ohos-arm64/graphic_2d/GLESv3"
    LIBS="$LIBS -L$OH/out/wukong100/innerkits/ohos-arm64/window_manager/libdm_ndk"
    LIBS="$LIBS -loh_skia_rtti_shim"
    # [C-4] G2.14bf 沉淀 — link libskia_canvaskit.z.so directly so SkSurface /
    # GrDirectContext / SkImage etc. resolve via NEEDED chain (previously
    # assumed liboh_hwui_shim.so covers all Skia refs — broke when G2.14ay
    # probes added direct SkSurface::readPixels / recordingContext / oomed calls).
    LIBS="$LIBS -lskia_canvaskit.z"
    LIBS="$LIBS -landroidfw"
    LIBS="$LIBS -lEGL -lGLESv3"
    LIBS="$LIBS -lminikin -lharfbuzz_ng -lft2 -licuuc -licui18n"
    LIBS="$LIBS -lutils -lcutils -lbase -llog -lhilog -lnative_display_manager"
    LIBS="$LIBS -ldl -lc++ -lm -lc -lpthread"
    LIBS="$LIBS -L$ADAPTER/out/aosp_lib64 -lnativehelper"

    local LINK_OUTPUT
    if [ "$STRICT_AUDIT" = "1" ]; then
        LINK_OUTPUT="$OUT_BUILD/libhwui.strict.so"
        log_info "  strict diagnostic mode — output: $LINK_OUTPUT (libhwui.so NOT touched)"
    else
        LINK_OUTPUT="$OUT_FINAL/libhwui.so"
    fi

    local OBJS=$(ls $OBJ/*.o 2>/dev/null | tr '\n' ' ')
    local NUM_OBJS=$(ls $OBJ/*.o 2>/dev/null | wc -l)

    echo "  Linking $LINK_OUTPUT with $NUM_OBJS object files..."
    echo "  Using Skia:      $SKIA_SO ($(stat -c%s $SKIA_SO 2>/dev/null) bytes)"
    echo "  Using RTTI shim: $OUT_RTTI_SHIM/liboh_skia_rtti_shim.so"

    $CXX $LDFLAGS -o "$LINK_OUTPUT" \
        -Wl,-soname=libhwui.so \
        $OBJS \
        $LIBS \
        -Wl,-rpath-link=$SYS_LIB \
        -Wl,-rpath-link=$OH/out/wukong100/thirdparty/skia \
        2>&1 | tee $LOG/link.log | tail -50

    if [ -f "$LINK_OUTPUT" ]; then
        local SIZE=$(stat -c%s "$LINK_OUTPUT")
        log_ok "Phase 3 DONE — $(basename "$LINK_OUTPUT") = $SIZE bytes"
    else
        die "Phase 3 FAIL — $LINK_OUTPUT not produced"
    fi
}

# ============================================================================
# Phase 4 — UND audit gate ([C-5])
# ============================================================================
phase4() {
    log_info "Phase 4/4 — UND audit gate"

    local SO_TO_AUDIT="$OUT_FINAL/libhwui.so"
    if [ "$STRICT_AUDIT" = "1" ]; then
        SO_TO_AUDIT="$OUT_BUILD/libhwui.strict.so"
    fi
    [ ! -f "$SO_TO_AUDIT" ] && die "audit target missing: $SO_TO_AUDIT"

    local WHITELIST=$SCRIPT_DIR/libhwui_und_whitelist_arm64.txt
    if [ ! -f "$WHITELIST" ]; then
        log_warn "  UND whitelist missing: $WHITELIST — skipping audit (treat as soft fail)"
        log_info "  to seed it: nm -D /path/to/known-good/libhwui.so | grep ' U ' | awk '{print \$2}' | sort -u > $WHITELIST"
        return 0
    fi

    local CUR_UND=$(mktemp)
    local NEW_UND=$(mktemp)
    local SORTED_WHITELIST=$(mktemp)
    trap "rm -f $CUR_UND $NEW_UND $SORTED_WHITELIST" RETURN

    $NM -D "$SO_TO_AUDIT" 2>/dev/null | grep ' U ' | awk '{print $2}' | sort -u > "$CUR_UND"
    sort -u "$WHITELIST" > "$SORTED_WHITELIST"
    comm -23 "$CUR_UND" "$SORTED_WHITELIST" > "$NEW_UND"

    local TOTAL_NEW=$(wc -l < "$NEW_UND")
    if [ "$TOTAL_NEW" -eq 0 ]; then
        log_ok "Phase 4 PASS — 0 new UND vs whitelist ($(wc -l < $CUR_UND) total UND, $(wc -l < $WHITELIST) whitelisted)"
        return 0
    fi

    local CPP_NEW=$(grep -c '^_Z' "$NEW_UND" || true)
    local C_NEW=$((TOTAL_NEW - CPP_NEW))

    echo ""
    echo "  --- $TOTAL_NEW NEW UND vs whitelist ($CPP_NEW C++ class method + $C_NEW C function) ---"
    head -20 "$NEW_UND" | sed 's/^/    /'
    [ "$TOTAL_NEW" -gt 20 ] && echo "    ... ($((TOTAL_NEW-20)) more)"

    if [ "$CPP_NEW" -gt 0 ]; then
        if [ "$NO_UND_GATE" = "1" ]; then
            log_warn "Phase 4 WARN ($NO_UND_GATE override) — $CPP_NEW new C++ class method UND would block dlopen on device"
        else
            die "Phase 4 FAIL — $CPP_NEW new C++ class method UND will block dlopen (OH musl/ART eager-relocates _Z*). Add stub or fix linker. Use --no-und-gate to override."
        fi
    fi

    if [ "$C_NEW" -gt 0 ]; then
        log_warn "Phase 4 WARN — $C_NEW new C function UND (typically OK via NEEDED chain lazy bind, but worth investigating if dlopen fails)"
    fi
}

# ============================================================================
# Main dispatch
# ============================================================================
have_phase 1 && phase1
( have_phase 2 || have_phase 2a || have_phase 2b || have_phase 2c ) && {
    have_phase 2a && phase2a
    have_phase 2b && phase2b
    have_phase 2c && phase2c
    if have_phase 2 && ! have_phase 2a && ! have_phase 2b && ! have_phase 2c; then
        phase2
    fi
}
have_phase 3 && phase3
have_phase 4 && phase4

echo ""
echo "=========================================="
echo "  Pipeline complete (phases: $PHASES)"
if [ -f "$OUT_FINAL/libhwui.so" ]; then
    echo "  Output: $OUT_FINAL/libhwui.so ($(stat -c%s $OUT_FINAL/libhwui.so) bytes)"
fi
echo "=========================================="
