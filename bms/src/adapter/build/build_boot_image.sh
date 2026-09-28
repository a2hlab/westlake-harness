#!/bin/bash
# ============================================================================
# build_boot_image.sh — ART boot image build entry (Phase 1)
# ============================================================================
#
# Generates the 27-segment ARM32 ART boot image (9 BCP jars × 3 file types).
#
# Run location: ECS only.
# Output: out/boot-image/boot-<jar>.{art,oat,vdex}  (27 files)
#
# Requires:
#   - out/host-tools/dex2oat64 (built by build_dex2oat.sh)
#   - All BCP jars in out/aosp_fwk/ + out/adapter/ (built by build_aosp_fw.sh)
#
# CRITICAL: When deploying, ALL 27 segments must be pushed to device together,
# otherwise ART rejects checksum mismatch. The boot.{art,oat,vdex} aggregate
# files alone are NOT enough — see memory feedback_pull_all_boot_image_segments.md.
#
# Usage:
#   bash build_boot_image.sh             # build all 27 segments
#   bash build_boot_image.sh --clean
# ============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Authorize calls into inner/ (helpers refuse direct invocation)
export BUILD_INNER_INVOKED=1

# 9 BCP jars × 3 file types = 27 segments. Phase 1: no granular subset
# (gen_boot_image.sh builds whole image atomically). Listed for --help reference.
declare -a BCP_SEGMENTS=(
    "boot-framework"
    "boot-core-oj"
    "boot-core-icu4j"
    "boot-oh-adapter-framework"
    "boot-okhttp"
    "boot-bouncycastle"
    "boot-conscrypt"
    "boot-ext"
    "boot-ahat"
)

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
Usage: $0 [--clean] [--target=<list>] [-j N] [--dry-run] [--help]

Generates the 27-segment ARM32 ART boot image.

Valid --target= values (Phase 1: ignored — image is atomic):
EOF
    for s in "${BCP_SEGMENTS[@]}"; do echo "  $s"; done
    cat <<EOF

Options:
  --clean             Remove existing boot-image artifacts before regenerating
  --target=<list>     Currently ignored — image generation is atomic.
                      Phase 4 will support per-segment rebuild.
  -j N                Parallel job count (default: $JOBS)
  --dry-run           Print what would be executed, do not run
  --help              Show this help

Notes:
  - Requires build_dex2oat.sh + build_aosp_fw.sh to have completed.
  - Deployment: ALL 27 files must be pushed to device together. The aggregate
    boot.{art,oat,vdex} alone is insufficient — push per-segment files too.
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

if [ ${#TARGETS[@]} -gt 0 ]; then
    log_warn "Phase 1: --target= for boot-image is ignored — full image always regenerated"
fi

log_info "build_boot_image: clean=$CLEAN dry_run=$DRY_RUN jobs=$JOBS"

export OH_FULL_BUILD_INVOKED=1
FORWARD_ARGS=()
[ "$CLEAN" = "1" ] && FORWARD_ARGS+=(--clean)

log_info "Forwarding to gen_boot_image.sh..."
dispatch bash "$SCRIPT_DIR/inner/gen_boot_image.sh" "${FORWARD_ARGS[@]}"

log_ok "build_boot_image complete: 27 segments in out/boot-image/"
log_info "Reminder: deploy ALL segments together (see feedback_boot_image_full_27_deploy.md)"
