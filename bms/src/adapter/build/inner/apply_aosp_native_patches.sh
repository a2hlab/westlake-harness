#!/bin/bash
# ============================================================================
# apply_aosp_native_patches.sh — AOSP art 原生交叉编译 patch(原 restore A10 段抽取)
# ============================================================================
# sourceable 函数库,由 restore_after_sync.sh::A10 `source` 后调用。
# 应用 aosp_patches/art/**/*.patch(libart.so 交叉编译修补,如 mark_compact.cc
# 的 uffdio_continue 结构补全)。
#
# 依赖调用方作用域:ADAPTER_ROOT, AOSP_ROOT, DRY_RUN, run(), log_info/log_ok/log_warn
#
# 两层幂等(与 apply_hwui_patches 一致,但用 git apply):Layer1 sig-marker 快速短路 +
# Layer2 逐 patch reverse-check-first。
#
# 范围说明:A2(setup_aosp_build_tree.sh,build_patches + product/bp-disable/cts 多用途)
# 与 A2b/A2c(.bak 模型 framework-libs compat)不在本组件,各自单独处理。
# ============================================================================

apply_aosp_native_patches() {
    log_info "A10. Apply aosp_patches/art/**/*.patch (native cross-compile fixes)"
    local ART_PATCH_ROOT="$ADAPTER_ROOT/aosp_patches/art"
    if [ ! -d "$ART_PATCH_ROOT" ]; then
        log_warn "A10 skipped — $ART_PATCH_ROOT not present"
        return 0
    fi
    local ART_REPO="$AOSP_ROOT/art"

    # ---- Layer 1: 组件级快速短路 ----
    local marker_dir="$AOSP_ROOT/.adapter_applied"
    local marker="$marker_dir/aosp_native" sig p
    sig=$(find "$ART_PATCH_ROOT" -name '*.patch' -type f | sort | xargs cat 2>/dev/null | md5sum | awk '{print $1}')
    if [ -f "$marker" ] && [ "$(cat "$marker" 2>/dev/null)" = "$sig" ]; then
        local spot
        spot=$(find "$ART_PATCH_ROOT" -name '*.patch' -type f | sort | head -1)
        if [ -n "$spot" ] && (cd "$ART_REPO" && git apply --check --reverse "$spot") 2>/dev/null; then
            log_ok "A10: art patches already applied (sig $sig + spot-check) — skip"
            return 0
        fi
        log_warn "A10: marker sig matched but spot-check failed — re-checking per-patch"
    fi

    # ---- Layer 2: 逐 patch(reverse-check 在前;art 用 git apply) ----
    local A10_APPLIED=0 A10_SKIPPED=0 A10_FAILED=0
    while IFS= read -r p; do
        [ -z "$p" ] && continue
        if (cd "$ART_REPO" && git apply --check --reverse "$p") 2>/dev/null; then
            A10_SKIPPED=$((A10_SKIPPED+1))                       # already applied
        elif (cd "$ART_REPO" && git apply --check "$p") 2>/dev/null; then
            run "(cd $ART_REPO && git apply $p)"
            log_ok "A10 APPLY: $(basename "$p")"
            A10_APPLIED=$((A10_APPLIED+1))
        else
            log_warn "A10 FAIL: $(basename "$p") (source drift — check manually)"
            A10_FAILED=$((A10_FAILED+1))
        fi
    done < <(find "$ART_PATCH_ROOT" -name "*.patch" -type f | sort)
    log_ok "A10 done: $A10_APPLIED applied / $A10_SKIPPED skipped / $A10_FAILED failed"

    if [ "$A10_FAILED" = "0" ]; then
        run "mkdir -p '$marker_dir' && echo '$sig' > '$marker'"
    fi
    [ "$A10_FAILED" = "0" ]
}

