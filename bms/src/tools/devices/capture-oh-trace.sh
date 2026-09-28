#!/usr/bin/env bash
# capture-oh-trace.sh — 鸿蒙板上**任意包**的框架层 trace 采集（②③ 线通用）。
#
# 为什么要从 ZigZag HAP 专用采集脚本提出来通用化：
#   那一份写死了 ② 线的包名/ability，并且负责装机。做 ②③ AB 对比时，两边必须用
#   **同一套 tag、同一缓冲大小、同一时序**采集，否则观测面差异会被工具差异污染，
#   分不清「③ 缺这一跳」还是「③ 那轮 tag 没开」。故把采集逻辑抽出来，包名做参数。
#
# 与原脚本的差异（有意为之）：
#   - 不装机：②③ 的包都已在板上，装机会引入版本漂移
#   - 包名/ability/启动命令全参数化
#   - run 目录带 --label，便于 ②③ 并排比对
#
# 用法:
#   ./capture-oh-trace.sh --bundle <包名> --ability <ability> --label <标签> \
#                         [--module entry] [--tap-x 600 --tap-y 1200] [--board <序列号>]
#
# 例（② 线，团结 HAP）:
#   ./capture-oh-trace.sh --bundle com.a2hlab.control.zigzag \
#       --ability TuanjiePlayerAbility --module entry --label line2-hap
#
# 例（③ 线，Bridge APK）:
#   ./capture-oh-trace.sh --bundle com.a2hlab.bridge.zigzag \
#       --ability com.unity3d.player.UnityPlayerActivity --label line3-bridge
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"

BUNDLE=""; ABILITY=""; LABEL=""; MODULE=""; BOARD=""; LAUNCH_TAP=""
ARTIFACT=""; TRACE_DEPTH="standard"
GRAPHICS_UPROBES=0
CHECKPOINT_TAPS=0
TAP_X=600; TAP_Y=1200
while [ $# -gt 0 ]; do
  case "$1" in
    --bundle)     BUNDLE="$2"; shift 2 ;;
    --ability)    ABILITY="$2"; shift 2 ;;
    --label)      LABEL="$2"; shift 2 ;;
    --module)     MODULE="$2"; shift 2 ;;
    --board)      BOARD="$2"; shift 2 ;;
    --launch-tap) LAUNCH_TAP="$2"; shift 2 ;;   # 桌面图标坐标 "x,y"
    --artifact)   ARTIFACT="$2"; shift 2 ;;     # 本轮安装件，写入哈希身份
    --trace-depth) TRACE_DEPTH="$2"; shift 2 ;; # standard|deep
    --graphics-uprobes) GRAPHICS_UPROBES=1; shift ;; # exact ZigZag BLAST/ANW/EGL ABI edges
    --checkpoint-taps) CHECKPOINT_TAPS=1; shift ;; # spread exactly five taps between t+3/9/15
    --tap-x)      TAP_X="$2"; shift 2 ;;        # M15 注入点击坐标
    --tap-y)      TAP_Y="$2"; shift 2 ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done
die() { echo "错误：$*" >&2; exit 1; }
[ -n "${BUNDLE}" ]  || die "缺 --bundle"
[ -n "${ABILITY}" ] || die "缺 --ability"
[ -n "${LABEL}" ]   || die "缺 --label（用于区分 ②③ 的 run 目录）"
case "${TRACE_DEPTH}" in standard|deep) ;; *) die "--trace-depth 只能是 standard|deep" ;; esac
[ -z "${ARTIFACT}" ] || [ -f "${ARTIFACT}" ] || die "--artifact 不存在: ${ARTIFACT}"

# ── hitrace tag 集：与 src/tools/zigzag/capture-hap-oh-trace.sh **保持一致** ──
# 改这里必须同步改那边，否则 ②③ 不再可比。每个 tag 注明覆盖哪几格。
TRACE_TAGS=(
  ark               # M03 运行时就绪
  app               # M04 应用入口被调
  ability           # M05 派发 / M06 onCreate / M14 前台报到完成
  ffrt              # M07 消息循环
  window            # M08 应用要窗口 / M09 宿主给窗口
  ace               # M10 首次测量 / M11 首次绘制
  graphic           # M11–M13 绘制→提交→上屏
  multimodalinput   # M15 触摸送达
  ohos              # 系统通用兜底
  binder rpc        # 跨进程因果链（应用↔AMS↔RS）
  sched             # 区分「没做」与「被抢占没轮到」
  sync              # dma fence / buffer 交接
)
if [ "${TRACE_DEPTH}" = deep ]; then
  TRACE_TAGS+=(freq idle irq workq power load memory)
  TRACE_BUF_KB=131072
else
  TRACE_BUF_KB=65536
fi

# AArch64 syscall numbers: exit=93, exit_group=94, kill/tkill/tgkill=129/130/131.
# Filtering at the tracepoint keeps the decisive termination calls without
# flooding the ring buffer with every syscall from every process.
EXIT_SYSCALL_FILTER='id == 93 || id == 94 || id == 129 || id == 130 || id == 131'
DIAG_EVENTS=(
  sched/sched_process_exit
  signal/signal_generate
  signal/signal_deliver
  oom/mark_victim
)

