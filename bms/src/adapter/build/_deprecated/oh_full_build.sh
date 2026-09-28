#!/bin/bash
# [DEPRECATED Phase 1 — 2026-05-21] Use build_ohos_service.sh instead.
echo "[DEPRECATED] $(basename "$0") is wrapped by build_ohos_service.sh — Phase 4 will remove this script" >&2
# oh_full_build.sh - One-shot OH build wrapper
# Handles the musl syscall.h generation order issue automatically.
#
# Usage: oh_full_build.sh [--clean]
#   --clean: Delete out/$OH_PRODUCT_NAME before building (full rebuild)
#
# Target product: rk3568 (DAYU200) — set via $OH_PRODUCT_NAME in config.sh.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

OH_OUT="$OH_ROOT/out/$OH_PRODUCT_NAME"

# Parse args
CLEAN=false
for arg in "$@"; do
    case "$arg" in
        --clean) CLEAN=true ;;
    esac
done

if [ "$CLEAN" = true ]; then
    echo "[oh_full_build] Cleaning $OH_OUT..."
    rm -rf "$OH_OUT"
fi

# Step 1: Run build.sh (GN + ninja). First run may fail on musl.
echo "[oh_full_build] Starting build (product=$OH_PRODUCT_NAME)..."
cd "$OH_ROOT"
# Bypass build.sh guard (Build Entry Discipline 2026-05-21) — this is the
# authorized wrapper invocation. See ohos_patches/build/build.sh.patch.
export OH_FULL_BUILD_INVOKED=1
set +e
./build.sh --product-name "$OH_PRODUCT_NAME" --ccache \
    --gn-args "$OH_GN_ARGS" \
    --build-target abilityms \
    --build-target libappms \
    --build-target scene_session_manager \
    --build-target scene_session \
    --build-target libbms
BUILD_RC=$?
set -e

if [ $BUILD_RC -eq 0 ]; then
    echo "[oh_full_build] Build succeeded on first attempt!"
    exit 0
fi

# Check if it's the musl SYS_* issue
if grep -q 'SYS_futex_time64\|SYS_mmap\|SYS_openat' "$OH_OUT/error.log" 2>/dev/null; then
    echo "[oh_full_build] Detected musl SYS_* issue, applying fix..."
    bash "$SCRIPT_DIR/musl_syscall_fix.sh" "$OH_OUT"

    echo "[oh_full_build] Retrying with --fast-rebuild..."
    ./build.sh --product-name "$OH_PRODUCT_NAME" --ccache \
        --gn-args "$OH_GN_ARGS" --fast-rebuild \
        --build-target abilityms \
        --build-target libappms \
        --build-target scene_session_manager \
        --build-target scene_session \
        --build-target libbms
    echo "[oh_full_build] Build succeeded after musl fix!"
else
    echo "[oh_full_build] Build failed with non-musl error. Check $OH_OUT/error.log"
    exit 1
fi
