#!/bin/bash
# ============================================================================
# build_aosp_lib.sh — AOSP native ARM32 cross-compile entry (Phase 1)
# ============================================================================
#
# Cross-compiles AOSP native .so for OH/musl on ARM32 (DAYU200).
#
# Run location: ECS only.
# Output: out/aosp_lib/*.so (25+ libraries)
#
# Underlying scripts (Phase 1 dispatches):
#   compile_libhwui.sh             — libhwui.so (5-phase pipeline)
#   cross_compile_minikin_stack.sh — libft2/libharfbuzz_ng/libminikin (co-built)
#   cross_compile_arm32.sh         — all other 22+ .so (co-built in one shot)
#
# Phase 1 limitation:
#   - cross_compile_arm32.sh has no per-target selection internally; selecting
#     any of its 22 .so triggers all 22. Phase 4 will granularize.
#   - cross_compile_minikin_stack.sh similarly co-builds 3 .so.
#
# Usage:
#   bash build_aosp_lib.sh                          # all
#   bash build_aosp_lib.sh --target=libhwui.so      # only libhwui
#   bash build_aosp_lib.sh --target=libart.so       # triggers all 22 arm32 .so
#   bash build_aosp_lib.sh --clean
# ============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Authorize calls into inner/ (helpers refuse direct invocation)
export BUILD_INNER_INVOKED=1

# Map: target → which underlying script handles it
# (Phase 1: this is informational; user selects target, we dispatch)
declare -a LIBHWUI_TARGETS=("libhwui.so")
declare -a MINIKIN_TARGETS=("libft2.so" "libharfbuzz_ng.so" "libminikin.so")
declare -a ARM32_TARGETS=(
    "libart.so" "libartbase.so" "libdexfile.so" "libartpalette.so"
    "libartpalette-system.so" "libsigchain.so" "libnativeloader.so"
    "libnativebridge.so" "libelffile.so" "libprofile.so" "libopenjdk.so"
    "libvixl.so" "liblz4.so" "libziparchive.so" "libexpat.so"
    "libbase.so" "libutils.so" "libcutils.so" "libnativehelper.so" "liblog.so"
    "libandroidfw.so" "libicu_jni.so" "libicui18n.so" "libicuuc.so"
    "libjavacore.so" "libcrypto.so" "libandroidio.so"
    "libbionic_compat.so" "libart_runtime_stubs.so"
)

declare -a ALL_TARGETS=(
    "${LIBHWUI_TARGETS[@]}"
    "${MINIKIN_TARGETS[@]}"
    "${ARM32_TARGETS[@]}"
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

Cross-compiles AOSP native .so for OH/musl ARM32 (DAYU200).

Valid --target= values (comma-separated, default: all):

  [libhwui group — granular]
    libhwui.so

  [minikin group — co-built]
    libft2.so / libharfbuzz_ng.so / libminikin.so

  [arm32 stack — 22+ .so co-built in one shot]
    libart.so / libartbase.so / libdexfile.so / libbase.so / libutils.so /
    libcutils.so / libandroidfw.so / libicuuc.so / libicui18n.so / ...
    (full list: see ARM32_TARGETS in this script's source)

Options:
  --clean             Clean build artifacts before compiling
  --target=<list>     Comma-separated subset (default: all)
  -j N                Parallel job count (default: $JOBS)
  --dry-run           Print what would be executed, do not run
  --help              Show this help

Notes:
  - Phase 1: minikin/arm32 groups are co-built (can't pick subset within group).
    Selecting any member triggers full group build. Phase 4 will granularize.
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
    valid=0
    for v in "${ALL_TARGETS[@]}"; do [ "$t" = "$v" ] && valid=1 && break; done
    if [ "$valid" -eq 0 ]; then
        log_error "Unknown target: $t"
        log_error "Use --help to see valid targets"
        exit 1
    fi
done

log_info "build_aosp_lib: targets=${TARGETS[*]} clean=$CLEAN dry_run=$DRY_RUN jobs=$JOBS"

# --- Figure out which underlying scripts to invoke ---
NEEDS_HWUI=0
NEEDS_MINIKIN=0
NEEDS_ARM32=0
for t in "${TARGETS[@]}"; do
    for h in "${LIBHWUI_TARGETS[@]}"; do [ "$t" = "$h" ] && NEEDS_HWUI=1; done
    for m in "${MINIKIN_TARGETS[@]}"; do [ "$t" = "$m" ] && NEEDS_MINIKIN=1; done
    for a in "${ARM32_TARGETS[@]}"; do [ "$t" = "$a" ] && NEEDS_ARM32=1; done
done

# --- Phase 0: 自动 apply AOSP 源补丁(build 自包含,原则1;按 target 选组件,原则3) ---
# 两层幂等(sig-marker + 逐 patch reverse-check),已应用则秒跳。源经 repo sync 清空后,
# 本脚本即可自带把 AOSP 源 patch 回可编译状态,不再依赖单独跑 restore_after_sync.sh。
# 仅 apply 当前 target 真正用到的组件:NEEDS_HWUI→hwui 源补丁;NEEDS_ARM32→art 交叉编译
# 补丁 + libandroidfw modern-API + icu/AndroidRuntime/Process。--no-apply 跳过。
if [ "${NO_APPLY:-0}" = "1" ]; then
    log_warn "Phase 0 skipped via --no-apply (assuming AOSP source already patched)"
else
    if [ "$NEEDS_HWUI" = "1" ]; then
        log_info "Phase 0: apply hwui source patches (apply_hwui_patches)"
        source "$SCRIPT_DIR/inner/apply_hwui_patches.sh"
        apply_hwui_patches || log_warn "Phase 0: some hwui patches failed (see above)"
    fi
    if [ "$NEEDS_ARM32" = "1" ]; then
        log_info "Phase 0: apply AOSP native patches (art + libandroidfw + jni-compat)"
        source "$SCRIPT_DIR/inner/apply_aosp_native_patches.sh"
        apply_aosp_native_patches       || log_warn "Phase 0: some art patches failed (see above)"
        apply_aosp_libandroidfw_patches || log_warn "Phase 0: some libandroidfw patches failed (see above)"
        apply_aosp_jni_compat_patches   || log_warn "Phase 0: some jni-compat patches failed (see above)"
    fi
fi

export OH_FULL_BUILD_INVOKED=1
FORWARD_ARGS=()
[ "$CLEAN" = "1" ] && FORWARD_ARGS+=(--clean)

# arm32 must run before hwui (hwui depends on libbase/libutils/libandroidfw/etc.)
if [ "$NEEDS_ARM32" = "1" ]; then
    log_info "Dispatching to cross_compile_arm32.sh (22+ .so co-built)"
    dispatch bash "$SCRIPT_DIR/inner/cross_compile_arm32.sh" "${FORWARD_ARGS[@]}"
fi

if [ "$NEEDS_MINIKIN" = "1" ]; then
    log_info "Dispatching to cross_compile_minikin_stack.sh (3 .so co-built)"
    dispatch bash "$SCRIPT_DIR/inner/cross_compile_minikin_stack.sh" "${FORWARD_ARGS[@]}"
fi

if [ "$NEEDS_HWUI" = "1" ]; then
    log_info "Dispatching to compile_libhwui.sh (5-phase pipeline)"
    dispatch bash "$SCRIPT_DIR/inner/compile_libhwui.sh" --phase=1,2,3,4
fi

log_ok "build_aosp_lib complete: ${TARGETS[*]}"
