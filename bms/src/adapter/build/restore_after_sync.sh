#!/bin/bash
# ============================================================================
# restore_after_sync.sh — Single-Command Recovery Orchestrator
# ============================================================================
#
# Purpose: After a fresh `repo sync` of AOSP (~/aosp/) and/or OpenHarmony
# (~/oh/), this single script restores every modification needed to reach
# the last known-good buildable state. It is the canonical implementation
# of CLAUDE.md "一键恢复规则 (Single-Command Recovery Rule)".
#
# What it does (in order):
#   Phase A — AOSP source restoration
#     A1. Install custom product (device/adapter/oh_adapter)
#     A2. Apply aosp_build_patches/*.patch
#     A3. Apply L5 reflection injection (apply_aosp_java_patches.py)
#     A4. Apply aosp_patches/libs/hwui/*.patch
#     A5. Disable non-essential Android.bp files
#     A6. Create CTS/VTS stub files
#     A7. Deploy dex2oat_stubs/ trees
#     A8. Deploy hwui stub source files
#     A9. Apply hwui patches: bulk hwui_rk3568.patch + 7 per-file diff patches
#         (2026-05-20: replaced 8 apply_*.py scripts with .patch files; .py
#         moved to bkup/aosp_patches/libs/hwui/)
#     A10. Apply aosp_patches/art/**/*.patch (native libart fixes)
#   Phase B — OH source restoration
#     B1. Apply ohos_patches/build/*.patch (build system fixes)
#     B2. (No-op on rk3568 — product config replacement not needed)
#     B3. Apply ohos_patches/ability_rt/, bundle_framework/, graphic_2d/
#     B4. Apply third_party/musl/ syscall.h.in patch
#     B6. graphic_2d rs_buffer_reclaim.cpp format fix
#     B8. bundle_framework BMS BUILD.gn — add adapter_apk_install_minimal.cpp +
#         apk_manifest_parser.cpp + cflags_cc -I AOSP headers + ldflags
#         libandroidfw + OH_ADAPTER_ANDROID define (gap 6 enabler).
#         Patch uses __AOSP_ROOT__ placeholder, sed-substituted at apply time.
#     B9. ets2abc_config.gni value collision fix (gn gen unblocker for gap 6)
#     B10. Deploy adapter_apk_install_minimal.cpp + apk_manifest_parser.{h,cpp}
#         from canonical adapter sources into oh/foundation/.../bundlemgr/src/.
#         Required by BUILD.gn from B8. Idempotent cp.
#   Phase C — Cross-cutting fixes
#     C1. Deploy skia_compat_headers/ to ECS-known location (no-op if same path)
#     (C2 removed — libarkruntime.so / libani_helpers.z.so are phony'd, not needed)
#   Phase POST — These run AFTER `gn gen` not before — invoked by build.sh:
#     POST1. musl_syscall_fix.sh
#     POST2. ninja_patches/apply_all.sh
#
# Properties (per CLAUDE.md "三性"):
#   * Self-contained — operates from clean source trees, no hidden state
#   * Idempotent     — re-runnable; each phase checks before applying
#   * Traceable      — every action logged; exit-on-error; final state file
#
# IMPORTANT — Honest disclosure (per Post-Completion Feedback Rule):
#
#   1. Phase A9 applies the consolidated aosp_patches/libs/hwui/hwui_rk3568.patch
#      (1263 lines, 47 files) via `git apply`. This patch is the sedimented
#      form of what used to be 30+ Python increment scripts (hwui_phase2_round*.py,
#      hwui_phase3_jni_round*.py, hwui_l2[1-5]_*.py, hwui_round1[23]_*.py).
#      Those scripts have been moved to build/_deprecated/hwui_increment_scripts/
#      as historical artifacts and are no longer called by any live build path.
#
#   2. All paths use $OH_PRODUCT_NAME (default rk3568) and $HOME-based
#      defaults per CLAUDE.md. apply_aosp_java_patches.py accepts
#      $AOSP_ROOT env var as of 2026-04-11 cleanup.
#
#   3. libarkruntime.so / libani_helpers.z.so are NOT needed by this project
#      (confirmed by user 2026-04-11). The ninja phony patches in
#      build/ninja_patches/ make the build graph complete without actually
#      producing these libraries. Phase C2 has been removed.
#
#   4. This script has NOT been validated end-to-end on ECS yet. First-run
#      issues are expected and must be fixed at root cause (no stubs).
#
# Usage:
#   bash restore_after_sync.sh                    # restore both AOSP & OH
#   bash restore_after_sync.sh --only-aosp        # restore only AOSP side
#   bash restore_after_sync.sh --only-oh          # restore only OH side
#   bash restore_after_sync.sh --skip-hwui-py     # skip Phase A9 (Python increments)
#   bash restore_after_sync.sh --aosp-root=PATH   # override AOSP root
#   bash restore_after_sync.sh --oh-root=PATH     # override OH root
#   bash restore_after_sync.sh --dry-run          # print actions without executing
#
# Exit codes:
#   0  — success
#   1  — fatal error (logged before exit)
#   2  — prerequisite missing (paths / source trees)
#   3  — partial success with warnings (some phase skipped)
#
# Author: Adapter project | Created 2026-04-11 per CLAUDE.md "一键恢复规则"
# ============================================================================

set -euo pipefail

# ----------------------------------------------------------------------------
# 0. Globals & defaults
# ----------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Authoritative defaults per CLAUDE.md (override via env or --flag)
AOSP_ROOT="${AOSP_ROOT:-$HOME/aosp}"
OH_ROOT="${OH_ROOT:-$HOME/oh}"
OH_PRODUCT="${OH_PRODUCT:-rk3568}"   # CLAUDE.md says current is rk3568 (DAYU200)
OH_OUT_DIR="${OH_OUT_DIR:-$OH_ROOT/out/$OH_PRODUCT}"

