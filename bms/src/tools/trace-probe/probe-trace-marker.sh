#!/usr/bin/env bash
# probe-trace-marker.sh — 双端探针：同一条 Android atrace 字节格式，分别用
# 安卓 atrace 与鸿蒙 hitrace 抓取，验证"框架层零改码观测"路是否成立。
#
# 背景：AOSP 的 ATRACE_* 与 OH 的 HITRACE_* 最终都写内核 ftrace 的 trace_marker
# 节点。若两边节点路径、权限、字节格式一致，则 Bridge 进程里 AOSP 自带的编译期
# 打点无需任何代码改动即可落进鸿蒙 trace。本脚本给出可复跑的判据。
#
# 用法:
#   ./probe-trace-marker.sh android [evidence_dir]
#   ./probe-trace-marker.sh harmony [evidence_dir]
#   ./probe-trace-marker.sh both    [evidence_dir]
set -euo pipefail

PROBE_TAG="ATRACE_WIRE_FORMAT_PROBE"
NODE_OH=/sys/kernel/debug/tracing/trace_marker
NODE_AN=/sys/kernel/tracing/trace_marker
MODE="${1:?usage: probe-trace-marker.sh <android|harmony|both> [evidence_dir]}"
EV="${2:-}"

# 写入的三条探针：Android atrace 的原生 wire format（begin / counter / end）
markers() { # $1=node
  echo "echo \"B|1234|$PROBE_TAG\" > $1; echo \"C|1234|probe_counter|42\" > $1; echo \"E|1234\" > $1"
}

probe_harmony() {
  local out="${1:-/tmp}"; mkdir -p "$out"
  echo "== [鸿蒙] 节点与权限"
  hdc shell "ls -la $NODE_OH $NODE_AN 2>&1" | tr -d '\r' | tee "$out/oh-node-perms.txt"
  echo "== [鸿蒙] 起 hitrace → 写 Android 格式探针 → 收"
  hdc shell "hitrace --trace_begin -b 4096 app ohos" >/dev/null 2>&1
  sleep 1
  hdc shell "$(markers $NODE_OH); echo wrote" | tr -d '\r'
  sleep 1
  hdc shell "hitrace --trace_finish -o /data/local/tmp/probe_oh.ftrace" >/dev/null 2>&1
  hdc file recv /data/local/tmp/probe_oh.ftrace "$out/oh-probe.ftrace" >/dev/null 2>&1 || true
  echo "== [鸿蒙] 命中："
  hdc shell "grep -m3 -E '$PROBE_TAG|probe_counter' /data/local/tmp/probe_oh.ftrace" | tr -d '\r' \
    | tee "$out/oh-hit.txt"
  echo "== [鸿蒙] tag 位分配（抓取中）"
  for c in graphic ohos app; do
    hdc shell "hitrace --trace_begin -b 2048 $c >/dev/null 2>&1" >/dev/null 2>&1
    v=$(hdc shell "param get debug.hitrace.tags.enableflags" 2>/dev/null | tr -d '\r ' | head -1)
    hdc shell "hitrace --trace_finish_nodump >/dev/null 2>&1" >/dev/null 2>&1
    echo "  $c = $v"
  done | tee "$out/oh-tagbits.txt"
}

probe_android() {
  local out="${1:-/tmp}"; mkdir -p "$out"
  echo "== [安卓] 节点与权限"
  adb shell "ls -la $NODE_AN 2>&1" | tr -d '\r' | tee "$out/android-node-perms.txt"
  echo "== [安卓] 起 atrace → 写同一条探针 → 收"
  adb shell "atrace --async_start -b 4096 -c gfx view" >/dev/null 2>&1
  sleep 1
  adb shell "$(markers $NODE_AN); echo wrote" | tr -d '\r'
  sleep 1
  adb shell "atrace --async_stop > /data/local/tmp/probe_android.ftrace 2>/dev/null" >/dev/null 2>&1
  adb pull /data/local/tmp/probe_android.ftrace "$out/android-probe.ftrace" >/dev/null 2>&1 || true
  echo "== [安卓] 命中："
  adb shell "grep -m3 -E '$PROBE_TAG|probe_counter' /data/local/tmp/probe_android.ftrace" | tr -d '\r' \
    | tee "$out/android-hit.txt"
  echo "== [安卓] tag 位分配（抓取中）"
  adb shell "atrace --async_start -b 2048 gfx >/dev/null 2>&1; getprop debug.atrace.tags.enableflags; atrace --async_stop >/dev/null 2>&1" \
    | tr -d '\r' | sed 's/^/  gfx = /' | tee "$out/android-tagbits.txt"
}

case "$MODE" in
  harmony) probe_harmony "$EV" ;;
  android) probe_android "$EV" ;;
  both)    probe_android "$EV"; echo; probe_harmony "$EV" ;;
  *) echo "usage: probe-trace-marker.sh <android|harmony|both> [evidence_dir]" >&2; exit 1 ;;
esac
