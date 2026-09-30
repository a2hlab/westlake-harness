#!/bin/bash
# verify_appspawnx_cfg.sh — Gap 7 verification (2026-04-11)
#
# Asserts that appspawn_x.cfg's BOOTCLASSPATH is well-formed and that every jar
# it references is present in the deploy_package. Also asserts that AppSpawnXInit
# is reachable through the listed jars (specifically that oh-adapter-framework.jar
# contains com.android.internal.os.AppSpawnXInit).
#
# Run AFTER prepare_deploy_package.sh, BEFORE deploy_to_dayu200.sh.
#
# Exit codes:
#   0 — verification passed
#   1 — missing jar in deploy_package
#   2 — AppSpawnXInit not found in any BOOTCLASSPATH jar
#   3 — cfg parse error

set -e

ADAPTER_ROOT="${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PKG="${PKG:-$ADAPTER_ROOT/out/deploy_package}"
CFG="${CFG:-$ADAPTER_ROOT/framework/appspawn-x/config/appspawn_x.cfg}"

# Git Bash on Windows: convert /d/code/... to D:/code/... for native python3
to_native() {
    case "$1" in
        /[a-zA-Z]/*) echo "${1:1:1}:/${1:3}" ;;
        *)           echo "$1" ;;
    esac
}
CFG_NATIVE=$(to_native "$CFG")
PKG_NATIVE=$(to_native "$PKG")

echo "============================================"
echo "appspawn_x.cfg verification (gap 7)"
echo "============================================"
echo "  cfg:  $CFG"
echo "  pkg:  $PKG"
echo ""

# Extract BOOTCLASSPATH value (single-line JSON value following "BOOTCLASSPATH")
BOOTCP=$(python3 -c "
import json, sys
with open(r'$CFG_NATIVE') as f:
    cfg = json.load(f)
for svc in cfg.get('services', []):
    for env in svc.get('env', []):
        if env.get('name') == 'BOOTCLASSPATH':
            print(env['value'])
            sys.exit(0)
sys.exit(1)
" 2>/dev/null) || { echo "ERROR: cannot extract BOOTCLASSPATH from cfg ($CFG_NATIVE)"; exit 3; }

if [ -z "$BOOTCP" ]; then
    echo "ERROR: BOOTCLASSPATH is empty"
    exit 3
fi

# Iterate jars
IFS=':' read -ra JARS <<< "$BOOTCP"
echo "BOOTCLASSPATH jars: ${#JARS[@]}"
MISSING=0
HAS_OH_ADAPTER_FWK=0
for jar in "${JARS[@]}"; do
    # device path -> local deploy_package path
    rel="${jar#/system/}"
    local_path="$PKG/system/$rel"
    if [ -f "$local_path" ]; then
        size=$(stat -c%s "$local_path" 2>/dev/null || stat -f%z "$local_path")
        echo "  OK    $jar  ($size bytes)"
        if [ "$(basename $jar)" = "oh-adapter-framework.jar" ]; then
            HAS_OH_ADAPTER_FWK=1
        fi
    else
        echo "  MISS  $jar  (expected at $local_path)"
        MISSING=$((MISSING + 1))
    fi
done

echo ""
if [ "$MISSING" -gt 0 ]; then
    echo "FAIL: $MISSING jar(s) missing from deploy_package"
    echo "      run: bash $ADAPTER_ROOT/build/prepare_deploy_package.sh"
    exit 1
fi

if [ "$HAS_OH_ADAPTER_FWK" = "0" ]; then
    echo "FAIL: oh-adapter-framework.jar is NOT on the BOOTCLASSPATH"
    echo "      AppSpawnXInit class will not be findable at runtime"
    echo "      Edit $CFG to append :/system/android/framework/oh-adapter-framework.jar"
    exit 2
fi

# Verify AppSpawnXInit is in oh-adapter-framework.jar
JAR="$PKG/system/android/framework/oh-adapter-framework.jar"
if [ -f "$JAR" ] && command -v unzip >/dev/null 2>&1; then
    if unzip -l "$JAR" 2>/dev/null | grep -q 'com/android/internal/os/AppSpawnXInit\.class'; then
        echo "OK: AppSpawnXInit.class found in oh-adapter-framework.jar"
    else
        echo "WARN: AppSpawnXInit.class NOT found in $JAR"
        echo "      preload() will not be invoked at appspawn-x startup"
        echo "      Check Android.bp glob 'framework/**/java/**/*.java' includes"
        echo "      framework/appspawn-x/java/com/android/internal/os/AppSpawnXInit.java"
        exit 2
    fi
fi

# Also verify ANDROID_BOOT_IMAGE points to a real file
BOOT_IMAGE=$(python3 -c "
import json
with open(r'$CFG_NATIVE') as f:
    cfg = json.load(f)
for svc in cfg.get('services', []):
    for env in svc.get('env', []):
        if env.get('name') == 'ANDROID_BOOT_IMAGE':
            print(env['value'])
            break
")
if [ -n "$BOOT_IMAGE" ]; then
    rel="${BOOT_IMAGE#/system/}"
    local_path="$PKG/system/$rel"
    if [ -f "$local_path" ]; then
        echo "OK: ANDROID_BOOT_IMAGE -> $local_path"
    else
        echo "WARN: ANDROID_BOOT_IMAGE $BOOT_IMAGE not in deploy_package"
        echo "      run: bash $ADAPTER_ROOT/build/gen_boot_image.sh"
    fi
fi

echo ""
echo "Gap 7 verification: PASS"
echo "============================================"
exit 0
