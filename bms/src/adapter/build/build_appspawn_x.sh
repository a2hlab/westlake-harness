#!/bin/bash
# ============================================================================
# build_appspawn_x.sh — appspawn-x executable build entry (Phase 1)
# ============================================================================
#
# Builds the hybrid spawner daemon that fuses OH appspawn with Android ART JVM
# startup. Loaded by OH init.
#
# Run location: ECS only.
# Legacy diagnostic output: out/adapter/appspawn-x  (executable)
#
# Product builds must use build_l03_a12_arm64_generation.sh.  This wrapper is
# intentionally fail-closed because its shared out/ directory cannot prove a
# same-generation NativeLoader/NativeHelper/runtime closure.
#
# Usage:
#   bash build_appspawn_x.sh                # build appspawn-x
#   bash build_appspawn_x.sh --clean        # clean rebuild
#   bash build_appspawn_x.sh --help
# ============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Fail before loading the legacy build configuration.  Besides being faster,
# this makes the product-policy gate independent of whatever host toolchain the
# obsolete shared-out path happened to require.
case " $* " in
    *" --help "*|*" -h "*) ;;
    *)
        if [ "${WESTLAKE_DIAGNOSTIC_LEGACY_SHARED_OUT:-0}" != "1" ]; then
            echo "ERROR: shared out/ builds are disabled for formal/GroundTruth products" >&2
            echo "ERROR: use build/build_l03_a12_arm64_generation.sh with a new L03_A12_GENERATION_ID and L03_A12_GENERATION_ROOT" >&2
            echo "ERROR: diagnostic-only override: WESTLAKE_DIAGNOSTIC_LEGACY_SHARED_OUT=1 (not ROM eligible)" >&2
            exit 2
        fi
        ;;
esac
source "$SCRIPT_DIR/config.sh"

# Authorize calls into inner/ (helpers refuse direct invocation)
export BUILD_INNER_INVOKED=1

declare -a ALL_TARGETS=("appspawn-x")

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
Usage: $0 [--clean] [--target=appspawn-x] [-j N] [--dry-run] [--help]

Builds the appspawn-x hybrid spawner executable.

Valid --target= values:
  appspawn-x  (only option; arg accepted for uniformity with other build_*.sh)

Options:
  --clean             Clean build artifacts before compiling
  --target=appspawn-x Only target supported (default)
  -j N                Parallel job count (default: $JOBS)
  --dry-run           Print what would be executed, do not run
  --help              Show this help

Notes:
  - Formal/GroundTruth builds must use build_l03_a12_arm64_generation.sh.
  - This shared-out wrapper is disabled by default. For an explicitly
    diagnostic-only build, set WESTLAKE_DIAGNOSTIC_LEGACY_SHARED_OUT=1.
    Its artifacts are never eligible for ROM packaging or acceptance.
  - oh-adapter-runtime.jar (BCP-loaded by appspawn-x at startup) is built by
    build_adapter.sh, not here. The two artifacts must stay version-aligned.
EOF
}

for arg in "$@"; do
    case "$arg" in
        --clean)        CLEAN=1 ;;
        --no-apply)     NO_APPLY=1 ;;
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
    [ "$t" = "appspawn-x" ] || { log_error "Unknown target: $t (only 'appspawn-x' supported)"; exit 1; }
done

# The generation orchestrator invokes the inner compiler directly with private
# output roots.  Keep this legacy public wrapper unavailable by default so a
# filename match in an old shared out/ tree can never become a product input.
log_warn "DIAGNOSTIC ONLY: legacy shared out/ enabled; output is not GroundTruth, ROM, deploy, or acceptance eligible"

log_info "build_appspawn_x: clean=$CLEAN dry_run=$DRY_RUN jobs=$JOBS no_apply=${NO_APPLY:-0}"

# --- Phase 0: 自动 apply OH 源补丁(build 自包含,原则1) ---
# appspawn-x 链接 OH appspawn inner_api,编译依赖 appspawn.h/appspawn_msg.h/appspawn_client
# 等 OH 源补丁(在 apply_ohos_patches 的 42 条清单内)。两层幂等:已应用则秒跳。
# 源经 repo sync 清空后本脚本即可自带恢复,不再依赖单独跑 restore_after_sync.sh。--no-apply 跳过。
if [ "${NO_APPLY:-0}" = "1" ]; then
    log_warn "Phase 0 skipped via --no-apply (assuming OH source already patched)"
else
    log_info "Phase 0: apply OH source patches (apply_ohos_patches)"
    source "$SCRIPT_DIR/inner/apply_ohos_patches.sh"
    if ! apply_ohos_patches; then
        log_error "Phase 0: OH patch application failed; refusing a mixed-generation build"
        exit 3
    fi
fi

# --- Forward to old script ---
export OH_FULL_BUILD_INVOKED=1
# The active product contract is D600/wukong100 only.  Do not let the legacy
# standalone compiler silently select its historical ARM32/rk3568 defaults.
APPSPAWN_TARGET_ARCH="${APPSPAWN_TARGET_ARCH:-arm64}"
OH_PRODUCT_NAME="${OH_PRODUCT_NAME:-wukong100}"
if [ "$APPSPAWN_TARGET_ARCH" != "arm64" ] || [ "$OH_PRODUCT_NAME" != "wukong100" ]; then
    log_error "D600 build requires APPSPAWN_TARGET_ARCH=arm64 and OH_PRODUCT_NAME=wukong100"
    exit 2
fi
export APPSPAWN_TARGET_ARCH OH_PRODUCT_NAME
FORWARD_ARGS=()
[ "$CLEAN" = "1" ] && FORWARD_ARGS+=(--clean)

log_info "Forwarding to compile_appspawnx.sh..."
dispatch bash "$SCRIPT_DIR/inner/compile_appspawnx.sh" "${FORWARD_ARGS[@]}"

log_ok "build_appspawn_x complete"
