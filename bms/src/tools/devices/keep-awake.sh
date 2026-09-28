#!/usr/bin/env bash
# keep-awake.sh — 让安卓机与鸿蒙板在采集期间保持亮屏解锁，并可一键还原。
#
# 为什么需要它：ab-compare-plan.md §4 把 M13「首帧上屏」定为 L3 级证据——判据是
# 屏幕真实像素。若设备在采集途中息屏，截图拍到的黑屏与「应用根本没上屏」在证据里
# 长得一模一样，直接触犯 §6.3「不许把『我们没看见』写成『它没发生』」。
# 故所有 ①②③ 线采集**开始前**必须先跑本脚本。
#
# 用法：
#   ./keep-awake.sh on   [android|harmony|both]   # 常亮（默认 both）
#   ./keep-awake.sh off  [android|harmony|both]   # 还原设备默认
#   ./keep-awake.sh show [android|harmony|both]   # 只看当前状态，不改
#
# 设备选择：默认自动取当前唯一在线设备；多设备时用环境变量指定
#   ANDROID_SERIAL=<adb序列号>  OH_TARGET=<hdc序列号>
set -euo pipefail

ACTION="${1:-show}"
SCOPE="${2:-both}"

# 安卓 stay_on_while_plugged_in 位掩码：AC(1)|USB(2)|WIRELESS(4) = 7，任何供电方式都不息屏
readonly ANDROID_STAYON_ALL=7
# 安卓 screen_off_timeout 上限（int32 max，约 24.8 天）
readonly ANDROID_TIMEOUT_MAX=2147483647
# 鸿蒙 power-shell timeout 覆盖值（毫秒）；OH 不接受 int32 max，取 24 小时足够一轮采集
readonly OH_TIMEOUT_MS=86400000

die() { echo "错误：$*" >&2; exit 1; }

# ── 设备解析 ─────────────────────────────────────────────────────────────
resolve_android() {
  if [[ -n "${ANDROID_SERIAL:-}" ]]; then echo "${ANDROID_SERIAL}"; return; fi
  local list
  list=$(adb devices | awk '$2=="device"{print $1}')
  [[ -z "${list}" ]] && die "没有在线的安卓设备（adb devices 为空）"
  [[ $(echo "${list}" | wc -l) -gt 1 ]] && die "安卓设备多于一台，请设 ANDROID_SERIAL：
${list}"
  echo "${list}"
}

resolve_oh() {
  if [[ -n "${OH_TARGET:-}" ]]; then echo "${OH_TARGET}"; return; fi
  local list
  list=$(hdc list targets 2>/dev/null | tr -d '\r' | grep -v '^\[Empty\]$' | grep -v '^$')
  [[ -z "${list}" ]] && die "没有在线的鸿蒙设备（hdc list targets 为空）"
  [[ $(echo "${list}" | wc -l) -gt 1 ]] && die "鸿蒙设备多于一台，请设 OH_TARGET：
${list}"
  echo "${list}"
}

# ── 安卓侧 ───────────────────────────────────────────────────────────────
android_show() {
  local s="$1"
  echo "── 安卓 ${s}"
  adb -s "${s}" shell "
    echo \"  wakefulness      = \$(dumpsys power | sed -n 's/.*mWakefulness=\([A-Za-z]*\).*/\1/p' | head -1)\"
    echo \"  screen_off_timeout = \$(settings get system screen_off_timeout)\"
    echo \"  stay_on_while_plugged_in = \$(settings get global stay_on_while_plugged_in)\"
  " 2>/dev/null | tr -d '\r'
}

android_on() {
  local s="$1"
  echo "── 安卓 ${s}：开常亮"
  # svc power stayon 与 settings 双管：前者对部分 ROM 更可靠，后者可被 show 读回核验
  adb -s "${s}" shell "svc power stayon true" 2>/dev/null | tr -d '\r' || true
  adb -s "${s}" shell "settings put global stay_on_while_plugged_in ${ANDROID_STAYON_ALL}" 2>/dev/null || true
  adb -s "${s}" shell "settings put system screen_off_timeout ${ANDROID_TIMEOUT_MAX}" 2>/dev/null || true
  # 已息屏则唤醒；KEYCODE_WAKEUP 幂等，屏已亮时无副作用（不同于 KEYCODE_POWER 的开关切换）
  adb -s "${s}" shell "input keyevent KEYCODE_WAKEUP" 2>/dev/null || true
  adb -s "${s}" shell "wm dismiss-keyguard" 2>/dev/null || true
  android_show "${s}"
}

android_off() {
  local s="$1"
  echo "── 安卓 ${s}：还原"
  adb -s "${s}" shell "svc power stayon false" 2>/dev/null || true
  adb -s "${s}" shell "settings put global stay_on_while_plugged_in 0" 2>/dev/null || true
  adb -s "${s}" shell "settings put system screen_off_timeout 60000" 2>/dev/null || true
  android_show "${s}"
}

# ── 鸿蒙侧 ───────────────────────────────────────────────────────────────
oh_show() {
  local t="$1"
  echo "── 鸿蒙 ${t}"
  # power-shell dump 输出较长，只取与息屏时间和电源态相关的行
  hdc -t "${t}" shell "power-shell dump" 2>/dev/null | tr -d '\r' \
    | grep -iE "state|timeout|screen|display" | head -12 | sed 's/^/  /' || true
}

oh_on() {
  local t="$1"
  echo "── 鸿蒙 ${t}：开常亮"
  # wakeup 先亮屏；OH 的 wakeup 在已亮屏时是空操作
  hdc -t "${t}" shell "power-shell wakeup" 2>/dev/null | tr -d '\r' || true
  # timeout -o 覆盖息屏时长（-r 恢复）；这是 OH 唯一不需 root 的息屏控制入口
  hdc -t "${t}" shell "power-shell timeout -o ${OH_TIMEOUT_MS}" 2>/dev/null | tr -d '\r' || true
  # setmode 602 = PERFORMANCE，避免省电策略在采集中途降频或压制合成
  hdc -t "${t}" shell "power-shell setmode 602" 2>/dev/null | tr -d '\r' || true
  oh_show "${t}"
}

oh_off() {
  local t="$1"
  echo "── 鸿蒙 ${t}：还原"
  hdc -t "${t}" shell "power-shell timeout -r" 2>/dev/null | tr -d '\r' || true
  hdc -t "${t}" shell "power-shell setmode 600" 2>/dev/null | tr -d '\r' || true
  oh_show "${t}"
}

# ── 主流程 ───────────────────────────────────────────────────────────────
case "${SCOPE}" in
  android|harmony|both) ;;
  *) die "范围只能是 android / harmony / both，收到：${SCOPE}" ;;
esac

do_android=0; do_oh=0
[[ "${SCOPE}" == "android" || "${SCOPE}" == "both" ]] && do_android=1
[[ "${SCOPE}" == "harmony" || "${SCOPE}" == "both" ]] && do_oh=1

case "${ACTION}" in
  on|off|show) ;;
  *) die "动作只能是 on / off / show，收到：${ACTION}" ;;
esac

if [[ ${do_android} -eq 1 ]]; then
  ASER=$(resolve_android)
  case "${ACTION}" in
    on)   android_on   "${ASER}" ;;
    off)  android_off  "${ASER}" ;;
    show) android_show "${ASER}" ;;
  esac
  echo
fi

if [[ ${do_oh} -eq 1 ]]; then
  OSER=$(resolve_oh)
  case "${ACTION}" in
    on)   oh_on   "${OSER}" ;;
    off)  oh_off  "${OSER}" ;;
    show) oh_show "${OSER}" ;;
  esac
fi
