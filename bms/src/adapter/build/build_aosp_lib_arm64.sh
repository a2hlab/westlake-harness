#!/bin/bash
# ============================================================================
# build_aosp_lib_arm64.sh — AOSP native ARM64 (aarch64-linux-ohos / musl)
# cross-compile entry, modeled on build_aosp_lib.sh target dispatch.
# ============================================================================
#
# Cross-compiles AOSP native .so for OH/musl ARM64 (D600/wukong100) from the
# AOSP source tree, via build/inner/cross_compile_arm64.sh.
#
# Output: out/aosp_lib64/*.so (23 libraries, incl. libart.so)
#
# Underlying scripts:
#   compile_app_native_loader_arm64.sh — libapp_native_loader.so (strict link
#       edge required by libnativeloader + Profile B gate)
#   inner/cross_compile_arm64.sh       — all 23 .so co-built in one shot
#
# Phase 1 limitation (same as arm32): cross_compile_arm64.sh has no per-target
# selection internally; selecting any of its 23 .so triggers the whole stack.
# Incremental .o caching in $AOSP_OBJ_DIR makes repeat runs cheap.
#
# Minimal env (all have working defaults on AlexPC):
#   OH_ROOT   (default /opt/build-trees/oh610_lts_source)
#   AOSP_ROOT (default /opt/build-trees/aosp-arm64-d600)
# Optional overrides:
#   AOSP_OUT_DIR (default $ADAPTER_ROOT/out/aosp_lib64)
#   AOSP_OBJ_DIR (default $ADAPTER_ROOT/out/.obj_aosp_lib64 — NOT shared /tmp/cc100)
#   AOSP_BUILD_ERROR_LOG, L03_A12_STRICT_BUILD (default 1), BUILD_NJOBS
#
# Usage:
#   bash build/build_aosp_lib_arm64.sh                      # all
#   bash build/build_aosp_lib_arm64.sh --target=libart.so   # triggers full stack
#   bash build/build_aosp_lib_arm64.sh --clean              # wipe obj dir first
# ============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# AlexPC local trees (override via env or --oh-root=/--aosp-root=).
# Must be set BEFORE sourcing config.sh, which pins $HOME/oh otherwise.
OH_ROOT="${OH_ROOT:-/opt/build-trees/oh610_lts_source}"
AOSP_ROOT="${AOSP_ROOT:-/opt/build-trees/aosp-arm64-d600}"
export OH_ROOT AOSP_ROOT

source "$SCRIPT_DIR/config.sh"

# Generation-style strict link (-z defs + soname + Profile B gate). This is the
# configuration L03.A12 validated; set L03_A12_STRICT_BUILD=0 for legacy mode.
export L03_A12_STRICT_BUILD="${L03_A12_STRICT_BUILD:-1}"

# A generation build must own every writable path; keep the same discipline
# here so two runs never share /tmp/cc100 objects.
export AOSP_OUT_DIR="${AOSP_OUT_DIR:-$ADAPTER_ROOT/out/aosp_lib64}"
export AOSP_OBJ_DIR="${AOSP_OBJ_DIR:-$ADAPTER_ROOT/out/.obj_aosp_lib64}"
export AOSP_BUILD_ERROR_LOG="${AOSP_BUILD_ERROR_LOG:-$ADAPTER_ROOT/out/build_errors_arm64.log}"

# OH toolchain (same defaults cross_compile_arm64.sh would derive from OH_ROOT)
OH_LLVM="$OH_ROOT/prebuilts/clang/ohos/linux-x86_64/llvm"
OH_MUSL_ROOT="$OH_ROOT/out/wukong100/obj/third_party/musl"

# The inner script's default libc++ include (include/c++/v1) lacks the
# generated __config_site on this OH version; the complete target tree is
# libcxx-ohos (same tree the L03.A12 generation pins via L03_A12_LIBCXX_INCLUDE).
export L03_A12_LIBCXX_INCLUDE="${L03_A12_LIBCXX_INCLUDE:-$OH_LLVM/include/libcxx-ohos/include/c++/v1}"

# Authorize calls into inner/ (helpers refuse direct invocation)
export BUILD_INNER_INVOKED=1

# Map: target → which underlying script handles it (informational; dispatch)
declare -a ANL_TARGETS=("libapp_native_loader.so")
declare -a ARM64_TARGETS=(
    "libart.so" "libart-compiler.so" "libartbase.so" "libdexfile.so"
    "libartpalette.so" "libartpalette-system.so" "libsigchain.so"
    "libnativeloader.so" "libnativebridge.so" "libelffile.so" "libprofile.so"
    "libvixl.so" "liblz4.so" "liblzma.so" "libziparchive.so" "libtinyxml2.so"
    "libunwindstack.so"
    "libbase.so" "libutils.so" "libcutils.so" "libnativehelper.so" "liblog.so"
    "libbionic_compat.so"
)

