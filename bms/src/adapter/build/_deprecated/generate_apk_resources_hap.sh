#!/bin/bash
# generate_apk_resources_hap.sh
#
# Synthesize a minimal OH "resources HAP" for an Android APK so that OH
# launcher's ResourceManager.getMediaBase64(iconId) resolves to the APK's
# launcher icon PNG.
#
# Inputs:
#   $1 = APK package name (e.g., com.example.helloworld)
#   $2 = APK launcher icon PNG path on host (e.g., out/app/hello_icon.png)
#   $3 = Output directory (e.g., out/app/, will produce <pkg>_resources.hap)
#
# Output:
#   <output_dir>/<pkg>_resources.hap (≈51KB ZIP of module.json + resources.index + resources/base/media/icon.png)
#
# Required runtime side (push to device):
#   1. <pkg>_resources.hap → /system/app/<pkg>/entry.hap (system_file SELinux label)
#      (libbms register patch handles cp from /data/local/tmp/<pkg>_resources.hap)
#
# After this script, the iconId used in InnerBundleInfo registration is FIXED:
#   ability iconId = 0x01000005 (MEDIA_ICON, from restool ResourceTable.h)
#   ability labelId = 0x01000003 (STRING_ENTRYABILITY_LABEL)
#   app iconId = 0x01000001 (MEDIA_APP_ICON)
#   app labelId = 0x01000000 (STRING_APP_NAME)
# These are baked into ohos_patches/bundle_framework/services/bundlemgr/apply_bms_apk_register_with_manifest.py
#
# This script is intended to run on ECS (where OH restool is built). For other
# hosts, ensure restool is available at $RESTOOL_PATH or first arg.

set -e

if [ $# -lt 3 ]; then
    echo "Usage: $0 <package_name> <icon_png_path> <output_dir>"
    echo "Example: $0 com.example.helloworld out/app/hello_icon.png out/app"
    exit 1
fi

PKG=$1
ICON_SRC=$2
OUT_DIR=$3

RESTOOL=${RESTOOL_PATH:-/home/HanBingChen/oh/out/rk3568/clang_x64/developtools/global_resource_tool/restool}

if [ ! -x "$RESTOOL" ]; then
    echo "ERROR: restool not found or not executable at $RESTOOL"
    echo "Set RESTOOL_PATH environment variable, or rebuild OH:"
    echo "  cd ~/oh && OH_FULL_BUILD_INVOKED=1 ./build.sh --product-name rk3568 --build-target restool"
    exit 1
fi

if [ ! -f "$ICON_SRC" ]; then
    echo "ERROR: icon PNG not found at $ICON_SRC"
    exit 1
fi

WORK=$(mktemp -d)
trap "rm -rf $WORK" EXIT

mkdir -p "$WORK/AppScope/resources/base/media"
mkdir -p "$WORK/AppScope/resources/base/element"
mkdir -p "$WORK/entry/src/main/resources/base/media"
mkdir -p "$WORK/entry/src/main/resources/base/element"

# Copy the APK icon to both AppScope (app-level) and entry (ability-level)
cp "$ICON_SRC" "$WORK/AppScope/resources/base/media/app_icon.png"
cp "$ICON_SRC" "$WORK/entry/src/main/resources/base/media/icon.png"

# AppScope/app.json (NOT .json5 — restool detects Stage Model only via .json suffix)
cat > "$WORK/AppScope/app.json" << JSON
{
  "app": {
    "bundleName": "$PKG",
    "vendor": "adapter",
    "versionCode": 1,
    "versionName": "1.0",
    "icon": "\$media:app_icon",
    "label": "\$string:app_name"
  }
}
JSON

cat > "$WORK/AppScope/resources/base/element/string.json" << 'JSON'
{"string": [{"name": "app_name", "value": "Hello World"}]}
JSON

cat > "$WORK/entry/src/main/resources/base/element/string.json" << 'JSON'
{
  "string": [
    {"name": "EntryAbility_label", "value": "Hello World"},
    {"name": "module_desc", "value": "adapter module"},
    {"name": "EntryAbility_desc", "value": "main"}
  ]
}
JSON

cat > "$WORK/entry/src/main/module.json" << 'JSON'
{
  "module": {
    "name": "entry",
    "type": "entry",
    "description": "$string:module_desc",
    "mainElement": "EntryAbility",
    "deviceTypes": ["default"],
    "deliveryWithInstall": true,
    "installationFree": false,
    "abilities": [
      {
        "name": "EntryAbility",
        "srcEntry": "./ets/entryability/EntryAbility.ts",
        "description": "$string:EntryAbility_desc",
        "icon": "$media:icon",
        "label": "$string:EntryAbility_label",
        "exported": true,
        "skills": [{"entities": ["entity.system.home"], "actions": ["action.system.home"]}]
      }
    ]
  }
}
JSON

mkdir -p "$WORK/build/header"

"$RESTOOL" \
    -i "$WORK/AppScope" \
    -i "$WORK/entry/src/main" \
    -j "$WORK/entry/src/main/module.json" \
    -p "$PKG" \
    -o "$WORK/build" \
    -r "$WORK/build/header/ResourceTable.h" \
    -f >/dev/null 2>&1

if [ ! -f "$WORK/build/resources.index" ]; then
    echo "ERROR: restool failed to produce resources.index. Re-run without redirect to see error."
    exit 1
fi

# Pack the resources HAP
mkdir -p "$OUT_DIR"
HAP_PATH="$OUT_DIR/${PKG}_resources.hap"
rm -f "$HAP_PATH"
( cd "$WORK/build" && zip -rq "$HAP_PATH" module.json resources.index resources/ )

echo "[OK] $HAP_PATH ($(stat -c '%s' $HAP_PATH) bytes)"
echo "     iconId  = 0x01000005 (ability media:icon)"
echo "     labelId = 0x01000003 (ability string:EntryAbility_label)"
echo
echo "Deploy steps (on device, after libbms.z.so containing register patch is loaded):"
echo "  hdc file send $HAP_PATH /data/local/tmp/${PKG}_resources.hap"
echo "  bm install -p HelloWorld.apk    # libbms patch auto-cps to /system/app/$PKG/entry.hap"
echo "OR pre-stage directly to /system/app/ (no install needed, requires mount remount,rw /):"
echo "  hdc shell 'mount -o remount,rw / && mkdir -p /system/app/$PKG'"
echo "  hdc file send $HAP_PATH /system/app/$PKG/entry.hap"
