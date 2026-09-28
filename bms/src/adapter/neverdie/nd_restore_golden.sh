#!/usr/bin/env bash
# ============================================================================
# nd_restore_golden.sh — 把 active golden 一键回滚到 adapter 工作区
# ============================================================================
#
# 这是「死机后复活」入口：当权威输入被坏 edit / 坏 patch / 坏 repo sync / 误删
# 搞烂时，用本脚本恢复到上一次 known-good golden。
#
# Usage:
#   bash neverdie/nd_restore_golden.sh           # 交互确认后回滚
#   bash neverdie/nd_restore_golden.sh --force   # 跳过确认 (供 nd_guard.sh 自动调)
#   bash neverdie/nd_restore_golden.sh --slot=B  # 指定 slot (默认 active)
#
# 安全网 (移植 16.16 R3 .corrupt 隔离)：
#   回滚前，把当前被保护项整体打包到 corrupt/ 隔离，绝不直接删——便于事后取证。
#
# Exit: 0 成功 / 2 无 golden / 3 解包失败
# ----------------------------------------------------------------------------
set -euo pipefail

. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/nd_common.sh"

FORCE=0
SLOT="$(nd_active_slot)"
for arg in "$@"; do
    case "$arg" in
        --force) FORCE=1 ;;
        --slot=*) SLOT="${arg#*=}" ;;
        *) log_warn "未知参数: $arg" ;;
    esac
done

log_phase "nd_restore_golden — 回滚 adapter 权威输入"
nd_init_root

if [ -z "$SLOT" ]; then
    log_error "尚无 active golden，无可回滚 — 先跑 nd_backup_golden.sh"
    exit 2
fi
TARBALL="$(nd_tarball "$SLOT")"
MANIFEST="$(nd_manifest "$SLOT")"
if [ ! -f "$TARBALL" ]; then
    log_error "golden 归档缺失: $TARBALL"
    exit 2
fi
log_info "将从 slot=$SLOT 回滚 ($TARBALL)"

if [ "$FORCE" = 0 ]; then
    printf '%s即将用 golden slot %s 覆盖工作区权威输入。当前内容会先隔离到 corrupt/。继续? [y/N] %s' \
        "$C_YELLOW" "$SLOT" "$C_RESET"
    read -r ans
    case "$ans" in y|Y|yes|YES) ;; *) log_info "已取消"; exit 0 ;; esac
fi

TS="$(date '+%Y%m%d-%H%M%S')"

# 1) 把当前被保护项隔离到 corrupt/ (打包，不删原地——下一步 tar 解包会覆盖)
QUAR="$ND_CORRUPT_DIR/pre-restore-$TS.tar.gz"
PRESENT=""
for item in $ND_PROTECT; do
    [ -e "$ADAPTER_ROOT/$item" ] && PRESENT="$PRESENT $item"
done
if [ -n "$PRESENT" ]; then
    log_info "隔离当前内容 → $QUAR"
    # shellcheck disable=SC2086
    tar -C "$ADAPTER_ROOT" $ND_EXCLUDES -czf "$QUAR" $PRESENT 2>/dev/null || \
        log_warn "隔离打包有非致命错误 (可能部分文件正在被写)，继续回滚"
fi

# 2) 解包 golden 覆盖工作区
log_info "解包 golden → $ADAPTER_ROOT"
if tar -C "$ADAPTER_ROOT" -xzf "$TARBALL"; then
    log_ok "解包成功"
else
    log_error "解包失败 — 工作区可能半残，隔离副本在 $QUAR"
    exit 3
fi

# 3) 回滚后立即自检 (verify 总是比对 active slot；回滚不改 active，故与本次 slot 一致)
RC=0
bash "$ND_DIR/nd_verify.sh" --quiet >/dev/null 2>&1 || RC=$?
if [ "$RC" -eq 0 ]; then
    log_ok "回滚后自检 HEALTHY (与 slot $SLOT 一致)"
else
    log_warn "回滚后自检仍有漂移 (rc=$RC) — 可能 manifest 含已被排除的易变文件，请人工确认"
fi

# 4) metrics + 配额清理
RC2=$(nd_metric_get restore_count); case "$RC2" in ''|*[!0-9]*) RC2=0 ;; esac
nd_metric_set restore_count "$((RC2 + 1))"
nd_metric_set last_restore_ts "$(date '+%Y-%m-%d %H:%M:%S')"
nd_metric_set last_restore_slot "$SLOT"
nd_disk_cleanup

log_phase "DONE — 已从 golden slot $SLOT 回滚 (隔离副本: ${QUAR:-无})"
echo "[nd_restore_golden] OK: slot=$SLOT quarantine=${QUAR:-none}"