if [ -z "${BOARD}" ]; then
  BOARD=$(hdc list targets 2>/dev/null | tr -d '\r' | grep -v '^\[Empty\]$' | grep -v '^$' | head -1)
fi
[ -n "${BOARD}" ] || die "无连接板（hdc list targets 为空）"
H() { hdc -t "${BOARD}" "$@"; }

UPROBES_CONFIGURED=0
cleanup_graphics_uprobes() {
  [ "${UPROBES_CONFIGURED}" = 1 ] || return 0
  H shell "echo 0 > /sys/kernel/tracing/events/zzgfx/enable 2>/dev/null || true; \
    for event in tuanjie_player_loop_return tuanjie_player_loop_enter \
      ndk_glgetstring_enter tuanjie_fill_glgetstring_dispatch \
      tuanjie_load_query_glgetstringi tuanjie_load_query_glgetintegerv \
      tuanjie_load_query_glgetstring tuanjie_core_before_dlsym \
      tuanjie_core_after_dlopen tuanjie_core_getproc_return \
      tuanjie_core_getproc_enter \
      tuanjie_display_startup_return tuanjie_display_startup_enter \
      tuanjie_graphics_startup_return tuanjie_graphics_startup_enter \
      tuanjie_apply_window_return tuanjie_apply_window_enter \
      tuanjie_set_window_return tuanjie_set_window_enter \
      tuanjie_attach_surface_return tuanjie_attach_surface_enter \
      tuanjie_recreate_return tuanjie_recreate_enter \
      tuanjie_render_return tuanjie_render_enter \
      tuanjie_focus_return tuanjie_focus_enter \
      tuanjie_resume_return tuanjie_resume_enter \
      guest_query_return guest_query_enter \
      guest_format_return guest_format_enter guest_height_return guest_height_enter \
      guest_width_return guest_width_enter guest_release guest_acquire \
      guest_geometry_return guest_geometry_enter \
      guest_egl_return guest_egl_enter guest_anw_return guest_anw_enter \
      surface_valid_return surface_valid_enter \
      surface_from_bbq_return surface_from_bbq_enter \
      adapter_queue_return adapter_queue_enter \
      adapter_dequeue_return adapter_dequeue_enter adapter_perform_return \
      adapter_perform_enter adapter_wrap_return adapter_wrap_enter \
      egl_return egl_enter anw_return anw_enter child_after_create \
      parent_after_lookup wm_getrs_enter create_session_enter singleton_return \
      child_window_return child_window_enter wm_last_return wm_last_enter wm_window_return \
      wm_window_enter bbq_update_enter bbq_get_surface_return \
      bbq_get_surface_enter bbq_create_return bbq_create_enter; do \
        echo -:zzgfx/\${event} >> /sys/kernel/tracing/uprobe_events 2>/dev/null || true; \
    done" >/dev/null 2>&1 || true
  UPROBES_CONFIGURED=0
}
trap cleanup_graphics_uprobes EXIT

