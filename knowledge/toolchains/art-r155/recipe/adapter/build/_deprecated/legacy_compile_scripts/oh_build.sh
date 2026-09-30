#!/bin/bash
# oh_build.sh - Build OH system services for the adapter project
#
# Usage: oh_build.sh [--oh-root=PATH] [--clean] [--skip-patches] [--skip-revert]
#
# Full lifecycle: apply patches -> build -> fix musl -> retry -> collect -> revert

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Parse arguments
CLEAN=false
SKIP_PATCHES=false
SKIP_REVERT=false

for arg in "$@"; do
    case "$arg" in
        --oh-root=*)     OH_ROOT="${arg#*=}" ;;
        --clean)         CLEAN=true ;;
        --skip-patches)  SKIP_PATCHES=true ;;
        --skip-revert)   SKIP_REVERT=true ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --oh-root=PATH    OH source root (default: $OH_ROOT)"
            echo "  --clean           Clean build (remove OH output dir)"
            echo "  --skip-patches    Skip patch application (assume already applied)"
            echo "  --skip-revert     Don't revert patches after build"
            echo "  --help            Show this help"
            exit 0 ;;
    esac
done

# ============================================================
# Cleanup handler: always revert patches on exit
# ============================================================
cleanup() {
    local exit_code=$?
    if [ "$SKIP_REVERT" = true ]; then
        log_warn "Skipping patch revert (--skip-revert)"
        return
    fi
    if [ -f "$PATCH_MARKER" ]; then
        log_info "Reverting patches..."
        "$SCRIPT_DIR/revert_oh_patches.sh" --oh-root="$OH_ROOT" || true
    fi
    exit $exit_code
}
trap cleanup EXIT

# ============================================================
# Main build flow
# ============================================================

log_info "============================================"
log_info "OH System Services Build"
log_info "  OH source: $OH_ROOT"
log_info "  Adapter:   $ADAPTER_ROOT"
log_info "  Targets:   ${OH_SERVICE_TARGETS[*]}"
log_info "============================================"

# Step 0: Prerequisites
check_prerequisites

# Step 1: Clean (optional)
if [ "$CLEAN" = true ]; then
    OH_OUT=$(detect_oh_output_dir)
    log_info "Cleaning $OH_OUT..."
    rm -rf "$OH_OUT" "$OH_ROOT/out/preloader" 2>/dev/null || true
fi

# Step 2: Apply patches
if [ "$SKIP_PATCHES" = true ]; then
    log_info "Skipping patch application (--skip-patches)"
else
    "$SCRIPT_DIR/apply_oh_patches.sh" --oh-root="$OH_ROOT" --type=build
fi

# Step 3: Build (first attempt)
log_info "Starting OH build (GN gen + Ninja)..."

BUILD_TARGETS=""
for t in "${OH_SERVICE_TARGETS[@]}"; do
    BUILD_TARGETS="$BUILD_TARGETS --build-target $t"
done

cd "$OH_ROOT"
set +e
./build.sh --product-name "$OH_PRODUCT_NAME" --ccache \
    --gn-args "$OH_GN_ARGS" \
    $BUILD_TARGETS \
    2>&1 | tee "$ADAPTER_ROOT/build/oh_build.log"
BUILD_RC=${PIPESTATUS[0]}
set -e

# Step 4: Check for musl syscall issue and retry if needed
if [ $BUILD_RC -ne 0 ]; then
    if grep -q "SYS_futex_time64\|SYS_mmap\|SYS_set_tid_address" "$ADAPTER_ROOT/build/oh_build.log"; then
        log_warn "Detected musl syscall.h issue - applying fix and retrying..."

        OH_OUT=$(detect_oh_output_dir)
        bash "$SCRIPT_DIR/oh_build_patches/musl_syscall_fix.sh" "$OH_OUT"

        log_info "Retrying build (ninja incremental)..."
        set +e
        ./build.sh --product-name "$OH_PRODUCT_NAME" --ccache \
            --gn-args "$OH_GN_ARGS" \
            $BUILD_TARGETS \
            2>&1 | tee "$ADAPTER_ROOT/build/oh_build.log"
        BUILD_RC=${PIPESTATUS[0]}
        set -e
    fi
fi

# Step 5: Check build result
if [ $BUILD_RC -ne 0 ]; then
    log_error "OH build failed (exit code $BUILD_RC)"
    log_error "Check build log: $ADAPTER_ROOT/build/oh_build.log"
    log_error "Check error log: $(detect_oh_output_dir)/error.log"
    exit 1
fi

log_ok "OH build completed successfully"

# Step 6: Collect artifacts
"$SCRIPT_DIR/collect_oh_artifacts.sh" --oh-root="$OH_ROOT"

log_ok "============================================"
log_ok "OH System Services Build Complete!"
log_ok "Artifacts in: $ADAPTER_OUT/oh-services/"
log_ok "============================================"
