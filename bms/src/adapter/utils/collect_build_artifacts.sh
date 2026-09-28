#!/usr/bin/env bash
# ============================================================================
# collect_build_artifacts.sh — copy OH-built system service artifacts into
# adapter/out/oh-service/ so that deploy scripts and generation provenance can
# treat them as first-class adapter artifacts.
#
# Usage:
#   bash utils/collect_build_artifacts.sh [--dry-run]
#
# The authoritative source map lives in build/config.sh (OH_ARTIFACTS).
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../build/config.sh"

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --help|-h)
            echo "Usage: $0 [--dry-run]"
            exit 0
            ;;
        *)
            echo "Unknown arg: $arg" >&2
            exit 1
            ;;
    esac
done

if [ "${BASH_VERSINFO[0]}" -lt 4 ]; then
    echo "ERROR: This script requires bash 4+ for associative arrays." >&2
    exit 1
fi

OH_OUT_DIR=$(detect_oh_output_dir)
DEST_DIR="$ADAPTER_OUT/oh-service"

if [ "$DRY_RUN" -eq 1 ]; then
    log_info() { echo "[DRY-RUN INFO] $*"; }
    log_ok()   { echo "[DRY-RUN OK]   $*"; }
else
    log_info() { echo "[INFO] $*"; }
    log_ok()   { echo "[OK]   $*"; }
fi

log_info "OH output dir: $OH_OUT_DIR"
log_info "Destination:   $DEST_DIR"

if [ "$DRY_RUN" -eq 0 ]; then
    mkdir -p "$DEST_DIR"
fi

errors=0
copied=0
for name in "${!OH_ARTIFACTS[@]}"; do
    rel="${OH_ARTIFACTS[$name]}"
    src="$OH_OUT_DIR/$rel"
    dst="$DEST_DIR/$name"
    if [ ! -f "$src" ]; then
        log_info "SKIP (not built): $name -> $src"
        continue
    fi
    if [ "$DRY_RUN" -eq 1 ]; then
        log_ok "would copy $src -> $dst"
    else
        cp "$src" "$dst"
        log_ok "copied $name"
    fi
    copied=$((copied + 1))
done

log_info "Artifacts processed: $copied"
if [ "$errors" -gt 0 ]; then
    exit 1
fi
