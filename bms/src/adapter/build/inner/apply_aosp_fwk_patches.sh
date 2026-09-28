#!/bin/bash
# ============================================================================
# apply_aosp_fwk_patches.sh — AOSP framework L5 反射注入 patch(原 restore A3 段抽取)
# ============================================================================
# sourceable 函数库,由 restore_after_sync.sh::A3 `source` 后调用。
# 4 个 .java patch 把 OH-adapter 反射加载注入到 framework 各 Singleton.create() 工厂
# (ActivityManager / ActivityTaskManager / ActivityThread / WindowManagerGlobal)。
#
# 依赖调用方作用域:ADAPTER_ROOT, AOSP_ROOT, DRY_RUN, run(), log_info/log_ok/log_warn
#
# 两层幂等(与 apply_hwui_patches 一致):Layer1 sig-marker 快速短路 +
# Layer2 逐 patch reverse-check-first。A2b/A2c(.bak 模型的 native 交叉编译修补)
# 不在此组件,留给 apply_aosp_native_patches。
# ============================================================================

apply_aosp_fwk_patches() {
    log_info "A3. Apply L5 reflection injection (4 per-file .patch via patch -p1)"
    local A3_PATCHES=(
        "frameworks/base/core/java/android/app/ActivityManager.java.patch"
        "frameworks/base/core/java/android/app/ActivityTaskManager.java.patch"
        "frameworks/base/core/java/android/app/ActivityThread.java.patch"
        "frameworks/base/core/java/android/view/WindowManagerGlobal.java.patch"
    )

    # ---- Layer 1: 组件级快速短路 ----
    local marker_dir="$AOSP_ROOT/.adapter_applied"
    local marker="$marker_dir/aosp_fwk" sig rel
    sig=$(for rel in "${A3_PATCHES[@]}"; do cat "$ADAPTER_ROOT/aosp_patches/$rel" 2>/dev/null; done | md5sum | awk '{print $1}')
    if [ -f "$marker" ] && [ "$(cat "$marker" 2>/dev/null)" = "$sig" ]; then
        local spot="$ADAPTER_ROOT/aosp_patches/${A3_PATCHES[0]}"
        if [ -f "$spot" ] && (cd "$AOSP_ROOT" && patch --dry-run -R -p1 < "$spot") >/dev/null 2>&1; then
            log_ok "A3: L5 reflection patches already applied (sig $sig + spot-check) — skip"
            return 0
        fi
        log_warn "A3: marker sig matched but spot-check failed — re-checking per-patch"
    fi

    # ---- Layer 2: 逐 patch(reverse-check 在前) ----
    local A3_APPLIED=0 A3_SKIPPED=0 A3_FAILED=0 A3_MISSING=0 patch_file
    for rel in "${A3_PATCHES[@]}"; do
        patch_file="$ADAPTER_ROOT/aosp_patches/$rel"
        if [ ! -f "$patch_file" ]; then
            log_warn "A3 SKIP — patch missing: $rel"
            A3_MISSING=$((A3_MISSING+1))
            continue
        fi
        if (cd "$AOSP_ROOT" && patch --dry-run -R -p1 < "$patch_file") >/dev/null 2>&1; then
            A3_SKIPPED=$((A3_SKIPPED+1))                       # already applied
        elif (cd "$AOSP_ROOT" && patch --dry-run -p1 < "$patch_file") >/dev/null 2>&1; then
            run "(cd $AOSP_ROOT && patch -p1 --no-backup-if-mismatch < $patch_file)"
            log_ok "A3 APPLY: $(basename "$rel")"
            A3_APPLIED=$((A3_APPLIED+1))
        else
            log_warn "A3 FAIL: $(basename "$rel") (neither forward nor reverse)"
            A3_FAILED=$((A3_FAILED+1))
        fi
    done
    log_ok "A3 done: $A3_APPLIED applied / $A3_SKIPPED skipped / $A3_FAILED failed / $A3_MISSING missing"

    if [ "$A3_FAILED" = "0" ] && [ "$A3_MISSING" = "0" ]; then
        run "mkdir -p '$marker_dir' && echo '$sig' > '$marker'"
    fi
    [ "$A3_FAILED" = "0" ]
}
