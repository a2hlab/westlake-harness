#!/bin/bash
# build.sh - Top-level build entry point for Android-OH Adapter project
#
# Usage:
#   ./build.sh --target=oh-services [--oh-root=/root/oh] [--clean]
#   ./build.sh --target=aosp-framework [--aosp-root=/root/aosp]
#   ./build.sh --target=all [--oh-root=/root/oh] [--aosp-root=/root/aosp]
#   ./build.sh --help

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"

# Source shared config
source "$BUILD_DIR/config.sh"

# ============================================================
# Parse arguments
# ============================================================
TARGET=""
EXTRA_ARGS=()

for arg in "$@"; do
    case "$arg" in
        --target=*)     TARGET="${arg#*=}" ;;
        --oh-root=*)    export OH_ROOT="${arg#*=}" ;;
        --aosp-root=*)  export AOSP_ROOT="${arg#*=}" ;;
        --help|-h)
            echo "Android-OH Adapter Build System"
            echo ""
            echo "Usage: $0 --target=TARGET [OPTIONS]"
            echo ""
            echo "Targets:"
            echo "  oh-services      Build OH system services (abilityms, libappms, libwms, libbms)"
            echo "  aosp-framework   Build AOSP framework.jar + resources"
            echo "  cross-compile    Cross-compile AOSP native libs (OH Clang → musl)"
            echo "  adapter-modules  Build adapter modules via OH GN (partial)"
            echo "  all              Build everything in correct order"
            echo ""
            echo "Options:"
            echo "  --oh-root=PATH   OH source root (default: $OH_ROOT)"
            echo "  --aosp-root=PATH AOSP source root (default: $AOSP_ROOT)"
            echo "  --clean          Clean build"
            echo "  --skip-patches   Skip patch application"
            echo "  --skip-revert    Don't revert patches after build"
            echo "  --help           Show this help"
            echo ""
            echo "Examples:"
            echo "  $0 --target=oh-services --oh-root=/root/oh"
            echo "  $0 --target=oh-services --clean"
            echo ""
            echo "Output directory: $ADAPTER_OUT/"
            exit 0 ;;
        *)
            EXTRA_ARGS+=("$arg") ;;
    esac
done

if [ -z "$TARGET" ]; then
    log_error "No target specified. Use --target=oh-services (or --help)"
    exit 1
fi

# ============================================================
# Dispatch to target build script
# ============================================================

log_info "============================================"
log_info "Android-OH Adapter Build"
log_info "  Target:    $TARGET"
log_info "  OH root:   $OH_ROOT"
log_info "  AOSP root: $AOSP_ROOT"
log_info "  Output:    $ADAPTER_OUT"
log_info "============================================"

case "$TARGET" in
    oh-services)
        exec bash "$BUILD_DIR/oh_build.sh" --oh-root="$OH_ROOT" "${EXTRA_ARGS[@]}"
        ;;
    aosp-framework)
        log_info "Building AOSP framework (framework.jar + resources)..."
        log_info "Step 1: Apply AOSP patches"
        bash "$BUILD_DIR/apply_patches.sh" --aosp-root="$AOSP_ROOT"
        log_info "Step 2: Build"
        (
            export AOSP_ROOT ADAPTER_ROOT="$SCRIPT_DIR"
            source "$BUILD_DIR/build_env.sh"
            build_framework
        )
        ;;
    cross-compile)
        log_info "Cross-compiling AOSP native libraries (OH Clang → musl)..."
        bash "$BUILD_DIR/cross_compile_100pct.sh" --oh-root="$OH_ROOT" --aosp-root="$AOSP_ROOT" "${EXTRA_ARGS[@]}"
        ;;
    adapter-modules)
        log_warn "Target 'adapter-modules' is not yet fully implemented"
        log_info "Planned: appspawn-x + apk_installer via OH GN"
        log_info "Use cross-compile target for liboh_adapter_bridge.so"
        exit 1
        ;;
    all)
        log_info "Building all targets..."
        echo ""

        log_info "=== Step 1/4: OH System Services ==="
        bash "$BUILD_DIR/oh_build.sh" --oh-root="$OH_ROOT" "${EXTRA_ARGS[@]}"
        echo ""

        log_info "=== Step 2/4: AOSP Framework ==="
        bash "$BUILD_DIR/apply_patches.sh" --aosp-root="$AOSP_ROOT"
        ( export AOSP_ROOT ADAPTER_ROOT="$SCRIPT_DIR"; source "$BUILD_DIR/build_env.sh"; build_framework )
        echo ""

        log_info "=== Step 3/4: Cross-compile Native Libraries ==="
        bash "$BUILD_DIR/cross_compile_100pct.sh" --oh-root="$OH_ROOT" --aosp-root="$AOSP_ROOT"
        echo ""

        log_warn "=== Step 4/4: Adapter Modules === (appspawn-x pending Layer 4)"
        echo ""

        log_ok "Build complete"
        ;;
    *)
        log_error "Unknown target: $TARGET"
        log_error "Valid targets: oh-services, aosp-framework, adapter-modules, all"
        exit 1
        ;;
esac
