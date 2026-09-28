#!/usr/bin/env bash
# ============================================================================
# nd_guard.sh — 编译生命周期守护 (失败计数 + 自动 golden + 兜底回滚)
# ============================================================================
#
# 移植 16.16 R2 (safe_boot 失败计数 + fallback)，把「boot 失败」换成「build 失败」。
#
# 接到编译/恢复管线里这样用：
#   bash restore_after_sync.sh && <build 命令> \
#       && bash neverdie/nd_guard.sh --mark-success \
#       || bash neverdie/nd_guard.sh --build-failed
#
# 子命令：
#   --mark-success   build 成功 → 清零失败计数 + 立刻拍一张新 golden (新 known-good)
#   --build-failed   build 失败 → 失败计数 +1；达阈值时按策略兜底 (见下)
#   --verify         跑一次非破坏性完整性体检 (= nd_verify.sh)
#   --status         打印计数 / active slot / metrics
#   --reset          清零失败计数
#
# 兜底策略 (达 ND_FAIL_THRESHOLD 次连续失败)：
#   默认：只「响亮告警」，指向 nd_restore_golden.sh，绝不自动覆盖手写输入。
#         (inputs 是手写恢复弹药，连续编译失败更可能是代码 bug 而非文件损坏，
#          自动覆盖反而会冲掉正在修的改动。)
#   ND_AUTO_RESTORE=1 时：才真的自动 nd_restore_golden.sh --force。
# ----------------------------------------------------------------------------
set -euo pipefail

. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/nd_common.sh"

_read_cnt() {
    local n; n="$(cat "$ND_FAILCNT" 2>/dev/null || echo 0)"
    case "$n" in ''|*[!0-9]*) n=0 ;; esac
    echo "$n"
}
_write_cnt() { nd_init_root; printf '%s\n' "$1" > "$ND_FAILCNT.tmp" && mv "$ND_FAILCNT.tmp" "$ND_FAILCNT"; }

CMD="${1:-}"
case "$CMD" in
    --mark-success)
        log_phase "nd_guard --mark-success"
        _write_cnt 0
        log_ok "失败计数清零"
        log_info "拍新 golden (capture known-good)…"
        bash "$ND_DIR/nd_backup_golden.sh"
        nd_metric_set last_success_ts "$(date '+%Y-%m-%d %H:%M:%S')"
        exit 0
        ;;

    --build-failed)
        log_phase "nd_guard --build-failed"
        N="$(_read_cnt)"; N=$((N + 1)); _write_cnt "$N"
        nd_metric_set last_fail_ts "$(date '+%Y-%m-%d %H:%M:%S')"
        log_warn "连续 build 失败 #$N (阈值 $ND_FAIL_THRESHOLD)"
        if [ "$N" -ge "$ND_FAIL_THRESHOLD" ]; then
            if [ "${ND_AUTO_RESTORE:-0}" = "1" ]; then
                log_warn "达阈值且 ND_AUTO_RESTORE=1 → 自动回滚 golden"
                bash "$ND_DIR/nd_restore_golden.sh" --force
                _write_cnt 0
                log_ok "已自动回滚并清零计数"
            else
                log_error "达阈值！权威输入可能已损坏。"
                log_error "  体检:  bash neverdie/nd_verify.sh"
                log_error "  回滚:  bash neverdie/nd_restore_golden.sh"
                log_error "  (确认是文件损坏而非代码 bug 后再回滚；或设 ND_AUTO_RESTORE=1 自动化)"
            fi
        fi
        exit 0
        ;;

    --verify)
        exec bash "$ND_DIR/nd_verify.sh"
        ;;

    --reset)
        _write_cnt 0
        log_ok "失败计数已清零"
        exit 0
        ;;

    --status|"")
        echo "===== nd_guard status ====="
        echo "ADAPTER_ROOT    : $ADAPTER_ROOT"
        echo "ND_GOLDEN_ROOT  : $ND_GOLDEN_ROOT"
        echo "active slot     : $(nd_active_slot || echo '(none)')"
        echo "fail count      : $(_read_cnt) / $ND_FAIL_THRESHOLD"
        echo "ND_AUTO_RESTORE : ${ND_AUTO_RESTORE:-0}"
        echo "----- metrics -----"
        cat "$ND_METRICS" 2>/dev/null || echo "(no metrics yet)"
        exit 0
        ;;

    *)
        log_error "未知命令: $CMD"
        echo "用法: nd_guard.sh [--mark-success|--build-failed|--verify|--reset|--status]"
        exit 1
        ;;
esac
