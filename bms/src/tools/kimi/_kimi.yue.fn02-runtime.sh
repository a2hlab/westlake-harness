#!/bin/bash
# _kimi.yue.fn02-runtime.sh
# Fn02 runtime lane: host-side wall root-cause analysis + concept lifecycle.
# Complements the remote Fn02 machine; does NOT grab device windows.
# Run this in its own terminal window for isolation.
set -euo pipefail

WORKDIR="/opt/Bridge"
KIMI_BIN="/Users/alexyang/.kimi-code/bin/kimi"
LOG="${WORKDIR}/evidence/runs/_kimi.yue.fn02-runtime.log"
ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_kimi.yue.env"

[ -f "${ENV_FILE}" ] && . "${ENV_FILE}"

mkdir -p "$(dirname "$LOG")"

cd "$WORKDIR"

exec > >(tee -a "$LOG") 2>&1

"${KIMI_BIN}" -p "$(cat <<'PROMPT'
你是 Bridge 项目（AOSP-on-OpenHarmony 适配层，仓库根 /opt/Bridge）的 Fn02 runtime 攻关 lane。Fn02（进程、Runtime、JNI 与 Native）是全项目关键路径：六个域的设备验证堵在 appspawn-x fork 墙、SELinux 与 runtime artifact 闭包上（见 docs/audits/2026-07-27-bottleneck-analysis.md 与 docs/workflows/improvement-backlog-20260727.md 的 B-01/B-02/B-03）。

你的任务（按序，全部 host 侧先行）：

1. 现状勘察：读 docs/progress.md 中 Fn02 与 appspawn-x 相关段落、docs/atom.md 的 Fn02.A01–A18、var/evidence/runs/ 最近 3 天的 fn01-fn03-r18-runtime-deploy 与 fn03-r1-route-a 系列 run 记录、backlog B-01/B-02/B-03 条目。给出三堵墙各自的当前事实清单（哪些板上什么状态、最近 run 的 verdict）。
2. B-01 fork 墙源码级根因分析：从 /opt/Bridge/src/adapter 与 src/AlexBridge 出发，追踪 appspawn-x parent→child fork 路径（含 ChildMain::run 的 fail-closed legacy 入口、stock Route A receipt producer build_pending 的现状），给出源码级根因假设树，每条假设标注可用 host 实验证伪的方法。不得无证据断言。
3. B-02 runtime artifact 闭包：盘点一个完整可持久的 /system/android 闭包需要哪些 artifact（参照 61b0 缺 lib64 的事故与 654b 基线证据 var/evidence/atoms/Fn01/A04/runs/20260728T012642Z-d600-runtime-baseline/），产出闭包清单与缺口表。
4. B-03 SELinux：审计 device file_contexts 覆盖（654B 缺 lib64 标签先例），列出 Enforcing 下安装/执行链路的标签需求。
5. 若以上有产出，按 br-concept-research/br-concept-decide 的纪律把 Fn02 相关 Action 的分析登记进对应四域目录；P/N/F 契约与实现授权未到时，只产 route-labelled 分析，不写产品代码。

硬性约束：

- 不独占设备：61b0/654b 今晚有 Fn01/Fn03 lane 在用。任何设备操作前先检查 var/evidence/runs/ 最近 30 分钟是否有其他 lane 的 run 在使用目标板；有则跳过设备步骤继续做 host 工作，并把设备需求记录为 DEVICE_WINDOW_REQUEST（写进你的日志与交接）。
- 另一台机器上有并行 Fn02 工作（owner 直接管理）：你的产出以"分析/清单/可证伪假设"为主，避免与其重复做同一件事；发现重叠时在交接里注明。
- 遵守 AGENTS.md：证据纪律、不得自行声明 PASS、不修改与本任务无关的文件、不做 git commit/push。
- 所有产出写入对应 var/evidence/ 或 docs/atoms/Fn02/ 目录，并在日志里记录每项产出的路径。
- 中文备注要求（owner 2026-07-28）：所有产出文档、证据 README、分析结论、实验记录与交接说明正文一律用中文；代码标识符、命令、路径、日志原文、错误码保持原样；英文日志引用后附一句中文解读。

现在开始第 1 步勘察。
PROMPT
)"

exec bash
