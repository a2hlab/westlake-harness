#!/bin/bash
# Build, sign, and package the aonb_confirm HAP.
# Runs on macOS with DevEco Studio + OpenHarmony SDK installed.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# DevEco toolchain paths. Adjust if your installation differs.
export DEVECO_SDK="${DEVECO_SDK:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony}"
export HVIGORW="${HVIGORW:-/Applications/DevEco-Studio.app/Contents/tools/hvigor/bin/hvigorw}"
export AONB_HAP_SIGN_TOOL="${AONB_HAP_SIGN_TOOL:-$DEVECO_SDK/toolchains/lib/hap-sign-tool.jar}"

if [ -z "${AONB_SIGNING_PASSWORD:-}" ]; then
  echo "ERROR: set AONB_SIGNING_PASSWORD for the ephemeral local signing keystore" >&2
  exit 1
fi

# Hvigor needs a writable SDK tree. /Applications is often read-only due to macOS
# protections, so we clone the SDK to a writable temp location on first build.
WRITABLE_SDK="/tmp/ohos-sdk-mac"
if [ ! -d "$WRITABLE_SDK/23" ]; then
  echo "[build] Cloning SDK to writable location: $WRITABLE_SDK/23"
  mkdir -p "$WRITABLE_SDK"
  cp -cR "$DEVECO_SDK" "$WRITABLE_SDK/23"
fi

# local.properties points hvigor at the writable SDK clone.
cat > local.properties <<EOF
sdk.dir=$WRITABLE_SDK
hwsdk.dir=$WRITABLE_SDK
nodejs.dir=/Applications/DevEco-Studio.app/Contents/tools/node
java.dir=/Applications/DevEco-Studio.app/Contents/jbr/Contents/Home
EOF

echo "[build] Cleaning previous outputs..."
"$HVIGORW" clean --no-daemon

echo "[build] Building unsigned HAP..."
"$HVIGORW" assembleHap -p product=default -p buildMode=debug --no-daemon

echo "[build] Signing HAP with local debug certs..."
cd signing
rm -rf result error.txt log.txt
./create_root.sh
./create_appcert_sign_profile.sh
./sign_hap.sh
cd ..

echo "[build] Copying signed HAP to dist/"
mkdir -p dist
cp signing/result/aonb-confirm-signed.hap "dist/aonb-confirm-default-signed.hap"

echo "[build] Done. Output: dist/aonb-confirm-default-signed.hap"
