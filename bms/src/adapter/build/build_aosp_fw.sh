#!/bin/bash
# ============================================================================
# build_aosp_fw.sh — AOSP Java framework + BCP jars build entry (Phase 1)
# ============================================================================
#
# Builds AOSP Java/jar artifacts:
#   mainline-stubs.jar          — Mainline module Java stubs
#   oh-adapter-framework.jar    — adapter L5 reflection + compat (BCP jar)
#
# ---------------------------------------------------------------------------
# 2026-07-09 CORRECTNESS FIX (misleading framework.jar dispatch)
# ---------------------------------------------------------------------------
# HISTORICAL BUG: this wrapper advertised framework.jar / core-oj.jar /
# core-icu4j.jar as targets, but the actual dispatch routed them to
# inner/compile_oh_adapter_framework.sh, which ONLY javac/d8/packages
# oh-adapter-framework.jar — it NEVER invokes AOSP Soong to build the real
# framework.jar / core-oj.jar / core-icu4j.jar. Selecting those targets built
# nothing they name and silently produced only the adapter BCP jar.
# (See _codex_handoff/yue_refs/jar_build_provenance.md §"Mixed-source risk 4".)
#
# FIX: those three pure-AOSP Soong jars are now REJECTED by this wrapper (see
# the guard below). Build them from a clean AOSP checkout via Soong, or use the
# manifested fresh wrapper:
#   build/inner/compile_fresh_jars_manifested.sh --with-aosp-soong \
#       --target=framework.jar   (LUNCH_TARGET=<product-variant> required)
#
# Run location: ECS only (uses AOSP Soong + javac + d8).
# Output: out/aosp_fwk/*.jar
#
# CRITICAL: Editing any BCP jar above (especially oh-adapter-framework.jar
# and framework.jar) requires rebuilding the ART boot image, otherwise ART
# rejects mismatched checksums at runtime. This script defaults to
# auto-triggering build_boot_image.sh after a successful BCP jar build.
# Use --no-boot-image to opt out (then you MUST run build_boot_image.sh
# manually before deploying).
#
# Usage:
#   bash build_aosp_fw.sh                                # adapter BCP + mainline + boot-image
#   bash build_aosp_fw.sh --target=oh-adapter-framework.jar   # adapter BCP jar (triggers boot-image)
#   bash build_aosp_fw.sh --target=mainline-stubs.jar         # mainline stubs
#   bash build_aosp_fw.sh --no-boot-image                # skip boot-image
#   bash build_aosp_fw.sh --clean
#
# framework.jar / core-oj.jar / core-icu4j.jar are REJECTED here (Soong-only) —
# see the correctness-fix note above.
# ============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Authorize calls into inner/ (helpers refuse direct invocation)
export BUILD_INNER_INVOKED=1

# Targets this wrapper actually builds (javac/d8 direct — no Soong).
declare -a ALL_TARGETS=(
    "mainline-stubs.jar"
    "oh-adapter-framework.jar"
)

# Pure-AOSP Soong jars this wrapper historically ADVERTISED but never really
# built. Now explicitly rejected (see correctness-fix note in the header).
declare -a REJECTED_SOONG_TARGETS=(
    "framework.jar"
    "core-oj.jar"
    "core-icu4j.jar"
)

# BCP jars — any of these triggers boot-image rebuild. Only oh-adapter-framework.jar
# is a BCP jar produced here (mainline-stubs.jar is non-BCP).
declare -a BCP_TARGETS=(
    "oh-adapter-framework.jar"
)

CLEAN=0
DRY_RUN=0
JOBS=$(nproc 2>/dev/null || echo 4)
TARGETS=()
NO_BOOT_IMAGE=0

dispatch() {
    if [ "$DRY_RUN" = "1" ]; then
        log_info "[DRY-RUN] would: $*"
    else
        "$@"
    fi
}

print_help() {
    cat <<EOF
Usage: $0 [--clean] [--target=<list>] [--no-boot-image] [-j N] [--dry-run] [--help]

Builds AOSP Java jars (framework, core-oj, mainline-stubs, etc.) + adapter
BCP jar (oh-adapter-framework.jar).

Valid --target= values (comma-separated, default: all):
EOF
    for t in "${ALL_TARGETS[@]}"; do
        for b in "${BCP_TARGETS[@]}"; do
            if [ "$t" = "$b" ]; then echo "  $t  [BCP — triggers boot-image]"; continue 2; fi
        done
        echo "  $t"
    done
    cat <<EOF

Options:
  --clean             Clean build artifacts before compiling
  --target=<list>     Comma-separated subset
  --no-boot-image     Skip auto-trigger of build_boot_image.sh (DANGEROUS:
                      device deployment will fail ART checksum if BCP jar
                      changed without matching boot image)
  -j N                Parallel job count (default: $JOBS)
  --dry-run           Print what would be executed, do not run
  --help              Show this help

Notes:
  - oh-adapter-runtime.jar (non-BCP) belongs to build_adapter.sh.
  - Phase 1: oh-adapter-framework.jar build co-produces oh-adapter-runtime.jar
    as side effect (Phase 4 will split).
EOF
}

for arg in "$@"; do
    case "$arg" in
        --clean)            CLEAN=1 ;;
        --no-apply)         NO_APPLY=1 ;;
        --dry-run)          DRY_RUN=1 ;;
        --target=*)         IFS=',' read -ra TARGETS <<< "${arg#--target=}" ;;
        --no-boot-image)    NO_BOOT_IMAGE=1 ;;
        -j*)                JOBS="${arg#-j}" ;;
        --jobs=*)           JOBS="${arg#--jobs=}" ;;
        --help|-h)          print_help; exit 0 ;;
        *)                  log_error "Unknown arg: $arg"; print_help; exit 1 ;;
    esac