declare -a ALL_TARGETS=(
    "${ANL_TARGETS[@]}"
    "${ARM64_TARGETS[@]}"
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

Cross-compiles AOSP native .so for OH/musl ARM64 (D600/wukong100).

Valid --target= values (comma-separated, default: all):

  [app-native-loader — granular]
    libapp_native_loader.so

  [arm64 stack — 23 .so co-built in one shot]
    libart.so / libart-compiler.so / libartbase.so / libdexfile.so /
    libsigchain.so / libnativeloader.so / libunwindstack.so / ...
    (full list: see ARM64_TARGETS in this script's source)

Options:
  --clean             Wipe \$AOSP_OBJ_DIR before compiling (full rebuild)
  --target=<list>     Comma-separated subset (default: all)
  -j N                Parallel job count (default: $JOBS)
  --oh-root=PATH      OH source root (default: $OH_ROOT)
  --aosp-root=PATH    AOSP source root (default: $AOSP_ROOT)
  --dry-run           Print what would be executed, do not run
  --help              Show this help

Notes:
  - Phase 1: the arm64 stack is co-built (can't pick a subset within the
    group). Selecting any member triggers the full stack build; incremental
    .o caching in \$AOSP_OBJ_DIR keeps repeats cheap.
  - Strict mode (L03_A12_STRICT_BUILD=1, default) requires
    libapp_native_loader.so in \$AOSP_OUT_DIR before the stack links
    libnativeloader; this script builds it first automatically.
  - STRICT failure semantics: any compile/link FAIL removes that .so from
    \$AOSP_OUT_DIR (never ships silent-partial).
EOF
}

for arg in "$@"; do
    case "$arg" in
        --clean)        CLEAN=1 ;;
        --dry-run)      DRY_RUN=1 ;;
        --target=*)     IFS=',' read -ra TARGETS <<< "${arg#--target=}" ;;
        -j*)            JOBS="${arg#-j}" ;;
        --jobs=*)       JOBS="${arg#--jobs=}" ;;
        --oh-root=*)    OH_ROOT="${arg#*=}"; export OH_ROOT ;;
        --aosp-root=*)  AOSP_ROOT="${arg#*=}"; export AOSP_ROOT ;;
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

# --- Prerequisite checks (fail fast with exact missing path) ---
[ -d "$OH_ROOT/out/wukong100" ] || { log_error "OH build output missing: $OH_ROOT/out/wukong100"; exit 1; }
[ -d "$OH_MUSL_ROOT/usr" ] || { log_error "musl sysroot missing: $OH_MUSL_ROOT/usr"; exit 1; }
[ -x "$OH_LLVM/bin/clang++" ] || { log_error "OH clang missing: $OH_LLVM/bin/clang++"; exit 1; }
[ -d "$AOSP_ROOT/art" ] || { log_error "AOSP source missing: $AOSP_ROOT/art"; exit 1; }

log_info "build_aosp_lib_arm64: targets=${TARGETS[*]} clean=$CLEAN dry_run=$DRY_RUN jobs=$JOBS"
log_info "  OH_ROOT=$OH_ROOT"
log_info "  AOSP_ROOT=$AOSP_ROOT"
log_info "  AOSP_OUT_DIR=$AOSP_OUT_DIR"
log_info "  AOSP_OBJ_DIR=$AOSP_OBJ_DIR"
log_info "  strict=$L03_A12_STRICT_BUILD"

# --- Figure out which underlying scripts to invoke ---
NEEDS_ANL=0
NEEDS_ARM64=0
for t in "${TARGETS[@]}"; do
    for a in "${ANL_TARGETS[@]}"; do [ "$t" = "$a" ] && NEEDS_ANL=1; done
    for s in "${ARM64_TARGETS[@]}"; do [ "$t" = "$s" ] && NEEDS_ARM64=1; done
done
# Strict stack link needs libapp_native_loader.so present in $AOSP_OUT_DIR.
if [ "$NEEDS_ARM64" = "1" ] && [ "$L03_A12_STRICT_BUILD" = "1" ]; then
    NEEDS_ANL=1
fi

# --- Phase 1: libapp_native_loader.so (strict link edge for libnativeloader) ---
if [ "$NEEDS_ANL" = "1" ]; then
    log_info "Dispatching to compile_app_native_loader_arm64.sh (libapp_native_loader.so)"
    dispatch env \
        ANL_OUT_DIR="$AOSP_OUT_DIR" \
        ANL_FIXTURE_OUT_DIR="${ANL_FIXTURE_OUT_DIR:-$ADAPTER_ROOT/out/app_native_loader_fixture_arm64}" \
        OH_CC="$OH_LLVM/bin/clang" \
        OH_READELF="$OH_LLVM/bin/llvm-readelf" \
        OH_SYSROOT="$OH_MUSL_ROOT" \
        bash "$SCRIPT_DIR/compile_app_native_loader_arm64.sh"
fi

# --- Phase 2: arm64 AOSP stack (23 .so co-built, libart.so included) ---
if [ "$NEEDS_ARM64" = "1" ]; then
    log_info "Dispatching to cross_compile_arm64.sh (23 .so co-built)"
    FORWARD_ARGS=()
    [ "$CLEAN" = "1" ] && FORWARD_ARGS+=(--clean)
    dispatch env BUILD_NJOBS="$JOBS" \
        bash "$SCRIPT_DIR/inner/cross_compile_arm64.sh" "${FORWARD_ARGS[@]}"
fi

log_ok "build_aosp_lib_arm64 complete: ${TARGETS[*]}"
