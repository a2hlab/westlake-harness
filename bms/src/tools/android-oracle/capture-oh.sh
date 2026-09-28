#!/usr/bin/env bash
# OH 侧行为采集 —— capture-genshin-golden.sh 的对照版本
#
# 目的：在 D600 上跑与安卓侧**完全相同**的操作，产出**同格式**的事件序列，
#       供 diff-events.py 与安卓基准逐条比对，算出这一层的欠账数。
#
# 事件格式（与安卓侧一致，只记顺序不记绝对时间）：
#   seq,pid,tid,name,effect,ts_order_only
#
# 用法：
#   export SERIAL=5ce1227d00000000000000000923012c
#   export BUNDLE=com.westlake.glxc2
#   export ABILITY=EntryAbility
#   bash src/tools/android-oracle/capture-oh.sh
#
# 红线（照抄全局约定，脚本内自我约束）：
#   - 绝不 reboot 板子；绝不 wipe / flash
#   - 绝不按名字批量 kill；只按确切 PID 收自己起的进程
#   - 板上缺命令时硬失败并写清缺什么，不走静默兜底（假报警曾导致整轮白干）
set -euo pipefail

HDC="${HDC:-hdc}"
SERIAL="${SERIAL:-}"
BUNDLE="${BUNDLE:?必须指定 BUNDLE，例：com.westlake.glxc2}"
ABILITY="${ABILITY:-EntryAbility}"
OUTDIR="${OUTDIR:-/tmp/oh-oracle/run-$(date +%Y%m%d-%H%M%S)}"
DURATION_SEC="${DURATION_SEC:-180}"

command -v "$HDC" >/dev/null 2>&1 || { echo "FATAL: 找不到 hdc（设 HDC=...）" >&2; exit 2; }

HDC_CMD=("$HDC")
[[ -n "$SERIAL" ]] && HDC_CMD+=(-t "$SERIAL")

sh_() { "${HDC_CMD[@]}" shell "$@"; }

mkdir -p "$OUTDIR"/{hilog,strace,screen,meta,events}
echo "OUTDIR=$OUTDIR"

# ---------- 环境与身份 ----------
{
  echo "time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "serial=${SERIAL:-<default>}"
  echo "bundle=$BUNDLE"
  echo "ability=$ABILITY"
  sh_ 'param get const.ohos.fullname 2>/dev/null || true'
  sh_ 'param get const.product.model 2>/dev/null || true'
  sh_ 'param get const.ohos.apiversion 2>/dev/null || true'
  sh_ 'uname -a'
  sh_ 'id'
} | tee "$OUTDIR/meta/device.txt"

# ---------- 门禁 5：依赖的命令必须真实存在，缺了硬失败 ----------
MISSING=""
for c in hilog aa bm; do
  sh_ "command -v $c >/dev/null 2>&1" || MISSING="$MISSING $c"
done
if [[ -n "$MISSING" ]]; then
  echo "FATAL: 板上缺命令:$MISSING —— 拒绝走兜底分支（静默兜底曾导致假报警+假回滚）" >&2
  echo "missing:$MISSING" > "$OUTDIR/meta/MISSING_TOOLS.txt"
  exit 4
fi
HAS_STRACE=0
sh_ 'command -v strace >/dev/null 2>&1' && HAS_STRACE=1
echo "has_strace=$HAS_STRACE" | tee -a "$OUTDIR/meta/device.txt"

# ---------- 包必须已装 ----------
if ! sh_ "bm dump -n $BUNDLE" 2>/dev/null | grep -q "$BUNDLE"; then
  echo "FATAL: bundle $BUNDLE 未安装。先装再采。" >&2
  exit 3
fi

# ---------- 冷启动前清场 ----------
sh_ "aa force-stop $BUNDLE" 2>/dev/null || true
sh_ 'hilog -p off' 2>/dev/null || echo "WARN: hilog -p off 失败，日志可能带 <private> 掩码" | tee -a "$OUTDIR/meta/device.txt"
sh_ 'hilog -r' >/dev/null 2>&1 || true

# ---------- 起日志采集 ----------
"${HDC_CMD[@]}" shell hilog >"$OUTDIR/hilog/all.txt" 2>&1 &
HILOG_PID=$!
echo "hilog_collector_pid=$HILOG_PID" >> "$OUTDIR/meta/device.txt"

# ---------- 拉起 ----------
START_TS=$(date +%s)
sh_ "aa start -b $BUNDLE -a $ABILITY" 2>&1 | tee "$OUTDIR/meta/aa-start.txt" || true

sleep 2
PID=$(sh_ "pidof $BUNDLE" 2>/dev/null | tr -d '\r' | awk '{print $1}' || true)
echo "pid=${PID:-<none>}" | tee "$OUTDIR/meta/pid.txt"

# ---------- strace（有就采，没有就采 maps/fd，并明确写出降级）----------
if [[ "$HAS_STRACE" == 1 && -n "${PID:-}" ]]; then
  sh_ "strace -f -tt -s 256 \
      -e trace=openat,open,epoll_wait,epoll_pwait,epoll_ctl,eventfd,eventfd2,futex,read,write \
      -o /data/local/tmp/oh-strace.txt -p $PID & sleep $DURATION_SEC; kill %1 2>/dev/null || true" \
      >"$OUTDIR/strace/strace.stdout" 2>"$OUTDIR/strace/strace.stderr" || true
  "${HDC_CMD[@]}" file recv /data/local/tmp/oh-strace.txt "$OUTDIR/strace/strace.txt" || true
else
  echo "strace 降级：has_strace=$HAS_STRACE pid=${PID:-none}；改采 maps/fd" | tee "$OUTDIR/strace/DEGRADED.txt"
  if [[ -n "${PID:-}" ]]; then
    sh_ "cat /proc/$PID/maps" >"$OUTDIR/strace/maps.txt" 2>/dev/null || true
    sh_ "ls -l /proc/$PID/fd" >"$OUTDIR/strace/fds.txt" 2>/dev/null || true
  fi
  sleep "$DURATION_SEC"
fi

# ---------- 收采集器（只收自己起的确切 PID）----------
kill "$HILOG_PID" 2>/dev/null || true
wait "$HILOG_PID" 2>/dev/null || true

# ---------- 截屏 ----------
sh_ 'snapshot_display -f /data/local/tmp/oh-final.jpeg' >/dev/null 2>&1 || true
"${HDC_CMD[@]}" file recv /data/local/tmp/oh-final.jpeg "$OUTDIR/screen/final.jpeg" >/dev/null 2>&1 || true

# ---------- 出事件序列（与安卓侧同格式）----------
python3 "$(dirname "$0")/parse-events-oh.py" \
  --hilog "$OUTDIR/hilog/all.txt" \
  ${HAS_STRACE:+--strace "$OUTDIR/strace/strace.txt"} \
  --outdir "$OUTDIR/events"

END_TS=$(date +%s)
echo "elapsed_sec=$((END_TS-START_TS))" | tee "$OUTDIR/meta/elapsed.txt"
echo "DONE $OUTDIR"