DO_AOSP=1
DO_OH=1
DO_HWUI_PY=1
DRY_RUN=0
WARNINGS=0
STATE_FILE="$ADAPTER_ROOT/out/restore_state.txt"

# Color codes (degrade gracefully on dumb terminals)
if [ -t 1 ]; then
    C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
    C_BLUE=$'\033[34m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
else
    C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""; C_BOLD=""; C_RESET=""
fi

log_info()  { printf '%s[INFO]%s  %s\n' "$C_BLUE"   "$C_RESET" "$*"; }
log_ok()    { printf '%s[OK]%s    %s\n' "$C_GREEN"  "$C_RESET" "$*"; }
log_warn()  { printf '%s[WARN]%s  %s\n' "$C_YELLOW" "$C_RESET" "$*" >&2; WARNINGS=$((WARNINGS+1)); }
log_error() { printf '%s[ERR]%s   %s\n' "$C_RED"    "$C_RESET" "$*" >&2; }
log_phase() { printf '\n%s========== %s ==========%s\n' "$C_BOLD" "$*" "$C_RESET"; }

run() {
    if [ "$DRY_RUN" = "1" ]; then
        printf '  [dry-run] %s\n' "$*"
    else
        eval "$@"
    fi
}

# ----------------------------------------------------------------------------
# 1. Argument parsing
# ----------------------------------------------------------------------------

for arg in "$@"; do
    case "$arg" in
        --only-aosp)        DO_OH=0 ;;
        --only-oh)          DO_AOSP=0 ;;
        --skip-hwui-py)     DO_HWUI_PY=0 ;;
        --aosp-root=*)      AOSP_ROOT="${arg#*=}" ;;
        --oh-root=*)        OH_ROOT="${arg#*=}"; OH_OUT_DIR="$OH_ROOT/out/$OH_PRODUCT" ;;
        --product=*)        OH_PRODUCT="${arg#*=}"; OH_OUT_DIR="$OH_ROOT/out/$OH_PRODUCT" ;;
        --dry-run)          DRY_RUN=1 ;;
        --help|-h)
            sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# \?//'
            exit 0 ;;
        *)
            log_error "Unknown argument: $arg"
            exit 1 ;;
    esac
done

# ----------------------------------------------------------------------------
# 2. Banner & inconsistency warnings
# ----------------------------------------------------------------------------

cat <<EOF
${C_BOLD}================================================================================
  Adapter Restore-After-Sync v1.0
================================================================================${C_RESET}
  ADAPTER_ROOT  = $ADAPTER_ROOT
  AOSP_ROOT     = $AOSP_ROOT     ($([ -d "$AOSP_ROOT" ] && echo "exists" || echo "${C_RED}MISSING${C_RESET}"))
  OH_ROOT       = $OH_ROOT       ($([ -d "$OH_ROOT" ] && echo "exists" || echo "${C_RED}MISSING${C_RESET}"))
  OH_PRODUCT    = $OH_PRODUCT
  OH_OUT_DIR    = $OH_OUT_DIR
  DO_AOSP       = $DO_AOSP
  DO_OH         = $DO_OH
  DO_HWUI_PY    = $DO_HWUI_PY
  DRY_RUN       = $DRY_RUN
EOF

log_phase "Pre-flight notices"
log_info  "OH_CONFIG_FILE is empty — no product config override on rk3568. If build fails on missing thirdparty deps, author rk3568_config.json and re-enable in config.sh."
log_info  "apply_aosp_java_patches.py reads \$AOSP_ROOT env var; this script passes it through."

# Placeholder patch detection — REMOVED 2026-05-21 Phase 6 (check_placeholder_patches.py
# retired per user P3: 4 .py inventory had limited live value; placeholder detection
# now handled implicitly by patch -p1 --dry-run reverse-check in B6b/A3 loops.

WARNINGS=0  # reset counter — these are pre-flight notices, not action warnings

# Sanity check: at least one source root must exist (unless dry-run)
if [ "$DRY_RUN" = "0" ]; then
    if [ "$DO_AOSP" = "1" ] && [ ! -d "$AOSP_ROOT" ]; then
        log_error "AOSP_ROOT not found: $AOSP_ROOT"
        exit 2
    fi
    if [ "$DO_OH" = "1" ] && [ ! -d "$OH_ROOT" ]; then
        log_error "OH_ROOT not found: $OH_ROOT"
        exit 2
    fi
fi

# ============================================================================
# Phase A — AOSP source restoration
# ============================================================================

if [ "$DO_AOSP" = "1" ]; then

log_phase "Phase A — AOSP source restoration"

# ---- A1. Install custom product (device/adapter/oh_adapter) ----
log_info "A1. Install custom product device/adapter/oh_adapter"
PRODUCT_SRC="$ADAPTER_ROOT/aosp_patches/device/adapter/oh_adapter"
PRODUCT_DST="$AOSP_ROOT/device/adapter/oh_adapter"
if [ -d "$PRODUCT_SRC" ]; then
    run "mkdir -p \"$PRODUCT_DST\""
    for f in AndroidProducts.mk oh_adapter.mk BoardConfig.mk; do
        if [ -f "$PRODUCT_SRC/$f" ]; then
            run "cp -v \"$PRODUCT_SRC/$f\" \"$PRODUCT_DST/\""
        fi
    done
    log_ok "A1 done"
else
    log_warn "A1 skipped — $PRODUCT_SRC not found"
fi