configure_graphics_uprobes() {
  [ "${GRAPHICS_UPROBES}" = 1 ] || return 0
  local runtime_sha adapter_sha libandroid_sha tuanjie_sha glesv2_sha
  runtime_sha=$(H shell "sha256sum /system/android/lib64/liboh_android_runtime.so" \
    2>/dev/null | tr -d '\r' | awk '{print $1}')
  adapter_sha=$(H shell "sha256sum /system/android/lib64/liboh_adapter_bridge.so" \
    2>/dev/null | tr -d '\r' | awk '{print $1}')
  libandroid_sha=$(H shell "sha256sum /system/android/lib64/libandroid.so" \
    2>/dev/null | tr -d '\r' | awk '{print $1}')
  tuanjie_sha=$(H shell "sha256sum /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so" \
    2>/dev/null | tr -d '\r' | awk '{print $1}')
  glesv2_sha=$(H shell "sha256sum /system/lib64/ndk/libGLESv2.so" \
    2>/dev/null | tr -d '\r' | awk '{print $1}')
  [ "${runtime_sha}" = "9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db" ] \
    || die "graphics uprobe runtime generation mismatch: ${runtime_sha}"
  [ "${adapter_sha}" = "84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a" ] \
    || die "graphics uprobe adapter generation mismatch: ${adapter_sha}"
  [ "${libandroid_sha}" = "9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db" ] \
    || die "graphics uprobe guest libandroid generation mismatch: ${libandroid_sha}"
  case "${tuanjie_sha}" in
    2afc88452f83d51b7f7efedc2024f43e2b7b730257930b6585aec02fab771c1b|\
    421344aca5dc7e2ed65b8f314d1af6bddcbf0827302efede277c364f1ebf7cba|\
    eb9d8c6de0f415e66896dfea5f5ddf16891d856766e5be1e6fb923166e844c9b)
      ;;
    *) die "graphics uprobe Tuanjie generation mismatch: ${tuanjie_sha}" ;;
  esac
  [ "${glesv2_sha}" = "5b4f734b081a4067ce36552085952268a4c72034107bae41df0222625a6e2319" ] \
    || die "graphics uprobe NDK GLESv2 generation mismatch: ${glesv2_sha}"

  # Offsets are ELF file offsets, not symbol virtual addresses. They are
  # mechanically derived from the exact unstripped artifacts above; the hash
  # fence prevents a probe from silently landing in another generation.
  H shell "set -e; test ! -s /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/bbq_create_enter /system/android/lib64/liboh_android_runtime.so:0x40614 jname=%x2 update_destination=%x3' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/bbq_create_return /system/android/lib64/liboh_android_runtime.so:0x40614 bbq=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/bbq_get_surface_enter /system/android/lib64/liboh_android_runtime.so:0x40768 bbq=%x2 include_sc=%x3' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/bbq_get_surface_return /system/android/lib64/liboh_android_runtime.so:0x40768 surface=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/bbq_update_enter /system/android/lib64/liboh_android_runtime.so:0x40bf0 bbq=%x2 sc=%x3 width=%x4 height=%x5 format=%x6' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/surface_from_bbq_enter /system/android/lib64/liboh_android_runtime.so:0x40198 old_surface=%x2 bbq=%x3' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/surface_from_bbq_return /system/android/lib64/liboh_android_runtime.so:0x40198 native_surface=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/surface_valid_enter /system/android/lib64/liboh_android_runtime.so:0x402b8 native_surface=%x2' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/surface_valid_return /system/android/lib64/liboh_android_runtime.so:0x402b8 valid=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/wm_window_enter /system/android/lib64/liboh_adapter_bridge.so:0xde9e4 session=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/wm_window_return /system/android/lib64/liboh_adapter_bridge.so:0xde9e4 window=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/wm_last_enter /system/android/lib64/liboh_adapter_bridge.so:0xdeba0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/wm_last_return /system/android/lib64/liboh_adapter_bridge.so:0xdeba0 session=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/singleton_return /system/android/lib64/liboh_adapter_bridge.so:0xdbc64 singleton=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/create_session_enter /system/android/lib64/liboh_adapter_bridge.so:0xdbfa0 this=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/wm_getrs_enter /system/android/lib64/liboh_adapter_bridge.so:0xde70c this=%x0 session=%x1 retstore=%x8' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/child_window_enter /system/android/lib64/liboh_adapter_bridge.so:0xdf7e8 session=%x0 child=%x1 width=%x2 height=%x3' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/parent_after_lookup /system/android/lib64/liboh_adapter_bridge.so:0xdf904 parent=%x8' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/child_after_create /system/android/lib64/liboh_adapter_bridge.so:0xdf9a8 child=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/child_window_return /system/android/lib64/liboh_adapter_bridge.so:0xdf7e8 window=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/adapter_wrap_enter /system/android/lib64/liboh_adapter_bridge.so:0xd5850 oh_window=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/adapter_wrap_return /system/android/lib64/liboh_adapter_bridge.so:0xd5850 window=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/adapter_perform_enter /system/android/lib64/liboh_adapter_bridge.so:0xd4d2c window=%x0 op=%x1 arg0=%x2 arg1=%x3 arg2=%x4' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/adapter_perform_return /system/android/lib64/liboh_adapter_bridge.so:0xd4d2c rc=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/adapter_dequeue_enter /system/android/lib64/liboh_adapter_bridge.so:0xd5060 window=%x0 buffer_store=%x1 fence_store=%x2' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/adapter_dequeue_return /system/android/lib64/liboh_adapter_bridge.so:0xd5060 rc=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/adapter_queue_enter /system/android/lib64/liboh_adapter_bridge.so:0xd5664 window=%x0 buffer=%x1 fence=%x2' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/adapter_queue_return /system/android/lib64/liboh_adapter_bridge.so:0xd5664 rc=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/guest_anw_enter /system/android/lib64/libandroid.so:0x3f7fc surface=%x1' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/guest_anw_return /system/android/lib64/libandroid.so:0x3f7fc window=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/guest_egl_enter /system/android/lib64/libandroid.so:0x3fe2c dpy=%x0 cfg=%x1 win=%x2 attrs=%x3' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/guest_egl_return /system/android/lib64/libandroid.so:0x3fe2c surface=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/guest_geometry_enter /system/android/lib64/libandroid.so:0x3fbd0 window=%x0 width=%x1 height=%x2 format=%x3' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/guest_geometry_return /system/android/lib64/libandroid.so:0x3fbd0 rc=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/guest_acquire /system/android/lib64/libandroid.so:0x3fa78 window=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/guest_release /system/android/lib64/libandroid.so:0x3fab0 window=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/guest_width_enter /system/android/lib64/libandroid.so:0x3fae8 window=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/guest_width_return /system/android/lib64/libandroid.so:0x3fae8 width=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/guest_height_enter /system/android/lib64/libandroid.so:0x3fb3c window=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/guest_height_return /system/android/lib64/libandroid.so:0x3fb3c height=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/guest_format_enter /system/android/lib64/libandroid.so:0x3fb90 window=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/guest_format_return /system/android/lib64/libandroid.so:0x3fb90 format=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/guest_query_enter /system/android/lib64/libandroid.so:0x3fd58 window=%x0 what=%x1 value_store=%x2' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/guest_query_return /system/android/lib64/libandroid.so:0x3fd58 rc=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_core_getproc_enter /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0xaaaad4 name=+0(%x0):string' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/tuanjie_core_getproc_return /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0xaaaad4 result=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_core_after_dlopen /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0xaaaafc handle=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_core_before_dlsym /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0xaaab04 handle=%x8 name=+0(%x19):string' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_load_query_glgetstring /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0xa88ce4 result=%x0 api=%x19' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_load_query_glgetintegerv /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0xa88cf4 result=%x0 api=%x19' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_load_query_glgetstringi /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0xa88d10 result=%x0 api=%x19' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_fill_glgetstring_dispatch /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0xa9e5a4 proc=%x8 api=%x20 pname=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/ndk_glgetstring_enter /system/lib64/ndk/libGLESv2.so:0x172d0 pname=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_resume_enter /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x6b6ef8 env=%x0 player=%x1' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/tuanjie_resume_return /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x6b6ef8 rc=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_focus_enter /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x6b6fd8 env=%x0 player=%x1 focused=%x2' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/tuanjie_focus_return /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x6b6fd8 rc=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_render_enter /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x6b70ec env=%x0 player=%x1' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/tuanjie_render_return /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x6b70ec keep_running=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_recreate_enter /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x6b702c env=%x0 player=%x1 display=%x2 surface=%x3' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/tuanjie_recreate_return /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x6b702c rc=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_attach_surface_enter /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x69e5d4 display=%x0 surface=%x1 env=%x2' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/tuanjie_attach_surface_return /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x69e5d4 rc=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_set_window_enter /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x69cfb8 display=%x0 window=%x1' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/tuanjie_set_window_return /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x69cfb8 rc=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_apply_window_enter /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x69d15c' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/tuanjie_apply_window_return /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x69d15c rc=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_graphics_startup_enter /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x69d52c' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/tuanjie_graphics_startup_return /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x69d52c ok=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_display_startup_enter /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x6a937c this=%x0 api=%x1 window=%x2' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/tuanjie_display_startup_return /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x6a937c ok=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/tuanjie_player_loop_enter /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x6a0bc0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/tuanjie_player_loop_return /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so:0x6a0bc0 rc=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/anw_enter /system/android/lib64/liboh_android_runtime.so:0x3f7fc surface=%x1' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/anw_return /system/android/lib64/liboh_android_runtime.so:0x3f7fc window=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 'p:zzgfx/egl_enter /system/android/lib64/liboh_android_runtime.so:0x3fe2c dpy=%x0 cfg=%x1 win=%x2 attrs=%x3' >> /sys/kernel/tracing/uprobe_events; \
    echo 'r:zzgfx/egl_return /system/android/lib64/liboh_android_runtime.so:0x3fe2c surface=%x0' >> /sys/kernel/tracing/uprobe_events; \
    echo 1 > /sys/kernel/tracing/events/zzgfx/enable" >/dev/null \
    || die "无法配置 ZigZag 图形 ABI uprobes"
  UPROBES_CONFIGURED=1
  H shell "cat /sys/kernel/tracing/uprobe_events" 2>/dev/null | tr -d '\r' \
    > "${RUN}/graphics-uprobes.txt"
}

