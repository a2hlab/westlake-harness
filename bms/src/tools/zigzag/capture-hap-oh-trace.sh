#!/usr/bin/env bash
# capture-oh-trace.sh — ② 线**框架层** trace 采集（capture-oh.sh 的补层）。
#
# 为什么要另开一层：ab-compare-plan.md §5 已实证，应用自己的代码只看得见
# M04 / M06 / M15 一小段，**M08–M14 全程在框架和宿主手里**。capture-oh.sh 采的是
# 应用层（hilog 的 ABCMP MILESTONE + 截图），恰好看不到出问题的那一段。
# 本脚本开鸿蒙自带 hitrace，把框架侧那段补上——零改码，只开开关。
#
# 产物只落 var/evidence/oh-native-control/（§6.1 目录隔离，验收工具不读此目录）。
# 本脚本**不产出「成功 / 通过」结论**（§6.1 产物限定），只产出可判定/不可判定的观测面。
#
# 用法:
#   ./capture-oh-trace.sh [hap路径]     # 默认 dist/zigzag-control-fmtfix.hap（B 态）
#   OH_TARGET=<序列号> ./capture-oh-trace.sh
#   SKIP_INSTALL=1 ./capture-oh-trace.sh   # 板上已装同一件时跳过装机
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"

HAP="${1:-${REPO_ROOT}/src/vendor/samples/haps/ZigZag/dist/zigzag-control-fmtfix.hap}"
[ -f "${HAP}" ] || HAP="${REPO_ROOT}/HAPS/ZigZag/dist/zigzag-control-fmtfix.hap"
BN=com.a2hlab.control.zigzag
ABILITY=TuanjiePlayerAbility

# ── hitrace tag 集：按 §4 里程碑逐个挑，不是「全开」──────────────────────
# 全开会把 buffer 冲爆（§5 实测 6 秒 38,493 条），且引入大量与里程碑无关的噪声。
# 每个 tag 后面注明它覆盖哪几格，删 tag 前先确认对应里程碑不再需要。
TRACE_TAGS=(
  ark               # M03 运行时就绪（方舟运行时）
  app               # M04 应用入口被调
  ability           # M05 派发 / M06 onCreate / **M14 前台报到完成**
  ffrt              # M07 消息循环（FFRT 任务）
  window            # M08 应用要窗口 / M09 宿主给窗口
  ace               # M10 首次测量 / M11 首次绘制（ArkUI）
  graphic           # M11–M13 绘制→提交→上屏
  multimodalinput   # M15 触摸送达
  ohos              # 系统通用，兜底
  binder rpc        # 跨进程因果链（应用↔AMS↔RS），用于把上面各段串起来
  sched             # 调度，用于区分「没做」与「被抢占没轮到」
)
# 缓冲区：§5 实测 6 秒近 4 万条；本轮窗口约 40 秒，取 128MB 留足余量。
# 溢出会**静默丢最早的事件**——恰好丢掉启动段，故宁大勿小。
TRACE_BUF_KB=131072

die() { echo "错误：$*" >&2; exit 1; }

[ -f "${HAP}" ] || die "缺 ${HAP}：先 ./build.sh openharmony 或 fmtfix/apply-fmtfix.sh"

if [ -n "${OH_TARGET:-}" ]; then
  BOARD="${OH_TARGET}"
else
  BOARD=$(hdc list targets 2>/dev/null | tr -d '\r' | grep -v '^\[Empty\]$' | grep -v '^$' | head -1)
fi
[ -n "${BOARD}" ] || die "无连接板（hdc list targets 为空）"
H() { hdc -t "${BOARD}" "$@"; }

TS=$(date +%Y%m%d-%H%M%S)
RUN="${REPO_ROOT}/var/evidence/oh-native-control/ZigZag/runs/${TS}-${BOARD:0:4}-trace"
mkdir -p "${RUN}"

