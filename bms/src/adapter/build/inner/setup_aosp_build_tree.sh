#!/bin/bash
# === GUARD: internal helper, do not invoke directly ===
if [ "${BUILD_INNER_INVOKED}" != "1" ]; then
    echo "[GUARD] $(basename "$0") is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc." >&2
    echo "[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 bash $(basename "$0")" >&2
    exit 2
fi
# === END GUARD ===
# setup_aosp_build_tree.sh — AOSP 构建树准备(2026-05-27 由 apply_aosp_patches.sh 改名)
# 多用途(非单纯 patch 应用):product 配置 + build_patches + 禁 Android.bp + CTS/VTS stub。
#
# 4 steps:
#   1. cp custom product config (aosp_patches/device/adapter/oh_adapter → AOSP)
#   2. Apply 16 build patches from aosp_patches/build_patches/*.patch
#      Each .patch uses component-relative headers (--- a/<rel-from-component>).
#      Apply by cd <component-dir> && patch -p1.
#   3. Disable test/non-essential Android.bp files (from disabled_bp_files.txt)
#   4. Create CTS/VTS stub files

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
AOSP_DIR="${AOSP_ROOT:-$HOME/aosp}"
for arg in "$@"; do case "$arg" in --aosp-root=*) AOSP_DIR="${arg#*=}" ;; esac; done

PRODUCT_DIR="$ADAPTER_ROOT/aosp_patches/device/adapter/oh_adapter"
PATCH_DIR="$ADAPTER_ROOT/aosp_patches/build_patches"

echo "=== Step 1: Install custom product ==="
mkdir -p "$AOSP_DIR/device/adapter/oh_adapter"
cp -v "$PRODUCT_DIR/AndroidProducts.mk" "$AOSP_DIR/device/adapter/oh_adapter/"
cp -v "$PRODUCT_DIR/oh_adapter.mk" "$AOSP_DIR/device/adapter/oh_adapter/"
cp -v "$PRODUCT_DIR/BoardConfig.mk" "$AOSP_DIR/device/adapter/oh_adapter/"

echo ""
echo "=== Step 2: Apply build patches from aosp_patches/build_patches/ ==="
APPLIED=0; SKIPPED=0; FAILED=0
for patch in "$PATCH_DIR"/*.patch; do
    name=$(basename "$patch")
    if [ ! -s "$patch" ]; then
        echo "  SKIP (empty): $name"; continue
    fi
    case "$name" in
        art.patch)                          repo_dir="art" ;;
        build_make.patch)                   repo_dir="build/make" ;;
        external_conscrypt.patch)           repo_dir="external/conscrypt" ;;
        external_icu.patch)                 repo_dir="external/icu" ;;
        frameworks_base.patch|frameworks_base_disabled.patch)
                                            repo_dir="frameworks/base" ;;
        modules_AdServices.patch)           repo_dir="packages/modules/AdServices" ;;
        modules_Bluetooth.patch)            repo_dir="packages/modules/Bluetooth" ;;
        modules_common.patch)               repo_dir="packages/modules/common" ;;
        modules_Connectivity.patch|modules_Connectivity_tethering.patch)
                                            repo_dir="packages/modules/Connectivity" ;;
        modules_Media.patch)                repo_dir="packages/modules/Media" ;;
        modules_Scheduling.patch)           repo_dir="packages/modules/Scheduling" ;;
        modules_StatsD.patch)               repo_dir="packages/modules/StatsD" ;;
        modules_Virtualization.patch)       repo_dir="packages/modules/Virtualization" ;;
        modules_Wifi.patch)                 repo_dir="packages/modules/Wifi" ;;
        *)  echo "  SKIP (unknown): $name"; continue ;;
    esac
    target="$AOSP_DIR/$repo_dir"
    if [ ! -d "$target" ]; then
        echo "ERROR: required target missing: $target ($repo_dir)" >&2; exit 1
    fi
    if (cd "$target" && patch --dry-run -R -p1 < "$patch") >/dev/null 2>&1; then
        echo "  SKIP (already applied): $name"
        SKIPPED=$((SKIPPED+1))
    elif (cd "$target" && patch --dry-run -p1 < "$patch") >/dev/null 2>&1; then
        (cd "$target" && patch -p1 --no-backup-if-mismatch < "$patch") >/dev/null
        echo "  APPLY: $name → $repo_dir"
        APPLIED=$((APPLIED+1))
    else
        echo "  FAIL (neither forward nor reverse): $name → $repo_dir"
        FAILED=$((FAILED+1))
    fi
done
echo "  Summary: $APPLIED applied / $SKIPPED skipped / $FAILED failed"

echo ""
echo "=== Step 3: Disable test/non-essential Android.bp files ==="
cd "$AOSP_DIR"
count=0
DISABLED_LIST="$SCRIPT_DIR/disabled_bp_files.txt"
while IFS= read -r f; do
    if [ -f "$f" ]; then
        current=$(head -1 "$f")
        if [ "$current" != "// Disabled" ]; then
            echo "// Disabled" > "$f"
            count=$((count + 1))
        fi
    fi
done < "$DISABLED_LIST"
echo "  Disabled $count Android.bp files"

echo ""
echo "=== Step 4: Create CTS stub files ==="
mkdir -p "$AOSP_DIR/cts/tests/tests/os/assets"
echo "14" > "$AOSP_DIR/cts/tests/tests/os/assets/platform_versions.txt"
echo "14" > "$AOSP_DIR/cts/tests/tests/os/assets/platform_releases.txt"
mkdir -p "$AOSP_DIR/cts/build" "$AOSP_DIR/test/suite_harness/tools/cts-instant-tradefed/build" "$AOSP_DIR/test/vts/tools/vts-core-tradefed/build" "$AOSP_DIR/test/cts-root/tools/build" "$AOSP_DIR/test/wvts/tools/build"
for d in cts/build test/suite_harness/tools/cts-instant-tradefed/build test/vts/tools/vts-core-tradefed/build test/cts-root/tools/build test/wvts/tools/build; do
    touch "$AOSP_DIR/$d/config.mk"
done
echo "  CTS/VTS stubs created"

echo ""
echo "=== All AOSP patches applied. ==="