TS=$(date +%Y%m%d-%H%M%S)
RUN="${REPO_ROOT}/var/evidence/ab-compare/${TS}-${BOARD:0:4}-${LABEL}"
mkdir -p "${RUN}"

ROM=$(H shell "param get const.ohos.fullname" 2>/dev/null | tr -d '\r' | tr -d ' ')
BOOT_ID=$(H shell "cat /proc/sys/kernel/random/boot_id" 2>/dev/null | tr -d '\r ')
ADAPTER_SHA=$(H shell "sha256sum /system/android/lib64/liboh_adapter_bridge.so" 2>/dev/null \
  | tr -d '\r' | awk '{print $1}')
ARTIFACT_SHA=""
if [ -n "${ARTIFACT}" ]; then
  ARTIFACT_SHA=$(sha256sum "${ARTIFACT}" | awk '{print $1}')
fi
{
  echo "ROM=${ROM}"
  echo "boot_id=${BOOT_ID}"
  echo "board=${BOARD}"
  echo "bundle=${BUNDLE}"
  echo "ability=${ABILITY}"
  echo "label=${LABEL}"
  echo "tags=${TRACE_TAGS[*]}"
  echo "buf_kb=${TRACE_BUF_KB}"
  echo "trace_depth=${TRACE_DEPTH}"
  echo "graphics_uprobes=${GRAPHICS_UPROBES}"
  echo "adapter_sha256=${ADAPTER_SHA:-UNAVAILABLE}"
  echo "artifact=${ARTIFACT:-UNSPECIFIED}"
  echo "artifact_sha256=${ARTIFACT_SHA:-UNSPECIFIED}"
} | tee "${RUN}/envstamp.txt"

MARK() {
  H shell "echo 'ABCMP ${TS} $*' > /sys/kernel/tracing/trace_marker" >/dev/null 2>&1 || true
}

# Native loader failures can terminate the child before the t+3 checkpoint.
# Keep the before-set so every newly-created faultlogger file can be pulled
# even when hilog has already rotated the decisive line away.
H shell "find /data/log/faultlog -type f 2>/dev/null | sort" 2>/dev/null \
  | tr -d '\r' > "${RUN}/faultlogs-before.txt" || true

