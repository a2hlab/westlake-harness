#!/bin/bash
# AOSP minimal build environment for OH Adapter project
# Usage: source build/build_env.sh && build_framework
#
# Override paths via env vars:
#   AOSP_ROOT=/path/to/aosp ADAPTER_ROOT=/path/to/adapter source build/build_env.sh

export ALLOW_MISSING_DEPENDENCIES=true
export BUILD_BROKEN_DISABLE_BAZEL=1

AOSP_DIR="${AOSP_ROOT:-/root/aosp}"
ADAPTER_OUT_DIR="${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd || echo /root/adapter)}/out"

setup_env() {
    cd "$AOSP_DIR"
    source build/envsetup.sh 2>/dev/null
    lunch oh_adapter-eng 2>/dev/null
    echo "Build environment ready. Target: oh_adapter-eng"
}

build_framework() {
    setup_env
    echo "Building framework-minus-apex..."
    m framework-minus-apex -j16
    if [ $? -eq 0 ]; then
        echo "=== Build succeeded, collecting outputs ==="
        collect_outputs
    else
        echo "=== Build failed ==="
        return 1
    fi
}

build_all() {
    setup_env
    echo "Building all adapter targets..."
    m framework-minus-apex framework-res libandroid_runtime dex2oat -j16
    if [ $? -eq 0 ]; then
        echo "=== Build succeeded, collecting outputs ==="
        collect_outputs
    fi
}

collect_outputs() {
    mkdir -p "$ADAPTER_OUT_DIR/java" "$ADAPTER_OUT_DIR/native" "$ADAPTER_OUT_DIR/tools" "$ADAPTER_OUT_DIR/res"

    # Java outputs
    cp -v "$AOSP_DIR/out/target/product/generic_arm64/system/framework/framework.jar" \
          "$ADAPTER_OUT_DIR/java/" 2>/dev/null || true

    cp -v "$AOSP_DIR/out/soong/.intermediates/frameworks/base/framework-minus-apex/android_common/dex/classes.dex.jar" \
          "$ADAPTER_OUT_DIR/java/framework-classes.dex.jar" 2>/dev/null || true

    # Resource outputs
    cp -v "$AOSP_DIR/out/soong/.intermediates/frameworks/base/core/res/framework-res-package-jar/android_common/gen/framework-res-package.jar" \
          "$ADAPTER_OUT_DIR/res/" 2>/dev/null || true

    echo ""
    echo "=== Build outputs ==="
    ls -lh "$ADAPTER_OUT_DIR/java/" "$ADAPTER_OUT_DIR/res/" 2>/dev/null
}

echo "OH Adapter AOSP build environment loaded."
echo "Commands:"
echo "  setup_env       - Initialize build environment"
echo "  build_framework - Build framework-minus-apex and collect outputs"
echo "  build_all       - Build all targets (framework + res + runtime + dex2oat)"
echo "  collect_outputs - Copy build outputs to $ADAPTER_OUT_DIR"