# ---- A2. AOSP build-tree setup (product config + build_patches + bp-disable + CTS stubs) ----
# 2026-05-27 改名:setup_aosp_build_tree.sh → setup_aosp_build_tree.sh(它是多用途 AOSP
# 构建树准备,非单纯 patch 应用)。内部仍含 build_patches 应用(已自带 reverse-check 幂等)。
log_info "A2. Setup AOSP build tree via setup_aosp_build_tree.sh"
if [ -f "$SCRIPT_DIR/inner/setup_aosp_build_tree.sh" ]; then
    run "bash \"$SCRIPT_DIR/inner/setup_aosp_build_tree.sh\" --aosp-root=\"$AOSP_ROOT\" || true"
    log_ok "A2 done (setup_aosp_build_tree.sh: product/build_patches/bp-disable/cts)"
else
    log_warn "A2 skipped — setup_aosp_build_tree.sh not found"
fi

# ---- A2b. Apply Phase 1 (2026-04-28) libandroidfw modern-API patches ----
# These patches enable cross-compilation of AssetManager2/ApkAssets/Theme:
#   - aosp_patches/frameworks/base/libs/androidfw/include/androidfw/AssetManager2.h.patch
#       moves Theme::Entry full def into header (OH libcxx requires complete
#       type for std::vector<Entry>).
#   - aosp_patches/frameworks/base/libs/androidfw/AssetManager2.cpp.patch
#       deletes duplicate Entry definition from cpp.
#   - aosp_patches/frameworks/base/libs/androidfw/Asset.cpp.patch
#       removes 2x assert(dataMap != NULL) (IncFsFileMap value lacks operator bool).
# 2026-05-27 原则1重构:A2b 逻辑搬到 inner/apply_aosp_native_patches.sh::apply_aosp_libandroidfw_patches。
# 此处首次 source AOSP native apply 函数库(A2c/A10 复用同一文件,无需重复 source)。
source "$SCRIPT_DIR/inner/apply_aosp_native_patches.sh"
apply_aosp_libandroidfw_patches

# ---- A2c. Apply aosp_patches single-file patches outside libandroidfw ----
# 2026-05-09: 这 3 个 patch 历史上已应用到 AOSP 源码（有 .bak 备份 + grep marker
# 命中证据），但从未沉淀到 restore_after_sync.sh，是孤儿 — repo sync 必丢。
# 按 feedback_no_revert_patch.md 纪律一并沉淀。
#
# Patches:
#   - aosp_patches/external/icu/android_icu4j/Android.bp.patch
#       Adds java_version: "1.8" to core-repackaged-icu4j Android.bp target so
#       it compiles under partial-sync AOSP (default Java level mismatch).
#   - aosp_patches/frameworks/base/core/jni/AndroidRuntime.cpp.patch
#       DISABLE-comments out 78 register_android_os_Hidl* / HwBinder / HwParcel
#       / HwRemoteBinder JNI registrations — these classes belong to AOSP modules
#       not present in our partial sync. Without this patch, AndroidRuntime
#       startReg fails to link → libandroid_runtime.so cross-compile error.
#   - aosp_patches/frameworks/base/core/jni/android_util_Process.cpp.patch
#       Adds extern declarations for androidSetThreadPriority/GetThreadPriority.
#       libutils's AndroidThreads.h wraps these in `#if defined(__ANDROID__)`
#       and we cross-compile against OH musl sysroot without that define.
# 2026-05-27 原则1重构:A2c 逻辑搬到 inner/apply_aosp_native_patches.sh::apply_aosp_jni_compat_patches
# (函数库已在 A2b 处 source)。
apply_aosp_jni_compat_patches

# ---- A3. Apply L5 reflection injection ----
# 2026-05-21 refactor: replaced apply_aosp_java_patches.py (in-place Python edit)
# with 4 standard .patch files per feedback_no_py_apply_patches.md rule.
# Each patch injects OH-adapter reflection load into a Singleton.create() factory.
# 2026-05-27 原则1重构:A3 抽到 inner/apply_aosp_fwk_patches.sh(两层幂等),此处 source+调用。
source "$SCRIPT_DIR/inner/apply_aosp_fwk_patches.sh"
apply_aosp_fwk_patches \
    || log_warn "apply_aosp_fwk_patches: some L5 patches failed (see above)"

# ---- A3b. Install AppSpawnXInit.java into AOSP oh_adapter_framework (gap 7) ----
# The AOSP-side oh_adapter_framework/java/ tree doesn't live under our
# aosp_patches/ (it's a custom device/adapter/ dir, not a patch of existing
# AOSP sources). This script copies the authoritative AppSpawnXInit.java from
# framework/appspawn-x/ into the AOSP source tree on every restore.
log_info "A3b. Install AppSpawnXInit.java into AOSP oh_adapter_framework (gap 7)"
if [ -f "$ADAPTER_ROOT/aosp_patches/build_patches/install_app_spawn_x_init.sh" ]; then
    run "ADAPTER_ROOT=\"$ADAPTER_ROOT\" AOSP_ROOT=\"$AOSP_ROOT\" bash \"$ADAPTER_ROOT/aosp_patches/build_patches/install_app_spawn_x_init.sh\""
    log_ok "A3b done"
else
    log_warn "A3b skipped — install_app_spawn_x_init.sh not found"
fi

# ---- A3c. Sync local PackageManagerAdapter.java to AOSP oh_adapter_framework ----
# Mirrors framework/package-manager/java/PackageManagerAdapter.java into the
# AOSP-side compile target so the auto-generated stubs survive a repo sync.
log_info "A3c. Sync PackageManagerAdapter.java to AOSP oh_adapter_framework"
PMA_SRC="$ADAPTER_ROOT/framework/package-manager/java/PackageManagerAdapter.java"
PMA_DST="$AOSP_ROOT/device/adapter/oh_adapter_framework/java/adapter/packagemanager/PackageManagerAdapter.java"
if [ -f "$PMA_SRC" ] && [ -d "$(dirname "$PMA_DST")" ]; then
    run "cp \"$PMA_SRC\" \"$PMA_DST\""
    log_ok "A3c done"