# ── 0. 常亮：M13 判据是屏幕真实像素，息屏会把「没上屏」和「屏幕关了」混为一谈 ──
# OH_TARGET 必须传：多板在线时 keep-awake.sh 会因无法自动选板而失败，而该失败
# 此前是被 `|| 警告` 吞掉的——结果整轮采到黑屏截图，L3 判据全废。
echo "== 常亮"
if ! OH_TARGET="${BOARD}" "${SCRIPT_DIR}/keep-awake.sh" on harmony >/dev/null 2>&1; then
  echo "  keep-awake.sh 失败，退回直接下发 power-shell"
  H shell "power-shell wakeup; power-shell timeout -o 86400000; power-shell setmode 602" >/dev/null 2>&1 || true
fi
# 无论走哪条路都实测一次亮度状态，不亮就停手——采到黑屏的 trace 没有判定价值
H shell "power-shell wakeup" >/dev/null 2>&1 || true

# 刷机或重启后常停在锁屏；Home 键不会解锁，随后按桌面坐标会得到 No Error，
# 但目标进程根本不会出现。只在确实检测到锁屏根节点时上滑解锁。
H shell "uitest uiInput keyEvent Home" >/dev/null 2>&1 || true
H shell "uitest dumpLayout -p /data/local/tmp/ab-prelaunch.json" >/dev/null 2>&1 || true
if H shell "grep -q ScreenLockRootComponent /data/local/tmp/ab-prelaunch.json" >/dev/null 2>&1; then
  echo "  检测到锁屏，先上滑解锁"
  H shell "uitest uiInput swipe 600 1700 600 300 800" >/dev/null 2>&1 || true
  sleep 2
  H shell "uitest uiInput keyEvent Home" >/dev/null 2>&1 || true
fi

# ── 1. 强杀：不冷启动就采不到 M01–M09 ────────────────────────────────────
echo "== 强杀旧进程（保证冷启动）"
H shell "aa force-stop ${BUNDLE}" 2>&1 | tr -d '\r' > "${RUN}/force-stop.txt" || true
sleep 2
if H shell "ps -ef | grep '${BUNDLE}' | grep -v grep" 2>/dev/null | tr -d '\r' | grep -q .; then
  echo "  警告：强杀后进程仍在，M01–M09 可能是热启动，判定须记 —" | tee -a "${RUN}/force-stop.txt"
fi

# ── 2. 起 trace（必须早于起应用，否则丢整个启动段）────────────────────────
echo "== 起 hitrace"
H shell "hitrace --trace_finish_nodump >/dev/null 2>&1" >/dev/null 2>&1 || true
H shell "hitrace --trace_begin --trace_clock boot -b ${TRACE_BUF_KB} ${TRACE_TAGS[*]}" 2>&1 \
  | tr -d '\r' > "${RUN}/trace-begin.txt"

# hitrace's sched tag does not enable process-exit or signal tracepoints on
# this ROM. Enable those explicitly, and fail closed if the diagnostic surface
# changes: otherwise an empty result would again be misread as "no signal".
: > "${RUN}/diagnostic-events.txt"
RAW_ENTER=/sys/kernel/tracing/events/raw_syscalls/sys_enter
if ! H shell "test -f ${RAW_ENTER}/filter -a -f ${RAW_ENTER}/enable" >/dev/null 2>&1; then
  die "板上缺 raw_syscalls/sys_enter 诊断事件"
fi
H shell "echo '${EXIT_SYSCALL_FILTER}' > ${RAW_ENTER}/filter && echo 1 > ${RAW_ENTER}/enable" \
  >/dev/null 2>&1 || die "无法启用过滤后的 exit/kill syscall 事件"
printf 'enabled=%s filter=%s\n' "${RAW_ENTER}" "${EXIT_SYSCALL_FILTER}" \
  >> "${RUN}/diagnostic-events.txt"
for diag_event in "${DIAG_EVENTS[@]}"; do
  diag_path="/sys/kernel/tracing/events/${diag_event}"
  H shell "test -f ${diag_path}/enable && echo 1 > ${diag_path}/enable" \
    >/dev/null 2>&1 || die "无法启用诊断事件 ${diag_event}"
  printf 'enabled=%s\n' "${diag_path}" >> "${RUN}/diagnostic-events.txt"
done
configure_graphics_uprobes
MARK RUN_BEGIN
sleep 1

# ── 3. 清日志 → 起应用 ───────────────────────────────────────────────────
H shell "hilog -r" >/dev/null 2>&1 || true
echo "== 启动 ${BUNDLE}/${ABILITY}"
MARK LAUNCH
APP_UID=$(H shell "bm dump -n ${BUNDLE}" 2>/dev/null | tr -d '\r' \
  | grep -oE '\"uid\": *[0-9]{6,}' | head -1 | grep -oE '[0-9]+$')