# ============================================================================
# A2b — libandroidfw modern-API patches(2026-05-27 由 restore A2b 段忠实搬入)
# .bak 模型:首次备份 target.bak,之后每次"从 .bak 恢复 pristine → patch -p0 重应用"
# (天然幂等;保持原行为,不转 reverse-check)。AssetManager2.{h,cpp}/Asset.cpp。
# ============================================================================
apply_aosp_libandroidfw_patches() {
    log_info "A2b. Apply Phase 1 libandroidfw modern-API patches"
    local AFW_PATCHES_DIR="$ADAPTER_ROOT/aosp_patches/frameworks/base/libs/androidfw"
    local AFW_TARGET_DIR="$AOSP_ROOT/frameworks/base/libs/androidfw"
    local patch_rel p target_rel target
    for patch_rel in "include/androidfw/AssetManager2.h.patch" "AssetManager2.cpp.patch" "Asset.cpp.patch"; do
        p="$AFW_PATCHES_DIR/$patch_rel"
        target_rel="${patch_rel%.patch}"
        target="$AFW_TARGET_DIR/$target_rel"
        if [ -f "$p" ] && [ -f "$target" ]; then
            if [ "${DRY_RUN:-0}" = "1" ]; then
                # .bak 模型每次"复原 pristine→重 patch",天然幂等;dry-run 不实际改文件。
                # (不能像真 run 那样跑 patch:cp 复原被 run() 跳过 → patch 会打到已 patch
                #  文件而误报 FAILED,故 dry-run 直接预览跳过。)
                log_info "A2b [dry] $patch_rel: would restore .bak + patch -p0 (idempotent)"
                continue
            fi
            if [ ! -f "${target}.bak" ]; then run "cp \"$target\" \"${target}.bak\""; fi
            run "cp \"${target}.bak\" \"$target\""
            if patch -p0 "$target" < "$p" >/dev/null 2>&1; then
                log_ok "A2b applied: $patch_rel"
            elif patch --forward -p0 "$target" < "$p" >/dev/null 2>&1; then
                log_ok "A2b applied (forward): $patch_rel"
            else
                log_warn "A2b apply FAILED for $patch_rel — manual inspection needed"
            fi
        elif [ ! -f "$target" ]; then
            log_warn "A2b skipped (target absent): $target"
        elif [ ! -f "$p" ]; then
            log_warn "A2b skipped (patch absent): $p"
        fi
    done
}

# ============================================================================
# A2c — icu/AndroidRuntime/Process single-file patches(2026-05-27 由 restore A2c 段搬入)
# 同 .bak 模型;apply 三级 fallback(git apply → patch -p1 → patch -p0)。
# ============================================================================
apply_aosp_jni_compat_patches() {
    log_info "A2c. Apply aosp_patches single-file patches (icu / AndroidRuntime / Process)"
    # 2026-05-27: 删除悬空条目 external/icu/android_icu4j/Android.bp.patch —— 该 .patch
    # 文件在 aosp_patches/ 下从不存在(经核实 aosp_patches/external/ 整个目录无任何 patch),
    # 留在清单只会每次 build 报 spurious "patch absent" WARN。如未来确需 patch icu
    # Android.bp,以实际 .patch 文件重新加入。
    local A2C_PATCHES=(
        "frameworks/base/core/jni/AndroidRuntime.cpp.patch"
        "frameworks/base/core/jni/android_util_Process.cpp.patch"
    )
    local patch_rel p target_rel target
    for patch_rel in "${A2C_PATCHES[@]}"; do
        p="$ADAPTER_ROOT/aosp_patches/$patch_rel"
        target_rel="${patch_rel%.patch}"
        target="$AOSP_ROOT/$target_rel"
        if [ ! -f "$p" ]; then log_warn "A2c skipped (patch absent): $p"; continue; fi
        if [ ! -f "$target" ]; then log_warn "A2c skipped (target absent): $target"; continue; fi
        if [ "${DRY_RUN:-0}" = "1" ]; then
            # 同 A2b:.bak 模型天然幂等,dry-run 仅预览不改文件(避免误报 FAILED)。
            log_info "A2c [dry] $patch_rel: would restore .bak + re-apply (idempotent)"
            continue
        fi
        if [ ! -f "${target}.bak" ]; then run "cp \"$target\" \"${target}.bak\""; fi
        run "cp \"${target}.bak\" \"$target\""
        if (cd "$AOSP_ROOT" && git apply --check "$p") 2>/dev/null; then
            run "(cd \"$AOSP_ROOT\" && git apply \"$p\")"
            log_ok "A2c applied (git apply): $patch_rel"
        elif patch -p1 -d "$AOSP_ROOT" < "$p" >/dev/null 2>&1; then
            log_ok "A2c applied (patch -p1): $patch_rel"
        elif patch -p0 "$target" < "$p" >/dev/null 2>&1; then
            log_ok "A2c applied (patch -p0): $patch_rel"
        else
            log_warn "A2c apply FAILED for $patch_rel — manual inspection needed"
        fi
    done
}