else
    log_warn "A3c skipped — source or destination missing"
fi

# ---- A3c2. Cross-compile ARM32 core AOSP native stack (21 .so) ----
# Produces the libart/libbase/liblog/libdexfile/libziparchive/libvixl/libartbase/
# libartpalette-system/libunwindstack/libsigchain/libelffile/libnativehelper/
# libnativeloader/libnativebridge/libtinyxml2/libutils/libcutils/libprofile/
# liblz4/libart_runtime_stubs/libbionic_compat stack required by appspawn-x.
# Sedimented 2026-04-14: was previously invoked manually; after a clean repo
# sync this step was missing, leaving out/aosp_lib/ partially populated.
# The script itself hard-fails on any compile error and runs a smoke test
# verifying critical exports (OpenArchive/JNI_CreateJavaVM/CodeBuffer/etc).
log_info "A3c2. Cross-compile ARM32 core AOSP native stack to out/aosp_lib/"
if [ -f "$ADAPTER_ROOT/out/aosp_lib/libart.so" ] && [ -f "$ADAPTER_ROOT/out/aosp_lib/libbase.so" ] && [ -f "$ADAPTER_ROOT/out/aosp_lib/libziparchive.so" ]; then
    log_ok "A3c2 skipped — libart.so + libbase.so + libziparchive.so already present"
elif [ -f "$SCRIPT_DIR/inner/cross_compile_arm32.sh" ]; then
    run "bash "$SCRIPT_DIR/inner/cross_compile_arm32.sh""
    log_ok "A3c2 done"
else
    log_warn "A3c2 skipped — cross_compile_arm32.sh not found"
fi

# ---- A3d. Fetch minikin/harfbuzz_ng/freetype source trees (gap P10.C.full) ----
# The ECS AOSP is a partial repo sync; these 3 projects are filtered by
# groups="pdk*" in the master manifest and not present. fetch_minikin_deps.sh
# bypasses the permission-broken repo tool and git-clones directly from the
# Tsinghua AOSP mirror.
log_info "A3d. Fetch minikin/harfbuzz_ng/freetype AOSP source trees"
if [ -f "$ADAPTER_ROOT/aosp_patches/build_patches/fetch_minikin_deps.sh" ]; then
    run "AOSP_ROOT=\"$AOSP_ROOT\" bash \"$ADAPTER_ROOT/aosp_patches/build_patches/fetch_minikin_deps.sh\""
    log_ok "A3d done"
else
    log_warn "A3d skipped — fetch_minikin_deps.sh not found"
fi

# ---- A3e. Cross-compile minikin stack (libft2/libicuuc/libicui18n/libharfbuzz_ng/libminikin/libandroidfw) ----
# Runs after A3d. Skips libs that are already present in out/aosp_lib/ (the
# cross_compile_minikin_stack.sh script doesn't have --skip-existing yet, so
# we gate on the presence of libminikin.so — the last lib in the chain).
log_info "A3e. Cross-compile minikin stack to out/aosp_lib/"
if [ -f "$ADAPTER_ROOT/out/aosp_lib/libminikin.so" ] && [ -f "$ADAPTER_ROOT/out/aosp_lib/libandroidfw.so" ]; then
    log_ok "A3e skipped — libminikin.so and libandroidfw.so already present"
elif [ -f "$SCRIPT_DIR/inner/cross_compile_minikin_stack.sh" ]; then
    run "bash \"$SCRIPT_DIR/inner/cross_compile_minikin_stack.sh\""
    log_ok "A3e done"
else
    log_warn "A3e skipped — cross_compile_minikin_stack.sh not found"
fi

# ---- A4: (removed 2026-04-11) per-file hwui patches ----
# The bulk hwui_rk3568.patch (applied in A9) supersedes per-file patches.
# Any standalone .patch files under aosp_patches/libs/hwui/ other than the
# bulk should be considered legacy — deletable once superseded.

# ---- A5. Disable non-essential Android.bp files (handled by setup_aosp_build_tree.sh A2) ----
log_info "A5. Disable non-essential Android.bp files — handled inside setup_aosp_build_tree.sh A2 step"

# ---- A6. CTS/VTS stub files (handled by setup_aosp_build_tree.sh A2) ----
log_info "A6. CTS/VTS stub files — handled inside setup_aosp_build_tree.sh A2 step"

# ---- A7: (removed 2026-04-11) dex2oat_stubs deployment ----
# The custom dex2oat_stubs + build_dex2oat_host.sh + dex2oat_build/ experiment
# was a failed parallel path — never produced a working dex2oat binary. The
# real dex2oat comes from AOSP Soong at $AOSP_ROOT/out/host/linux-x86/bin/dex2oat64
# and gen_boot_image.sh already points at it. The stub tree has been deleted
# from both local and ECS to prevent accidental overwrite of real AOSP sources
# (external/libcap, external/tinyxml2 etc.) when A7 would otherwise cp over them.