echo "  应用 uid=${APP_UID:-未解析}"
# 启动方式为什么可选：② 线的 HAP 用 `aa start` 会被 AMS 以 10107101（调用方身份）
# 驳回，只有桌面点击能起；③ 线的 Bridge APK 两种都行。做 AB 对比时**两边必须用
# 同一种**，否则「sceneboard→AMS」与「shell→AMS」两条不同的调用方路径会混进观测面。
if [ -n "${LAUNCH_TAP}" ]; then
  LAUNCH_DESC="tap ${LAUNCH_TAP}"
  echo "mode=tap coords=${LAUNCH_TAP}" > "${RUN}/launch.txt"
  # 必须先回桌面**并翻到应用页**：Home 只回到第 1 页，而三个样本的图标都在第 2 页。
  # 少了这一跳，点击会落在空白壁纸上、返回 "No Error"，看起来成功实际什么也没起。
  H shell "uitest uiInput keyEvent Home" >/dev/null 2>&1 || true
  sleep 2
  H shell "uitest uiInput swipe 1000 1000 200 1000 600" >/dev/null 2>&1 || true
  sleep 2
  H shell "uitest uiInput click ${LAUNCH_TAP/,/ }" 2>&1 | tr -d '\r' | tee -a "${RUN}/launch.txt"
else
  if [ -n "${MODULE}" ]; then
    LAUNCH_CMD="aa start -b ${BUNDLE} -m ${MODULE} -a ${ABILITY}"
  else
    LAUNCH_CMD="aa start -a ${ABILITY} -b ${BUNDLE}"
  fi
  LAUNCH_DESC="${LAUNCH_CMD}"
  echo "mode=aa cmd=${LAUNCH_CMD}" > "${RUN}/launch.txt"
  H shell "${LAUNCH_CMD}" 2>&1 | tr -d '\r' | tee -a "${RUN}/launch.txt"
fi
echo "  启动方式: ${LAUNCH_DESC}"

# Sub-second sampler: the Unity constructor can fail in roughly 150 ms. The
# regular t+3/9/15 checkpoints describe persistence; this file proves whether
# a child existed at all and preserves its first observed PID.
: > "${RUN}/proc-early.txt"
FIRST_PID=""
LIFETIME_SAMPLER_HOST_PID=""
for early_sample in $(seq 1 24); do
  sample_proc=""
  if [ -n "${APP_UID}" ]; then
    sample_proc=$(H shell "ps -ef | grep -E '^${APP_UID}[[:space:]]|${BUNDLE}' | grep -v grep" \
      2>/dev/null | tr -d '\r' || true)
  else
    sample_proc=$(H shell "ps -ef | grep '${BUNDLE}' | grep -v grep" \
      2>/dev/null | tr -d '\r' || true)
  fi
  {
    printf 'sample=%s host_epoch_ms=%s\n' "${early_sample}" "$(date +%s%3N 2>/dev/null || date +%s000)"
    printf '%s\n' "${sample_proc}"
  } >> "${RUN}/proc-early.txt"
  if [ -z "${FIRST_PID}" ] && [ -n "${sample_proc}" ]; then
    if [ -n "${APP_UID}" ]; then
      FIRST_PID=$(printf '%s\n' "${sample_proc}" \
        | awk -v uid="${APP_UID}" '$1 == uid && $2 ~ /^[0-9]+$/ {print $2; exit}')
    else
      FIRST_PID=$(printf '%s\n' "${sample_proc}" \
        | awk '$2 ~ /^[0-9]+$/ {print $2; exit}')
    fi
    if [ -n "${FIRST_PID}" ]; then
      printf '%s\n' "${FIRST_PID}" > "${RUN}/first-pid.txt"
      H shell "echo ===STATUS===; cat /proc/${FIRST_PID}/status 2>/dev/null; echo ===MAPS===; cat /proc/${FIRST_PID}/maps 2>/dev/null; echo ===MOUNTINFO===; cat /proc/${FIRST_PID}/mountinfo 2>/dev/null; echo ===FD===; ls -laZ /proc/${FIRST_PID}/fd 2>/dev/null; echo ===TASKS===; for task in /proc/${FIRST_PID}/task/*; do tid=\${task##*/}; echo ===TID:\${tid}:COMM===; cat \${task}/comm 2>/dev/null; echo ===TID:\${tid}:SYSCALL===; cat \${task}/syscall 2>/dev/null; echo ===TID:\${tid}:WCHAN===; cat \${task}/wchan 2>/dev/null; echo ===TID:\${tid}:STACK===; cat \${task}/stack 2>/dev/null; done" \
        2>&1 | tr -d '\r' > "${RUN}/proc-first-snapshot.txt" || true
      # Sample every thread's current syscall/wchan across the short lifetime.
      # This is read-only and avoids processdump's signal-35 perturbation.
      H shell "pid=${FIRST_PID}; sample=0; while [ -d /proc/\${pid} ] && [ \${sample} -lt 20 ]; do echo ===SAMPLE:\${sample}===; for task in /proc/\${pid}/task/*; do tid=\${task##*/}; printf 'TID=%s COMM=' \${tid}; cat \${task}/comm 2>/dev/null; printf 'SYSCALL='; cat \${task}/syscall 2>/dev/null; printf 'WCHAN='; cat \${task}/wchan 2>/dev/null; done; sample=\$((sample + 1)); sleep 0.05; done; echo ===SAMPLER-END=== sample=\${sample}" \
        2>&1 | tr -d '\r' > "${RUN}/proc-lifetime.txt" &
      LIFETIME_SAMPLER_HOST_PID=$!
    fi
  fi
  sleep 0.1
