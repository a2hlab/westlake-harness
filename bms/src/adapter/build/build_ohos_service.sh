#!/bin/bash
# ============================================================================
# build_ohos_service.sh — OH system service .so build entry (Phase 1)
# ============================================================================
#
# Builds OH-tree system service shared libraries that adapter patches:
#   abilityms / libappms / scene_session / scene_session_manager / libbms
# (Phase 4 will expand to all 8 in config.sh OH_SERVICE_TARGETS)
#
# Run location: ECS only.
# Output: ~/oh/out/<product>/<subsystem>/lib*.z.so (collected to out/oh-service/
#         via utils/collect_build_artifacts.sh)
#
# Usage:
#   bash build_ohos_service.sh                          # build all 5 targets
#   bash build_ohos_service.sh --target=libbms          # build one target
#   bash build_ohos_service.sh --target=abilityms,libappms --clean
#   bash build_ohos_service.sh --help
# ============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Authorize calls into inner/ (helpers refuse direct invocation)
export BUILD_INNER_INVOKED=1

# --- Phase 1 target list (subset of config.sh OH_SERVICE_TARGETS) ---
declare -a ALL_TARGETS=(
    "abilityms"
    "mission_list"
    "libappms"
    "scene_session_manager"
    "scene_session"
    "libbms"
)

CLEAN=0
DRY_RUN=0
FAST_REBUILD=1   # default ON: skip full GN gen, reuse build.ninja (hb --fast-rebuild)
JOBS=$(nproc 2>/dev/null || echo 4)
TARGETS=()

print_help() {
    cat <<EOF
Usage: $0 [--clean] [--target=<list>] [-j N] [--dry-run] [--help]

Builds OH system service .so (Phase 1 scope: 5 targets).

Valid --target= values (comma-separated, default: all):
EOF
    for t in "${ALL_TARGETS[@]}"; do echo "  $t"; done
    cat <<EOF

Options:
  --clean             Remove ~/oh/out/$OH_PRODUCT_NAME before building
  --full-gen          Force a full GN gen (PRELOAD/LOAD/gn_gen). Use after any
                      BUILD.gn/.gni/config.gni change. (aliases: --gen, --no-fast)
  --target=<list>     Comma-separated subset of valid targets
  -j N                Parallel job count (default: $JOBS)
  --dry-run           Print what would be executed, do not run
  --help              Show this help

Notes:
  - This script must run on ECS (OH_ROOT=$OH_ROOT).
  - Exports OH_FULL_BUILD_INVOKED=1 to bypass build.sh guard.
  - By DEFAULT this script passes hb --fast-rebuild: it skips the full GN gen
    and reuses out/$OH_PRODUCT_NAME/build.ninja (fast .cpp-only rebuild). It
    auto-falls back to a full gen when the graph is missing or --clean is used.
    Pass --full-gen to force a full gen after any GN-script change.
  - Phase 1: no musl SYS_* auto-retry. If first build hits musl error,
    run: bash $SCRIPT_DIR/inner/musl_syscall_fix.sh && rerun this script.
EOF
}

for arg in "$@"; do
    case "$arg" in
        --clean)        CLEAN=1 ;;
        --full-gen|--gen|--no-fast) FAST_REBUILD=0 ;;
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
    valid=0
    for v in "${ALL_TARGETS[@]}"; do [ "$t" = "$v" ] && valid=1 && break; done
    if [ "$valid" -eq 0 ]; then
        log_error "Unknown target: $t"
        log_error "Valid targets: ${ALL_TARGETS[*]}"
        exit 1
    fi
done

# --- Prerequisite check ---
check_oh_source || exit 2

log_info "build_ohos_service: targets=${TARGETS[*]} clean=$CLEAN dry_run=$DRY_RUN jobs=$JOBS no_apply=${NO_APPLY:-0}"

# --- Phase 0: 自动 apply OH 源补丁(build 自包含,原则1) ---
# 两层幂等:已应用则秒跳(sig-marker + spot-check)。源码经 repo sync 清空后,本脚本即可
# 自带把 OH 源 patch 回可编译状态,不再依赖单独跑 restore_after_sync.sh。
# --no-apply 跳过(适用于"已确认源已 patch、只想纯编译"的场景)。
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

# --- Clean if requested ---
if [ "$CLEAN" = "1" ]; then
    if [ "$DRY_RUN" = "1" ]; then
        log_info "[DRY-RUN] would: rm -rf $OH_ROOT/out/$OH_PRODUCT_NAME"
    else
        log_warn "--clean: removing $OH_ROOT/out/$OH_PRODUCT_NAME"
        rm -rf "$OH_ROOT/out/$OH_PRODUCT_NAME"
    fi
fi

# --- Build target flags ---
TARGET_FLAGS=()
for t in "${TARGETS[@]}"; do
    TARGET_FLAGS+=(--build-target "$t")
done

# --- Fast-rebuild preflight (default: skip full GN gen) ---
# build.sh -> hb build runs PRELOAD/LOAD/gn_gen on every invocation; the gn_gen
# step (enumerating the whole product, hundreds of components) is the slow part.
# hb --fast-rebuild skips prepare/preloader/gn_gen and reuses the existing
# out/<product>/build.ninja, going straight to ninja. We pass --build-target
# explicitly, and ninja consumes it directly (build_args_resolver/ninja.py), so
# it does not depend on the skipped loader output. Default ON because the common
# iteration only edits .cpp; auto-fall back to a full gen when there is no graph
# to reuse (clean tree / first build / --clean), and let --full-gen force it.
GEN_FLAGS=()
NINJA_GRAPH="$OH_ROOT/out/$OH_PRODUCT_NAME/build.ninja"
if [ "$FAST_REBUILD" = "1" ] && [ "$CLEAN" = "1" ]; then
    log_warn "--clean removes the GN graph; forcing a full GN gen this run."
    FAST_REBUILD=0
fi
if [ "$FAST_REBUILD" = "1" ] && [ ! -f "$NINJA_GRAPH" ]; then
    log_warn "No existing GN graph at $NINJA_GRAPH; forcing a full GN gen this run."
    FAST_REBUILD=0
fi
if [ "$FAST_REBUILD" = "1" ]; then
    log_info "Fast mode: reusing $NINJA_GRAPH, skipping full GN gen (hb --fast-rebuild)."
    log_warn "If you changed any BUILD.gn/.gni/config.gni, re-run with --full-gen."
    GEN_FLAGS+=(--fast-rebuild)
else
    log_info "Full mode: running complete GN gen (preloader/loader/gn_gen + ninja)."
fi

# --- Invoke OH build (bypass guard) ---
export OH_FULL_BUILD_INVOKED=1
cd "$OH_ROOT"

if [ "$DRY_RUN" = "1" ]; then
    log_info "[DRY-RUN] would: cd $OH_ROOT && export OH_FULL_BUILD_INVOKED=1 && ./build.sh --product-name $OH_PRODUCT_NAME --ccache --gn-args \"$OH_GN_ARGS\" ${GEN_FLAGS[*]} ${TARGET_FLAGS[*]}"
else
    log_info "Invoking ~/oh/build.sh with ${#TARGETS[@]} target(s)... (fast_rebuild=$FAST_REBUILD)"
    ./build.sh --product-name "$OH_PRODUCT_NAME" --ccache \
        --gn-args "$OH_GN_ARGS" \
        "${GEN_FLAGS[@]}" \
        "${TARGET_FLAGS[@]}"
fi

log_ok "build_ohos_service complete: ${TARGETS[*]}"
log_info "Run 'bash utils/collect_build_artifacts.sh' to copy artifacts to out/oh-service/"
