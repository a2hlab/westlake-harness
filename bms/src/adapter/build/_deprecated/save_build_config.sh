#!/bin/bash
# Save AOSP build configuration and outputs for the OH Adapter project
set -e

BUILD_DIR="/root/adapter/build"
OUT_DIR="/root/adapter/out"
AOSP_DIR="/root/aosp"

echo "=== Saving build configuration ==="

# 1. Custom product config
mkdir -p "$BUILD_DIR/device/adapter/oh_adapter"
cp -v "$AOSP_DIR/device/adapter/oh_adapter/AndroidProducts.mk" "$BUILD_DIR/device/adapter/oh_adapter/"
cp -v "$AOSP_DIR/device/adapter/oh_adapter/oh_adapter.mk" "$BUILD_DIR/device/adapter/oh_adapter/"
cp -v "$AOSP_DIR/device/adapter/oh_adapter/BoardConfig.mk" "$BUILD_DIR/device/adapter/oh_adapter/"

# 2. Generate patches for meaningful AOSP modifications
mkdir -p "$BUILD_DIR/aosp_build_patches"

# frameworks/base modifications (Android.bp, api/, libs/hwui, etc.)
cd "$AOSP_DIR/frameworks/base"
git diff -- Android.bp api/Android.bp api/StubLibraries.bp libs/hwui/Android.bp > "$BUILD_DIR/aosp_build_patches/frameworks_base.patch" 2>/dev/null || true

# art modifications (service-art unsafe_ignore)
cd "$AOSP_DIR/art"
git diff -- libartservice/service/Android.bp > "$BUILD_DIR/aosp_build_patches/art.patch" 2>/dev/null || true

# external/conscrypt modifications
cd "$AOSP_DIR/external/conscrypt"
git diff -- Android.bp > "$BUILD_DIR/aosp_build_patches/external_conscrypt.patch" 2>/dev/null || true

# external/icu modifications
cd "$AOSP_DIR/external/icu"
git diff -- android_icu4j/Android.bp > "$BUILD_DIR/aosp_build_patches/external_icu.patch" 2>/dev/null || true

# packages/modules/common modifications
cd "$AOSP_DIR/packages/modules/common"
git diff -- sdk/ModuleDefaults.bp > "$BUILD_DIR/aosp_build_patches/modules_common.patch" 2>/dev/null || true

# Module java_sdk_library patches (unsafe_ignore_missing_latest_api)
for mod in Bluetooth Connectivity Wifi Media StatsD AdServices Scheduling Virtualization; do
  dir="$AOSP_DIR/packages/modules/$mod"
  if [ -d "$dir" ]; then
    cd "$dir"
    patch=$(git diff -- "*/Android.bp" 2>/dev/null | grep -A2 -B2 unsafe_ignore_missing_latest_api)
    if [ -n "$patch" ]; then
      git diff -- $(find . -name Android.bp -not -path */test* | head -5) > "$BUILD_DIR/aosp_build_patches/modules_${mod}.patch" 2>/dev/null || true
    fi
  fi
done

# Connectivity TetheringLib (cronet stub)
cd "$AOSP_DIR/packages/modules/Connectivity"
git diff -- Tethering/common/TetheringLib/Android.bp > "$BUILD_DIR/aosp_build_patches/modules_Connectivity_tethering.patch" 2>/dev/null || true

# 3. Build environment script
cat > "$BUILD_DIR/build_env.sh" << EOF
#!/bin/bash
# AOSP minimal build environment for OH Adapter project
# Usage: source build_env.sh && build_framework

export ALLOW_MISSING_DEPENDENCIES=true
export BUILD_BROKEN_DISABLE_BAZEL=1

AOSP_DIR="/root/aosp"
ADAPTER_BUILD_DIR="/root/adapter/build"
ADAPTER_OUT_DIR="/root/adapter/out"

setup_env() {
    cd "$AOSP_DIR"
    source build/envsetup.sh 2>/dev/null
    lunch oh_adapter-eng 2>/dev/null
    echo "Build environment ready."
}

build_framework() {
    setup_env
    m framework-minus-apex -j16
    if [ $? -eq 0 ]; then
        echo "=== Copying outputs ==="
        collect_outputs
    fi
}

collect_outputs() {
    mkdir -p "$ADAPTER_OUT_DIR/java" "$ADAPTER_OUT_DIR/native" "$ADAPTER_OUT_DIR/tools"

    # Java outputs
    cp -v "$AOSP_DIR/out/target/product/generic_arm64/system/framework/framework.jar" \
          "$ADAPTER_OUT_DIR/java/" 2>/dev/null

    cp -v "$AOSP_DIR/out/soong/.intermediates/frameworks/base/core/res/framework-res-package-jar/android_common/gen/framework-res-package.jar" \
          "$ADAPTER_OUT_DIR/java/framework-res-package.jar" 2>/dev/null

    # Collect sizes
    echo "=== Build outputs ==="
    ls -lh "$ADAPTER_OUT_DIR/java/"
    echo "=== Done ==="
}

echo "OH Adapter AOSP build environment loaded."
echo "  setup_env       - Initialize build environment"
echo "  build_framework - Build framework-minus-apex and collect outputs"
echo "  collect_outputs - Copy build outputs to $ADAPTER_OUT_DIR"
EOF

# 4. Build instructions
cat > "$BUILD_DIR/README.txt" << EOF
# AOSP Minimal Build for OH Adapter Project
# ==========================================
#
# Prerequisites:
#   - AOSP source at /root/aosp (80+ repos synced)
#   - Custom product at /root/aosp/device/adapter/oh_adapter/
#   - Build patches applied
#
# Quick start:
#   cd /root/aosp
#   source /root/adapter/build/build_env.sh
#   build_framework
#
# Manual build:
#   export ALLOW_MISSING_DEPENDENCIES=true
#   export BUILD_BROKEN_DISABLE_BAZEL=1
#   source build/envsetup.sh
#   lunch oh_adapter-eng
#   m framework-minus-apex -j16
#
# Apply patches (first time only):
#   cd /root/aosp
#   for p in /root/adapter/build/aosp_build_patches/*.patch; do
#     git apply "$p" 2>/dev/null || echo "Patch already applied: $p"
#   done
#
# Output:
#   /root/adapter/out/java/framework.jar   (39MB, client-side framework)
EOF

echo "=== Configuration saved to $BUILD_DIR ==="
ls -la "$BUILD_DIR"

