#!/usr/bin/env bash
# build-helloworld.sh — one-command signed HAP build for src/apps/apkinstaller (task #30).
# Uses only tools bundled inside /Applications/DevEco-Studio.app; no network access needed.
set -euo pipefail

DEVECO=${DEVECO_HOME:-/Applications/DevEco-Studio.app}
PROJ="$(cd "$(dirname "$0")/../../src/apps/apkinstaller" && pwd)"

export DEVECO_SDK_HOME="$DEVECO/Contents/sdk"
export NODE_HOME="$DEVECO/Contents/tools/node"
export JAVA_HOME="$DEVECO/Contents/jbr/Contents/Home"
export PATH="$JAVA_HOME/bin:$NODE_HOME/bin:$PATH"

# Project-local copies of hvigor + plugin (copied from $DEVECO/Contents/tools/hvigor).
# Refresh them after a DevEco upgrade:
#   rsync -a --delete "$DEVECO/Contents/tools/hvigor/hvigor"                "$PROJ/node_modules/@ohos/"
#   rsync -a --delete "$DEVECO/Contents/tools/hvigor/hvigor-ohos-plugin"    "$PROJ/node_modules/@ohos/"
test -d "$PROJ/node_modules/@ohos/hvigor" || {
  echo "node_modules missing; see docs/guides/devecostudio.md (setup section)" >&2; exit 1; }

cd "$PROJ"
node node_modules/@ohos/hvigor/bin/hvigor.js \
  --mode module -p product=default -p buildMode=debug assembleHap --no-daemon "$@"

HAP="$PROJ/entry/build/default/outputs/default/entry-default-signed.hap"
echo "== signed HAP =="
ls -la "$HAP"
shasum -a 256 "$HAP"
