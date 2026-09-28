#!/bin/bash
# ============================================================================
# apply_hwui_patches.sh — hwui 组件 patch 应用(原 restore_after_sync.sh A9 段抽取)
# ============================================================================
# 这是一个 *sourceable 函数库*,不独立运行。由 restore_after_sync.sh 总入口
# `source` 后调用 apply_hwui_patches。
#
# 依赖调用方作用域已定义:
#   变量: ADAPTER_ROOT, AOSP_ROOT, DRY_RUN
#   函数: run(), log_info(), log_ok(), log_warn()
#
# 两层幂等(2026-05-27,原则 1 重构):
#   Layer 1 组件级快速短路:patch-set 内容 md5 签名 + marker 文件;sig 匹配且
#           代表性 patch 抽验(reverse-check)通过 → 整组秒跳(常态 0 实际 apply)。
#           marker 放 $AOSP_ROOT/.adapter_applied/(untracked,repo sync 会清→自动失效)。
#   Layer 2 逐 patch 回退:reverse-check 在前(已应用 1 次 dry-run 即跳过),
#           否则 forward dry-run→apply,都不通过则报源漂移。无 FAIL 才写 marker。
# ============================================================================

apply_hwui_patches() {
    log_info "A9. Apply hwui per-file patches (aosp_patches/libs/hwui/patches/*.patch)"
    local PATCHES_DIR="$ADAPTER_ROOT/aosp_patches/libs/hwui/patches"
    if [ ! -d "$PATCHES_DIR" ]; then
        log_warn "A9 skipped — $PATCHES_DIR not found"
        return 0
    fi
    local FB="$AOSP_ROOT/frameworks/base"

    # ---- Layer 1: 组件级快速短路 ----
    local marker_dir="$AOSP_ROOT/.adapter_applied"
    local marker="$marker_dir/hwui"
    local sig
    sig=$(find "$PATCHES_DIR" -name '*.patch' -type f | sort | xargs cat 2>/dev/null | md5sum | awk '{print $1}')
    if [ -f "$marker" ] && [ "$(cat "$marker" 2>/dev/null)" = "$sig" ]; then
        local spot
        spot=$(find "$PATCHES_DIR" -name '*.patch' -type f | sort | head -1)
        if [ -n "$spot" ] && (cd "$FB" && patch --dry-run -R -p1 < "$spot") >/dev/null 2>&1; then
            log_ok "A9: hwui patches already applied (sig $sig + spot-check) — skip"
            return 0
        fi
        log_warn "A9: marker sig matched but spot-check failed — re-checking per-patch"
    fi

    # ---- Layer 2: 逐 patch(reverse-check 在前) ----
    local APPLIED=0 SKIPPED=0 FAILED=0 p rel
    while IFS= read -r p; do
        rel="${p#$PATCHES_DIR/}"
        if (cd "$FB" && patch --dry-run -R -p1 < "$p") >/dev/null 2>&1; then
            SKIPPED=$((SKIPPED+1))                       # already applied
        elif (cd "$FB" && patch --dry-run -p1 < "$p") >/dev/null 2>&1; then
            run "(cd $FB && patch -p1 --no-backup-if-mismatch < $p)"
            APPLIED=$((APPLIED+1))
        else
            log_warn "A9 FAIL — $rel: neither applies nor reverse-applies (source drift)"
            FAILED=$((FAILED+1))
        fi
    done < <(find "$PATCHES_DIR" -name '*.patch' -type f | sort)
    log_ok "A9 summary: $APPLIED applied / $SKIPPED already-applied / $FAILED failed"

    # 补 2 个空 api/test-*.txt(untracked,非 patch 跟踪)
    mkdir -p "$FB/libs/hwui/api"
    : > "$FB/libs/hwui/api/test-current.txt"
    : > "$FB/libs/hwui/api/test-removed.txt"
    log_info "A9: ensured empty api/test-{current,removed}.txt"

    # 仅在无 FAIL 时写 marker(不把部分失败的 apply 标记成已完成)
    if [ "$FAILED" = "0" ]; then
        run "mkdir -p '$marker_dir' && echo '$sig' > '$marker'"
    fi
}
