#!/bin/bash
# _kimi.yue.ilane.sh — 交互式 lane 启动器（Fn01/Fn03 模式：TUI 底部输入框可互动）
# 用法: _kimi.yue.ilane.sh <任务书.md路径> [窗口bounds: "x1 y1 x2 y2"]
# 行为: 打开 iTerm 窗口 → 启动交互式 kimi --auto → 注入一行引导语让 agent 读任务书执行。
# 之后你可以随时在窗口底部输入框插话指挥该 lane。
set -euo pipefail

PROMPT_FILE="${1:?用法: _kimi.yue.ilane.sh <任务书.md路径> [bounds]}"
BOUNDS="${2:-}"
BOUNDS_CSV="$(echo "${BOUNDS}" | tr ' ' ',')"
KICK="阅读 ${PROMPT_FILE} 并严格按照其执行。产出与交接一律中文备注。"

osascript <<EOF
tell application "iTerm"
	activate
	set newWindow to (create window with default profile command "bash -c 'source /opt/Bridge/_kimi.yue.env; cd /opt/Bridge; exec /Users/alexyang/.kimi-code/bin/kimi --auto'")
	delay 6
	tell current session of newWindow to write text "${KICK}"
	$(if [ -n "${BOUNDS}" ]; then echo "	set bounds of newWindow to {${BOUNDS_CSV}}"; fi)
	log "interactive lane window id " & (id of newWindow as string)
end tell
EOF