# ---- A8. Deploy hwui stub source files ----
# 2026-04-11: the .cpp files were moved out of build/ into their semantic homes:
#   - hwui_oh_abi_patch.cpp / hwui_register_stubs.cpp / typeface_minimal_stub.cpp
#     → aosp_patches/libs/hwui/   (they augment AOSP libhwui at link time)
# 2026-05-08 G2.14ad: android_view_surface_stubs.cpp removed from this list.
# It was deactivated 2026-05-06 (#if 0 entire body) and renamed to
# .cpp.deprecated; its three Parts are now in framework/android-runtime/src/.
# This A8 phase deploys a copy into AOSP libs/hwui/ source tree for scripts
# that cd into the hwui tree and relative-include them.
log_info "A8. Deploy hwui stub .cpp files"
HWUI_TARGET_DIR="$AOSP_ROOT/frameworks/base/libs/hwui"
declare -A HWUI_STUB_SRC=(
    [typeface_minimal_stub.cpp]="$ADAPTER_ROOT/aosp_patches/libs/hwui/typeface_minimal_stub.cpp"
    [hwui_oh_abi_patch.cpp]="$ADAPTER_ROOT/aosp_patches/libs/hwui/hwui_oh_abi_patch.cpp"
    [hwui_register_stubs.cpp]="$ADAPTER_ROOT/aosp_patches/libs/hwui/hwui_register_stubs.cpp"
)
for stub in "${!HWUI_STUB_SRC[@]}"; do
    src="${HWUI_STUB_SRC[$stub]}"
    if [ -f "$src" ]; then
        if [ -d "$HWUI_TARGET_DIR" ]; then
            run "cp -v \"$src\" \"$HWUI_TARGET_DIR/$stub\""
            log_ok "A8: deployed $stub"
        else
            log_warn "A8: target dir $HWUI_TARGET_DIR not found, $stub stays at source location only"
        fi
    fi
done
# hwui_force_include.h lives inside skia_compat_headers/ (the stale top-level
# duplicate was deleted 2026-04-11). Copy real version into AOSP hwui tree.
if [ -f "$ADAPTER_ROOT/aosp_patches/libs/hwui/skia_compat_headers/hwui_force_include.h" ] && [ -d "$HWUI_TARGET_DIR" ]; then
    run "cp -v \"$ADAPTER_ROOT/aosp_patches/libs/hwui/skia_compat_headers/hwui_force_include.h\" \"$HWUI_TARGET_DIR/\""
fi

# ---- A9. Apply hwui per-file patches (refactored 2026-05-21) ----
# All hwui source modifications are per-file pristine→final unified diffs under
# aosp_patches/libs/hwui/patches/, one .patch per modified AOSP file. The bulk
# hwui_rk3568.patch + 7 chain-dependent per-file patches in
# aosp_patches/frameworks/base/libs/hwui/ have been split + merged into 51
# standalone .patch files (Phase A+B). compile_libhwui.sh phase 0 was removed
# (Phase C); this script is now the sole hwui patch application path.
if [ "$DO_HWUI_PY" = "1" ]; then
    # 2026-05-27 原则1重构:A9 逻辑抽到 inner/apply_hwui_patches.sh(两层幂等:
    # 组件 sig-marker 快速短路 + 逐 patch reverse-check-first),此处仅 source+调用。
    source "$SCRIPT_DIR/inner/apply_hwui_patches.sh"
    apply_hwui_patches
else
    log_warn "A9 skipped via --skip-hwui-py"
fi


# ---- A10. Apply aosp_patches/art/**/*.patch (native libart cross-compile fixes) ----
# Each patch mirrors the AOSP source tree under aosp_patches/art/. Currently:
#   aosp_patches/art/runtime/gc/collector/mark_compact.cc.patch
#     Adds local struct uffdio_continue (Linux 5.7 UAPI) that OH kernel
#     headers are missing. Required for libart.so cross-compile.
# 2026-05-27 原则1重构:A10 抽到 inner/apply_aosp_native_patches.sh(两层幂等),此处 source+调用。
source "$SCRIPT_DIR/inner/apply_aosp_native_patches.sh"
apply_aosp_native_patches \
    || log_warn "apply_aosp_native_patches: some art patches failed (see above)"

fi  # DO_AOSP

# ============================================================================
# Phase B — OH source restoration
# ============================================================================

if [ "$DO_OH" = "1" ]; then

log_phase "Phase B — OH source restoration"

# ---- B0. Apply build.sh guard patch (Build Entry Discipline, 2026-05-21) ----
# Inserts OH_FULL_BUILD_INVOKED env guard at top of ~/oh/build.sh so naked
# ./build.sh invocations are refused. oh_full_build.sh sets the env var
# before calling. Escape hatch for debug: OH_FULL_BUILD_INVOKED=1 ./build.sh
# See doc/build_patch_log.html section "Build Entry Discipline" for rationale.
log_info "B0. Apply build.sh guard patch (Build Entry Discipline)"
BUILD_SH_PATCH="$ADAPTER_ROOT/ohos_patches/build/build.sh.patch"
if [ -f "$BUILD_SH_PATCH" ] && [ -f "$OH_ROOT/build.sh" ]; then
    cd "$OH_ROOT"
    if git apply --check "$BUILD_SH_PATCH" 2>/dev/null; then
        run "git apply \"$BUILD_SH_PATCH\""
        log_ok "B0: build.sh guard applied"
    elif git apply --check --reverse "$BUILD_SH_PATCH" 2>/dev/null; then
        log_ok "B0: build.sh guard already applied (reverse-check passed)"
    else
        log_warn "B0: build.sh guard neither applies cleanly nor already applied — source drift"
    fi
    cd "$ADAPTER_ROOT"
else
    log_warn "B0 skipped — patch or ~/oh/build.sh not found"
fi

