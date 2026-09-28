#!/bin/bash
# _kimi.yue.fn04-07-lifecycle.sh
# Lifecycle lane: end-to-end concept lifecycle for Fn04/Fn05/Fn06/Fn07
# until unit tests and on-device verification complete.
# Run this in its own terminal window for isolation (launched by _kimi.yue.sh).
set -euo pipefail

WORKDIR="/opt/Bridge"
KIMI_BIN="/Users/alexyang/.kimi-code/bin/kimi"
LOG="${WORKDIR}/evidence/runs/_kimi.yue.fn04-07-lifecycle.log"
ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_kimi.yue.env"

# 模型/API 凭据注入：默认 ~/.kimi-code 无 default_model，headless 必须显式提供。
[ -f "${ENV_FILE}" ] && . "${ENV_FILE}"

mkdir -p "$(dirname "$LOG")"

cd "$WORKDIR"

exec > >(tee -a "$LOG") 2>&1

# 注意：当前 kimi CLI 版本不允许 --auto/-y 与 -p 组合；headless -p 模式默认自动执行工具调用。
"${KIMI_BIN}" -p "$(cat <<'PROMPT'
你是 Bridge 项目（AOSP-on-OpenHarmony 适配层，仓库根 /opt/Bridge）的 Concept 生命周期推进 agent。

目标：端到端推进 Fn04（Window/Surface/Rendering）、Fn05（输入）、Fn06（Intent/Task）、Fn07（Android Service）四个 Concept Domain 的生命周期，直到其中的 Action 完成设计、实现、host 单元测试与真机验证。

硬性要求：

1. 严格遵守 /opt/Bridge/AGENTS.md：mono-branch（直接提交 main，不建长期分支）、Fn/C/A 语义层次、四域一致（docs/spec/evidence/src）、证据纪律。
2. 先阅读 docs/progress.md、docs/atom.md 和目标 Fn 的 docs/concepts/FnXX/ 了解当前状态，从成熟度最低、无依赖阻塞的 Action 开始。
3. 按阶段使用项目技能：br-concept-research → br-concept-decide → br-action-design → br-action-implement → br-unit-test → br-action-verify；单个 Action 的端到端流程可用 br-atom-lifecycle 编排。
4. 单元测试先在 host 侧真实跑通并留下运行证据，再进入真机验证；真机验证按 br-action-verify 执行正向/负向/失败用例并保存原始证据。
5. 每个 Action 的最终 PASS 必须由未参与实现的独立核验给出；你作为实现者只能提交原始证据和自测，不得自行声明 PASS。
6. 所有验收结论必须链接 var/evidence/ 下可复核的运行证据；任何 atom/design/verification hash 变化使旧 verdict 失效。
7. 一次只推进一个 Action 的一个阶段，完成并记录后再进入下一个；遇到设备不可用等外部阻塞时，明确记录 BLOCK 并转推进其他不受阻的 Action，不要空等。
8. 不要修改与本任务无关的文件；不要 force-push 或删除他人分支。

现在开始：先做现状勘察并给出 Fn04–Fn07 的推进顺序计划，然后立即开始第一个 Action 的第一阶段。
PROMPT
)"

exec bash
