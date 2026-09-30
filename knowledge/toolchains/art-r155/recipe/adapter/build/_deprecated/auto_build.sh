#!/bin/bash
# Auto-build AOSP with iterative missing-dependency resolution
# Usage: auto_build.sh [--aosp-root=PATH]
AOSP_DIR="${AOSP_ROOT:-/root/aosp}"
for arg in "$@"; do case "$arg" in --aosp-root=*) AOSP_DIR="${arg#*=}";; esac; done
cd "$AOSP_DIR"
MAX_ITER=30
for i in $(seq 1 $MAX_ITER); do
    echo "=== Build attempt $i ==="
    OUTPUT=$(bash -c 'export ALLOW_MISSING_DEPENDENCIES=true; export BUILD_BROKEN_DISABLE_BAZEL=1; source build/envsetup.sh 2>/dev/null; lunch oh_adapter-eng 2>/dev/null; m framework-minus-apex -j16 2>&1')

    # Check success
    if echo "$OUTPUT" | grep -q "build completed successfully"; then
        echo "BUILD SUCCEEDED!"
        echo "$OUTPUT" | tail -5
        break
    fi

    # Check for missing ninja targets
    MISSING=$(echo "$OUTPUT" | grep "missing and no known rule to make it" | head -1 | sed "s/.*ninja: '//;s/', needed.*//")
    if [ -n "$MISSING" ]; then
        echo "Missing ninja target: $MISSING"

        # Extract possible repo name from the missing path
        TOOL_NAME=$(basename "$MISSING" .jar)
        TOOL_NAME=$(echo "$TOOL_NAME" | sed 's/\.so$//')
        echo "  Looking for repo providing: $TOOL_NAME"

        # Search in manifest for matching repos
        REPO=$(grep "path=\"external/$TOOL_NAME\"" .repo/manifests/default.xml | head -1 | grep -o 'path="[^"]*"' | sed 's/path="//;s/"//')
        if [ -z "$REPO" ]; then
            # Try partial match
            REPO=$(grep "$TOOL_NAME" .repo/manifests/default.xml | head -1 | grep -o 'path="[^"]*"' | sed 's/path="//;s/"//')
        fi

        if [ -n "$REPO" ] && [ ! -d "/root/aosp/$REPO" ]; then
            echo "  Syncing: $REPO"
            /usr/local/bin/repo-google sync "$REPO" -c --no-tags -j4 2>&1 | tail -2
            # Clear soong cache
            rm -rf out/soong/build.ninja
        else
            echo "  Cannot auto-resolve: $TOOL_NAME (repo=$REPO)"
            echo "$OUTPUT" | tail -5
            break
        fi
    else
        # Other error
        echo "Build failed with non-ninja error:"
        echo "$OUTPUT" | grep -E "error:|FAILED:" | head -10
        echo "---"
        echo "$OUTPUT" | tail -10
        break
    fi
done
