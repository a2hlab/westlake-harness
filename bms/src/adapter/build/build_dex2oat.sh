#!/bin/bash
# ============================================================================
# build_dex2oat.sh — dex2oat64 host tool build entry (Phase 1)
# ============================================================================
#
# Builds the host-side dex2oat64 used by build_boot_image.sh.
#
# Run location: ECS only.
# Output: out/host-tools/dex2oat64
#
# CRITICAL: dex2oat-host MUST be built with ART_USE_READ_BARRIER=false +
# ART_DEFAULT_GC_TYPE=CMS env to stay ABI-compatible with device libart.so
# (which is cross-compiled with CMS, no read barrier). compile_dex2oat_host.sh
# enforces this via fixed export — do not override.
#
# Usage:
#   bash build_dex2oat.sh                # build dex2oat64
#   bash build_dex2oat.sh --clean
# ============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Authorize calls into inner/ (helpers refuse direct invocation)
export BUILD_INNER_INVOKED=1

declare -a ALL_TARGETS=("dex2oat64")

CLEAN=0
DRY_RUN=0
JOBS=$(nproc 2>/dev/null || echo 4)
TARGETS=()

dispatch() {
    if [ "$DRY_RUN" = "1" ]; then
        log_info "[DRY-RUN] would: $*"
    else
        "$@"
    fi
}

print_help() {
    cat <<EOF
Usage: $0 [--clean] [--target=dex2oat64] [-j N] [--dry-run] [--help]

Builds host-side dex2oat64 tool.

Valid --target= values:
  dex2oat64  (only option; arg accepted for uniformity)

Options:
  --clean             Clean build artifacts before compiling
  --target=dex2oat64  Only target supported (default)
  -j N                Parallel job count (default: $JOBS)
  --dry-run           Print what would be executed, do not run
  --help              Show this help

Notes:
  - Required by build_boot_image.sh.
  - ABI compatibility with device libart.so is enforced via fixed env
    (ART_USE_READ_BARRIER=false, ART_DEFAULT_GC_TYPE=CMS).
EOF
}

for arg in "$@"; do
    case "$arg" in
        --clean)        CLEAN=1 ;;
        --dry-run)      DRY_RUN=1 ;;
        --target=*)     IFS=',' read -ra TARGETS <<< "${arg#--target=}" ;;
        -j*)            JOBS="${arg#-j}" ;;
        --jobs=*)       JOBS="${arg#--jobs=}" ;;
        --help|-h)      print_help; exit 0 ;;
        *)              log_error "Unknown arg: $arg"; print_help; exit 1 ;;
    esac
done

[ ${#TARGETS[@]} -eq 0 ] && TARGETS=("${ALL_TARGETS[@]}")

for t in "${TARGETS[@]}"; do
    [ "$t" = "dex2oat64" ] || { log_error "Unknown target: $t"; exit 1; }
done

log_info "build_dex2oat: clean=$CLEAN dry_run=$DRY_RUN jobs=$JOBS"

export OH_FULL_BUILD_INVOKED=1
FORWARD_ARGS=()
[ "$CLEAN" = "1" ] && FORWARD_ARGS+=(--clean)

log_info "Forwarding to compile_dex2oat_host.sh..."
dispatch bash "$SCRIPT_DIR/inner/compile_dex2oat_host.sh" "${FORWARD_ARGS[@]}"

log_ok "build_dex2oat complete"