done
if [ ! -s "${RUN}/first-pid.txt" ] && [ -n "${APP_UID}" ]; then
  awk -v uid="${APP_UID}" '$1 == uid && $2 ~ /^[0-9]+$/ {print $2; exit}' \
    "${RUN}/proc-early.txt" > "${RUN}/first-pid.txt"
fi

# ── 4. 三个时间点各拍一次：捕捉「起来了又被回收」这类中间态 ──────────────
# ③ 线实测过：子进程在 t+1.5s 存在、t+9s 被 AMS 超时回收。只在末尾拍一张会把
# 「孵化成功但被回收」误读成「从未孵化」。
#
# 进程为什么按 uid 认而不按包名 grep：Bridge 孵出的安卓子进程在 `ps -ef` 里显示的
# 仍是父进程命令行 `appspawn-x --socket-name AppSpawnX`（Java 侧 setArgV0 改的是
# 进程名，未反映到 cmdline）。按包名 grep 对 ③ 线**恒为 0**，会把「孵化成功后被
# 回收」误报成「从未孵化」——正是 §6.3 要防的把 `—` 写成 `✗`。
PREV_T=0
LAUNCH_VALID=1
DELIVERED_TAPS=0
for t in 3 9 15; do
  sleep "$(( t - PREV_T ))"; PREV_T="${t}"
  MARK "SCREEN_T${t}"
  H shell "snapshot_display -f /data/local/tmp/ab-t${t}.jpeg" >/dev/null 2>&1 || true
  if [ -n "${APP_UID}" ]; then
    H shell "ps -ef | grep -E '^${APP_UID}[[:space:]]|${BUNDLE}' | grep -v grep" 2>&1 \
      | tr -d '\r' > "${RUN}/proc-t${t}.txt" || true
  else
    H shell "ps -ef | grep '${BUNDLE}' | grep -v grep" 2>&1 | tr -d '\r' \
      > "${RUN}/proc-t${t}.txt" || true
  fi
  # A lifecycle timeout often kills the child before the final log snapshot.
  # Capture every target thread's kernel stack/wchan at the same t+3/9/15
  # checkpoints as the screenshots so the earliest blocked hop remains
  # inspectable even when the process disappears later in the run.
  : > "${RUN}/thread-stacks-t${t}.txt"
  while read -r target_pid; do
    case "${target_pid}" in ''|*[!0-9]*) continue ;; esac
    H shell "echo ===PID:${target_pid}===; cat /proc/${target_pid}/status 2>/dev/null; for task in /proc/${target_pid}/task/*; do tid=\${task##*/}; echo ===TID:\${tid}:COMM===; cat \${task}/comm 2>/dev/null; echo ===TID:\${tid}:WCHAN===; cat \${task}/wchan 2>/dev/null; echo ===TID:\${tid}:STACK===; cat \${task}/stack 2>/dev/null; done" \
      2>&1 | tr -d '\r' >> "${RUN}/thread-stacks-t${t}.txt" || true
  done < <(awk '{print $2}' "${RUN}/proc-t${t}.txt" 2>/dev/null | sort -u)
  echo "  t+${t}s 进程数: $(grep -c . "${RUN}/proc-t${t}.txt" 2>/dev/null || echo 0)"
  if [ "${t}" = 3 ] && ! grep -q . "${RUN}/proc-t3.txt" 2>/dev/null; then
    if grep -Eq '^[0-9]+$' "${RUN}/first-pid.txt" 2>/dev/null; then
      echo "EARLY_EXIT: 目标进程已出现但未存活到 t+3s，first_pid=$(cat "${RUN}/first-pid.txt")" \
        | tee "${RUN}/EARLY_EXIT.txt"
    else
      LAUNCH_VALID=0
      echo "INVALID_LAUNCH: t+3s 前从未观测到目标 UID/包进程，禁止把本轮用于 A/B 判定" \
        | tee "${RUN}/INVALID_LAUNCH.txt"
    fi
  fi

  # ZigZag's title page is intentionally static. For the interactive acceptance
  # run, distribute exactly five taps between checkpoints so the screenshots
  # prove changing game pixels as well as persistence. PREV_T includes the
  # one-second tap cadence, keeping the next checkpoint close to wall-clock t.
  if [ "${CHECKPOINT_TAPS}" = 1 ] && [ "${t}" = 3 ]; then
    echo "== t+3→t+9 注入点击 ×3"
    for i in 1 2 3; do
      MARK "TOUCH_${i}"
      if H shell "uitest uiInput click ${TAP_X} ${TAP_Y}" >/dev/null 2>&1 || \
          H shell "uinput -T -c ${TAP_X} ${TAP_Y}" >/dev/null 2>&1; then
        DELIVERED_TAPS=$((DELIVERED_TAPS + 1))
      fi
      sleep 1
    done
    PREV_T=6
  elif [ "${CHECKPOINT_TAPS}" = 1 ] && [ "${t}" = 9 ]; then
    echo "== t+9→t+15 注入点击 ×2"
    # Keep the result page visible until about t+12, then hit RETRY/start near
    # the next checkpoint. This makes t+15 sample the second live round rather
    # than the same static result page seen at t+9.
    sleep 3
    for i in 4 5; do
      MARK "TOUCH_${i}"
      if H shell "uitest uiInput click ${TAP_X} ${TAP_Y}" >/dev/null 2>&1 || \
          H shell "uinput -T -c ${TAP_X} ${TAP_Y}" >/dev/null 2>&1; then
        DELIVERED_TAPS=$((DELIVERED_TAPS + 1))
      fi
      sleep 1
    done
    H shell "snapshot_display -f /data/local/tmp/ab-taps.jpeg" >/dev/null 2>&1 || true
    PREV_T=14
  fi