done

[ ${#TARGETS[@]} -eq 0 ] && TARGETS=("${ALL_TARGETS[@]}")

for t in "${TARGETS[@]}"; do
    # Reject the misleading Soong-only targets (historical fake dispatch).
    for r in "${REJECTED_SOONG_TARGETS[@]}"; do
        if [ "$t" = "$r" ]; then
            log_error "Target '$t' is a pure-AOSP Soong jar and is NO LONGER accepted here."
            log_error "This wrapper's old dispatch NEVER invoked Soong for it — it only built"
            log_error "oh-adapter-framework.jar under that name (silent mismatch). To build the"
            log_error "real $t, use AOSP Soong from a clean checkout, or:"
            log_error "  build/inner/compile_fresh_jars_manifested.sh --with-aosp-soong --target=$t"
            log_error "  (requires LUNCH_TARGET=<product-variant>)"
            exit 1
        fi
    done
    valid=0
    for v in "${ALL_TARGETS[@]}"; do [ "$t" = "$v" ] && valid=1 && break; done
    if [ "$valid" -eq 0 ]; then
        log_error "Unknown target: $t"
        log_error "Valid targets: ${ALL_TARGETS[*]}"
        exit 1
    fi
done

log_info "build_aosp_fw: targets=${TARGETS[*]} clean=$CLEAN dry_run=$DRY_RUN no_boot_image=$NO_BOOT_IMAGE jobs=$JOBS"

# --- Detect if any selected target is a BCP jar ---
BUILT_BCP=0
for t in "${TARGETS[@]}"; do
    for b in "${BCP_TARGETS[@]}"; do
        if [ "$t" = "$b" ]; then BUILT_BCP=1; break 2; fi
    done
done

export OH_FULL_BUILD_INVOKED=1
FORWARD_ARGS=()
[ "$CLEAN" = "1" ] && FORWARD_ARGS+=(--clean)

# --- Dispatch per target ---
# Phase 1: most AOSP jar targets are co-built by compile_oh_adapter_framework.sh
# (which drives AOSP Soong). Mainline-stubs has a separate path.
NEEDS_AOSP_FW=0
NEEDS_MAINLINE_STUBS=0
for t in "${TARGETS[@]}"; do
    case "$t" in
        framework.jar|core-oj.jar|core-icu4j.jar|oh-adapter-framework.jar)
            NEEDS_AOSP_FW=1 ;;
        mainline-stubs.jar)
            NEEDS_MAINLINE_STUBS=1 ;;
    esac
done

# --- Phase 0: 自动 apply AOSP framework L5 反射注入补丁(build 自包含,原则1) ---
# 两层幂等(sig-marker + 逐 patch reverse-check),已应用则秒跳。framework.jar 等 AOSP
# jar 的 L5 注入(ActivityManager/ActivityTaskManager/ActivityThread/WindowManagerGlobal
# 的 Singleton.create() 反射加载 adapter)必须在编 jar 前落到 AOSP 源。源经 repo sync 清空
# 后本脚本即可自带恢复,不再依赖单独跑 restore_after_sync.sh。--no-apply 跳过。
if [ "${NO_APPLY:-0}" = "1" ]; then
    log_warn "Phase 0 skipped via --no-apply (assuming AOSP source already patched)"
elif [ "$NEEDS_AOSP_FW" = "1" ]; then
    log_info "Phase 0: apply AOSP framework L5 reflection patches (apply_aosp_fwk_patches)"
    source "$SCRIPT_DIR/inner/apply_aosp_fwk_patches.sh"
    apply_aosp_fwk_patches || { log_error "Phase 0: required L5 patches failed (see missing paths above)"; exit 1; }
fi

if [ "$NEEDS_AOSP_FW" = "1" ]; then
    log_info "Dispatching to compile_oh_adapter_framework.sh (AOSP Soong jars)"
    dispatch bash "$SCRIPT_DIR/inner/compile_oh_adapter_framework.sh" "${FORWARD_ARGS[@]}"
fi

if [ "$NEEDS_MAINLINE_STUBS" = "1" ]; then
    log_info "Dispatching to compile_mainline_real.sh (mainline stubs)"
    dispatch bash "$SCRIPT_DIR/inner/compile_mainline_real.sh" "${FORWARD_ARGS[@]}"
fi

log_ok "build_aosp_fw jar build complete: ${TARGETS[*]}"

# --- BCP jar auto-trigger boot-image rebuild ---
if [ "$BUILT_BCP" = "1" ] && [ "$NO_BOOT_IMAGE" = "0" ]; then
    log_warn "BCP jar(s) rebuilt — auto-triggering build_boot_image.sh"
    log_warn "(use --no-boot-image to skip; only safe if you know what you're doing)"
    BOOT_ARGS=()
    [ "$DRY_RUN" = "1" ] && BOOT_ARGS+=(--dry-run)
    dispatch bash "$SCRIPT_DIR/build_boot_image.sh" "${BOOT_ARGS[@]}"
elif [ "$BUILT_BCP" = "1" ] && [ "$NO_BOOT_IMAGE" = "1" ]; then
    log_warn "BCP jar(s) rebuilt but --no-boot-image set — SKIPPING boot-image rebuild"
    log_warn "DEPLOYMENT WILL FAIL on device until you run: bash $SCRIPT_DIR/build_boot_image.sh"
fi

log_ok "build_aosp_fw complete"
