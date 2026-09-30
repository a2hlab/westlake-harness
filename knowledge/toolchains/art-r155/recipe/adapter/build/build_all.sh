#!/bin/bash
# ============================================================================
# build_all.sh — Top-level: build EVERYTHING in topological order (Phase 1)
# ============================================================================
#
# Runs all 7 build_*.sh entries in dependency order. Estimated total time:
# 2-6 hours from clean, 20-60 min incremental. ALWAYS prompts for confirmation.
#
# Order (per dependency graph):
#   1. build_aosp_fw.sh      — Java jars (no boot-image; we do that ourselves later)
#   2. build_aosp_lib.sh     — Native ARM32 .so (libart, libhwui, ...)
#   3. build_ohos_service.sh — OH system service .so (depends on patched OH source)
#   4. build_adapter.sh      — Adapter own .so + oh-adapter-runtime.jar
#   5. build_appspawn_x.sh   — appspawn-x executable
#   6. build_dex2oat.sh      — host dex2oat64
#   7. build_boot_image.sh   — final boot image (requires #1 jars + #6 dex2oat)
#
# Run location: ECS only.
#
# Usage:
#   bash build_all.sh                # interactive confirmation
#   bash build_all.sh --yes          # skip confirmation (CI/automation only)
#   bash build_all.sh --clean        # clean rebuild of all stages
#   bash build_all.sh --help
# ============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Authorize calls into inner/ (helpers refuse direct invocation)
export BUILD_INNER_INVOKED=1

CLEAN=0
DRY_RUN=0
YES=0
JOBS=$(nproc 2>/dev/null || echo 4)

print_help() {
    cat <<EOF
Usage: $0 [--clean] [--yes] [-j N] [--dry-run] [--help]

Builds ALL adapter artifacts in topological order. Estimated 2-6 hours clean,
20-60 min incremental.

Options:
  --clean             Pass --clean to every stage (clean rebuild)
  --yes               Skip interactive confirmation prompt (CI mode)
  -j N                Parallel job count (default: $JOBS)
  --dry-run           Print what each stage would do without running
  --help              Show this help

Stage order:
  1. build_aosp_fw.sh      --no-boot-image  (we do boot-image at end ourselves)
  2. build_aosp_lib.sh
  3. build_ohos_service.sh
  4. build_adapter.sh      --no-boot-image  (would otherwise re-trigger via fw)
  5. build_appspawn_x.sh
  6. build_dex2oat.sh
  7. build_boot_image.sh
EOF
}

for arg in "$@"; do
    case "$arg" in
        --clean)        CLEAN=1 ;;
        --dry-run)      DRY_RUN=1; YES=1 ;;
        --yes|-y)       YES=1 ;;
        -j*)            JOBS="${arg#-j}" ;;
        --jobs=*)       JOBS="${arg#--jobs=}" ;;
        --help|-h)      print_help; exit 0 ;;
        *)              log_error "Unknown arg: $arg"; print_help; exit 1 ;;
    esac
done

# --- Estimate ---
if [ "$CLEAN" = "1" ]; then
    log_warn "=========================================="
    log_warn "  build_all.sh — CLEAN FULL REBUILD"
    log_warn "  Estimated time: 2-6 HOURS on ECS"
    log_warn "  Disk usage: ~30-60 GB additional"
    log_warn "=========================================="
else
    log_info "=========================================="
    log_info "  build_all.sh — incremental build"
    log_info "  Estimated time: 20-60 MIN on ECS"
    log_info "=========================================="
fi

log_info "Stages: aosp_fw -> aosp_lib -> ohos_service -> adapter -> appspawn_x -> dex2oat -> boot_image"
log_info "Output: $ADAPTER_ROOT/out/"

# --- Confirmation ---
if [ "$YES" = "0" ]; then
    echo
    read -r -p "Proceed? [y/N]: " ans
    case "$ans" in
        [yY]|[yY][eE][sS]) ;;
        *) log_warn "Aborted by user"; exit 0 ;;
    esac
fi

# --- Common forward args ---
COMMON_ARGS=()
[ "$CLEAN" = "1" ] && COMMON_ARGS+=(--clean)
[ "$DRY_RUN" = "1" ] && COMMON_ARGS+=(--dry-run)
COMMON_ARGS+=("-j$JOBS")

run_stage() {
    local stage="$1"; shift
    log_info "===== Stage: $stage ====="
    bash "$SCRIPT_DIR/$stage" "$@" || {
        log_error "Stage $stage FAILED — aborting build_all"
        exit 3
    }
}

# Disable per-stage boot-image auto-trigger; we run boot-image once at the end
run_stage "build_aosp_fw.sh" "${COMMON_ARGS[@]}" --no-boot-image
run_stage "build_aosp_lib.sh" "${COMMON_ARGS[@]}"
run_stage "build_ohos_service.sh" "${COMMON_ARGS[@]}"
run_stage "build_adapter.sh" "${COMMON_ARGS[@]}"
run_stage "build_appspawn_x.sh" "${COMMON_ARGS[@]}"
run_stage "build_dex2oat.sh" "${COMMON_ARGS[@]}"
run_stage "build_boot_image.sh" "${COMMON_ARGS[@]}"

log_ok "======================================"
log_ok "  build_all.sh COMPLETE"
log_ok "======================================"
log_info "Next: bash utils/pull_ecs_artifacts.sh (ECS->Local), then deploy/deploy_to_dayu200.sh"