APP_SHA=$(shasum -a 256 "${HAP}" | awk '{print $1}')
ROM=$(H shell "param get const.ohos.fullname" 2>/dev/null | tr -d '\r' | tr -d ' ')

echo "== 环境戳（§6.4：任一项变化则本轮清单自动过期）"
printf '  ROM=%s\n  板=%s\n  应用=%s\n' "${ROM}" "${BOARD}" "${APP_SHA}" | tee "${RUN}/envstamp.txt"

# ── 0. 常亮：M13 判据是屏幕真实像素，息屏会把「没上屏」和「屏幕关了」混为一谈 ──
echo "== 常亮"
"${REPO_ROOT}/src/tools/devices/keep-awake.sh" on harmony >/dev/null 2>&1 || \
  echo "  警告：keep-awake 失败，截图可能拍到息屏黑屏——本轮 M13 判定须记 —（不可判定）"

# ── 1. 装机 ──────────────────────────────────────────────────────────────
if [ "${SKIP_INSTALL:-0}" = "1" ]; then
  echo "== 跳过装机（SKIP_INSTALL=1）"
  echo "skipped (SKIP_INSTALL=1)" > "${RUN}/install.txt"
else
  echo "== 装机 ${BN}"
  H file send "${HAP}" /data/local/tmp/zz-trace.hap 2>&1 | tr -d '\r' | tail -1
  H shell "bm install -p /data/local/tmp/zz-trace.hap" 2>&1 | tr -d '\r' | tee "${RUN}/install.txt"
  grep -qi 'success' "${RUN}/install.txt" || die "安装失败，详见 ${RUN}/install.txt"
fi

# ── 2. 强杀旧进程：不冷启动就采不到 M01–M09 ──────────────────────────────
# 实证（20260807-231552 那轮）：应用已在运行时 `aa start` 只是拉到前台，窗口创建
# 早在开 trace 之前就完成了，M08/M09 因此恒为 0——那是「事件不在这段 trace 里」，
# 与「事件没发生」完全不同（§6.3）。故必须先杀干净再采。
echo "== 强杀旧进程（保证冷启动）"
H shell "aa force-stop ${BN}" 2>&1 | tr -d '\r' | tee "${RUN}/force-stop.txt" || true
sleep 2
if H shell "ps -ef | grep '${BN}' | grep -v grep" 2>/dev/null | tr -d '\r' | grep -q .; then
  echo "  警告：强杀后进程仍在，本轮 M01–M09 可能仍是热启动，判定须记 —" \
    | tee -a "${RUN}/force-stop.txt"
fi

# ── 3. 起 trace（必须在起应用之前，否则丢掉整个启动段）────────────────────
echo "== 起 hitrace：${TRACE_TAGS[*]}"
H shell "hitrace --trace_finish_nodump >/dev/null 2>&1" >/dev/null 2>&1 || true  # 清残留会话
H shell "hitrace --trace_begin -b ${TRACE_BUF_KB} ${TRACE_TAGS[*]}" 2>&1 | tr -d '\r' | tee "${RUN}/trace-begin.txt"
sleep 1

# ── 4. 清日志 → 起应用 ───────────────────────────────────────────────────
H shell "hilog -r" >/dev/null 2>&1 || true
echo "== 启动"
LAUNCH_T0=$(H shell "cat /proc/uptime" 2>/dev/null | tr -d '\r' | awk '{print $1}')
H shell "aa start -b ${BN} -m entry -a ${ABILITY}" 2>&1 | tr -d '\r' | tee "${RUN}/launch.txt"
echo "launch_uptime=${LAUNCH_T0}" >> "${RUN}/launch.txt"

sleep 8
H shell "snapshot_display -f /data/local/tmp/t1.jpeg" >/dev/null 2>&1
H shell "ps -ef | grep '${BN}' | grep -v grep" 2>&1 | tr -d '\r' > "${RUN}/proc-after-launch.txt" || true

