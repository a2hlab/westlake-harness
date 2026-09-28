#!/usr/bin/env bash
# ============================================================================
# nd_backup_golden.sh — 给 adapter 权威输入做 golden 快照 (A/B 双 slot)
# ============================================================================
#
# Usage:
#   bash neverdie/nd_backup_golden.sh            # 写 inactive slot 并切为 active
#   ND_GOLDEN_ROOT=/data/.adapter-neverdie bash neverdie/nd_backup_golden.sh
#
# 何时调：每次「确认当前 adapter 输入是 known-good」后——典型是一次成功编译 /
#         成功 restore_after_sync.sh 之后 (可由 nd_guard.sh --mark-success 串起来)。
#
# 设计 (移植 16.16 R3 + R13)：
#   golden.A.tar.gz / golden.B.tar.gz  ← 双 slot，永远保留一个完好的
#   golden.A.manifest / golden.B.manifest ← 每文件 sha256
#   active 文件                          ← 内含 "A"/"B"，原子切换
#   算法：写 inactive slot → 全部成功 → 原子改 active。写一半崩了，旧 active 仍完好。
#
# 排除：out/ 大包、oh-build-*.tar.gz、prebuilts/、正在复制的 OH 产物 (白名单天然排除)。
# ----------------------------------------------------------------------------
set -euo pipefail

. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/nd_common.sh"

log_phase "nd_backup_golden — adapter 权威输入 golden 快照"
nd_init_root

# 1) 选 inactive slot
SLOT="$(nd_inactive_slot)"
TARBALL="$(nd_tarball "$SLOT")"
MANIFEST="$(nd_manifest "$SLOT")"
log_info "目标 slot=$SLOT (当前 active='$(nd_active_slot)')"

# 2) 校验白名单条目存在性 (缺失只 warn，不阻断——首次/部分工程也能起步)
PRESENT=""
MISSING=0
for item in $ND_PROTECT; do
    if [ -e "$ADAPTER_ROOT/$item" ]; then
        PRESENT="$PRESENT $item"
    else
        log_warn "保护项缺失，跳过: $item"
        MISSING=$((MISSING + 1))
    fi
done
if [ -z "$PRESENT" ]; then
    log_error "无任何保护项存在，放弃快照 (ADAPTER_ROOT=$ADAPTER_ROOT)"
    exit 2
fi

# 3) 打 tar.gz 到 inactive slot 的 .tmp，成功再 mv (原子落地)
log_info "归档 → $TARBALL"
# shellcheck disable=SC2086
tar -C "$ADAPTER_ROOT" $ND_EXCLUDES -czf "$TARBALL.tmp" $PRESENT
mv "$TARBALL.tmp" "$TARBALL"
TAR_KB=$(du -sk "$TARBALL" 2>/dev/null | cut -f1)
log_ok "归档完成 ($TAR_KB KB)"

# 4) 生成 manifest (每文件 sha256)——校验时逐项比对
log_info "生成 manifest → $MANIFEST"
: > "$MANIFEST.tmp"
# shellcheck disable=SC2086
while IFS= read -r f; do
    # tar 排除规则在 find 侧也复刻一遍，保证 manifest 与归档内容一致
    case "$f" in
        */out/*|*/inner/out/*) continue ;;
        *.log|*/.git/*|*/__pycache__/*|*.tar.gz|*/.DS_Store) continue ;;
    esac
    sum="$(nd_sha256 "$f")"
    rel="${f#"$ADAPTER_ROOT"/}"
    printf '%s  %s\n' "$sum" "$rel" >> "$MANIFEST.tmp"
done < <(cd "$ADAPTER_ROOT" && find $PRESENT -type f 2>/dev/null | sed "s#^#$ADAPTER_ROOT/#")
sort -k2 "$MANIFEST.tmp" -o "$MANIFEST.tmp"
mv "$MANIFEST.tmp" "$MANIFEST"
FILE_CNT=$(wc -l < "$MANIFEST" | tr -d ' ')
log_ok "manifest 完成 ($FILE_CNT 文件)"

# 5) 原子切 active 到新 slot
nd_set_active_slot "$SLOT"
log_ok "active → slot $SLOT (旧 slot 作为热备保留)"

# 6) metrics + 配额清理
BK=$(nd_metric_get backup_count); case "$BK" in ''|*[!0-9]*) BK=0 ;; esac
nd_metric_set backup_count "$((BK + 1))"
nd_metric_set last_backup_ts "$(date '+%Y-%m-%d %H:%M:%S')"
nd_metric_set last_backup_slot "$SLOT"
nd_metric_set last_backup_files "$FILE_CNT"
nd_metric_set last_backup_kb "$TAR_KB"
nd_disk_cleanup

log_phase "DONE — golden slot $SLOT 就绪 ($FILE_CNT 文件, $TAR_KB KB, 缺失 $MISSING 项)"
echo "[nd_backup_golden] OK: slot=$SLOT files=$FILE_CNT size=${TAR_KB}KB missing=$MISSING"