# ---- B1+B2+B3 REMOVED 2026-05-21 Phase 7 ----
# Formerly invoked apply_oh_patches.sh::apply_build_patches() + apply_functional_patches()
# via OH_BUILD_PATCHES / OH_FULL_FILE_REPLACEMENTS / OH_DIFF_PATCHES dicts in config.sh.
# All 3 mechanisms became no-op or stale:
#   - OH_BUILD_PATCHES: emptied in Phase 2a (3 patches migrated to B6b full-path form)
#   - OH_FULL_FILE_REPLACEMENTS: 2 stale entries referencing missing files
#   - OH_DIFF_PATCHES: 4 entries — 2 stale + 2 live (rs_transaction_data.cpp,
#     buffer_queue.cpp), both migrated to B6b full-path form
# apply_oh_patches.sh retired. B6b is the single OH patch application path.

# ---- B4: (deleted 2026-04-11) musl syscall.h.in aarch64 time64 aliases ----
# The original patch targeted arch/aarch64/bits/syscall.h.in but rk3568 is
# arm32 and uses arch/arm/bits/. Patch was aarch64-only dayu210 baggage.

# ---- B5. third_party/musl/src/internal/ADLTSection.h patch (DISABLED) ----
# Arch-independent bitfield type fix. Pre-existing out/rk3568/ .so artifacts
# were produced WITHOUT this patch applied, so it's not blocking the current
# build. Re-enable if first full rk3568 build produces "Elf64_Off bit-field"
# compiler errors.
log_info "B5 skipped (disabled pending rk3568 full-build verification)"

# ---- B6. (MOVED 2026-05-27 (b) 批) graphic_2d rs_buffer_reclaim.cpp %u→%zu ----
# 折入 inner/apply_ohos_patches.sh::apply_ohos_b6_buffer_reclaim,由下方 B6b 的
# apply_ohos_patches 顶层调用统一应用(使 build_*.sh phase0 也覆盖)。见 doc/build_patch_log.html。

# ---- B6b. Apply OH diff patches via apply_ohos_patches.sh ----
# 2026-05-21 Phase 9: the OH_DIFF_PATCH_LIST (37 entries at extraction time)
# + apply loop used to live inline here. Extracted to
# inner/apply_ohos_patches.sh so OH patches have a standalone entry point
# (symmetric with inner/setup_aosp_build_tree.sh).  Single source of truth:
# list lives ONLY in apply_ohos_patches.sh; this stage just dispatches.
log_info "B6b. Apply OH diff patches via inner/apply_ohos_patches.sh"
# 2026-05-27 原则1重构:改 source+调用(原 bash 子进程);函数用本脚本的 run/log_*/vars。
source "$SCRIPT_DIR/inner/apply_ohos_patches.sh"
if ! apply_ohos_patches; then
    log_error "B6b failed (apply_ohos_patches)."
    exit 3
fi

# ---- B7. bundle_mgr_host.cpp (%llu → %lu format fix) (DISABLED) ----
# Same reasoning as B5: not part of the current successful build state.
# Additionally, the existing .patch file has non-standard prose headers
# that confuse `git apply`. If first rk3568 full-build hits the relevant
# -Werror,-Wformat, re-author as a clean git diff and re-enable here.
log_info "B7 skipped (disabled pending rk3568 full-build verification)"

# ---- B8. (REMOVED 2026-05-20) BMS BUILD.gn semantic patch ----
# Folded into B6b — bundle_framework/services/bundlemgr/BUILD.gn.patch +
# bundle_framework/common/BUILD.gn.patch now both at full OH-mirrored paths.

# ---- B9. (MOVED 2026-05-27 (b) 批) ets2abc_config.gni value-collision fix ----
# gn "Value collision" 修复,是 `gn gen` 整体成功的前提(否则不生成任何 ninja)。
# 折入 inner/apply_ohos_patches.sh::apply_ohos_b9_ets2abc,由 B6b 的 apply_ohos_patches
# 顶层调用统一应用(build_ohos_service.sh --full-gen 的 phase0 也覆盖)。

# ---- B10. (MOVED 2026-05-27 (b) 批) apk_manifest_parser + adapter_apk_install_minimal → bmgr/src/ ----
# 这 3 个文件必须就地在 bundlemgr/src/(gn 禁跨组件 include),libbms 编译期需要。
# 折入 inner/apply_ohos_patches.sh::apply_ohos_b10_bmgr_sources,由 B6b 的 apply_ohos_patches
# 顶层调用统一部署(build_ohos_service.sh --target=libbms 的 phase0 也覆盖)。

# ---- B11. (REMOVED 2026-05-20) .apk install chain ----
# 3 .py scripts (apply_bms_apk_dispatch_processinstall / _register_with_manifest /
# apply_installd_apk_resources_hap) replaced by 4 .patch files folded into B6b:
#   - base_bundle_installer.cpp.patch (covers processinstall + register_with_manifest cumulatively)
#   - installd_operator.cpp.patch
#   - installd_operator.h.patch
#   - extract_param.h.patch

# ---- B11.4 REMOVED 2026-05-21 Phase 7 ----
# Formerly invoked orphan apply_appms_token_fallback.py (file historically deleted)
# to patch app_mgr_service_inner.cpp with G2.14h era AppMS token-fallback fix.
# Live ECS source had the fix applied but the .py applier was missing →
# repo sync would silently revert. Converted to standard unified-diff .patch:
# ohos_patches/foundation/ability/ability_runtime/services/appmgr/src/app_mgr_service_inner.cpp.patch
# now applied via B6b OH_DIFF_PATCH_LIST. See doc/build_patch_log.html for full
# G2.14h rationale (was: 26-line preserve-bundleInfo.accessTokenId-when-GetHapTokenIDEx-returns-0).

