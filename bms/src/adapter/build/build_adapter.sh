#!/bin/bash
# ============================================================================
# build_adapter.sh — Adapter native + non-BCP Java build entry (Phase 1)
# ============================================================================
#
# Builds adapter project's own artifacts:
#   liboh_adapter_bridge.so     — JNI bridge to OH IPC ([BRIDGED] methods)
#   liboh_android_runtime.so    — trimmed AOSP libandroid_runtime
#   libapk_installer.so         — APK unpacking + dex2oat delegation
#   oh-adapter-runtime.jar      — non-BCP runtime jar (loaded by appspawn-x)
#
# NOT in scope (intentional):
#   oh-adapter-framework.jar    — BCP jar, built by build_aosp_fw.sh
#                                 (changing it requires boot-image rebuild)
#
# Run location: ECS only.
# Output: out/adapter/{liboh_adapter_bridge,liboh_android_runtime,
#                     libapk_installer}.so + out/adapter/oh-adapter-runtime.jar
#
# Usage:
#   bash build_adapter.sh                                          # all 4
#   bash build_adapter.sh --target=liboh_adapter_bridge.so
#   bash build_adapter.sh --target=libapk_installer.so,oh-adapter-runtime.jar
#   bash build_adapter.sh --clean
# ============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Authorize calls into inner/ (helpers refuse direct invocation)
export BUILD_INNER_INVOKED=1

declare -a ALL_TARGETS=(
    "liboh_adapter_bridge.so"
    "liboh_android_runtime.so"
    "libapk_installer.so"
    "oh-adapter-framework.jar"
    "oh-adapter-runtime.jar"
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

Builds adapter's own native .so + non-BCP runtime jar.

Valid --target= values (comma-separated, default: all):
EOF
    for t in "${ALL_TARGETS[@]}"; do echo "  $t"; done
    cat <<EOF

Options:
  --clean             Clean build artifacts before compiling
  --target=<list>     Comma-separated subset
  -j N                Parallel job count (default: $JOBS)
  --dry-run           Print what would be executed, do not run
  --help              Show this help

Notes:
  - 2026-05-25: each adapter jar dispatches to its own builder —
    oh-adapter-framework.jar (BCP)     -> inner/compile_oh_adapter_framework.sh,
    oh-adapter-runtime.jar (non-BCP)   -> inner/compile_oh_adapter_runtime.sh
    (moved back from build/_deprecated/ to build/inner/).
  - oh-adapter-framework.jar is also built by build_aosp_fw.sh (same builder).
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
        log_error "Valid targets: ${ALL_TARGETS[*]}"
        exit 1
    fi
done

log_info "build_adapter: targets=${TARGETS[*]} clean=$CLEAN dry_run=$DRY_RUN jobs=$JOBS no_apply=${NO_APPLY:-0}"

# --- Phase 0: 自动 apply OH 源补丁(build 自包含,原则1) ---
# adapter 自有 .so(liboh_adapter_bridge / liboh_android_runtime / libapk_installer)链接
# OH inner_api,编译依赖打过补丁的 OH 源(如 application_info.h 的 BundleType::APP_ANDROID)。
# 两层幂等:已应用则秒跳。源经 repo sync 清空后本脚本即可自带恢复。--no-apply 跳过。
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

export OH_FULL_BUILD_INVOKED=1
FORWARD_ARGS=()
[ "$CLEAN" = "1" ] && FORWARD_ARGS+=(--clean)

# --- Dispatch per target ---
for t in "${TARGETS[@]}"; do
    case "$t" in
        liboh_adapter_bridge.so)
            log_info "[$t] dispatching to compile_oh_adapter_bridge.sh"
            dispatch bash "$SCRIPT_DIR/inner/compile_oh_adapter_bridge.sh" "${FORWARD_ARGS[@]}"
            ;;
        liboh_android_runtime.so)
            log_info "[$t] dispatching to compile_oh_android_runtime.sh"
            dispatch bash "$SCRIPT_DIR/inner/compile_oh_android_runtime.sh" "${FORWARD_ARGS[@]}"
            ;;
        libapk_installer.so)
            log_info "[$t] dispatching to compile_apk_installer.sh"
            dispatch bash "$SCRIPT_DIR/inner/compile_apk_installer.sh" "${FORWARD_ARGS[@]}"
            ;;
        oh-adapter-framework.jar)
            log_info "[$t] dispatching to compile_oh_adapter_framework.sh"
            dispatch bash "$SCRIPT_DIR/inner/compile_oh_adapter_framework.sh" "${FORWARD_ARGS[@]}"
            ;;
        oh-adapter-runtime.jar)
            log_info "[$t] dispatching to compile_oh_adapter_runtime.sh"
            dispatch bash "$SCRIPT_DIR/inner/compile_oh_adapter_runtime.sh" "${FORWARD_ARGS[@]}"
            ;;
    esac
done

log_ok "build_adapter complete: ${TARGETS[*]}"
