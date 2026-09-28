#!/usr/bin/env bash
# ============================================================================
# nd_verify.sh — adapter 权威输入完整性「健康检查」
# ============================================================================
#
# 这是本子系统的「liveness probe」：16.16 watchdog 检查 daemon 是否活着，
# 这里检查「恢复弹药」是否完好——和 active golden 的 manifest 逐项比对。
#
# Usage:
#   bash neverdie/nd_verify.sh           # 比对当前工作区 vs active golden
#   bash neverdie/nd_verify.sh --quiet   # 只给退出码 (供 nd_guard.sh 调)
#
# Exit:
#   0  健康 (无漂移)
#   1  漂移 (有文件被改 / 缺失 / 新增)——可能是正常迭代，也可能是损坏
#   2  尚无 golden (需先 nd_backup_golden.sh)
# ----------------------------------------------------------------------------
set -euo pipefail

. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/nd_common.sh"

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

SLOT="$(nd_active_slot)"
if [ -z "$SLOT" ]; then
    [ "$QUIET" = 0 ] && log_error "尚无 active golden — 先跑 nd_backup_golden.sh"
    exit 2
fi
MANIFEST="$(nd_manifest "$SLOT")"
if [ ! -f "$MANIFEST" ]; then
    [ "$QUIET" = 0 ] && log_error "active slot=$SLOT 但 manifest 缺失: $MANIFEST"
    exit 2
fi

[ "$QUIET" = 0 ] && log_phase "nd_verify — 工作区 vs golden slot $SLOT"

CHANGED=0; MISSING=0; OK=0
# 逐项比对 manifest
while IFS= read -r line; do
    [ -z "$line" ] && continue
    exp_sum="${line%% *}"
    rel="${line#*  }"
    cur="$ADAPTER_ROOT/$rel"
    if [ ! -f "$cur" ]; then
        MISSING=$((MISSING + 1))
        [ "$QUIET" = 0 ] && log_warn "缺失: $rel"
        continue
    fi
    cur_sum="$(nd_sha256 "$cur")"
    if [ "$cur_sum" = "$exp_sum" ]; then
        OK=$((OK + 1))
    else
        CHANGED=$((CHANGED + 1))
        [ "$QUIET" = 0 ] && log_warn "改动: $rel"
    fi
done < "$MANIFEST"

DRIFT=$((CHANGED + MISSING))
nd_metric_set last_verify_ts "$(date '+%Y-%m-%d %H:%M:%S')"
nd_metric_set last_verify_drift "$DRIFT"

if [ "$DRIFT" -eq 0 ]; then
    [ "$QUIET" = 0 ] && log_ok "健康：$OK 文件全部匹配，无漂移"
    [ "$QUIET" = 0 ] && echo "[nd_verify] HEALTHY: ok=$OK"
    exit 0
else
    [ "$QUIET" = 0 ] && log_warn "漂移：changed=$CHANGED missing=$MISSING ok=$OK (slot $SLOT)"
    [ "$QUIET" = 0 ] && echo "[nd_verify] DRIFT: changed=$CHANGED missing=$MISSING ok=$OK"
    exit 1
fi