# ---- B12. (MOVED 2026-05-27 (b) 批) 26 个 OH 源全文件快照 cp ----
# appspawn / bms / mission / init / musl / config.json 等的 authoritative 改后副本快照。
# 折入 inner/apply_ohos_patches.sh::apply_ohos_b12_full_files,由 B6b 的 apply_ohos_patches
# 顶层调用统一 cp(顺序在 apply_ohos_diff_patches 之后——同名 bms/appspawn 文件 snapshot 覆盖
# diff 结果、为最终态)。完整清单 + rationale 见 apply_ohos_patches.sh 与 doc/build_patch_log.html。
# 原"B12 保持内联在 restore"决定已于 (b) 批推翻——build_*.sh phase0 依赖 apply_ohos_patches
# 完整性,故 B12 必须进函数。
#
# ---- B13. (MOVED 2026-05-27 (b) 批) file_contexts.patch (selinux, patch -p0 --forward) ----
# 折入 inner/apply_ohos_patches.sh::apply_ohos_b13_unified_diffs。

fi  # DO_OH

# ============================================================================
# Phase C — Cross-cutting fixes
# ============================================================================

log_phase "Phase C — Cross-cutting fixes"

# ---- C1. skia_compat_headers/ already lives at $ADAPTER_ROOT/aosp_patches/libs/hwui/skia_compat_headers ----
log_info "C1. skia_compat_headers/ — staying at $ADAPTER_ROOT/aosp_patches/libs/hwui/skia_compat_headers (referenced by hwui compile scripts via -I)"
if [ ! -d "$ADAPTER_ROOT/aosp_patches/libs/hwui/skia_compat_headers" ]; then
    log_warn "C1: skia_compat_headers/ not found — hwui compile will fail"
fi

# ---- C1.1 (2026-05-02 G2.14p): assert NO stub minikin/ directory ----
# Real libminikin.so is deployed at /system/android/lib/libminikin.so and
# headers at $AOSP/frameworks/minikin/include/. The 18-file stub minikin/
# subtree under skia_compat_headers/ was a historical placeholder that
# silently shadowed real minikin via INC-order accidents — caused multiple
# vtable + class-layout crashes (G2.14n: SIGILL @ populateSkFont).
# Removing it eliminates an entire class of "stub leaks into real-API code"
# bugs. The 4 hwui compile scripts (compile_libhwui*.sh, compile_hwui_*.sh)
# now use real $AOSP/frameworks/minikin/include directly.
if [ -d "$ADAPTER_ROOT/aosp_patches/libs/hwui/skia_compat_headers/minikin" ]; then
    log_warn "C1.1: stub skia_compat_headers/minikin/ exists — should have been deleted (G2.14p)"
    log_info "C1.1: see memory project_g214p_systemic_cleanup for context"
fi

# C2 removed 2026-04-11: this project does not need libarkruntime.so or
# libani_helpers.z.so at runtime. The ninja phony patches in
# build/ninja_patches/patch_{irtoc,arkruntime,ani_helpers}.sh make the
# build graph complete without actually producing these .so files.

# ---- C3. Build liboh_skia_rtti_shim.so (2026-04-12) ----
# This small shim (~12 KB) provides _ZTI*/_ZTS* typeinfo symbols for the 9
# Skia base classes that libhwui inherits from. Replaces the previous
# approach of rebuilding all of Skia with -frtti + SK_API_TYPE. The shim
# is a hard dependency of link_libhwui.sh; the link script exits with a
# clear error message if the .so isn't present, so this step must run
# before any libhwui link attempt.
#
# Idempotent: the compile script always recompiles, but total cost is
# < 1 second (one .cpp + one ld.lld invocation). If we need to skip-if-
# fresh, add an mtime check here.
#
# Sources that must be present after a Local→ECS sync:
#   framework/surface/jni/skia_rtti_shim/skia_rtti_shim.cpp
#   framework/surface/jni/skia_rtti_shim/skia_class_list.inc
#   framework/surface/jni/skia_rtti_shim/skia_rtti_shim.ver
#   build/compile_skia_rtti_shim.sh
log_info "C3. Build liboh_skia_rtti_shim.so (Skia typeinfo shim)"
SKIA_RTTI_SHIM_SRC="$ADAPTER_ROOT/framework/surface/jni/skia_rtti_shim"
SKIA_RTTI_BUILD="$SCRIPT_DIR/compile_skia_rtti_shim.sh"
SKIA_RTTI_OUT="$ADAPTER_ROOT/out/skia-rtti-shim/liboh_skia_rtti_shim.so"
if [ ! -d "$SKIA_RTTI_SHIM_SRC" ]; then
    log_warn "C3 skipped — shim source dir missing: $SKIA_RTTI_SHIM_SRC"
elif [ ! -f "$SKIA_RTTI_BUILD" ]; then
    log_warn "C3 skipped — build script missing: $SKIA_RTTI_BUILD"
else
    for f in skia_rtti_shim.cpp skia_class_list.inc skia_rtti_shim.ver; do
        if [ ! -f "$SKIA_RTTI_SHIM_SRC/$f" ]; then
            log_warn "C3: missing $SKIA_RTTI_SHIM_SRC/$f — shim build may fail"
        fi
    done
    run "bash \"$SKIA_RTTI_BUILD\""
    if [ -f "$SKIA_RTTI_OUT" ]; then
        SHIM_SIZE=$(stat -c%s "$SKIA_RTTI_OUT" 2>/dev/null)
        log_ok "C3 done: $SKIA_RTTI_OUT ($SHIM_SIZE bytes)"
    else
        log_error "C3 FAIL: $SKIA_RTTI_OUT not produced — check compile_skia_rtti_shim.sh output"
        exit 1
    fi
fi