done

# ── 5. 注入点击（M15）─────────────────────────────────────────────────────
if [ "${CHECKPOINT_TAPS}" != 1 ]; then
  echo "== 注入点击 ×5"
  for i in 1 2 3 4 5; do
    MARK "TOUCH_${i}"
    if H shell "uitest uiInput click ${TAP_X} ${TAP_Y}" >/dev/null 2>&1 || \
        H shell "uinput -T -c ${TAP_X} ${TAP_Y}" >/dev/null 2>&1; then
      DELIVERED_TAPS=$((DELIVERED_TAPS + 1))
    fi
    sleep 1.2
  done
  H shell "snapshot_display -f /data/local/tmp/ab-taps.jpeg" >/dev/null 2>&1 || true
fi
printf 'requested=5\ndelivered=%s\nx=%s\ny=%s\n' \
  "${DELIVERED_TAPS}" "${TAP_X}" "${TAP_Y}" > "${RUN}/touches.env"
sleep 3

# ── 6. 收 trace + 日志 + 截图 ────────────────────────────────────────────
echo "== 收 hitrace"
if [ -n "${LIFETIME_SAMPLER_HOST_PID}" ]; then
  wait "${LIFETIME_SAMPLER_HOST_PID}" || true
fi
MARK RUN_END
H shell "for f in /sys/kernel/tracing/per_cpu/cpu*/stats; do echo ===\$f; cat \$f; done" \
  2>&1 | tr -d '\r' > "${RUN}/trace-stats.txt" || true
H shell "hitrace --trace_finish -o /data/local/tmp/ab.ftrace" 2>&1 | tr -d '\r' | tail -3 \
  > "${RUN}/trace-finish.txt"
H file recv /data/local/tmp/ab.ftrace "${RUN}/framework.ftrace" 2>&1 | tr -d '\r' | tail -1
cleanup_graphics_uprobes

H shell "hilog -x > /data/local/tmp/ab-hilog.log 2>&1" >/dev/null 2>&1 || true
H file recv /data/local/tmp/ab-hilog.log "${RUN}/hilog.log" >/dev/null 2>&1 || true
H shell "find /data/log/faultlog -type f 2>/dev/null | sort" 2>/dev/null \
  | tr -d '\r' > "${RUN}/faultlogs-after.txt" || true
comm -13 "${RUN}/faultlogs-before.txt" "${RUN}/faultlogs-after.txt" \
  > "${RUN}/faultlogs-new.txt" || true
while IFS= read -r faultlog; do
  [ -n "${faultlog}" ] || continue
  fault_name=$(basename "${faultlog}")
  H file recv "${faultlog}" "${RUN}/faultlog-${fault_name}" >/dev/null 2>&1 || true
done < "${RUN}/faultlogs-new.txt"
for t in 3 9 15; do
  H file recv "/data/local/tmp/ab-t${t}.jpeg" "${RUN}/screen-t${t}.jpeg" >/dev/null 2>&1 || true
done
H file recv /data/local/tmp/ab-taps.jpeg "${RUN}/screen-after-taps.jpeg" >/dev/null 2>&1 || true

# ── 7. 观测面统计（唯一真源是 analyze-trace.py：按发出进程归属，不做全局计数）──
FT="${RUN}/framework.ftrace"
APP_PID=$(awk '{print $2}' "${RUN}/proc-t3.txt" 2>/dev/null | head -1)
if [ -z "${APP_PID}" ] && [ -s "${RUN}/first-pid.txt" ]; then
  APP_PID=$(head -1 "${RUN}/first-pid.txt")
fi
if [ -s "${FT}" ]; then
  "${REPO_ROOT}/src/tools/zigzag/analyze-trace.py" "${FT}" \
    ${APP_PID:+--app-pid "${APP_PID}"} --out "${RUN}/OBSERVABILITY.md"
else
  printf '# 框架层观测面\n\n**framework.ftrace 为空 —— 本轮框架层全部记 `—`（无观测能力），不得记 `✗`。**\n' \
    > "${RUN}/OBSERVABILITY.md"
fi

echo
echo "== run 目录: ${RUN}"
echo "== ftrace: $(ls -lh "${FT}" 2>/dev/null | awk '{print $5}' || echo 缺)"
echo "== 本记录不含「成功 / 通过」结论（§6.1）；无输出的格子记 —，不得记 ✗（§6.3）"
if [ "${LAUNCH_VALID}" != 1 ]; then
  echo "== INVALID_LAUNCH：目标进程未出现，本轮只能用于诊断桌面启动，不能进入 A/B 清单" >&2
  exit 3
fi