# ── 5. 注入点击（M15）─────────────────────────────────────────────────────
echo "== 注入点击 ×5"
for i in 1 2 3 4 5; do
  H shell "uitest uiInput click 600 1200" >/dev/null 2>&1 || H shell "uinput -T -c 600 1200" >/dev/null 2>&1 || true
  sleep 1.2
done
H shell "snapshot_display -f /data/local/tmp/t2.jpeg" >/dev/null 2>&1
sleep 4

# ── 6. 收 trace ──────────────────────────────────────────────────────────
echo "== 收 hitrace"
H shell "hitrace --trace_finish -o /data/local/tmp/zz.ftrace" 2>&1 | tr -d '\r' | tail -3 | tee "${RUN}/trace-finish.txt"
H file recv /data/local/tmp/zz.ftrace "${RUN}/framework.ftrace" 2>&1 | tr -d '\r' | tail -1

# ── 7. 收应用层 + 截图 ───────────────────────────────────────────────────
H shell "hilog -x" 2>/dev/null | tr -d '\r' | grep 'ABCMP MILESTONE' > "${RUN}/milestones-app.log" || true
H shell "hilog -x" 2>/dev/null | tr -d '\r' | tail -3000 > "${RUN}/hilog-tail.log" || true
H file recv /data/local/tmp/t1.jpeg "${RUN}/1-after-launch.jpeg" >/dev/null 2>&1 || true
H file recv /data/local/tmp/t2.jpeg "${RUN}/2-after-taps.jpeg" >/dev/null 2>&1 || true

# ── 8. 观测面统计 ────────────────────────────────────────────────────────
# 交给 analyze-trace.py 做（唯一真源）：它按**发出进程**归属命中，而不是全局计数。
# 全局计数会把系统其他应用触发的合成活动记到本应用头上——§6.1 要防的正是这种偷换。
FT="${RUN}/framework.ftrace"
APP_PID=$(awk '{print $2}' "${RUN}/proc-after-launch.txt" 2>/dev/null | head -1)
if [ -s "${FT}" ]; then
  "${SCRIPT_DIR}/analyze-trace.py" "${FT}" ${APP_PID:+--app-pid "${APP_PID}"} --out "${RUN}/OBSERVABILITY.md"
else
  printf '# ② 线框架层观测面\n\n**framework.ftrace 为空或缺失 —— 本轮框架层全部记 `—`（无观测能力），不得记 `✗`。**\n' \
    > "${RUN}/OBSERVABILITY.md"
fi
{
  echo
  echo "## 应用层 ABCMP MILESTONE（L1，会说谎）"
  echo '```'
  sed -e 's/^/  /' "${RUN}/milestones-app.log" 2>/dev/null | head -40 || echo "  (空)"
  echo '```'
} >> "${RUN}/OBSERVABILITY.md"

cat > "${RUN}/RUN.md" <<EOF
# ② 线框架层 trace 采集 run（ZigZag 引擎档对照件 · B 态 fmtfix）

- 环境戳: ROM=${ROM} 板=${BOARD} 应用=${APP_SHA}
- 时间: ${TS}
- 流程: [常亮] → hitrace --trace_begin → bm install → aa start → 截图 → 注入点击×5 → 截图 → trace_finish → 收割
- 层次: 应用层 milestones-app.log（L1，会说谎）+ 框架层 framework.ftrace（L2）+ 截图（L3）
- 观测面统计: OBSERVABILITY.md
- **纪律**: 本记录不含任何「成功 / 通过」结论（§6.1 产物限定）；
  唯一合法下游产物是缺步清单。框架层无输出的格子一律记 \`—\`（无观测能力），
  **不得记 \`✗\`**（§6.3）。
EOF

echo
echo "== run 目录: ${RUN}"
echo "== ftrace 大小: $(ls -lh "${FT}" 2>/dev/null | awk '{print $5}' || echo 缺)"
echo "== 应用层里程碑行数: $(wc -l < "${RUN}/milestones-app.log" 2>/dev/null | tr -d ' ' || echo 0)"