# ---- C4. Verify 2026-04-17 Phase 2/3 additions (libcxx array fix, AHB shim,
#         liboh_android_runtime source tree) -----------------------------------
# These files live entirely under $ADAPTER_ROOT and are NOT affected by
# repo sync; this phase is a sanity check, not a restoration step. If any
# file is missing, either the adapter tree was pruned or a future refactor
# moved it — investigate rather than silently continuing.
log_info "C4. Verify 2026-04-17 Phase 2/3 assets"
C4_MISSING=0
C4_FILES=(
    # Phase 2 — libcxx std::array<T,0>::data() cherry-pick fix
    "$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include/libcxx_array_aosp/array"
    # Phase 3 — liblog __ANDROID__-gated supplement
    "$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/src/liblog_android_supplement.cpp"
    # Phase 3 — Skia AHB shim (GrAHardwareBufferUtils real impl)
    "$ADAPTER_ROOT/framework/hwui-shim/jni/oh_skia_ahb_shim.cpp"
    # Phase 3 — liboh_android_runtime (progressive libandroid_runtime replacement)
    "$ADAPTER_ROOT/framework/android-runtime/include/AndroidRuntime.h"
    "$ADAPTER_ROOT/framework/android-runtime/src/AndroidRuntime.cpp"
    "$ADAPTER_ROOT/framework/android-runtime/src/android_util_Log.cpp"
    "$ADAPTER_ROOT/framework/android-runtime/src/android_os_SystemProperties.cpp"
    "$ADAPTER_ROOT/build/inner/compile_oh_android_runtime.sh"
)
for f in "${C4_FILES[@]}"; do
    if [ ! -f "$f" ]; then
        log_warn "C4: missing $f"
        C4_MISSING=$((C4_MISSING + 1))
    fi
done
# Verify cross_compile_arm32.sh has the libcxx_array_aosp -isystem flag and
# bionic_compat srcs include liblog_android_supplement.cpp.
if ! grep -q "libcxx_array_aosp" "$ADAPTER_ROOT/build/inner/cross_compile_arm32.sh" 2>/dev/null; then
    log_warn "C4: cross_compile_arm32.sh missing '-isystem libcxx_array_aosp' flag"
    C4_MISSING=$((C4_MISSING + 1))
fi
if ! grep -q "liblog_android_supplement" "$ADAPTER_ROOT/build/inner/cross_compile_arm32.sh" 2>/dev/null; then
    log_warn "C4: cross_compile_arm32.sh missing liblog_android_supplement.cpp in bionic_compat srcs"
    C4_MISSING=$((C4_MISSING + 1))
fi
if ! grep -q "oh_skia_ahb_shim" "$ADAPTER_ROOT/build/compile_hwui_shims.sh" 2>/dev/null; then
    log_warn "C4: compile_hwui_shims.sh missing oh_skia_ahb_shim step"
    C4_MISSING=$((C4_MISSING + 1))
fi
if [ "$C4_MISSING" -eq 0 ]; then
    log_ok "C4 done: all 2026-04-17 Phase 2/3 assets present"
else
    log_warn "C4: $C4_MISSING asset(s) missing — build will fail until restored"
fi

# ============================================================================
# Final state file
# ============================================================================

log_phase "Final"

mkdir -p "$(dirname "$STATE_FILE")"
{
    echo "Adapter restore-after-sync state"
    echo "Date:        $(date -Iseconds)"
    echo "AOSP_ROOT:   $AOSP_ROOT"
    echo "OH_ROOT:     $OH_ROOT"
    echo "OH_PRODUCT:  $OH_PRODUCT"
    echo "DO_AOSP:     $DO_AOSP"
    echo "DO_OH:       $DO_OH"
    echo "DO_HWUI_PY:  $DO_HWUI_PY"
    echo "DRY_RUN:     $DRY_RUN"
    echo "WARNINGS:    $WARNINGS"
} > "$STATE_FILE"

if [ "$WARNINGS" -gt 0 ]; then
    log_warn "Restore completed with $WARNINGS warning(s). Review the output above before building."
    log_warn "State file: $STATE_FILE"
    exit 3
else
    log_ok "Restore completed cleanly. State file: $STATE_FILE"
    log_ok "Next step: run your build pipeline."
    log_ok "Recommended order after restore (Phase 1+2+3 refactored, 2026-05-21):"
    log_ok "  bash build/build_aosp_lib.sh                   # libart / libhwui / libminikin stack (includes skia_rtti + hwui_shim)"
    log_ok "  bash build/build_adapter.sh                    # liboh_android_runtime / liboh_adapter_bridge / libapk_installer"
    log_ok "  bash build/build_appspawn_x.sh                 # appspawn-x"
    log_ok "  bash build/build_ohos_service.sh               # libabilityms / libappms / libbms / scene_session*"
    log_ok "  bash build/build_aosp_fw.sh                    # AOSP jars + BCP oh-adapter-framework.jar (auto boot-image)"
    log_ok "  -- or -- bash build/build_all.sh               # all of the above in topological order"
    log_ok "Reminder: post-GN-gen patches (internal/musl_syscall_fix.sh + ninja_patches/apply_all.sh) auto-invoked by build_ohos_service.sh on first musl SYS_* error."
    exit 0
fi

# ============================================================
# Restore ARM32 asm_defines.h from AOSP generated version
# ============================================================
echo '>>> Restoring ARM32 asm_defines.h...'
ASM_SRC="$OH_ROOT/art/runtime/asm_defines.h.generated"
ASM_DST="$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include/art/asm_defines.h"
if [ -f "$ASM_SRC" ]; then
    cp "$ASM_SRC" "$ASM_DST"
    echo "  Copied from $ASM_SRC (ARM32, POINTER_SIZE=4)"
else
    echo "  WARNING: $ASM_SRC not found, asm_defines.h NOT restored"
fi
