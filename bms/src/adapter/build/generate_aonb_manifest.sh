#!/bin/bash
# generate_aonb_manifest.sh - Build-provenance manifest for AonB seamless runtime.
#
# Produces a MANIFEST.yaml compatible with /opt/Bridge/docs/aonb-seamless-definition.md §9.
# The manifest records exact inputs, build command, and artifact hashes so that a
# D600 deployment can be reproduced and independently audited.
#
# Usage:
#   bash build/generate_aonb_manifest.sh [--out-dir=DIR] [--build-command="..."]
#
# Output:
#   <out-dir>/aonb-build-MANIFEST.yaml
#
# Note: this script is intentionally portable (macOS bash 3.2 compatible) and does
# not source config.sh, which uses bash 4 associative arrays.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER_ROOT="${ADAPTER_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
ADAPTER_OUT="${ADAPTER_OUT:-$ADAPTER_ROOT/out}"
OH_ROOT="${OH_ROOT:-$HOME/oh}"
AOSP_ROOT="${AOSP_ROOT:-$HOME/aosp}"
OH_PRODUCT_NAME="${OH_PRODUCT_NAME:-wukong100}"
OH_OUT="${OH_ROOT}/out/${OH_PRODUCT_NAME}"

OUT_DIR="$ADAPTER_OUT"
BUILD_COMMAND=""
REASON="G11-build-provenance"

for arg in "$@"; do
    case "$arg" in
        --out-dir=*) OUT_DIR="${arg#*=}" ;;
        --build-command=*) BUILD_COMMAND="${arg#*=}" ;;
        --reason=*) REASON="${arg#*=}" ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

mkdir -p "$OUT_DIR"

MANIFEST_FILE="$OUT_DIR/aonb-build-MANIFEST.yaml"

# ---------------------------------------------------------------------------
# Helper: best-effort git HEAD and dirty flag for a directory.
# ---------------------------------------------------------------------------
git_info() {
    local dir="$1"
    local name="$2"
    if [ ! -d "$dir/.git" ]; then
        echo "  ${name}_ref: null"
        echo "  ${name}_dirty: unknown"
        return
    fi
    local ref dirty
    ref=$(cd "$dir" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    dirty=$(cd "$dir" && git status --short 2>/dev/null | wc -l | tr -d ' ')
    echo "  ${name}_ref: $ref"
    echo "  ${name}_dirty: $dirty"
}

# ---------------------------------------------------------------------------
# Helper: SHA-256 of a file, or null if missing.
# ---------------------------------------------------------------------------
sha256_or_null() {
    local f="$1"
    if [ -f "$f" ]; then
        if command -v sha256sum >/dev/null 2>&1; then
            sha256sum "$f" | awk '{print $1}'
        elif command -v shasum >/dev/null 2>&1; then
            shasum -a 256 "$f" | awk '{print $1}'
        else
            echo "unsupported"
        fi
    else
        echo "null"
    fi
}

# ---------------------------------------------------------------------------
# Gather data.
# ---------------------------------------------------------------------------
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
HOST_ARCH=$(uname -m)
HOST_OS=$(uname -s)
BUILDER=$(whoami)

# Adapter bridge artifact (primary AonB runtime artifact).
BRIDGE_SO="$ADAPTER_OUT/liboh_adapter_bridge.so"
BRIDGE_SHA=$(sha256_or_null "$BRIDGE_SO")

# Boot image segments (segmented boot image is a G10 artifact).
BOOT_IMAGE_DIR="$ADAPTER_OUT/boot_image"
BOOT_SEGMENTS=()
if [ -d "$BOOT_IMAGE_DIR" ]; then
    while IFS= read -r seg; do
        BOOT_SEGMENTS=("${BOOT_SEGMENTS[@]}" "$seg")
    done < <(find "$BOOT_IMAGE_DIR" -maxdepth 1 -type f -name 'boot-*.art' 2>/dev/null | sort)
fi

# OH service artifacts collected by collect_build_artifacts.sh.
OH_SERVICE_DIR="$ADAPTER_OUT/oh-service"
OH_SERVICE_ARTIFACTS=()
if [ -d "$OH_SERVICE_DIR" ]; then
    while IFS= read -r art; do
        OH_SERVICE_ARTIFACTS=("${OH_SERVICE_ARTIFACTS[@]}" "$art")
    done < <(find "$OH_SERVICE_DIR" -maxdepth 1 -type f \( -name '*.z.so' -o -name 'file_contexts' \) 2>/dev/null | sort)
fi

# ---------------------------------------------------------------------------
# Write YAML.
# ---------------------------------------------------------------------------
{
    echo "# AonB build-provenance manifest"
    echo "# Compatible with /opt/Bridge/docs/aonb-seamless-definition.md §9"
    echo "manifest_kind: aonb-build"
    echo "reason: $REASON"
    echo "timestamp: $TIMESTAMP"
    echo "builder: $BUILDER"
    echo "host:"
    echo "  arch: $HOST_ARCH"
    echo "  os: $HOST_OS"
    echo "environment:"
    echo "  OH_ROOT: ${OH_ROOT:-null}"
    echo "  AOSP_ROOT: ${AOSP_ROOT:-null}"
    echo "  OH_PRODUCT_NAME: ${OH_PRODUCT_NAME:-null}"
    echo "  OH_OUT: $OH_OUT"
    echo "  ADAPTER_ROOT: $ADAPTER_ROOT"
    echo "source_snapshots:"
    git_info "$ADAPTER_ROOT" adapter
    git_info "$OH_ROOT" ohos
    git_info "$AOSP_ROOT" aosp
    echo "build_command: ${BUILD_COMMAND:-null}"
    echo "primary_artifact:"
    echo "  path: ${BRIDGE_SO#$ADAPTER_ROOT/}"
    echo "  sha256: $BRIDGE_SHA"
    echo "  exists: $( [ -f "$BRIDGE_SO" ] && echo true || echo false )"
    echo "boot_image_segments:"
    if [ ${#BOOT_SEGMENTS[@]} -eq 0 ]; then
        echo "  []"
    else
        for seg in "${BOOT_SEGMENTS[@]}"; do
            seg_name=$(basename "$seg")
            seg_sha=$(sha256_or_null "$seg")
            echo "  - name: $seg_name"
            echo "    sha256: $seg_sha"
        done
    fi
    echo "oh_service_artifacts:"
    if [ ${#OH_SERVICE_ARTIFACTS[@]} -eq 0 ]; then
        echo "  []"
    else
        for art in "${OH_SERVICE_ARTIFACTS[@]}"; do
            art_name=$(basename "$art")
            art_sha=$(sha256_or_null "$art")
            echo "  - name: $art_name"
            echo "    sha256: $art_sha"
        done
    fi
} > "$MANIFEST_FILE"

echo "[INFO] Generated build manifest: $MANIFEST_FILE"
echo "[INFO] Primary artifact: ${BRIDGE_SO#$ADAPTER_ROOT/} ($BRIDGE_SHA)"
